#!/usr/bin/env python3
"""Self-test: audit_metric_trend.py raises an ADVISORY alarm when a hard metric moves
the wrong way between loops, and stays silent when metrics hold or are absent.

This is the diagnostic half of the deterministic-scoring idea the doctrine keeps (Part
1c / Meta-Rule 1): a deterministic "did coverage/complexity/lint move the wrong way?"
signal that *feeds* the Critic as evidence — never a score, never a gate. The alarm
emits a `METRIC REGRESSION` candidate line; downstream judgment decides what it means.

No pytest in this repo (pyproject configures only ruff), so this standalone check builds
throwaway REVIEW_HISTORY.json files in a tempdir, runs the audit CLI as a subprocess, and
asserts on stdout. "METRIC REGRESSION" present == an alarm was raised.

Cases:
  - coverage_pct drops between loops      -> alarm naming coverage
  - lint_count rises                      -> alarm naming lint
  - complexity rises                      -> alarm naming complexity
  - every metric stable or improving      -> silent
  - loop entries with no loop_metrics      -> no crash, silent

Run: python3 scripts/_audit_metric_trend_selftest.py   (exit 0 = pass, 1 = fail)
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

AUDIT = Path(__file__).with_name("audit_metric_trend.py")


def _history(metrics_by_loop: list[dict | None]) -> dict:
    loops = []
    for i, m in enumerate(metrics_by_loop, start=1):
        entry = {"loop": i, "schema_version": 2, "state": "CONTINUE"}
        if m is not None:
            entry["loop_metrics"] = m
        loops.append(entry)
    return {"schema_version": 2, "loops": loops}


def _run(path: Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(AUDIT), str(path)], capture_output=True, text=True)


def main() -> int:
    if not AUDIT.is_file():
        print(f"FAIL: audit script missing: {AUDIT}")
        return 1

    failures: list[str] = []
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)

        def check(name: str, metrics: list[dict | None], expect_alarm: bool, needle: str | None = None):
            path = base / f"{name}.json"
            path.write_text(json.dumps(_history(metrics), indent=2), encoding="utf-8")
            p = _run(path)
            if p.returncode != 0:
                failures.append(f"{name}: non-zero exit (alarm is advisory, must exit 0)\n{p.stderr.rstrip()}")
                return
            alarmed = "METRIC REGRESSION" in p.stdout
            if alarmed != expect_alarm:
                verb = "expected an alarm, got none" if expect_alarm else "false alarm"
                failures.append(f"{name}: {verb}\n--- stdout ---\n{p.stdout.rstrip()}")
            elif expect_alarm and needle and needle not in p.stdout.lower():
                failures.append(f"{name}: alarm should name {needle!r}\n{p.stdout.rstrip()}")

        check("coverage-drop", [{"coverage_pct": 82.0}, {"coverage_pct": 74.5}], True, "coverage")
        check("lint-up", [{"lint_count": 3}, {"lint_count": 11}], True, "lint")
        check("complexity-up", [{"complexity": 12}, {"complexity": 19}], True, "complexity")
        check("all-stable", [{"coverage_pct": 80, "lint_count": 2, "complexity": 10},
                             {"coverage_pct": 80, "lint_count": 2, "complexity": 10}], False)
        check("improving", [{"coverage_pct": 70, "lint_count": 9, "complexity": 20},
                            {"coverage_pct": 85, "lint_count": 1, "complexity": 11}], False)
        check("no-metrics", [None, None], False)

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    print(
        "OK: audit_metric_trend — coverage drop / lint rise / complexity rise each raise "
        "an advisory alarm; stable, improving, and metric-less histories stay silent"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
