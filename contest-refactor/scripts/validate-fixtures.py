#!/usr/bin/env python3
"""Fixture-discipline validator for the contest-refactor skill.

Hard-blocking: exit 0 on success, non-zero on any violation. Imports
`_canon.load_canon()` so enum ownership stays in canon/*.toml.

Checks every `<fixtures-dir>/<id>/fixture.toml`:
- Required fields present + non-empty: `id`, `purpose`, `tested_rules[]`,
  `expected_result`. `notes` is optional.
- `id` matches directory name.
- `expected_result ∈ {pass, fail}`.
- Each `tested_rules[i]` has `kind ∈ canon.fixture_rule_kinds` and an `id`
  that resolves per kind:
    * gate              → id ∈ canon.validation_gates.keys()
    * method-step       → id matches `^<id>\\b` in references/method.md
                          (tolerates "1", "1.5", "1.6", "10", "-1", ...)
    * canon-enum        → id appears in any canon list (states, halt_subtypes,
                          finding_statuses, verdicts, severity_anchors,
                          dependency_categories, retirement_reasons)
    * scorecard-dimension → id ∈ canon.scorecard_dimensions
    * residual-rule     → id ∈ RESIDUAL_RULES (small canonical set)
- Every file the fixture references on disk in CURRENT_REVIEW.json's
  `findings_registry_path` (best-effort) is reachable.
- Negative fixtures (`expected_result: fail`) actually fail
  `validate-artifact.py --mode strict`.
- Positive fixtures (`expected_result: pass`) actually pass it.
- Negative fixtures with gate-kind `tested_rules` must fail for the *cited*
  gate: at least one fired issue's rule must equal the cited gate id or be one
  of its documented sub-rules (`<gate>-<suffix>`, e.g. `G21-scorecard` for
  `G21`; see `_gate_satisfies`). `aspirational = true` marks a citation whose
  gate has no emitting code path yet — the assertion is skipped only in the
  direction of *not yet firing*; if the cited gate ever DOES fire, that is
  itself reported (`aspirational-gate-implemented`) so the flag can't go
  stale silently. `example = true` marks a fixture with no gate-kind
  `tested_rules` at all (e.g. only `method-step`/`canon-enum`) — a
  scenario/documentation fixture with nothing for the cited-gate assertion to
  check; it is an error to combine `example = true` with a gate-kind citation.
- Flag/restraint pairing: every fixture declares either (`pair_id` +
  `pair_role` in {flag, restraint}) or an explicit `pair_exception` reason —
  silence is an error. Each `pair_id` must resolve to exactly one flag and
  exactly one restraint fixture across the whole corpus.

Usage:
    python3 scripts/validate-fixtures.py evals/fixtures/
    python3 scripts/validate-fixtures.py evals/fixtures/ --no-run-artifact-check
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
from collections.abc import Sequence
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import _canon  # type: ignore[import-not-found]  # noqa: E402

SKILL_ROOT = SCRIPT_DIR.parent
REFERENCES_DIR = SKILL_ROOT / "references"
ARTIFACT_VALIDATOR = SCRIPT_DIR / "validate-artifact.py"

REQUIRED_FIXTURE_FIELDS = ("id", "purpose", "tested_rules", "expected_result")
EXPECTED_RESULT_VALUES = {"pass", "fail"}
OPTIONAL_BOOL_FIELDS = ("aspirational", "example")
PAIR_ROLE_VALUES = {"flag", "restraint"}

RESIDUAL_RULES = {
    "9.5-threshold",
    "accepted-residual",
    "queued-residual",
    "expired-residual",
    "terminal-normalization",
}

# --- Fixture storage: materialized final history --------------------------
# G18 (_artifact_history.py:check_g18_review_history_append) requires
# REVIEW_HISTORY.json.loops[-1] to equal CURRENT_REVIEW.json verbatim. Most
# fixtures satisfy this by literally repeating CURRENT_REVIEW.json as their
# last loops[] entry -- hundreds of duplicated lines that must be hand-
# mirrored on every fixture edit. This is a FIXTURE-STORAGE convention only;
# the production artifact contract (a real run's REVIEW_HISTORY.json) is
# unchanged.
#
# A fixture opts in by setting a top-level `"materialize_final_history":
# true` key in its REVIEW_HISTORY.json, alongside storing only the PREFIX
# loops (everything before the current one) in `loops[]` -- `loops: []` for
# a single-loop fixture. `_materialized_fixture()` below then builds a
# throwaway copy of the fixture directory with a parsed copy of
# CURRENT_REVIEW.json appended as the final loops[] entry, and hands that
# copy to validate-artifact.py. Fixtures without the key are used unchanged
# (no copy, no behavior change) -- this is what keeps explicit full
# histories possible for fixtures that deliberately store a NON-matching
# last entry to exercise a G18 failure (`expected_result = "fail"`), and for
# the two `transition-*` fixtures that `_transition_table_selftest.py` reads
# directly off disk (bypassing this script entirely, so they cannot rely on
# materialization and must keep their full explicit `loops[]`).
MATERIALIZE_FINAL_HISTORY_KEY = "materialize_final_history"


class Violation:
    """A single rule failure."""

    __slots__ = ("message", "path", "rule")

    def __init__(self, rule: str, message: str, path: Path | None = None) -> None:
        self.rule = rule
        self.message = message
        self.path = path

    def render(self) -> str:
        prefix = f"[{self.rule}]"
        if self.path is not None:
            try:
                rel = self.path.relative_to(SKILL_ROOT)
            except ValueError:
                rel = self.path
            return f"{prefix} {rel}: {self.message}"
        return f"{prefix} {self.message}"


def _canon_enum_values(canon: _canon.Canon) -> set[str]:
    """Union of every list-shaped canon enum (gate ids are checked separately)."""
    values: set[str] = set()
    values.update(canon.states)
    values.update(canon.halt_subtypes)
    values.update(canon.finding_statuses)
    values.update(canon.verdicts)
    values.update(canon.severity_anchors)
    values.update(canon.dependency_categories)
    values.update(canon.retirement_reasons)
    return values


def _fixture_rule_kinds(canon: _canon.Canon) -> Sequence[str]:
    """Fetch fixture_rule_kinds from canon, falling back to extra mapping."""
    if hasattr(canon, "fixture_rule_kinds"):  # promoted to first-class field
        kinds = canon.fixture_rule_kinds
        if kinds:
            return kinds
    extra = getattr(canon, "extra", {}) or {}
    return extra.get("fixture_rule_kinds", ())


def _load_toml(path: Path) -> Any:
    try:
        with path.open("rb") as fh:
            return tomllib.load(fh)
    except tomllib.TOMLDecodeError as exc:
        raise SystemExit(f"error: {path}: TOML parse failed: {exc}") from exc


_METHOD_STEPS_CACHE: set[str] | None = None


def _method_step_labels() -> set[str]:
    """Extract every ordered-list label from references/method.md.

    Returns labels like "1", "1.5", "1.6", "2", ..., "10". Matches the
    `^<label>\\.` (or `^<label>\\b`) shape the plan specifies. Tolerates
    sub-labels like "1.5" and bare negative labels like "-1" (the plan
    explicitly mentions "-1").
    """
    global _METHOD_STEPS_CACHE
    if _METHOD_STEPS_CACHE is not None:
        return _METHOD_STEPS_CACHE
    path = REFERENCES_DIR / "method.md"
    if not path.exists():
        _METHOD_STEPS_CACHE = set()
        return _METHOD_STEPS_CACHE
    text = path.read_text(encoding="utf-8")
    labels: set[str] = set()
    # Match list items at line start: "<label>." or "<label> " — tolerates
    # negative labels via the optional sign.
    for match in re.finditer(r"^(-?\d+(?:\.\d+)?)[.)\s]", text, flags=re.MULTILINE):
        labels.add(match.group(1))
    _METHOD_STEPS_CACHE = labels
    return _METHOD_STEPS_CACHE


def _validate_tested_rule(rule: Any, canon: _canon.Canon, kinds: Sequence[str]) -> list[str]:
    """Return list of error strings for a single tested_rules[i] entry."""
    errors: list[str] = []
    if not isinstance(rule, dict):
        return ["entry must be a mapping with 'kind' and 'id' keys"]
    kind = rule.get("kind")
    rid = rule.get("id")
    if kind is None:
        errors.append("missing 'kind'")
    elif kind not in kinds:
        errors.append(f"unknown kind {kind!r} (allowed: {sorted(kinds)})")
    if rid is None or (isinstance(rid, str) and not rid.strip()):
        errors.append("missing or empty 'id'")
        return errors
    # Coerce id to string for uniform comparison
    rid_str = str(rid)
    if kind == "gate":
        if rid_str not in canon.validation_gates:
            errors.append(f"unknown gate id {rid_str!r} (not in canon/validation-gates.toml)")
    elif kind == "method-step":
        if rid_str not in _method_step_labels():
            errors.append(
                f"method-step {rid_str!r} not found as an ordered-list label "
                f"in references/method.md"
            )
    elif kind == "canon-enum":
        if rid_str not in _canon_enum_values(canon):
            errors.append(
                f"canon-enum value {rid_str!r} not found in any canon list "
                f"(states/halt_subtypes/finding_statuses/verdicts/severity_anchors/"
                f"dependency_categories/retirement_reasons)"
            )
    elif kind == "scorecard-dimension":
        if rid_str not in canon.scorecard_dimensions:
            errors.append(f"scorecard-dimension {rid_str!r} not in canon/scorecard-dimensions.toml")
    elif kind == "residual-rule" and rid_str not in RESIDUAL_RULES:
        errors.append(f"residual-rule {rid_str!r} not in canonical set {sorted(RESIDUAL_RULES)}")
    return errors


def _validate_pair_fields(
    fixture_dir: Path, data: dict, toml_path: Path
) -> tuple[list[Violation], tuple[str, str] | None]:
    """Check the flag/restraint pairing fields on one fixture.

    Returns (violations, pair_entry). pair_entry is (pair_id, pair_role) when
    the fixture declares a syntactically valid pair_id + pair_role, else None
    (either it's a pair_exception fixture, or the pair fields are malformed
    and already reported below — malformed entries are excluded from the
    cross-fixture cardinality check rather than polluting it).
    """
    violations: list[Violation] = []
    has_pair_id = "pair_id" in data
    has_exception = "pair_exception" in data
    if has_pair_id and has_exception:
        violations.append(
            Violation(
                "pair-schema",
                "declares both pair_id and pair_exception; a fixture is either "
                "paired or an exception, not both",
                toml_path,
            )
        )
        return violations, None
    if not has_pair_id and not has_exception:
        violations.append(
            Violation(
                "pair-schema",
                "declares neither pair_id (+ pair_role) nor pair_exception; every "
                "fixture must be paired or an explicit exception",
                toml_path,
            )
        )
        return violations, None
    if has_exception:
        exc = data.get("pair_exception")
        if not isinstance(exc, str) or not exc.strip():
            violations.append(
                Violation(
                    "pair-schema",
                    f"pair_exception must be a non-empty string, got {exc!r}",
                    toml_path,
                )
            )
        return violations, None
    # has_pair_id
    pair_id = data.get("pair_id")
    role = data.get("pair_role")
    valid = True
    if not isinstance(pair_id, str) or not pair_id.strip():
        violations.append(
            Violation(
                "pair-schema", f"pair_id must be a non-empty string, got {pair_id!r}", toml_path
            )
        )
        valid = False
    if role not in PAIR_ROLE_VALUES:
        violations.append(
            Violation(
                "pair-schema",
                f"pair_role={role!r} not in {sorted(PAIR_ROLE_VALUES)}",
                toml_path,
            )
        )
        valid = False
    if not valid:
        return violations, None
    return violations, (pair_id, role)


def _validate_pairing(entries: list[tuple[str, str, Path]]) -> list[Violation]:
    """Cross-fixture check: every pair_id has exactly one flag + one restraint.

    entries is a list of (pair_id, role, toml_path) collected across the
    whole corpus by _validate_one_fixture. Catches missing twins, dangling
    single-sided pair_ids, and duplicate pair_ids (>1 flag or >1 restraint
    sharing an id) with one uniform message.
    """
    by_pair: dict[str, dict[str, list[Path]]] = {}
    for pair_id, role, toml_path in entries:
        by_pair.setdefault(pair_id, {"flag": [], "restraint": []})[role].append(toml_path)

    violations: list[Violation] = []
    for pair_id in sorted(by_pair):
        roles = by_pair[pair_id]
        flags, restraints = roles["flag"], roles["restraint"]
        if len(flags) == 1 and len(restraints) == 1:
            continue
        violations.append(
            Violation(
                "pair-cardinality",
                f"pair_id {pair_id!r} has {len(flags)} flag(s) and {len(restraints)} "
                f"restraint(s); every pair_id must resolve to exactly one flag and "
                f"exactly one restraint. flags={[str(p) for p in flags]} "
                f"restraints={[str(p) for p in restraints]}",
            )
        )
    return violations


def _validate_one_fixture(
    fixture_dir: Path, canon: _canon.Canon, kinds: Sequence[str]
) -> tuple[list[Violation], tuple[str, str, Path] | None]:
    """Schema + content checks on a single fixture's fixture.toml.

    Returns (violations, pair_entry). pair_entry is (pair_id, role, toml_path)
    when the fixture declares a valid pair_id/pair_role, for the caller to
    feed into _validate_pairing's cross-fixture cardinality check.
    """
    violations: list[Violation] = []
    toml_path = fixture_dir / "fixture.toml"
    if not toml_path.exists():
        violations.append(
            Violation(
                "missing-sidecar",
                "fixture.toml is required for every evals/fixtures/<id>/",
                toml_path,
            )
        )
        return violations, None
    data = _load_toml(toml_path)
    if not isinstance(data, dict):
        violations.append(
            Violation("schema", "fixture.toml top-level must be a mapping", toml_path)
        )
        return violations, None
    for field in REQUIRED_FIXTURE_FIELDS:
        value = data.get(field)
        if value in (None, "", [], {}):
            violations.append(
                Violation(
                    "schema",
                    f"missing or empty required field {field!r}",
                    toml_path,
                )
            )
    declared_id = data.get("id")
    if declared_id is not None and declared_id != fixture_dir.name:
        violations.append(
            Violation(
                "id-mismatch",
                f"fixture.toml id={declared_id!r} does not match directory name "
                f"{fixture_dir.name!r}",
                toml_path,
            )
        )
    expected = data.get("expected_result")
    if expected is not None and expected not in EXPECTED_RESULT_VALUES:
        violations.append(
            Violation(
                "schema",
                f"expected_result={expected!r} not in {sorted(EXPECTED_RESULT_VALUES)}",
                toml_path,
            )
        )
    # Type-check optional boolean fields. Aspirational fixtures opt out of
    # rule-id assertion in the cross-check (see _cross_check_expected_result).
    # Reject string typos like "true"/"false" that would silently degrade
    # the assertion.
    for field in OPTIONAL_BOOL_FIELDS:
        if field in data and not isinstance(data[field], bool):
            violations.append(
                Violation(
                    "schema",
                    f"{field} must be a boolean (true/false), got {type(data[field]).__name__}: {data[field]!r}",
                    toml_path,
                )
            )
    tested = data.get("tested_rules") or []
    if not isinstance(tested, list):
        violations.append(Violation("schema", "tested_rules must be a list", toml_path))
        tested = []
    for idx, rule in enumerate(tested):
        for err in _validate_tested_rule(rule, canon, kinds):
            violations.append(
                Violation(
                    "tested-rules",
                    f"tested_rules[{idx}]: {err}",
                    toml_path,
                )
            )
    if data.get("example") is True and _extract_cited_gates(data):
        violations.append(
            Violation(
                "example-with-gate",
                "example = true fixtures must not cite gate-kind tested_rules "
                "(there is nothing for the cited-gate assertion to skip); drop "
                "`example` or drop the gate citation",
                toml_path,
            )
        )
    pair_violations, pair_role_entry = _validate_pair_fields(fixture_dir, data, toml_path)
    violations.extend(pair_violations)
    pair_entry = (pair_role_entry[0], pair_role_entry[1], toml_path) if pair_role_entry else None
    return violations, pair_entry


def _needs_materialization(fixture_dir: Path) -> bool:
    """True when REVIEW_HISTORY.json opts into final-entry materialization.

    See the "Fixture storage: materialized final history" comment above.
    """
    hist_path = fixture_dir / "REVIEW_HISTORY.json"
    if not hist_path.is_file():
        return False
    try:
        hist = json.loads(hist_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    return isinstance(hist, dict) and hist.get(MATERIALIZE_FINAL_HISTORY_KEY) is True


@contextlib.contextmanager
def _materialized_fixture(fixture_dir: Path):
    """Yield a directory ready to hand to validate-artifact.py.

    Fixtures without the opt-in key are yielded unchanged -- no copy, byte-
    identical behavior to before this convention existed. Opted-in fixtures
    are copied to a throwaway temp dir where REVIEW_HISTORY.json.loops gets a
    parsed copy of CURRENT_REVIEW.json appended as its final entry, so the
    copy looks exactly like a real G18-compliant artifact on disk.
    """
    if not _needs_materialization(fixture_dir):
        yield fixture_dir
        return
    with tempfile.TemporaryDirectory(prefix="validate-fixtures-materialize-") as td:
        materialized = Path(td) / fixture_dir.name
        shutil.copytree(fixture_dir, materialized)
        hist_path = materialized / "REVIEW_HISTORY.json"
        hist = json.loads(hist_path.read_text(encoding="utf-8"))
        current = json.loads((materialized / "CURRENT_REVIEW.json").read_text(encoding="utf-8"))
        hist.pop(MATERIALIZE_FINAL_HISTORY_KEY, None)
        loops = hist.get("loops")
        hist["loops"] = [*loops, current] if isinstance(loops, list) else [current]
        hist_path.write_text(json.dumps(hist, indent=2) + "\n", encoding="utf-8")
        yield materialized


def _run_artifact_check(
    fixture_dir: Path, reference_now: str | None = None
) -> tuple[int, str, list[dict]]:
    """Invoke validate-artifact.py --mode strict --json on a fixture.

    Returns (exit_code, combined_text_output, issues_list). The issues list is
    parsed from the --json sidecar payload; empty if the run produced no JSON
    file or it failed to parse. Runs against a materialized copy when the
    fixture opts in (see `_materialized_fixture`); otherwise against
    `fixture_dir` directly, same as always.
    """
    with tempfile.NamedTemporaryFile(
        mode="r", suffix=".json", delete=False, encoding="utf-8"
    ) as tf:
        json_path = Path(tf.name)
    try:
        env = os.environ.copy()
        if reference_now:
            env["CONTEST_REFACTOR_NOW"] = reference_now
        with _materialized_fixture(fixture_dir) as run_dir:
            result = subprocess.run(
                [
                    # sys.executable, not "python3": on Windows the bare name resolves to an
                    # App Execution Alias stub that exits 9009, so every cross-check reported
                    # expected-pass/wrong-gate-fired for an environment reason. Matches the
                    # convention already used by _smoke_check.py.
                    sys.executable,
                    str(ARTIFACT_VALIDATOR),
                    str(run_dir),
                    "--mode",
                    "strict",
                    "--json",
                    str(json_path),
                    "--quiet",
                    # G47 determinism: point the attestation config at nonexistent temp
                    # paths so fixture outcomes never read the developer's real
                    # ~/.contest-refactor state. Repo-independent G47 fixtures terminate
                    # on artifact-local checks before any environment access.
                    "--attestation-ledger",
                    str(json_path.parent / f"{json_path.stem}-g47-no-ledger.jsonl"),
                    "--attestation-trust",
                    str(json_path.parent / f"{json_path.stem}-g47-no-trust.json"),
                ],
                capture_output=True,
                text=True,
                env=env,
            )
        output = (result.stdout or "") + (result.stderr or "")
        issues: list[dict] = []
        try:
            payload = json.loads(json_path.read_text(encoding="utf-8"))
            raw_issues = payload.get("issues") if isinstance(payload, dict) else None
            if isinstance(raw_issues, list):
                issues = [i for i in raw_issues if isinstance(i, dict)]
        except (json.JSONDecodeError, OSError):
            pass
    finally:
        with contextlib.suppress(OSError):
            json_path.unlink()
    return result.returncode, output.strip(), issues


def _extract_cited_gates(fixture_data: dict) -> list[str]:
    """Return the list of gate-kind tested_rules[].id entries."""
    out: list[str] = []
    for rule in fixture_data.get("tested_rules") or []:
        if isinstance(rule, dict) and rule.get("kind") == "gate":
            rid = rule.get("id")
            if isinstance(rid, str) and rid:
                out.append(rid)
    return out


def _gate_satisfies(cited: str, fired: str) -> bool:
    """True when a fired issue rule id satisfies a cited canonical gate id.

    A canonical gate (e.g. `G21`) may be structurally mechanized under a
    sub-rule label (e.g. `G21-scorecard`) rather than emitted verbatim --
    `validate-artifact.py`'s check_* functions do this deliberately so a
    single canonical gate can cover several independently-firing structural
    checks. A sub-rule satisfies its gate when it is exactly the gate id, or
    the gate id followed by a `-` (never a bare prefix: `G2` must not match
    `G21-scorecard`, hence the split on `-` rather than `str.startswith`).
    """
    return fired == cited or fired.startswith(f"{cited}-")


def _cross_check_expected_result(fixture_dir: Path, fixture_data: dict) -> list[Violation]:
    """Run validate-artifact.py --mode strict, confirm exit code matches
    expected_result, and (for fail fixtures with cited gates) assert that at
    least one fired issue's rule satisfies a cited gate id (see
    `_gate_satisfies`).

    `aspirational = true` marks a fixture whose cited gate has no emitting
    code path in `_artifact_*.py` yet -- the assertion is one-directional for
    those: it does not fail when the cited gate stays silent (that's the
    expected, documented state), but it DOES fail
    (`aspirational-gate-implemented`) if the cited gate ever starts firing,
    so a stale flag on a now-implemented gate can't hide silently the way a
    blanket skip would.
    """
    violations: list[Violation] = []
    expected = fixture_data.get("expected_result")
    reference_now = fixture_data.get("reference_now")
    if not isinstance(reference_now, str) or not reference_now.strip():
        reference_now = None
    exit_code, output, issues = _run_artifact_check(fixture_dir, reference_now)
    if expected == "pass" and exit_code != 0:
        violations.append(
            Violation(
                "expected-pass",
                f"expected_result=pass but validate-artifact.py --mode strict "
                f"exited {exit_code}; first line of output: "
                f"{output.splitlines()[0] if output else '(empty)'}",
                fixture_dir,
            )
        )
        return violations
    if expected == "fail" and exit_code == 0:
        violations.append(
            Violation(
                "expected-fail",
                "expected_result=fail but validate-artifact.py --mode strict "
                "exited 0 (passed); fixture cannot regression-test a failure case",
                fixture_dir,
            )
        )
        return violations
    if expected != "fail":
        return violations  # only fail-fixtures get the rule-id assertion
    cited_gates = _extract_cited_gates(fixture_data)
    if not cited_gates:
        return violations  # nothing to assert against (e.g. example fixtures)
    fired_rules = {issue.get("rule") for issue in issues if issue.get("rule")}
    matched = any(_gate_satisfies(cited, fired) for cited in cited_gates for fired in fired_rules)
    aspirational = fixture_data.get("aspirational") is True
    if aspirational:
        if matched:
            violations.append(
                Violation(
                    "aspirational-gate-implemented",
                    f"aspirational=true but cited gate(s) {cited_gates} already fire "
                    f"(fired rules: {sorted(r for r in fired_rules if r)}); the validator "
                    "now covers this behavior -- remove `aspirational = true` from "
                    "fixture.toml.",
                    fixture_dir,
                )
            )
        return violations
    if not matched:
        violations.append(
            Violation(
                "wrong-gate-fired",
                f"expected_result=fail with cited gates {cited_gates} but none fired; "
                f"actual fired rules: {sorted(r for r in fired_rules if r) or '(none)'}. "
                "If this gate is not yet validator-implemented, set "
                "`aspirational = true` in fixture.toml.",
                fixture_dir,
            )
        )
    return violations


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "fixtures_dir",
        type=Path,
        help="directory containing fixture subdirectories (e.g., evals/fixtures/)",
    )
    parser.add_argument(
        "--run-artifact-check",
        dest="run_artifact_check",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="run validate-artifact.py --mode strict against each fixture and "
        "cross-check exit code against expected_result (default: on)",
    )
    args = parser.parse_args(argv)

    fixtures_dir: Path = args.fixtures_dir
    if not fixtures_dir.is_dir():
        sys.stderr.write(f"error: not a directory: {fixtures_dir}\n")
        return 2

    canon = _canon.load_canon(SKILL_ROOT)
    kinds = _fixture_rule_kinds(canon)
    if not kinds:
        sys.stderr.write(
            "error: canon/fixture-rule-kinds.toml missing or empty; PR2 requires this canon file\n"
        )
        return 2

    fixture_subdirs = sorted(
        [p for p in fixtures_dir.iterdir() if p.is_dir()],
        key=lambda p: p.name,
    )
    if not fixture_subdirs:
        sys.stderr.write(f"error: no fixture subdirectories in {fixtures_dir}\n")
        return 2

    violations: list[Violation] = []
    pair_entries: list[tuple[str, str, Path]] = []
    for fixture_dir in fixture_subdirs:
        fixture_violations, pair_entry = _validate_one_fixture(fixture_dir, canon, kinds)
        violations.extend(fixture_violations)
        if pair_entry is not None:
            pair_entries.append(pair_entry)
        # Only run the cross-check if the fixture.toml's expected_result parses
        # cleanly; otherwise the upstream schema error is sufficient.
        if args.run_artifact_check and not any(
            v.rule in {"missing-sidecar", "schema"} for v in fixture_violations
        ):
            data = _load_toml(fixture_dir / "fixture.toml") or {}
            expected = data.get("expected_result")
            if expected in EXPECTED_RESULT_VALUES:
                violations.extend(_cross_check_expected_result(fixture_dir, data))

    violations.extend(_validate_pairing(pair_entries))

    if violations:
        for v in violations:
            sys.stderr.write(v.render() + "\n")
        sys.stderr.write(
            f"\nvalidate-fixtures: {len(violations)} violation(s) "
            f"across {len(fixture_subdirs)} fixture(s)\n"
        )
        return 1
    sys.stdout.write(f"validate-fixtures: OK ({len(fixture_subdirs)} fixtures passed)\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
