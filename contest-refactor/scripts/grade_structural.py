#!/usr/bin/env python3
"""Mechanically grade the structurally-checkable assertions in a Layer 2/3 eval case.

Backlog item 16: "mechanize every structurally checkable assertion before any judge
alignment work." Layers 2 (evals/scenarios/) and 3 (evals/reviewer-cases/) grade a
candidate's verdict JSON semantically end-to-end, against a `grader.md` subagent, even
though a slice of every assertions[] list is purely structural: the verdict word comes
from a closed set (canon/verdicts.toml), flagged_smells values are supposed to be
canon-exact vocabulary, dimension_scores is a shaped dict, blocks_95/blocking_severity
must cohere. This script answers those questions with code, not a model, so the judge's
surface shrinks to what's left: genuine reading comprehension.

It does NOT grade judgment. Every assertion tagged `method: "semantic"` in evals.json /
reviewer_baseline.json is emitted verbatim in the `residue` list and never evaluated here
-- that is backlog item 10's (still-open) alignment work. A clean exit 0 from this script
means the candidate's structure holds; it says nothing about whether the candidate's
REASONING is any good.

Usage:
  grade_structural.py <candidate-output-file> <scenario-or-case-id>

<candidate-output-file>  the model's response: either a Layer-2 `review-verdict.md`
                          (prose + a trailing fenced ```json block, per evals/README.md
                          "The structured verdict contract") or a Layer-3 implementation-
                          reviewer response (bare JSON per
                          references/implementation-reviewer.md "JSON output contract").
                          This script tries json.loads on the whole file first, then
                          falls back to the LAST fenced ```json block.
<scenario-or-case-id>    a Layer-2 evals.json `name` (e.g. suppression-flag) or numeric
                          `id`, OR a Layer-3 reviewer_baseline.json case `id`
                          (e.g. reality-persists-1). Looked up in both manifests in that
                          order; the first hit decides the layer and its JSON contract.

What this checks (Layer A, general -- always run against the candidate regardless of
which scenario/case it answers):
  - verdict-word membership (canon/verdicts.toml)
  - flagged_smells values are canon-exact smell names (Layer 2 only; the vocabulary is
    parsed read-only from references/architecture-rubric.md "Vocabulary -- Smells", since
    there is no canon/*.toml for smell names -- see _smell_vocabulary())
  - required top-level fields present (the verdict-contract shape from evals/README.md
    for Layer 2, the JSON output contract from implementation-reviewer.md for Layer 3)
  - dimension_scores shape (Layer 2 only: keys subset of canon/scorecard-dimensions.toml,
    values numeric 0-10)
  - boolean coherence: Layer 2 -- blocks_95 true implies a non-null canon
    blocking_severity, blocks_95 false implies blocking_severity is null (this pairing is
    this harness's own inferred coherence rule, not quoted skill canon -- the schema
    doesn't state it explicitly, but "the severity of the thing that blocks 9.5" implies
    it). Layer 3 -- the verdict/checks/regressions/conditions rules stated verbatim in
    implementation-reviewer.md "JSON output contract > Rules".

Then (Layer B, per-case) every assertion/field tagged `method: "deterministic"` in the
manifest is evaluated against its `check` spec (Layer 2) or, for Layer 3, the single fixed
comparison `verdict == expected_verdict`. Every `method: "semantic"` assertion is skipped
and listed in `residue` -- the axis this script deliberately does not judge.

Exit codes: 0 = every deterministic check + assertion passed, 1 = at least one failed,
2 = plumbing (bad args, candidate unreadable/unparseable, unknown scenario/case id).
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

from _canon import load_canon

SKILL_ROOT = Path(__file__).resolve().parent.parent
EVALS_DIR = SKILL_ROOT / "evals"
EVALS_JSON = EVALS_DIR / "evals.json"
REVIEWER_BASELINE = EVALS_DIR / "reviewer_baseline.json"
ARCHITECTURE_RUBRIC = SKILL_ROOT / "references" / "architecture-rubric.md"

LAYER3_CHECK_STATUSES = ("passed", "failed", "skipped")  # implementation-reviewer.md
LAYER3_CHECK_NAMES = ("reality", "honesty", "regression")
# The two JSON output contracts' required top-level fields, hoisted to module level (backlog
# item 22) so the required-field vocabulary has exactly one definition -- scripts/_paired_baseline.py
# imports these rather than re-deriving them, per the house rule against reimplementing logic
# that already exists (see its docstring). No behavior change here: the two functions below
# already built this exact list inline; this only names it.
LAYER2_REQUIRED_FIELDS = (
    "verdict",
    "blocks_95",
    "blocking_severity",
    "dimension_scores",
    "flagged_smells",
    "evidence_demanded",
)
LAYER3_REQUIRED_FIELDS = ("verdict", "reason", "checks", "regressions", "conditions")


class Plumbing(Exception):
    """A precondition failed before grading could start (exit 2)."""


def _normalize(s: str) -> str:
    return re.sub(r"[\s_-]+", " ", s.strip().lower())


def _smell_vocabulary() -> tuple[str, ...]:
    """Canon-equivalent smell vocabulary, read-only-parsed from architecture-rubric.md.

    There is no canon/*.toml for smell names (verified: grep -rl smell canon/ -- nothing).
    architecture-rubric.md "Vocabulary -- Smells (use only in this exact sense)" is the
    documented source of truth instead, so this reads it fresh rather than hardcoding the
    list. Extracts only the bold span immediately after "- " at each top-level bullet
    (the smell name itself) plus "**Sub-pattern: <name>.**" spans (e.g. suppression-as-fix)
    -- NOT every bold span in the section, which would also catch incidental emphasis like
    **unless** or **style/tooling**.
    """
    text = ARCHITECTURE_RUBRIC.read_text()
    start = text.find("## Vocabulary — Smells")
    if start == -1:
        raise Plumbing(f"could not find 'Vocabulary — Smells' section in {ARCHITECTURE_RUBRIC}")
    end = text.find("\n## ", start + 1)
    section = text[start : end if end != -1 else None]

    names: list[str] = []
    for line in section.splitlines():
        line = line.strip()
        if line.startswith("- "):
            m = re.match(r"-\s+\*\*([^*]+)\*\*", line)
            if m:
                names.append(m.group(1).strip())
        for m in re.finditer(r"\*\*Sub-pattern:\s*([^*.]+)\.\*\*", line):
            names.append(m.group(1).strip())
    if not names:
        raise Plumbing(f"parsed zero smell names from {ARCHITECTURE_RUBRIC}")
    return tuple(names)


def _extract_json(candidate_text: str) -> dict[str, Any]:
    """Layer-3 responses are bare JSON; Layer-2 responses end with a fenced ```json block."""
    stripped = candidate_text.strip()
    try:
        parsed = json.loads(stripped)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    blocks = re.findall(r"```(?:json)?\s*\n(.*?)```", candidate_text, re.S)
    for block in reversed(blocks):  # prompts say "end the file with" the json block
        try:
            parsed = json.loads(block.strip())
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
    raise Plumbing("no parseable JSON object found (tried whole file, then fenced blocks)")


def _load_candidate(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise Plumbing(f"candidate output file not found: {path}")
    return _extract_json(path.read_text())


def _find_case(case_id: str) -> tuple[int, dict[str, Any]]:
    """Returns (layer, record). layer is 2 or 3."""
    if EVALS_JSON.exists():
        data = json.loads(EVALS_JSON.read_text())
        for ev in data.get("evals", []):
            if ev.get("name") == case_id or str(ev.get("id")) == case_id:
                if not ev.get("assertions"):
                    raise Plumbing(
                        f"'{case_id}' is a Layer-1 eval (id={ev.get('id')}) with no "
                        "assertions[] -- grade_structural.py only covers Layers 2-3"
                    )
                return 2, ev
    if REVIEWER_BASELINE.exists():
        data = json.loads(REVIEWER_BASELINE.read_text())
        for case in data.get("cases", []):
            if case.get("id") == case_id:
                return 3, case
    raise Plumbing(
        f"'{case_id}' not found in {EVALS_JSON.name} (evals[].name/id) "
        f"or {REVIEWER_BASELINE.name} (cases[].id)"
    )


# ---- op interpreter for Layer-2 `check` specs -----------------------------------------


def _eval_check(check: dict[str, Any], candidate: dict[str, Any]) -> tuple[bool, str]:
    field = check["field"]
    op = check["op"]
    if op == "eq":
        got = candidate.get(field)
        return got == check["value"], f"{field}={got!r} expected=={check['value']!r}"
    if op == "in":
        got = candidate.get(field)
        return got in check["value"], f"{field}={got!r} expected in {check['value']!r}"
    if op == "any_lt":
        scores = candidate.get(field) or {}
        present = {d: scores[d] for d in check["dims"] if isinstance(scores, dict) and d in scores}
        if not present:
            return False, f"none of {check['dims']} present in {field}={scores!r}"
        hit = any(isinstance(v, (int, float)) and v < check["value"] for v in present.values())
        return hit, f"{field} subset {present!r} vs <{check['value']}"
    if op == "contains_any":
        values = candidate.get(field) or []
        norm_values = [_normalize(str(v)) for v in values] if isinstance(values, list) else []
        targets = [_normalize(v) for v in check["value"]]
        hit = any(t in v for v in norm_values for t in targets)
        return (
            hit,
            f"{field}={values!r} does not contain any of {check['value']!r}"
            if not hit
            else f"{field} contains a match for {check['value']!r}",
        )
    if op == "excludes_all":
        values = candidate.get(field) or []
        norm_values = [_normalize(str(v)) for v in values] if isinstance(values, list) else []
        targets = [_normalize(v) for v in check["value"]]
        hit = not any(t in v for v in norm_values for t in targets)
        return hit, f"{field}={values!r} vs excluded {check['value']!r}"
    if op == "nonempty":
        values = candidate.get(field)
        hit = bool(values)
        return hit, f"{field}={values!r} nonempty={hit}"
    raise Plumbing(f"unknown check op {op!r}")


def _eval_checks(checks: list[dict[str, Any]], candidate: dict[str, Any]) -> tuple[bool, str]:
    details = []
    ok = True
    for c in checks:
        passed, detail = _eval_check(c, candidate)
        ok = ok and passed
        details.append(detail)
    return ok, "; ".join(details)


# ---- Layer A: general structural checks -------------------------------------------------


def _general_checks_layer2(candidate: dict[str, Any], canon) -> list[dict[str, Any]]:
    results = []
    required = LAYER2_REQUIRED_FIELDS
    missing = [f for f in required if f not in candidate]
    results.append(
        {
            "name": "required_fields_present",
            "pass": not missing,
            "detail": "all present" if not missing else f"missing: {missing}",
        }
    )

    verdict = candidate.get("verdict")
    results.append(
        {
            "name": "verdict_word_membership",
            "pass": verdict in canon.verdicts,
            "detail": f"verdict={verdict!r} canon={canon.verdicts}",
        }
    )

    smells = candidate.get("flagged_smells")
    if isinstance(smells, list):
        vocab_norm = {_normalize(v) for v in _smell_vocabulary()}
        bad = [s for s in smells if _normalize(str(s)) not in vocab_norm]
        results.append(
            {
                "name": "flagged_smells_canon_exact",
                "pass": not bad,
                "detail": "all canon-exact" if not bad else f"non-canon values: {bad}",
            }
        )
    else:
        results.append(
            {
                "name": "flagged_smells_canon_exact",
                "pass": False,
                "detail": "flagged_smells missing or not a list",
            }
        )

    dims = candidate.get("dimension_scores")
    if isinstance(dims, dict):
        bad_keys = [k for k in dims if k not in canon.scorecard_dimensions]
        bad_vals = [
            k for k, v in dims.items() if not isinstance(v, (int, float)) or not (0 <= v <= 10)
        ]
        ok = not bad_keys and not bad_vals
        detail = "shape OK" if ok else f"bad_keys={bad_keys} bad_vals={bad_vals}"
        results.append({"name": "dimension_scores_shape", "pass": ok, "detail": detail})
    else:
        results.append(
            {
                "name": "dimension_scores_shape",
                "pass": False,
                "detail": "dimension_scores missing or not a dict",
            }
        )

    blocks_95 = candidate.get("blocks_95")
    severity = candidate.get("blocking_severity")
    if blocks_95 is True:
        coherent = severity is not None and severity in canon.severity_anchors
        detail = f"blocks_95=true requires a canon blocking_severity, got {severity!r}"
    elif blocks_95 is False:
        coherent = severity is None
        detail = f"blocks_95=false requires blocking_severity=null, got {severity!r}"
    else:
        coherent = False
        detail = f"blocks_95={blocks_95!r} is not a boolean"
    results.append({"name": "boolean_coherence", "pass": coherent, "detail": detail})

    return results


def _general_checks_layer3(candidate: dict[str, Any], canon) -> list[dict[str, Any]]:
    results = []
    required = LAYER3_REQUIRED_FIELDS
    missing = [f for f in required if f not in candidate]
    results.append(
        {
            "name": "required_fields_present",
            "pass": not missing,
            "detail": "all present" if not missing else f"missing: {missing}",
        }
    )

    verdict = candidate.get("verdict")
    results.append(
        {
            "name": "verdict_word_membership",
            "pass": verdict in canon.verdicts,
            "detail": f"verdict={verdict!r} canon={canon.verdicts}",
        }
    )

    checks = candidate.get("checks")
    if isinstance(checks, dict):
        bad = {
            k: checks.get(k)
            for k in LAYER3_CHECK_NAMES
            if checks.get(k) not in LAYER3_CHECK_STATUSES
        }
        results.append(
            {
                "name": "checks_status_membership",
                "pass": not bad,
                "detail": "all valid"
                if not bad
                else f"invalid: {bad} (allowed: {LAYER3_CHECK_STATUSES})",
            }
        )
    else:
        checks = {}
        results.append(
            {
                "name": "checks_status_membership",
                "pass": False,
                "detail": "checks missing or not a dict",
            }
        )

    regressions = candidate.get("regressions")
    conditions = candidate.get("conditions")
    reality, honesty, regression = (checks.get(k) for k in LAYER3_CHECK_NAMES)
    if verdict == "approved":
        coherent = (
            reality == honesty == regression == "passed" and not regressions and not conditions
        )
        detail = "approved requires reality/honesty/regression all passed and regressions/conditions empty"
    elif verdict == "rejected":
        coherent = "failed" in (reality, honesty, regression)
        detail = "rejected requires at least one check failed"
    elif verdict == "conditional":
        coherent = reality == "passed" and ("failed" in (honesty, regression)) and bool(conditions)
        detail = "conditional requires reality passed, honesty or regression failed, and a non-empty conditions[]"
    else:
        coherent = False
        detail = f"verdict={verdict!r} is not a recognized verdict for coherence rules"
    results.append({"name": "boolean_coherence", "pass": coherent, "detail": detail})

    return results


# ---- Layer B: per-assertion deterministic checks -----------------------------------------


def _grade_layer2(record: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    canon = load_canon(SKILL_ROOT)
    general = _general_checks_layer2(candidate, canon)

    assertions_out = []
    residue = []
    for a in record.get("assertions", []):
        method = a.get("method")
        if method != "deterministic":
            residue.append(a["text"])
            continue
        passed, detail = _eval_checks(a["check"], candidate)
        assertions_out.append(
            {"text": a["text"], "method": method, "pass": passed, "detail": detail}
        )

    return {
        "layer": 2,
        "id": record.get("name") or record.get("id"),
        "general_checks": general,
        "assertions": assertions_out,
        "residue": residue,
    }


def _grade_layer3(record: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    canon = load_canon(SKILL_ROOT)
    general = _general_checks_layer3(candidate, canon)

    assertions_out = []
    residue = []
    if record.get("expected_verdict_method") == "deterministic":
        expected = record.get("expected_verdict")
        got = candidate.get("verdict")
        passed = got == expected
        assertions_out.append(
            {
                "text": f"verdict equals expected_verdict ({expected!r})",
                "method": "deterministic",
                "pass": passed,
                "detail": f"got={got!r} expected={expected!r}",
            }
        )
    if record.get("expected_reason_class_method") == "semantic":
        cls = record.get("expected_reason_class") or "(none registered)"
        residue.append(f"reason names expected_reason_class {cls!r}")

    return {
        "layer": 3,
        "id": record.get("id"),
        "general_checks": general,
        "assertions": assertions_out,
        "residue": residue,
    }


def grade(candidate_path: Path, case_id: str) -> dict[str, Any]:
    layer, record = _find_case(case_id)
    candidate = _load_candidate(candidate_path)
    report = _grade_layer2(record, candidate) if layer == 2 else _grade_layer3(record, candidate)

    det_total = len(report["assertions"])
    det_pass = sum(1 for a in report["assertions"] if a["pass"])
    gen_total = len(report["general_checks"])
    gen_pass = sum(1 for g in report["general_checks"] if g["pass"])
    report["counts"] = {
        "general_checks_total": gen_total,
        "general_checks_pass": gen_pass,
        "deterministic_assertions_total": det_total,
        "deterministic_assertions_pass": det_pass,
        "semantic_residue": len(report["residue"]),
    }
    report["all_deterministic_pass"] = gen_pass == gen_total and det_pass == det_total
    return report


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(
            "usage: grade_structural.py <candidate-output-file> <scenario-or-case-id>",
            file=sys.stderr,
        )
        return 2
    candidate_path = Path(argv[0])
    case_id = argv[1]
    try:
        report = grade(candidate_path, case_id)
    except Plumbing as exc:
        print(json.dumps({"error": str(exc)}, indent=2))
        print(f"grade_structural: PLUMBING: {exc}", file=sys.stderr)
        return 2

    print(json.dumps(report, indent=2))
    if report["all_deterministic_pass"]:
        print("grade_structural: OK (all deterministic checks passed)", file=sys.stderr)
        return 0
    print(
        "grade_structural: FAIL (a deterministic check failed -- see JSON above)", file=sys.stderr
    )
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
