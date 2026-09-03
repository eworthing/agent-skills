#!/usr/bin/env python3
"""grade_site_pass.py -- site-level recall/restraint of a contest-refactor artifact
against a frozen OCR site manifest (SITE-PASS plan W0, 2026-09-03).

Usage:
  grade_site_pass.py <CURRENT_REVIEW.json> <manifest.json> [--baseline ARTIFACT]
                     [--label TEXT] [--json]

A manifest site is HIT when any finding's `evidence` entry cites the site's path
with a cited range that intersects the site's range; a single-line cite gets
+/- 5 lines. `verdict: real` hits are recall; `verdict: rejected` hits are
restraint failures unless the site is in the baseline exclusion set --
`--baseline` grades the pre-change artifact and records the rejected sites its
own findings already touch (the pinned rubric findings' known overlaps).
`roster_gap` lists manifest site paths absent from
`discovery.site_pass_roster.paths`; it is null when the artifact carries no
roster (every pre-site-pass artifact). Exit 0 always; numbers are the output.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# `path:12`, `path:12-40`, `path:311,316`, each optionally followed by ` (note)`.
_EVIDENCE_RE = re.compile(r"^\s*(?P<path>[^\s:]+):(?P<spans>\d+(?:-\d+)?(?:\s*,\s*\d+(?:-\d+)?)*)")
SINGLE_LINE_TOLERANCE = 5


def parse_evidence(entry: str) -> list[tuple[str, int, int]]:
    """One evidence string -> [(path, start, end)]; single lines widen by the tolerance."""
    m = _EVIDENCE_RE.match(entry or "")
    if not m:
        return []
    path = m.group("path")
    out = []
    for span in re.split(r"\s*,\s*", m.group("spans")):
        if "-" in span:
            a, b = (int(x) for x in span.split("-", 1))
            if b < a:
                a, b = b, a
            out.append((path, a, b))
        else:
            line = int(span)
            out.append((path, max(1, line - SINGLE_LINE_TOLERANCE), line + SINGLE_LINE_TOLERANCE))
    return out


def cited_spans(artifact: dict) -> list[tuple[str, int, int, str]]:
    spans = []
    for finding in artifact.get("findings") or []:
        fid = str(finding.get("id") or finding.get("stable_id") or "?")
        for entry in finding.get("evidence") or []:
            for path, a, b in parse_evidence(str(entry)):
                spans.append((path, a, b, fid))
    return spans


def hits_for(site: dict, spans: list[tuple[str, int, int, str]]) -> list[str]:
    s0, s1 = int(site["line_start"]), int(site["line_end"])
    return sorted(
        {fid for path, a, b, fid in spans if path == site["path"] and a <= s1 and b >= s0}
    )


def grade(
    artifact: dict, manifest: dict, baseline: dict | None = None, label: str | None = None
) -> dict:
    spans = cited_spans(artifact)
    exclusion: set[int] = set()
    if baseline is not None:
        bspans = cited_spans(baseline)
        exclusion = {
            int(s["fid"])
            for s in manifest.get("sites", [])
            if s["verdict"] == "rejected" and hits_for(s, bspans)
        }
    rows = []
    for site in manifest.get("sites", []):
        fids = hits_for(site, spans)
        rows.append(
            {
                "fid": int(site["fid"]),
                "verdict": site["verdict"],
                "question": site.get("question"),
                "path": site["path"],
                "lines": [int(site["line_start"]), int(site["line_end"])],
                "hit": bool(fids),
                "finding_ids": fids,
                "excluded": int(site["fid"]) in exclusion,
            }
        )
    real = [r for r in rows if r["verdict"] == "real"]
    rejected = [r for r in rows if r["verdict"] == "rejected"]
    roster = ((artifact.get("discovery") or {}).get("site_pass_roster") or {}).get("paths")
    roster_gap = (
        None
        if roster is None
        else sorted({s["path"] for s in manifest.get("sites", [])} - set(roster))
    )
    return {
        "label": label,
        "manifest_scope": manifest.get("scope"),
        "real_total": len(real),
        "real_hits": sum(r["hit"] for r in real),
        "rejected_total": len(rejected),
        "rejected_hits": sum(r["hit"] for r in rejected),
        "exclusion_set": sorted(exclusion),
        "restraint_failures": [r["fid"] for r in rejected if r["hit"] and not r["excluded"]],
        "roster_gap": roster_gap,
        "sites": rows,
    }


def _print_table(result: dict) -> None:
    print(f"grade_site_pass: {result['label'] or '-'} | scope {result['manifest_scope']}")
    for r in result["sites"]:
        mark = "HIT " if r["hit"] else "miss"
        excl = " (excluded)" if r["excluded"] else ""
        ids = ",".join(r["finding_ids"])
        print(
            f"  {mark} {r['verdict']:8s} {r['fid']:>4} {r['question'] or '--':3s} {r['path'].split('/')[-1]}:{r['lines'][0]}-{r['lines'][1]} {ids}{excl}"
        )
    print(
        f"real {result['real_hits']}/{result['real_total']} | rejected hits {result['rejected_hits']}/{result['rejected_total']}"
        f" | restraint failures {result['restraint_failures']} | exclusion {result['exclusion_set']}"
        f" | roster_gap {result['roster_gap'] if result['roster_gap'] is None else len(result['roster_gap'])}"
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("artifact")
    ap.add_argument("manifest")
    ap.add_argument("--baseline")
    ap.add_argument("--label")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    artifact = json.loads(Path(args.artifact).read_text())
    manifest = json.loads(Path(args.manifest).read_text())
    baseline = json.loads(Path(args.baseline).read_text()) if args.baseline else None
    result = grade(artifact, manifest, baseline, args.label)
    if args.json:
        json.dump(result, sys.stdout, indent=1)
        print()
    else:
        _print_table(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
