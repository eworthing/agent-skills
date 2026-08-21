#!/usr/bin/env python3
"""Coverage-citation analyzer — item 24's missing decision data.

Read-only: walks every historical CURRENT_REVIEW.json blob in a target repo,
extracts file-path citations from ALL string values (schema-agnostic on
purpose — findings, scorecard proofs, evidence, prose), and maps them against
the repo's file inventory at HEAD. Output: how uneven the loop's actual
coverage is, per top-level directory.

Caveats stated in the report: inventory is at HEAD, so citations of deleted
files land in `unresolved`; a citation is attributed by unique suffix match,
ambiguous basenames are counted separately, never guessed.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

EXTS = (
    "swift|py|pyi|ts|tsx|js|jsx|mjs|md|json|jsonl|sh|bash|yml|yaml|toml|cs|kt|kts|java"
    "|m|mm|h|c|cc|cpp|hpp|rs|go|rb|plist|xcconfig|entitlements|strings|sql|proto"
)
CITE_RE = re.compile(rf"[A-Za-z0-9_\-./+]*[A-Za-z0-9_\-+]\.(?:{EXTS})\b(?::\d+)?")


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)


def _strings(obj) -> list[str]:
    out: list[str] = []
    stack = [obj]
    while stack:
        cur = stack.pop()
        if isinstance(cur, str):
            out.append(cur)
        elif isinstance(cur, dict):
            stack.extend(cur.values())
        elif isinstance(cur, list):
            stack.extend(cur)
    return out


def collect_citations(repo: Path) -> Counter[str]:
    log = _git(repo, "log", "--reverse", "--format=%H", "--", "CURRENT_REVIEW.json")
    cites: Counter[str] = Counter()
    for commit in log.stdout.split():
        show = _git(repo, "show", f"{commit}:CURRENT_REVIEW.json")
        if show.returncode != 0:
            continue
        try:
            art = json.loads(show.stdout)
        except json.JSONDecodeError:
            continue
        for s in _strings(art):
            for m in CITE_RE.findall(s):
                cites[m.rsplit(":", 1)[0] if re.search(r":\d+$", m) else m] += 1
    return cites


def resolve(cites: Counter[str], inventory: list[str]) -> dict:
    inv_set = set(inventory)
    by_suffix: dict[str, list[str]] = {}
    for p in inventory:
        parts = p.split("/")
        for i in range(len(parts)):
            by_suffix.setdefault("/".join(parts[i:]), []).append(p)
    resolved: Counter[str] = Counter()
    ambiguous: Counter[str] = Counter()
    unresolved: Counter[str] = Counter()
    for cand, n in cites.items():
        c = cand.lstrip("./")
        if c in inv_set:
            resolved[c] += n
            continue
        hits = by_suffix.get(c, [])
        if len(hits) == 1:
            resolved[hits[0]] += n
        elif len(hits) > 1:
            ambiguous[c] += n
        else:
            unresolved[c] += n
    return {"resolved": resolved, "ambiguous": ambiguous, "unresolved": unresolved}


def to_markdown(repo: Path, r: dict, inventory: list[str]) -> str:
    resolved: Counter[str] = r["resolved"]
    by_dir_total: Counter[str] = Counter()
    by_dir_cited: Counter[str] = Counter()
    for p in inventory:
        by_dir_total[p.split("/", 1)[0]] += 1
    for p in resolved:
        by_dir_cited[p.split("/", 1)[0]] += 1
    out = [
        f"# Coverage citations — {repo}",
        "",
        f"Inventory at HEAD: {len(inventory)} files. Cited (resolved): {len(resolved)} files, "
        f"{sum(resolved.values())} citations. Ambiguous: {len(r['ambiguous'])} names. "
        f"Unresolved (deleted/non-repo): {len(r['unresolved'])} names.",
        "",
        "| top-level dir | files | cited | coverage |",
        "|---|---|---|---|",
    ]
    for d, total in by_dir_total.most_common():
        cited = by_dir_cited.get(d, 0)
        out.append(f"| {d} | {total} | {cited} | {cited / total:.0%} |")
    out += ["", "## Most-cited files", ""]
    out += [f"- {p} — {n}" for p, n in resolved.most_common(25)]
    out += ["", "## Ambiguous citations (unattributed, never guessed)", ""]
    out += [f"- {p} — {n}" for p, n in r["ambiguous"].most_common(15)] or ["- none"]
    out += ["", "## Unresolved citations (deleted files, tool names, non-repo paths)", ""]
    out += [f"- {p} — {n}" for p, n in r["unresolved"].most_common(15)] or ["- none"]
    out.append("")
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("repo", type=Path)
    ap.add_argument("--out-json", type=Path)
    ap.add_argument("--out-md", type=Path)
    args = ap.parse_args()
    repo = args.repo.resolve()
    inventory = [
        p for p in _git(repo, "ls-files").stdout.splitlines() if re.search(rf"\.(?:{EXTS})$", p)
    ]
    cites = collect_citations(repo)
    r = resolve(cites, inventory)
    md = to_markdown(repo, r, inventory)
    if args.out_json:
        args.out_json.write_text(
            json.dumps(
                {
                    "repo": str(repo),
                    "inventory_files": len(inventory),
                    "resolved": dict(r["resolved"]),
                    "ambiguous": dict(r["ambiguous"]),
                    "unresolved": dict(r["unresolved"]),
                },
                indent=1,
            )
            + "\n"
        )
    if args.out_md:
        args.out_md.write_text(md)
    else:
        print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
