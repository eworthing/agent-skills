#!/usr/bin/env python3
"""Behavior checks for G18 review-history append semantics.

Run: python3 scripts/_g18_selftest.py   (exit 0 = pass, 1 = fail)
"""

from __future__ import annotations

from _artifact_history import check_g18_review_history_append


def main() -> int:
    failures: list[str] = []
    old_run = "run-2026-08-23-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    current_run = "run-2026-08-24-bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
    prior = [
        {"schema_version": 4, "loop": 1, "run_id": old_run, "state": "CONTINUE"},
        {"schema_version": 4, "loop": 2, "run_id": old_run, "state": "HALT_STAGNATION"},
    ]
    current_1 = {
        "schema_version": 4,
        "loop": 1,
        "run_id": current_run,
        "state": "CONTINUE",
    }
    current_2 = {
        "schema_version": 4,
        "loop": 2,
        "run_id": current_run,
        "state": "HALT_SUCCESS",
    }

    # Reverting G18 to len(history.loops) == current.loop must fail this case:
    # reset preserves the old run, while the active run still has exactly 2 loops.
    issues = check_g18_review_history_append(
        current_2,
        {"loops": [*prior, current_1, current_2]},
    )
    if issues:
        failures.append(f"preserved prior runs must not count against the active run: {issues}")

    incomplete = check_g18_review_history_append(
        current_2,
        {"loops": [*prior, current_2]},
    )
    if not any("active run" in issue.message for issue in incomplete):
        failures.append(f"an incomplete active run must fail its loop count: {incomplete}")

    candidate = {**current_2, "state": "HALT_SUCCESS_candidate"}
    stale_promotion = check_g18_review_history_append(
        current_2,
        {"loops": [*prior, current_1, candidate]},
    )
    if not any("must equal CURRENT_REVIEW.json" in issue.message for issue in stale_promotion):
        failures.append(f"a promotion not mirrored into history must fail: {stale_promotion}")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print("OK: G18 — reset history preserved, active-run count and promotion mirror enforced")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
