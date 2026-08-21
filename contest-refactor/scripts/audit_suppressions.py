#!/usr/bin/env python3
"""audit_suppressions.py — suppression and delivery-gate hygiene in the TARGET repo.

Candidate DD-06 (`docs/contest-refactor-detection-domains.md`). Points the skill's
own anti-fake-green instinct at the repository under review: a suppressed warning
and an absent warning look identical in a green build, and a CI gate that reports
failure while exiting 0 proves nothing at all.

Three checks, all deterministic greps -- this is a detector, not a judgment lens,
so it ships as a script rather than as loop-path prose and costs zero per-loop
tokens.

  1. Reason-free suppressions   -- `# noqa`, `# type: ignore`, `swiftlint:disable`,
     `#[allow(...)]`, `@ts-ignore`, `eslint-disable` carrying no rationale.
  2. Lint / type baselines      -- a baseline file is a frozen debt ledger; its
     entry count is the number of known defects the gate is instructed to ignore.
  3. Swallowed delivery gates   -- `continue-on-error: true`, `|| true`, or a
     trailing `exit 0` on a CI step that runs a checker.

EVERY HIT IS CANDIDATE EVIDENCE (`promotion_allowed: false`). A suppression with a
real rationale one line up is correct engineering, and this script cannot read
rationale -- only its absence on the same line. Method Step 3 re-derives every hit
against source before it can become a finding (Meta-Rule 1).

Exit: 0 clean, 2 hits found, 1 bad usage. Report-only either way.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import audit_boundaries as _ab

# Suppression token -> regex capturing the token and any rule ids that follow it.
# The trailing group is whatever prose is left on the line; empty prose with no
# comment on the line above is what makes a suppression reason-free.
SUPPRESSIONS: tuple[tuple[str, str], ...] = (
    ("noqa", r"#\s*noqa(?::\s*(?P<code>[A-Z]+[0-9]+(?:\s*,\s*[A-Z]+[0-9]+)*))?"),
    ("type-ignore", r"#\s*type:\s*ignore(?:\[(?P<code>[^\]]*)\])?"),
    ("swiftlint-disable", r"//\s*swiftlint:disable(?::\w+)?(?P<code>(?:\s+[\w_]+)*)"),
    ("rust-allow", r"#\[allow\((?P<code>[^)]*)\)\]"),
    ("ts-ignore", r"//\s*@ts-(?:ignore|expect-error)"),
    ("eslint-disable", r"//\s*eslint-disable(?:-next-line|-line)?(?P<code>(?:\s+[\w@/-]+)*)"),
    ("pylint-disable", r"#\s*pylint:\s*disable=(?P<code>[\w,-]+)"),
)

BASELINE_NAMES: frozenset[str] = frozenset(
    {
        ".swiftlint-baseline",
        "swiftlint-baseline.json",
        "mypy-baseline.json",
        ".mypy-baseline",
        "tslint-baseline.json",
        "eslint-baseline.json",
        ".pylint-baseline",
        "baseline.sarif",
    }
)

CI_GLOBS: tuple[str, ...] = (
    ".github/workflows/*.yml",
    ".github/workflows/*.yaml",
    ".gitlab-ci.yml",
    "azure-pipelines.yml",
    "Jenkinsfile",
    ".circleci/config.yml",
)

# A swallow only matters on a step that actually checks something.
CHECKER_WORDS = re.compile(
    r"\b(lint|test|typecheck|type-check|mypy|ruff|swiftlint|eslint|audit|check|"
    r"verify|validate|coverage|clippy|vet|sanitiz)",
    re.I,
)
SWALLOWERS: tuple[tuple[str, str], ...] = (
    ("continue-on-error", r"continue-on-error:\s*true"),
    ("or-true", r"\|\|\s*true\b"),
    ("or-exit-zero", r"\|\|\s*exit\s+0\b"),
    ("trailing-exit-zero", r";\s*exit\s+0\s*$"),
)

TEXT_SUFFIXES = frozenset(
    {".py", ".swift", ".rs", ".ts", ".tsx", ".js", ".jsx", ".go", ".kt", ".java", ".rb"}
)
# ponytail: 2 MiB/file cap keeps a vendored bundle or a generated blob from
# dominating the walk. Raise it if a real first-party source file is ever skipped.
MAX_BYTES = 2 * 1024 * 1024


def _walk(root: Path, include_tests: bool) -> list[Path]:
    out: list[Path] = []
    for p in sorted(root.rglob("*")):
        if not p.is_file() or p.suffix not in TEXT_SUFFIXES:
            continue
        if any(part in _ab.IGNORE_DIRS for part in p.parts):
            continue
        if not include_tests and _ab._is_test_file(p.name):
            continue
        try:
            if p.stat().st_size > MAX_BYTES:
                continue
        except OSError:
            continue
        out.append(p)
    return out


def _read_lines(path: Path) -> list[str]:
    try:
        return path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []


def _is_comment(line: str) -> bool:
    return line.lstrip().startswith(("#", "//", "/*", "*"))


def scan_suppressions(root: Path, include_tests: bool) -> list[dict]:
    """A suppression is reason-free when nothing but the token sits on its line
    and the line above is not a comment. Both halves matter: `# noqa: E501  keep
    the URL intact` is fine, and so is a bare `# noqa` under an explaining line.

    Reason-free splits again on **scope**, and the split is what keeps this usable:
    `blanket` names no rule and silences everything at that site, which is the
    class the candidate is actually about; `coded` names the rule it silences,
    which is narrow by construction and idiomatic in places (`# noqa: F401` on a
    deliberate re-export). Only `blanket` counts toward the headline. A `coded`
    hit is reported so the number is auditable, never so it reads as a defect."""
    hits: list[dict] = []
    compiled = [(kind, re.compile(pat)) for kind, pat in SUPPRESSIONS]
    for path in _walk(root, include_tests):
        lines = _read_lines(path)
        for i, line in enumerate(lines):
            for kind, rx in compiled:
                m = rx.search(line)
                if not m:
                    continue
                residue = (line[: m.start()] + line[m.end() :]).strip()
                # Code before the token is the suppressed statement, not a reason.
                trailing = line[m.end() :].strip(" \t#/*-:")
                prior_comment = i > 0 and _is_comment(lines[i - 1])
                if trailing or prior_comment:
                    continue
                code = (m.groupdict().get("code") or "").strip()
                hits.append(
                    {
                        "check": "reason_free_suppression",
                        "kind": kind,
                        "scope": "coded" if code else "blanket",
                        "rule": code or None,
                        "file": str(path.relative_to(root)),
                        "line": i + 1,
                        "has_code": bool(residue),
                    }
                )
                break
    return hits


def scan_baselines(root: Path) -> list[dict]:
    hits: list[dict] = []
    for p in sorted(root.rglob("*")):
        if not p.is_file() or p.name not in BASELINE_NAMES:
            continue
        if any(part in _ab.IGNORE_DIRS for part in p.parts):
            continue
        entries = -1
        try:
            raw = p.read_text(encoding="utf-8", errors="replace")
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                entries = len(parsed)
            elif isinstance(parsed, dict):
                entries = sum(len(v) if isinstance(v, list) else 1 for v in parsed.values())
        except (OSError, ValueError):
            # Not JSON, or unreadable: count non-blank lines instead of guessing.
            entries = sum(1 for ln in _read_lines(p) if ln.strip())
        hits.append(
            {
                "check": "lint_baseline",
                "file": str(p.relative_to(root)),
                "line": 1,
                "entries": entries,
            }
        )
    return hits


def scan_gates(root: Path) -> list[dict]:
    hits: list[dict] = []
    seen: set[Path] = set()
    compiled = [(kind, re.compile(pat)) for kind, pat in SWALLOWERS]
    for glob in CI_GLOBS:
        for p in sorted(root.glob(glob)):
            if not p.is_file() or p in seen:
                continue
            seen.add(p)
            lines = _read_lines(p)
            for i, line in enumerate(lines):
                for kind, rx in compiled:
                    if not rx.search(line):
                        continue
                    # The checker word may sit on the step's `name:`/`run:` line
                    # rather than on the swallowing line itself.
                    window = " ".join(lines[max(0, i - 3) : i + 2])
                    if not CHECKER_WORDS.search(window):
                        continue
                    hits.append(
                        {
                            "check": "swallowed_gate",
                            "kind": kind,
                            "file": str(p.relative_to(root)),
                            "line": i + 1,
                        }
                    )
                    break
    return hits


def audit(root: Path, include_tests: bool = False) -> dict:
    sup = scan_suppressions(root, include_tests)
    base = scan_baselines(root)
    gates = scan_gates(root)
    blanket = [h for h in sup if h["scope"] == "blanket"]
    # Only blanket suppressions and the two machinery checks are hits. A coded
    # suppression is disclosed under `counts`, never promoted into `hits` --
    # otherwise the detector reports idiom as defect and fails restraint.
    hits = blanket + base + gates
    return {
        "root": str(root),
        "promotion_allowed": False,
        "coded_suppressions": [h for h in sup if h["scope"] == "coded"],
        "counts": {
            "reason_free_suppression": len(blanket),
            "coded_suppression": len(sup) - len(blanket),
            "lint_baseline": len(base),
            "swallowed_gate": len(gates),
            "baseline_entries": sum(h["entries"] for h in base if h["entries"] > 0),
        },
        "hits": hits,
    }


def _render(report: dict) -> str:
    c = report["counts"]
    out = [
        "# suppression & delivery-gate hygiene (candidate evidence, promotion_allowed: false)",
        f"  blanket suppressions     : {c['reason_free_suppression']}"
        f"   (+{c['coded_suppression']} coded, disclosed not flagged)",
        f"  lint/type baselines      : {c['lint_baseline']} "
        f"({c['baseline_entries']} suppressed entries)",
        f"  swallowed delivery gates : {c['swallowed_gate']}",
    ]
    if report["hits"]:
        out.append("")
        out.append("| check | kind | file:line |")
        out.append("| --- | --- | --- |")
        for h in report["hits"][:60]:
            out.append(f"| {h['check']} | {h.get('kind', '-')} | {h['file']}:{h['line']} |")
        if len(report["hits"]) > 60:
            out.append(f"| … | … | {len(report['hits']) - 60} more not listed |")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("root", nargs="?", default=".", help="repo root to audit")
    ap.add_argument("--json", metavar="PATH", help="write the report as JSON")
    ap.add_argument("--include-tests", action="store_true", help="also scan test files")
    args = ap.parse_args(argv)

    root = Path(args.root).resolve()
    if not root.is_dir():
        print(f"audit_suppressions: not a directory: {root}", file=sys.stderr)
        return 1

    report = audit(root, include_tests=args.include_tests)
    if args.json:
        Path(args.json).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(_render(report))
    return 2 if report["hits"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
