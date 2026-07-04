#!/usr/bin/env python3
"""Self-test: render_report.py turns a CURRENT_REVIEW.json (+ optional REVIEW_HISTORY)
into a self-contained, OFFLINE HTML dashboard — every {{TOKEN}} resolved, no leaks, no
network dependency — and also offers a markdown format.

No pytest in this repo (pyproject configures only ruff), so this standalone check builds
throwaway artifacts in a tempdir, runs the render CLI as a subprocess, and asserts on the
output text.

Cases:
  - html: all placeholders resolved (no "{{" leaks); fully offline (no <script src>,
    no http(s) CDN); scorecard rows for each dimension; a trend sparkline (<svg>/<polyline>)
    when history carries per-loop scores; a finding rendered.
  - markdown: a scorecard table emitted; --format honored.
  - compressed history (loop entries with no scorecard) -> renders without crashing.

Run: python3 scripts/_render_report_selftest.py   (exit 0 = pass, 1 = fail)
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

RENDER = Path(__file__).with_name("render_report.py")


def _review() -> dict:
    return {
        "schema_version": 2,
        "loop": 3,
        "loop_cap": 10,
        "state": "CONTINUE",
        "verdict": "Strong contender",
        "verdict_explanation": "Two dims still climbing.",
        "scorecard": {
            "architecture_quality": {
                "score": 10,
                "delta": "SAME",
                "proof": "A.swift:1",
                "residual_blocking_10": None,
                "residual_disposition": None,
                "residual_rationale_or_backlog_ref": None,
            },
            "concurrency": {
                "score": 9.5,
                "delta": "UP",
                "proof": "B.swift:8",
                "residual_blocking_10": "deinit carve-out",
                "residual_disposition": "accepted",
                "residual_rationale_or_backlog_ref": "Swift constraint; covered by test.",
            },
        },
        "strengths": ["Module graph enforced by source <like this & that>."],
        "findings": [
            {
                "title": "Reducer mutates shared state",
                "severity": "Serious deduction",
                "why_it_matters": "Two writers race on AppState.",
                "evidence": ["Core/AppState.swift:42"],
            },
        ],
    }


def _history_with_scores() -> dict:
    def loop_entry(n, arch, conc):
        return {
            "loop": n,
            "schema_version": 2,
            "state": "CONTINUE",
            "scorecard": {"architecture_quality": {"score": arch}, "concurrency": {"score": conc}},
        }

    return {"schema_version": 2, "loops": [loop_entry(1, 8.0, 7.5), loop_entry(2, 9.0, 9.0)]}


def _history_compressed() -> dict:
    return {
        "schema_version": 2,
        "loops": [
            {"loop": 1, "schema_version": 2, "state": "CONTINUE"},
            {"loop": 2, "schema_version": 2, "state": "CONTINUE"},
        ],
    }


def _run(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(RENDER), *args], capture_output=True, text=True)


def _write(path: Path, obj: dict) -> None:
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")


def main() -> int:
    if not RENDER.is_file():
        print(f"FAIL: render script missing: {RENDER}")
        return 1

    failures: list[str] = []
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        review = base / "CURRENT_REVIEW.json"
        hist = base / "REVIEW_HISTORY.json"
        _write(review, _review())
        _write(hist, _history_with_scores())

        # --- html with trend ---
        p = _run([str(review), "--history", str(hist), "--format", "html"])
        if p.returncode != 0:
            failures.append(f"html: non-zero exit\n{p.stderr.rstrip()}")
        else:
            html = p.stdout
            if "{{" in html or "}}" in html:
                leaked = [ln for ln in html.splitlines() if "{{" in ln or "}}" in ln]
                failures.append("html: unresolved placeholder(s):\n  " + "\n  ".join(leaked[:5]))
            if (
                "<script src" in html.lower()
                or "http://" in html.lower()
                or "https://" in html.lower()
            ):
                failures.append("html: must be offline — found a script src or http(s) URL")
            if "Concurrency" not in html and "concurrency" not in html:
                failures.append("html: concurrency dimension row missing")
            if "<polyline" not in html:
                failures.append(
                    "html: expected an inline <svg> sparkline (<polyline>) for the trend"
                )
            if "Reducer mutates shared state" not in html:
                failures.append("html: finding not rendered")
            # raw angle brackets from the strength text must be escaped, not injected
            if "<like this" in html:
                failures.append("html: unescaped user text injected (XSS/markup risk)")

        # --- markdown ---
        p = _run([str(review), "--format", "markdown"])
        if p.returncode != 0:
            failures.append(f"markdown: non-zero exit\n{p.stderr.rstrip()}")
        else:
            md = p.stdout
            names_present = ("Concurrency" in md) or ("concurrency" in md)
            if "|" not in md or not names_present:
                failures.append("markdown: expected a scorecard table mentioning the dimensions")

        # --- compressed history must not crash ---
        _write(hist, _history_compressed())
        p = _run([str(review), "--history", str(hist), "--format", "html"])
        if p.returncode != 0:
            failures.append(
                f"compressed-history: non-zero exit (should degrade gracefully)\n{p.stderr.rstrip()}"
            )
        elif "{{" in p.stdout:
            failures.append("compressed-history: unresolved placeholder leaked")

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    print(
        "OK: render_report — HTML resolves every placeholder, stays offline, draws "
        "inline-SVG trend sparklines, escapes user text; markdown table renders; "
        "compressed history degrades gracefully"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
