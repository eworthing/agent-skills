#!/usr/bin/env python3
"""Self-test for G21-scorecard — HALT_SUCCESS scorecard gate.

Covers two RED-first fixes:
  - Finding 663: an empty/missing scorecard must not vacuously pass HALT_SUCCESS
    (universal quantification over zero dimensions is not satisfaction).
  - Finding 664: score must be strictly int/float (excluding bool) and finite --
    a numeric string like "10" must not coerce through float() and pass.

Run: python3 scripts/_g21_selftest.py   (exit 0 = pass, 1 = fail)
"""

from __future__ import annotations

import sys

from _selftest_lib import load_validator as _load_validator


def _art(scorecard, state="HALT_SUCCESS"):
    return {"state": state, "scorecard": scorecard}


def main() -> int:
    va = _load_validator()
    failures: list[str] = []

    # Baseline: a clean pass must stay clean.
    clean = _art({"simplicity": {"score": 10}})
    if va.check_g21_scorecard(clean):
        failures.append("clean score==10 scorecard should not fire G21")

    # Finding 663 — empty scorecard must FAIL, not vacuously pass.
    empty = _art({})
    if not va.check_g21_scorecard(empty):
        failures.append("empty scorecard on HALT_SUCCESS vacuously passed G21")

    missing = _art(None)
    if not va.check_g21_scorecard(missing):
        failures.append("missing scorecard on HALT_SUCCESS vacuously passed G21")

    # Finding 664 — a numeric string must not coerce through float() and pass.
    string_score = _art({"simplicity": {"score": "10"}})
    if not va.check_g21_scorecard(string_score):
        failures.append('score="10" (string) passed G21 instead of being rejected')

    # bool is technically an int subclass in Python -- must not coerce either.
    bool_score = _art({"simplicity": {"score": True}})
    if not va.check_g21_scorecard(bool_score):
        failures.append("score=True (bool) passed G21 instead of being rejected")

    # non-finite must still be rejected (pre-existing behavior, guard against regression).
    nan_score = _art({"simplicity": {"score": float("nan")}})
    if not va.check_g21_scorecard(nan_score):
        failures.append("score=nan passed G21 instead of being rejected")

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    print("OK: G21-scorecard rejects empty scorecards and non-numeric/non-finite scores")
    return 0


if __name__ == "__main__":
    sys.exit(main())
