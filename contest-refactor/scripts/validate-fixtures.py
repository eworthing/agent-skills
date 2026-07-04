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
OPTIONAL_BOOL_FIELDS = ("aspirational",)

RESIDUAL_RULES = {
    "9.5-threshold",
    "accepted-residual",
    "queued-residual",
    "expired-residual",
    "terminal-normalization",
}


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


def _validate_one_fixture(
    fixture_dir: Path, canon: _canon.Canon, kinds: Sequence[str]
) -> list[Violation]:
    """Schema + content checks on a single fixture's fixture.toml."""
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
        return violations
    data = _load_toml(toml_path)
    if not isinstance(data, dict):
        violations.append(
            Violation("schema", "fixture.toml top-level must be a mapping", toml_path)
        )
        return violations
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
    # Cross-check: every artifact file the fixture references in fixture.toml
    # (a `files:` array, optional) actually exists. The plan's "Every file the
    # fixture lists exists" bullet covers this. fixture.toml doesn't have a
    # mandatory files[] field today; if present, validate it.
    listed_files = data.get("files")
    if listed_files is not None:
        if not isinstance(listed_files, list):
            violations.append(
                Violation("schema", "files must be a list of relative paths", toml_path)
            )
        else:
            for rel in listed_files:
                if not isinstance(rel, str):
                    violations.append(
                        Violation(
                            "schema",
                            f"files[] entry {rel!r} must be a string path",
                            toml_path,
                        )
                    )
                    continue
                candidate = fixture_dir / rel
                if not candidate.exists():
                    violations.append(
                        Violation(
                            "files",
                            f"declared fixture file does not exist: {rel}",
                            toml_path,
                        )
                    )
    return violations


def _run_artifact_check(
    fixture_dir: Path, reference_now: str | None = None
) -> tuple[int, str, list[dict]]:
    """Invoke validate-artifact.py --mode strict --json on a fixture.

    Returns (exit_code, combined_text_output, issues_list). The issues list is
    parsed from the --json sidecar payload; empty if the run produced no JSON
    file or it failed to parse.
    """
    with tempfile.NamedTemporaryFile(
        mode="r", suffix=".json", delete=False, encoding="utf-8"
    ) as tf:
        json_path = Path(tf.name)
    try:
        env = os.environ.copy()
        if reference_now:
            env["CONTEST_REFACTOR_NOW"] = reference_now
        result = subprocess.run(
            [
                "python3",
                str(ARTIFACT_VALIDATOR),
                str(fixture_dir),
                "--mode",
                "strict",
                "--json",
                str(json_path),
                "--quiet",
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


def _cross_check_expected_result(fixture_dir: Path, fixture_data: dict) -> list[Violation]:
    """Run validate-artifact.py --mode strict, confirm exit code matches
    expected_result, and (for non-aspirational fail fixtures with cited gates)
    assert that at least one fired issue's rule matches a cited gate id.

    The aspirational flag (top-level boolean, default false) exempts a fixture
    from the rule-id assertion. Use it for fixtures whose cited gate is not yet
    validator-implemented; the fixture continues to regression-test exit code
    only until the gate is wired.
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
    if fixture_data.get("aspirational") is True:
        return violations  # aspirational fixtures skip the rule-id assertion
    cited_gates = _extract_cited_gates(fixture_data)
    if not cited_gates:
        return violations  # nothing to assert against
    fired_rules = {issue.get("rule") for issue in issues if issue.get("rule")}
    if not (fired_rules & set(cited_gates)):
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
    for fixture_dir in fixture_subdirs:
        fixture_violations = _validate_one_fixture(fixture_dir, canon, kinds)
        violations.extend(fixture_violations)
        # Only run the cross-check if the fixture.toml's expected_result parses
        # cleanly; otherwise the upstream schema error is sufficient.
        if args.run_artifact_check and not any(
            v.rule in {"missing-sidecar", "schema"} for v in fixture_violations
        ):
            data = _load_toml(fixture_dir / "fixture.toml") or {}
            expected = data.get("expected_result")
            if expected in EXPECTED_RESULT_VALUES:
                violations.extend(_cross_check_expected_result(fixture_dir, data))

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
