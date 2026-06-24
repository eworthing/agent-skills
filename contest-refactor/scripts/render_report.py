#!/usr/bin/env python3
"""Render a contest-refactor review into a self-contained report (HTML or markdown).

The loop already emits CURRENT_REVIEW.md (human) + .json (machine). This adds an
at-a-glance dashboard: the 9-dimension scorecard plus a per-dimension score *trend*
across loops, drawn from REVIEW_HISTORY.json. The HTML form is fully OFFLINE — inline
CSS, hand-rolled inline-SVG sparklines, no d3, no external <script src>, no CDN — so a
committed report renders with no network (shadowX4fox@ed5118f, adapted: CDN dropped in
favour of inline SVG). Read-only: never mutates artifacts, scores, or gates.

Usage:
    render_report.py <CURRENT_REVIEW.json> [--history REVIEW_HISTORY.json]
                     [--format html|markdown] [-o OUT]

Exit codes: 0 = rendered; 2 = usage / unreadable input.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import tomllib
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
SKELETON = SKILL_ROOT / "assets" / "report-skeleton.html"

_DELTAS = {"UP", "DOWN", "SAME"}


def _die(msg: str) -> int:
    print(f"render_report: {msg}", file=sys.stderr)
    return 2


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _dimension_labels() -> dict[str, str]:
    """id -> display_label from canon (falls back to the id if canon is unavailable)."""
    canon = SKILL_ROOT / "canon" / "scorecard-dimensions.toml"
    try:
        data = tomllib.loads(canon.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return {}
    return {d["id"]: d.get("display_label", d["id"]) for d in data.get("scorecard_dimensions", [])}


def _ordered_dims(scorecard: dict, labels: dict[str, str]) -> list[str]:
    """Canonical order first (for the dims present), then any extras in insertion order."""
    ordered = [d for d in labels if d in scorecard]
    ordered += [d for d in scorecard if d not in labels]
    return ordered


def _score_series(dim: str, current: float | None, history: list[dict]) -> list[float]:
    """Per-loop scores for one dimension, oldest first, with the current loop appended.

    History entries may be compressed (no scorecard) — those simply contribute no point.
    """
    pts: list[float] = []
    for entry in sorted(history, key=lambda e: e.get("loop", 0)):
        cell = (entry.get("scorecard") or {}).get(dim)
        if isinstance(cell, dict) and isinstance(cell.get("score"), (int, float)):
            pts.append(float(cell["score"]))
    if isinstance(current, (int, float)):
        pts.append(float(current))
    return pts


def _sparkline_svg(points: list[float]) -> str:
    """A tiny inline SVG sparkline mapping score 0..10 to a 120x24 box. No deps."""
    w, h, pad = 120, 24, 3
    if not points:
        return '<span class="empty">—</span>'
    if len(points) == 1:
        y = h - pad - (h - 2 * pad) * (points[0] / 10.0)
        return (f'<svg class="spark" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
                f'role="img" aria-label="score trend">'
                f'<circle cx="{w - pad}" cy="{y:.1f}" r="2.2"/></svg>')
    n = len(points)
    xs = [pad + (w - 2 * pad) * i / (n - 1) for i in range(n)]
    ys = [h - pad - (h - 2 * pad) * (p / 10.0) for p in points]
    poly = " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, ys, strict=True))
    return (f'<svg class="spark" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
            f'role="img" aria-label="score trend {points[0]:g} to {points[-1]:g}">'
            f'<polyline points="{poly}"/></svg>')


def _esc(value: object) -> str:
    return html.escape("" if value is None else str(value))


def _scorecard_rows_html(review: dict, history: list[dict], labels: dict[str, str]) -> str:
    scorecard = review.get("scorecard") or {}
    rows: list[str] = []
    for dim in _ordered_dims(scorecard, labels):
        cell = scorecard.get(dim) or {}
        label = labels.get(dim, dim)
        score = cell.get("score")
        delta = cell.get("delta") if cell.get("delta") in _DELTAS else "SAME"
        spark = _sparkline_svg(_score_series(dim, score, history))
        residual = cell.get("residual_blocking_10")
        disposition = cell.get("residual_disposition")
        resid_txt = ""
        if residual:
            resid_txt = f"{_esc(residual)}"
            if disposition:
                resid_txt += f" <em>({_esc(disposition)})</em>"
        rows.append(
            "<tr>"
            f"<td>{_esc(label)}</td>"
            f'<td class="num">{_esc(score)}</td>'
            f'<td class="delta-{_esc(delta)}">{_esc(delta)}</td>'
            f"<td>{spark}</td>"
            f'<td class="residual">{resid_txt}</td>'
            "</tr>"
        )
    return "\n        ".join(rows)


def _strengths_html(review: dict) -> str:
    items = review.get("strengths") or []
    if not items:
        return '<li class="empty">None recorded.</li>'
    return "".join(f"<li>{_esc(s)}</li>" for s in items)


def _findings_html(review: dict) -> str:
    findings = review.get("findings") or []
    if not findings:
        return '<p class="empty">No open findings.</p>'
    blocks: list[str] = []
    for f in findings:
        sev = _esc(f.get("severity"))
        title = _esc(f.get("title"))
        why = _esc(f.get("why_it_matters") or f.get("what_is_wrong") or "")
        evidence = ", ".join(_esc(e) for e in (f.get("evidence") or []))
        block = f'<div class="finding"><span class="sev">{sev}</span> — {title}'
        if why:
            block += f"<br>{why}"
        if evidence:
            block += f'<br><span class="residual">{evidence}</span>'
        block += "</div>"
        blocks.append(block)
    return "\n    ".join(blocks)


def render_html(review: dict, history: list[dict], labels: dict[str, str], generated: str) -> str:
    if not SKELETON.is_file():
        raise FileNotFoundError(f"missing skeleton: {SKELETON}")
    skeleton = SKELETON.read_text(encoding="utf-8")
    # Drop the authoring comment (it documents the {{TOKEN}} set and is not part of the
    # rendered output); this also keeps the report free of stray placeholder text.
    skeleton = re.sub(r"<!--.*?-->", "", skeleton, flags=re.DOTALL).lstrip("\n")
    loop = review.get("loop", "?")
    loop_cap = review.get("loop_cap", "?")
    subtitle = f"{_esc(review.get('state'))} · loop {_esc(loop)}/{_esc(loop_cap)} · {_esc(review.get('verdict'))}"
    tokens = {
        "{{TITLE}}": f"contest-refactor — loop {_esc(loop)}",
        "{{SUBTITLE}}": subtitle,
        "{{VERDICT_EXPLAIN}}": _esc(review.get("verdict_explanation") or review.get("narrative") or ""),
        "{{SCORECARD_ROWS}}": _scorecard_rows_html(review, history, labels),
        "{{STRENGTHS}}": _strengths_html(review),
        "{{FINDINGS}}": _findings_html(review),
        "{{GENERATED}}": _esc(generated),
    }
    out = skeleton
    for token, value in tokens.items():
        out = out.replace(token, value)
    return out


def render_markdown(review: dict, history: list[dict], labels: dict[str, str], generated: str) -> str:
    scorecard = review.get("scorecard") or {}
    lines = [
        f"# contest-refactor report — loop {review.get('loop', '?')}",
        "",
        f"**State:** {review.get('state')} · **Verdict:** {review.get('verdict')}",
        "",
        f"_{review.get('verdict_explanation') or review.get('narrative') or ''}_",
        "",
        "| Dimension | Score | Δ | Trend | Residual |",
        "|---|---|---|---|---|",
    ]
    for dim in _ordered_dims(scorecard, labels):
        cell = scorecard.get(dim) or {}
        label = labels.get(dim, dim)
        series = _score_series(dim, cell.get("score"), history)
        trend = " → ".join(f"{p:g}" for p in series) if series else "—"
        residual = cell.get("residual_blocking_10") or ""
        if residual and cell.get("residual_disposition"):
            residual += f" ({cell['residual_disposition']})"
        lines.append(f"| {label} | {cell.get('score')} | {cell.get('delta', '')} | {trend} | {residual} |")
    findings = review.get("findings") or []
    lines += ["", "## Findings", ""]
    if findings:
        for f in findings:
            lines.append(f"- **{f.get('severity')}** — {f.get('title')}")
    else:
        lines.append("_No open findings._")
    lines += ["", f"_Generated {generated}._", ""]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render a contest-refactor review as HTML or markdown.")
    parser.add_argument("review", help="path to CURRENT_REVIEW.json")
    parser.add_argument("--history", help="path to REVIEW_HISTORY.json (enables trend sparklines)")
    parser.add_argument("--format", choices=("html", "markdown"), default="html")
    parser.add_argument("-o", "--output", help="write here instead of stdout")
    args = parser.parse_args(argv)

    review_path = Path(args.review)
    if not review_path.is_file():
        return _die(f"review not found: {review_path}")
    try:
        review = _load_json(review_path)
    except (json.JSONDecodeError, OSError) as exc:
        return _die(f"cannot read review {review_path}: {exc}")

    history: list[dict] = []
    if args.history:
        history_path = Path(args.history)
        if not history_path.is_file():
            return _die(f"history not found: {history_path}")
        try:
            history = (_load_json(history_path).get("loops") or [])
        except (json.JSONDecodeError, OSError) as exc:
            return _die(f"cannot read history {history_path}: {exc}")

    labels = _dimension_labels()
    # Stamp from the artifact when present; this script is invoked by a human, so a wall
    # clock is fine, but we avoid embedding one in tests by preferring an artifact field.
    generated = str(review.get("generated_at") or "report")

    if args.format == "html":
        text = render_html(review, history, labels, generated)
    else:
        text = render_markdown(review, history, labels, generated) + "\n"

    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
