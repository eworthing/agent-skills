#!/usr/bin/env python3
"""Self-test: the `--strictness` preset never reaches the HALT_SUCCESS threshold.

`--strictness aggressive` raises the *evidence* an inline accepted residual must
carry before the Critic may mark it `accepted` (a directive in
architecture-rubric.md). It must NOT change the pass/fail *threshold*: G21/G5 and
HALT_SUCCESS gating stay `score == 10 OR (score >= 9.5 AND disposition ==
"accepted")` regardless of preset.

This check enforces that programmatically against the REAL gate functions in
validate-artifact.py: it runs `check_g21_scorecard` and `check_halt_success_gating`
on artifacts identical except for `strictness` and asserts the verdict is
byte-identical. If a future edit ever wires `strictness` into a threshold, the
boundary cases below diverge and this fails.

No pytest in this repo (pyproject configures only ruff) → standalone _*.py helper.

Run: python3 scripts/_strictness_isolation_selftest.py   (exit 0 = pass, 1 = fail)
"""

from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path


def _load_validator():
    path = Path(__file__).with_name("validate-artifact.py")
    spec = importlib.util.spec_from_file_location("_va_strictness", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _artifact(score: float, disposition: str | None) -> dict:
    entry = {"score": score, "residual_disposition": disposition}
    return {
        "state": "HALT_SUCCESS",
        "scorecard": {"architecture_quality": entry},
        "findings": [],
    }


# (label, score, disposition): the boundary + the cases on either side of it.
CASES = [
    ("9.5-accepted (pass boundary)", 9.5, "accepted"),
    ("10-clean (pass)", 10, None),
    ("9.5-queued (fail)", 9.5, "queued"),
    ("9.4-accepted (sub-threshold fail)", 9.4, "accepted"),
]


def _verdict(va, art: dict) -> list[str]:
    issues = va.check_g21_scorecard(art) + va.check_halt_success_gating(art, None)
    return sorted(f"{i.rule}: {i.message}" for i in issues)


def main() -> int:
    va = _load_validator()
    failures: list[str] = []

    for label, score, disp in CASES:
        std = _artifact(score, disp)
        std["strictness"] = "standard"
        agg = copy.deepcopy(std)
        agg["strictness"] = "aggressive"

        v_std = _verdict(va, std)
        v_agg = _verdict(va, agg)
        if v_std != v_agg:
            failures.append(
                f"{label}: preset changed the verdict\n  standard:   {v_std}\n  aggressive: {v_agg}"
            )

    # Sanity: the boundary really does separate pass from fail (so the test above
    # isn't vacuously comparing two always-empty verdicts).
    if _verdict(va, _artifact(9.5, "accepted")):
        failures.append("expected 9.5-accepted to PASS the gate (got issues)")
    if not _verdict(va, _artifact(9.4, "accepted")):
        failures.append("expected 9.4-accepted to FAIL the gate (got none)")

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    print(
        f"OK: strictness is threshold-independent — {len(CASES)} boundary case(s) "
        "give an identical HALT_SUCCESS verdict under standard and aggressive"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
