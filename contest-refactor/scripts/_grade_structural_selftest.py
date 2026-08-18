#!/usr/bin/env python3
"""Self-test: grade_structural.py mechanizes what it claims to, nothing more.

Backlog item 16 acceptance constraint: this selftest EXECS the shipped artifact
(subprocess against scripts/grade_structural.py) against small synthetic candidate
outputs -- it does not reimplement grade_structural's checking logic. RED-first: every
failure class below is asserted to actually fail (exit 1, the specific check reporting
pass:false) before this file is considered green, not merely assumed.

Covers, against real registered scenarios/cases (evals/evals.json `suppression-flag`,
evals/reviewer_baseline.json `reality-persists-1`):
  - a fully-passing Layer-2 candidate (exit 0)
  - one candidate failing each Layer-A general-check class: bad verdict word, non-canon
    smell name, missing required field, incoherent blocks_95/blocking_severity
  - a scenario with zero deterministic assertions (crossplat-restraint), asserting the
    residue list is EXACTLY its four semantic-tagged assertion texts, verbatim
  - a fully-passing Layer-3 candidate (reality-persists-1), and plumbing on an unknown id

Run: python3 scripts/_grade_structural_selftest.py   (exit 0 = pass, 1 = fail)
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
GRADE_SCRIPT = SKILL_ROOT / "scripts" / "grade_structural.py"

FAILURES: list[str] = []


def _run(candidate_text: str, case_id: str, tmpdir: Path, name: str) -> tuple[int, dict]:
    p = tmpdir / name
    p.write_text(candidate_text)
    proc = subprocess.run(
        [sys.executable, str(GRADE_SCRIPT), str(p), case_id],
        capture_output=True,
        text=True,
    )
    try:
        report = json.loads(proc.stdout)
    except json.JSONDecodeError:
        report = {}
    return proc.returncode, report


def _check(label: str, condition: bool, detail: str = "") -> None:
    mark = "PASS" if condition else "FAIL"
    print(f"  [{mark}] {label}" + (f"  ({detail})" if detail else ""))
    if not condition:
        FAILURES.append(label)


def _general(report: dict, name: str) -> dict:
    for g in report.get("general_checks", []):
        if g["name"] == name:
            return g
    raise AssertionError(f"general check {name!r} not present in report")


SUPPRESSION_FLAG_PASS = {
    "verdict": "rejected",
    "blocks_95": True,
    "blocking_severity": "Serious deduction",
    "dimension_scores": {"concurrency": 6.0},
    "flagged_smells": ["suppression-as-fix"],
    "evidence_demanded": ["TSAN run on ImageCache.insert under concurrent prefetch"],
}


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)

        # ---- fence pairing: prose that quotes code around the verdict block --------
        # Regression guard for the defect the paired-arm cost pilot surfaced: BOTH arms quoted a
        # ```sql block in their reasoning, and the extractor's untagged pattern could not open on
        # it -- so it opened on that block's CLOSING fence, swallowed the prose up to the ```json
        # opener, and left the real verdict block unopened. Two well-formed reviews were scored
        # `malformed`. A grader that cannot read a reviewer who quotes code is not measuring the
        # reviewer.
        print("== fenced code in prose does not break verdict extraction ==")
        quoted = (
            "The pre-refactor query was:\n\n```sql\nSELECT * FROM orders;\n```\n\n"
            "and the Swift call site:\n\n```swift\nlet ok = policy.isEligible(m)\n```\n\n"
            "Verdict below.\n\n```json\n" + json.dumps(SUPPRESSION_FLAG_PASS) + "\n```\n"
        )
        rc, report = _run(quoted, "suppression-flag", tmpdir, "fenced.json")
        _check("prose with ```sql/```swift blocks still parses -> exit 0", rc == 0, f"got {rc}")
        _check(
            "the LAST fenced block is the one graded",
            len(report.get("assertions", [])) == 4,
            str(len(report.get("assertions", []))),
        )

        # ---- GREEN: fully-passing Layer-2 candidate --------------------------------
        print("== fully-passing Layer-2 candidate (suppression-flag) ==")
        rc, report = _run(
            json.dumps(SUPPRESSION_FLAG_PASS), "suppression-flag", tmpdir, "pass2.json"
        )
        _check("exit code 0", rc == 0, f"got {rc}")
        _check("all general checks pass", all(g["pass"] for g in report.get("general_checks", [])))
        _check(
            "all deterministic assertions pass",
            all(a["pass"] for a in report.get("assertions", [])),
        )
        _check(
            "4 deterministic assertions found",
            len(report.get("assertions", [])) == 4,
            str(len(report.get("assertions", []))),
        )
        _check(
            "3 semantic assertions in residue",
            len(report.get("residue", [])) == 3,
            str(len(report.get("residue", []))),
        )

        # ---- RED: bad verdict word --------------------------------------------------
        print("== RED: bad verdict word ==")
        bad = dict(SUPPRESSION_FLAG_PASS, verdict="maybe")
        rc, report = _run(json.dumps(bad), "suppression-flag", tmpdir, "bad_verdict.json")
        _check("exit code 1", rc == 1, f"got {rc}")
        _check(
            "verdict_word_membership fails",
            _general(report, "verdict_word_membership")["pass"] is False,
        )
        _check(
            "other general checks unaffected",
            _general(report, "flagged_smells_canon_exact")["pass"] is True,
        )

        # ---- RED: non-canon smell name -----------------------------------------------
        print("== RED: non-canon smell name ==")
        bad = dict(SUPPRESSION_FLAG_PASS, flagged_smells=["made-up-smell-that-is-not-canon"])
        rc, report = _run(json.dumps(bad), "suppression-flag", tmpdir, "bad_smell.json")
        _check("exit code 1", rc == 1, f"got {rc}")
        _check(
            "flagged_smells_canon_exact fails",
            _general(report, "flagged_smells_canon_exact")["pass"] is False,
        )
        _check(
            "verdict_word_membership unaffected",
            _general(report, "verdict_word_membership")["pass"] is True,
        )

        # ---- RED: missing required field ---------------------------------------------
        print("== RED: missing required field ==")
        bad = {k: v for k, v in SUPPRESSION_FLAG_PASS.items() if k != "evidence_demanded"}
        rc, report = _run(json.dumps(bad), "suppression-flag", tmpdir, "missing_field.json")
        _check("exit code 1", rc == 1, f"got {rc}")
        _check(
            "required_fields_present fails",
            _general(report, "required_fields_present")["pass"] is False,
        )
        _check(
            "names the missing field",
            "evidence_demanded" in _general(report, "required_fields_present")["detail"],
        )

        # ---- RED: incoherent booleans --------------------------------------------------
        print("== RED: incoherent booleans (blocks_95=true, blocking_severity=null) ==")
        bad = dict(SUPPRESSION_FLAG_PASS, blocking_severity=None)
        rc, report = _run(json.dumps(bad), "suppression-flag", tmpdir, "incoherent.json")
        _check("exit code 1", rc == 1, f"got {rc}")
        _check("boolean_coherence fails", _general(report, "boolean_coherence")["pass"] is False)
        _check(
            "verdict_word_membership unaffected",
            _general(report, "verdict_word_membership")["pass"] is True,
        )

        # ---- residue-only scenario: crossplat-restraint has 0 deterministic assertions --
        print("== residue-only scenario (crossplat-restraint, 0 deterministic assertions) ==")
        clean = {
            "verdict": "approved",
            "blocks_95": False,
            "blocking_severity": None,
            "dimension_scores": {"framework_idioms": 9.0},
            "flagged_smells": [],
            "evidence_demanded": [],
        }
        rc, report = _run(json.dumps(clean), "crossplat-restraint", tmpdir, "residue_only.json")
        expected_residue = [
            "[restraint] Does not flag a cross-platform / tvOS compile problem (the guard is #if os(iOS), which is correct)",
            "[restraint] Recognizes the recorded per-target compile evidence satisfies Meta-Rule 4",
            '[restraint] verdict is not "rejected" for cross-platform reasons; does not demand changing #if os(iOS) to canImport (a score-honesty pushback on the Actor\'s unearned 9.5 is not a carve-out flag)',
            "[restraint] Attributes no framework_idioms deduction to the #if os(iOS) guard; any sub-9.5 score rests on the missing-residual rule, not on the cross-platform guard",
        ]
        _check(
            "exit code 0 (all general checks pass, 0 deterministic assertions)",
            rc == 0,
            f"got {rc}",
        )
        _check("zero deterministic assertions", report.get("assertions") == [])
        _check(
            "residue is exactly the 4 semantic-tagged assertions, verbatim",
            report.get("residue") == expected_residue,
        )

        # ---- Layer 3: fully-passing candidate -----------------------------------------
        print("== fully-passing Layer-3 candidate (reality-persists-1) ==")
        l3_pass = {
            "verdict": "rejected",
            "reason": "Both selectSegment and resetToDefault still write selectedSegment.",
            "checks": {"reality": "failed", "honesty": "skipped", "regression": "skipped"},
            "regressions": ["FilterSegmentViewModel.swift:9 second writer persists"],
            "conditions": [],
        }
        rc, report = _run(json.dumps(l3_pass), "reality-persists-1", tmpdir, "l3_pass.json")
        _check("exit code 0", rc == 0, f"got {rc}")
        _check("layer detected as 3", report.get("layer") == 3)
        _check(
            "1 deterministic assertion (verdict==expected_verdict)",
            len(report.get("assertions", [])) == 1,
        )
        _check(
            "1 semantic residue item (expected_reason_class)", len(report.get("residue", [])) == 1
        )

        # ---- plumbing: unknown id -------------------------------------------------------
        print("== plumbing: unknown scenario/case id ==")
        rc, report = _run(json.dumps(l3_pass), "not-a-real-id", tmpdir, "unknown_id.json")
        _check("exit code 2", rc == 2, f"got {rc}")
        _check("error field present", "error" in report)

    print()
    if FAILURES:
        print(f"_grade_structural_selftest: FAIL ({len(FAILURES)} check(s) failed)")
        return 1
    print("_grade_structural_selftest: OK (all checks passed)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
