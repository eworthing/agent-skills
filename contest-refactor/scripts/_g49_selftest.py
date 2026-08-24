#!/usr/bin/env python3
"""Self-test for G49 persisted implementation-hotspot evidence.

Run: python3 scripts/_g49_selftest.py   (exit 0 = pass, 1 = fail)
"""

from __future__ import annotations

import copy
import json
import sys
import tempfile
from pathlib import Path

from _selftest_lib import load_validator as _load_validator


def _coverage(
    *,
    python: tuple[int, int, int] = (0, 0, 0),
    ast_grep: tuple[int, int, int, str] = (4, 3, 1, "partial"),
) -> dict:
    py_discovered, py_scanned, py_failed = python
    ast_discovered, ast_scanned, ast_failed, outcome = ast_grep
    return {
        "python": {
            "discovered": py_discovered,
            "scanned": py_scanned,
            "failed": py_failed,
        },
        "ast_grep": {
            "discovered": ast_discovered,
            "scanned": ast_scanned,
            "failed": ast_failed,
            "outcome": outcome,
        },
    }


def _scan(**overrides) -> dict:
    scan = {
        "schema_version": 2,
        "status": "partial",
        "promotion_allowed": False,
        "coverage": _coverage(),
        "candidates": [],
        "queue_counts": {"control": 0, "mutation": 0, "navigation": 0},
    }
    scan.update(overrides)
    return scan


def _artifact(scan=...) -> dict:
    discovery = {
        "source_roots": ["BenchHypeKit/Sources/"],
        "test_command": "./scripts/run_local_gate.sh --quick",
        "lens": "Apple",
    }
    if scan is not ...:
        discovery["hotspot_scan"] = scan
    return {
        "schema_version": 4,
        "skill_rev": "651ea50",
        "loop": 2,
        "discovery": discovery,
    }


def _candidate() -> dict:
    return {
        "path": "Sources/BenchHypeApplication/Reducer/AppReducer+Workflow.swift",
        "symbol": "AppReducer.reduceWorkflow",
        "line_range": {"start": 7, "end": 171},
        "candidate_queues": ["control", "navigation"],
        "primary_queue": "control",
        "signals": {
            "decision_count": 54,
            "max_nesting": 2,
            "condition_operand_max": 1,
            "logical_lines": 164,
            "mutation_sites": 0,
            "mutation_span": 0,
            "distinct_mutated_fields": 0,
            "mutable_local_count": 0,
            "private_helper_fanout": 2,
            "single_use_private_helper_count": 2,
            "private_call_depth": 1,
            "direct_call_fanout": 57,
        },
        "neighborhood": {"direct_private_helpers": ["dismissTransientNotification"]},
    }


def main() -> int:
    va = _load_validator()
    check = getattr(va, "check_g49_hotspot_scan", None)
    if check is None:
        print("FAIL: validate-artifact.py does not expose check_g49_hotspot_scan")
        return 1

    valid_ok = _scan(
        status="ok",
        coverage=_coverage(python=(1, 1, 0), ast_grep=(0, 0, 0, "not_applicable")),
    )
    valid_partial = _scan(
        candidates=[_candidate()],
        queue_counts={"control": 1, "mutation": 0, "navigation": 1},
    )
    valid_absent = _scan(
        status="absent",
        coverage=_coverage(ast_grep=(4, 0, 4, "absent")),
    )
    valid_not_applicable = _scan(
        status="not_applicable",
        coverage=_coverage(ast_grep=(0, 0, 0, "not_applicable")),
    )
    placeholder = _scan(status="absent", coverage=None, queue_counts=None)

    cases = [
        ("real ok output", _artifact(valid_ok), False),
        ("real partial output", _artifact(valid_partial), False),
        ("real absent output", _artifact(valid_absent), False),
        ("real not-applicable output", _artifact(valid_not_applicable), False),
        ("hotspot_scan missing", _artifact(), True),
        ("BenchHype placeholder", _artifact(placeholder), True),
        ("promotion enabled", _artifact(_scan(promotion_allowed=True)), True),
        ("non-string status", _artifact(_scan(status={"partial": True})), True),
        (
            "coverage totals inconsistent",
            _artifact(_scan(coverage=_coverage(ast_grep=(4, 2, 1, "partial")))),
            True,
        ),
        (
            "non-string ast-grep outcome",
            _artifact(_scan(coverage=_coverage(ast_grep=(4, 3, 1, {"outcome": "partial"})))),
            True,
        ),
        ("unknown top-level field", _artifact(_scan(raw_output="unsafe")), True),
        (
            "queue count exceeds retained memberships",
            _artifact(
                _scan(
                    candidates=[_candidate()],
                    queue_counts={"control": 2, "mutation": 0, "navigation": 1},
                )
            ),
            True,
        ),
        (
            "retained queue membership requires a positive count",
            _artifact(
                _scan(
                    candidates=[_candidate()],
                    queue_counts={"control": 0, "mutation": 0, "navigation": 1},
                )
            ),
            True,
        ),
        (
            "candidate queues reject non-strings without crashing",
            _artifact(
                _scan(
                    candidates=[dict(_candidate(), candidate_queues=[{"queue": "control"}])],
                )
            ),
            True,
        ),
        (
            "candidate field outside whitelist",
            _artifact(
                _scan(
                    candidates=[dict(_candidate(), source="untrusted prose")],
                    queue_counts={"control": 1, "mutation": 0, "navigation": 1},
                )
            ),
            True,
        ),
    ]

    pre_epoch = _artifact()
    pre_epoch["skill_rev"] = "2b81c10"
    cases.append(("pre-hotspot artifact remains compatible", pre_epoch, False))

    failures: list[str] = []
    triggers = 0
    for label, artifact, expect_fire in cases:
        issues = check(copy.deepcopy(artifact))
        fired = bool(issues)
        if expect_fire:
            triggers += 1
        if fired != expect_fire:
            failures.append(
                f"{label}: expected {'FIRE' if expect_fire else 'silence'}, "
                f"got {'FIRE' if fired else 'silence'}"
            )
        for issue in issues:
            if issue.rule != "G49":
                failures.append(f"{label}: emitted {issue.rule!r}, expected 'G49'")

    with tempfile.TemporaryDirectory(prefix="contest-g49-") as tmp:
        artifact_dir = Path(tmp)
        artifact_dir.joinpath("CURRENT_REVIEW.json").write_text(
            json.dumps(_artifact(placeholder)), encoding="utf-8"
        )
        integrated_issues = va.run_checks(artifact_dir)
    if not any(issue.rule == "G49" for issue in integrated_issues):
        failures.append("integration: run_checks did not execute G49")

    if triggers == 0:
        failures.append("vacuity: no G49 trigger cases")
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print(f"OK: G49 selftest — {len(cases)} cases ({triggers} trigger)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
