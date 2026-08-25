#!/usr/bin/env python3
"""Self-test for G50 hotspot triage completeness.

RED-first: the 5/6 case models the real production miss (register "Instrumented
run #7" additional-defect 2) -- 6 scanner candidates, 5 triage rows, Builder
Notes said "5 of 6 candidates inspected" and nothing machine-checked it.

Run: python3 scripts/_g50_selftest.py   (exit 0 = pass, 1 = fail)
"""

from __future__ import annotations

import copy
import sys

from _selftest_lib import load_validator as _load_validator


def _candidate(path: str, symbol: str) -> dict:
    return {
        "path": path,
        "symbol": symbol,
        "line_range": {"start": 1, "end": 10},
        "candidate_queues": ["control"],
        "primary_queue": "control",
        "signals": {
            "decision_count": 1,
            "max_nesting": 1,
            "condition_operand_max": 1,
            "logical_lines": 1,
            "mutation_sites": 0,
            "mutation_span": 0,
            "distinct_mutated_fields": 0,
            "mutable_local_count": 0,
            "private_helper_fanout": 0,
            "single_use_private_helper_count": 0,
            "private_call_depth": 0,
            "direct_call_fanout": 0,
        },
        "neighborhood": {"direct_private_helpers": []},
    }


_SIX_CANDIDATES = [_candidate(f"Sources/File{i}.swift", f"Type{i}.method") for i in range(1, 7)]


def _scan(candidates: list[dict]) -> dict:
    return {
        "schema_version": 2,
        "status": "ok",
        "promotion_allowed": False,
        "coverage": {
            "python": {"discovered": 0, "scanned": 0, "failed": 0},
            "ast_grep": {"discovered": 6, "scanned": 6, "failed": 0, "outcome": "ok"},
        },
        "candidates": candidates,
        "queue_counts": {"control": len(candidates), "mutation": 0, "navigation": 0},
    }


def _triage_row(candidate: dict, disposition: str) -> dict:
    return {"path": candidate["path"], "symbol": candidate["symbol"], "disposition": disposition}


def _artifact(*, state: str, candidates: list[dict], triage=...) -> dict:
    discovery: dict = {
        "source_roots": ["src/"],
        "test_command": "pytest",
        "lens": "Generic",
        "hotspot_scan": _scan(candidates),
    }
    artifact: dict = {
        "schema_version": 4,
        "skill_rev": "7ffd502",
        "loop": 3,
        "state": state,
        "discovery": discovery,
    }
    if triage is not ...:
        artifact["discovery_consumption"] = {"hotspot_triage": triage}
    return artifact


def main() -> int:
    va = _load_validator()
    check = getattr(va, "check_g50_hotspot_triage", None)
    if check is None:
        print("FAIL: validate-artifact.py does not expose check_g50_hotspot_triage")
        return 1

    full_triage = [_triage_row(c, "confirm") for c in _SIX_CANDIDATES]
    five_of_six = [_triage_row(c, "confirm") for c in _SIX_CANDIDATES[:5]]  # the observed miss

    cases: list[tuple[str, dict, bool]] = [
        (
            "6/6 triaged, HALT_SUCCESS_candidate",
            _artifact(
                state="HALT_SUCCESS_candidate", candidates=_SIX_CANDIDATES, triage=full_triage
            ),
            False,
        ),
        (
            "6/6 triaged, HALT_SUCCESS",
            _artifact(state="HALT_SUCCESS", candidates=_SIX_CANDIDATES, triage=full_triage),
            False,
        ),
        (
            "5/6 triaged -- the observed production miss",
            _artifact(
                state="HALT_SUCCESS_candidate", candidates=_SIX_CANDIDATES, triage=five_of_six
            ),
            True,
        ),
        (
            "hotspot_triage field entirely absent",
            _artifact(state="HALT_SUCCESS_candidate", candidates=_SIX_CANDIDATES),
            True,
        ),
        (
            "empty candidates -- nothing to triage, field absent is fine",
            _artifact(state="HALT_SUCCESS_candidate", candidates=[]),
            False,
        ),
        (
            "CONTINUE loop is prose-governed, never gated",
            _artifact(state="CONTINUE", candidates=_SIX_CANDIDATES),
            False,
        ),
        (
            "invalid disposition",
            _artifact(
                state="HALT_SUCCESS_candidate",
                candidates=_SIX_CANDIDATES,
                triage=[
                    *[_triage_row(c, "confirm") for c in _SIX_CANDIDATES[:5]],
                    _triage_row(_SIX_CANDIDATES[5], "maybe"),
                ],
            ),
            True,
        ),
        (
            "duplicate triage key",
            _artifact(
                state="HALT_SUCCESS_candidate",
                candidates=_SIX_CANDIDATES,
                triage=[*full_triage, _triage_row(_SIX_CANDIDATES[0], "dismiss")],
            ),
            True,
        ),
        (
            "extra triage row outside the scanner roster",
            _artifact(
                state="HALT_SUCCESS_candidate",
                candidates=_SIX_CANDIDATES,
                triage=[
                    *full_triage,
                    _triage_row(_candidate("Sources/Ghost.swift", "X.y"), "dismiss"),
                ],
            ),
            True,
        ),
        (
            "row with missing/unrecognized fields",
            _artifact(
                state="HALT_SUCCESS_candidate",
                candidates=_SIX_CANDIDATES,
                triage=[
                    *[_triage_row(c, "confirm") for c in _SIX_CANDIDATES[:5]],
                    {"path": _SIX_CANDIDATES[5]["path"], "disposition": "confirm"},
                ],
            ),
            True,
        ),
    ]

    pre_epoch = _artifact(state="HALT_SUCCESS_candidate", candidates=_SIX_CANDIDATES)
    pre_epoch["skill_rev"] = "2b81c10"
    cases.append(("pre-epoch artifact remains compatible without the field", pre_epoch, False))

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
            if issue.rule != "G50":
                failures.append(f"{label}: emitted {issue.rule!r}, expected 'G50'")

    if triggers == 0:
        failures.append("vacuity: no G50 trigger cases")
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print(f"OK: G50 selftest — {len(cases)} cases ({triggers} trigger)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
