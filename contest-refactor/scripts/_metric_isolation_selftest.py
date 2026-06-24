#!/usr/bin/env python3
"""Self-test: the optional `loop_metrics` field never reaches a score or gate path.

T2.4 records hard metrics (coverage, lint, complexity) per loop and lets a deterministic
alarm (audit_metric_trend.py) surface regressions as *evidence*. The doctrine line (Part
1c / Meta-Rule 1) is that a metric must never become a verdict. This check enforces that
programmatically against the REAL gate functions in validate-artifact.py: it runs
`check_g21_scorecard` and `check_halt_success_gating` on artifacts that are identical
except for `loop_metrics` — absent, "healthy" numbers, and "regressed" numbers — and
asserts the HALT_SUCCESS verdict is byte-identical. If a future edit ever wires
loop_metrics into a threshold, the variants diverge and this fails.

No pytest in this repo (pyproject configures only ruff) -> standalone _*.py helper.

Run: python3 scripts/_metric_isolation_selftest.py   (exit 0 = pass, 1 = fail)
"""

from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path


def _load_validator():
    path = Path(__file__).with_name("validate-artifact.py")
    spec = importlib.util.spec_from_file_location("_va_metric", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _artifact(score: float, disposition: str | None) -> dict:
    return {
        "state": "HALT_SUCCESS",
        "scorecard": {"architecture_quality": {"score": score, "residual_disposition": disposition}},
        "findings": [],
    }


# The HALT_SUCCESS boundary + the cases on either side of it.
CASES = [
    ("9.5-accepted (pass boundary)", 9.5, "accepted"),
    ("10-clean (pass)", 10, None),
    ("9.5-queued (fail)", 9.5, "queued"),
    ("9.4-accepted (sub-threshold fail)", 9.4, "accepted"),
]

# loop_metrics variants that must all yield the SAME verdict as no metrics at all.
METRIC_VARIANTS = {
    "absent": None,
    "healthy": {"coverage_pct": 92.0, "lint_count": 0, "complexity": 8},
    "regressed": {"coverage_pct": 41.0, "lint_count": 99, "complexity": 80},
}


def _verdict(va, art: dict) -> list[str]:
    issues = va.check_g21_scorecard(art) + va.check_halt_success_gating(art, None)
    return sorted(f"{i.rule}: {i.message}" for i in issues)


def main() -> int:
    va = _load_validator()
    failures: list[str] = []

    for label, score, disp in CASES:
        baseline = _verdict(va, _artifact(score, disp))  # no loop_metrics
        for vname, metrics in METRIC_VARIANTS.items():
            art = _artifact(score, disp)
            if metrics is not None:
                art["loop_metrics"] = copy.deepcopy(metrics)
            v = _verdict(va, art)
            if v != baseline:
                failures.append(
                    f"{label} / loop_metrics={vname}: metric field changed the verdict\n"
                    f"  no-metrics: {baseline}\n  {vname}: {v}"
                )

    # Sanity: the boundary really separates pass from fail (test isn't vacuous).
    if _verdict(va, _artifact(9.5, "accepted")):
        failures.append("expected 9.5-accepted to PASS the gate (got issues)")
    if not _verdict(va, _artifact(9.4, "accepted")):
        failures.append("expected 9.4-accepted to FAIL the gate (got none)")

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    print(
        f"OK: loop_metrics is gate-independent — {len(CASES)} boundary case(s) give an "
        f"identical HALT_SUCCESS verdict whether loop_metrics is absent, healthy, or regressed"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
