#!/usr/bin/env python3
"""Cross-loop metric-regression alarm — advisory evidence ONLY, never a score or gate.

A refactor can pass the LLM scorecard while a hard metric silently slid backwards:
coverage fell, lint count rose, complexity grew. This deterministic check reads the
per-loop `loop_metrics` recorded in REVIEW_HISTORY.json (and, optionally, the current
review), and flags any metric that moved the *wrong way* on its latest transition.

Doctrine boundary (Meta-Rule 1, method.md; Part 1c anti-fit): the output is a candidate
finding the Critic *investigates*. It is NOT a verdict. This script assigns no score,
fails no gate, and writes no artifact field. A metric-as-verdict oracle is exactly what
the rubric exists to defeat; this is the diagnostic half that stays on the evidence side
of that line. `_metric_isolation_selftest.py` proves the metric field never reaches a
gate path. Stdlib-only, Python 3.11+. Always exits 0 (advisory).

Usage:
    audit_metric_trend.py <REVIEW_HISTORY.json> [--current CURRENT_REVIEW.json]
"""

from __future__ import annotations

import argparse
import contextlib
import json
import sys
from pathlib import Path

# metric key -> (human label, "bad direction"): does a HIGHER value mean worse?
_METRICS = {
    "coverage_pct": ("coverage", False),   # lower is worse
    "lint_count": ("lint count", True),    # higher is worse
    "complexity": ("complexity", True),    # higher is worse
}


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _series(loops: list[dict], metric: str) -> list[tuple[int, float]]:
    """Ordered (loop, value) points for one metric across loops that recorded it."""
    pts: list[tuple[int, float]] = []
    for entry in sorted(loops, key=lambda e: e.get("loop", 0)):
        m = entry.get("loop_metrics") or {}
        v = m.get(metric)
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            pts.append((int(entry.get("loop", 0)), float(v)))
    return pts


def _regression(metric: str, prev: float, curr: float) -> bool:
    _, higher_is_worse = _METRICS[metric]
    return curr > prev if higher_is_worse else curr < prev


def audit(loops: list[dict]) -> list[str]:
    """Return one advisory line per metric that regressed on its latest transition."""
    alarms: list[str] = []
    for metric, (label, _) in _METRICS.items():
        pts = _series(loops, metric)
        if len(pts) < 2:
            continue
        (lp, pv), (lc, cv) = pts[-2], pts[-1]
        if _regression(metric, pv, cv):
            direction = "rose" if _METRICS[metric][1] else "fell"
            alarms.append(
                f"METRIC REGRESSION: {label} {direction} {pv:g} -> {cv:g} "
                f"(loop {lp} -> {lc}). Investigate before trusting the scorecard delta; "
                f"this is evidence for the Critic, not a score or gate."
            )
    return alarms


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Advisory cross-loop metric-regression alarm (never scores or gates)."
    )
    parser.add_argument("history", help="path to REVIEW_HISTORY.json")
    parser.add_argument("--current", help="path to CURRENT_REVIEW.json (appended as the latest loop)")
    args = parser.parse_args(argv)

    history_path = Path(args.history)
    if not history_path.is_file():
        print(f"audit_metric_trend: history not found: {history_path}", file=sys.stderr)
        return 0  # advisory tool: a missing history is not a hard failure
    try:
        loops = list(_load_json(history_path).get("loops") or [])
    except (json.JSONDecodeError, OSError) as exc:
        print(f"audit_metric_trend: cannot read history: {exc}", file=sys.stderr)
        return 0

    if args.current:
        current_path = Path(args.current)
        if current_path.is_file():
            with contextlib.suppress(json.JSONDecodeError, OSError):
                loops.append(_load_json(current_path))

    alarms = audit(loops)
    if alarms:
        print("audit_metric_trend: advisory metric-regression evidence (NOT a score/gate):")
        for line in alarms:
            print(f"  - {line}")
    else:
        print(f"audit_metric_trend: no metric regressions across {len(loops)} loop(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
