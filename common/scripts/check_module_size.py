#!/usr/bin/env python3
"""
check_module_size.py — Enforce per-module LoC caps.

Two thresholds:
- Soft cap (default 600 LoC): warning, advisory.
- Hard cap (default 800 LoC): non-zero exit unless the module declares
  an explicit waiver in its first 20 lines:

      # WAIVER: module-size <reason>

The waiver is intentionally noisy in a PR diff so reviewers see it and
can push back if the reason is weak. Use it sparingly.

Usage:

    check_module_size.py <module_dir> [--soft 600] [--hard 800]
    check_module_size.py quorum-review/scripts/quorum/
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

WAIVER_RE = re.compile(r"^\s*#\s*WAIVER:\s*module-size\b(.*)$")


def count_loc(path: Path) -> int:
    """Count physical lines in a Python file."""
    return sum(1 for _ in path.read_text(encoding="utf-8", errors="replace").splitlines())


def has_waiver(path: Path) -> tuple[bool, str | None]:
    """Return (waived, reason) by inspecting first 20 lines for a WAIVER comment."""
    with path.open(encoding="utf-8", errors="replace") as f:
        for i, line in enumerate(f):
            if i >= 20:
                break
            m = WAIVER_RE.match(line)
            if m:
                return True, m.group(1).strip(" :-") or "(no reason given)"
    return False, None


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("module_dir", help="Directory containing .py modules to check")
    parser.add_argument(
        "--soft", type=int, default=600, help="Soft cap (warning) in LoC. Default: 600."
    )
    parser.add_argument(
        "--hard", type=int, default=800, help="Hard cap (fail) in LoC. Default: 800."
    )
    args = parser.parse_args(argv)

    root = Path(args.module_dir).resolve()
    if not root.is_dir():
        print(f"error: not a directory: {root}", file=sys.stderr)
        return 2

    py_files = sorted(p for p in root.rglob("*.py") if "__pycache__" not in p.parts)
    warnings: list[str] = []
    failures: list[str] = []

    for path in py_files:
        loc = count_loc(path)
        rel = path.relative_to(root)
        if loc >= args.hard:
            waived, reason = has_waiver(path)
            if waived:
                print(f"WAIVED: {rel} ({loc} LoC, hard cap {args.hard}) — {reason}")
            else:
                failures.append(
                    f"  {rel} = {loc} LoC (hard cap {args.hard}). "
                    f"Split the module OR add `# WAIVER: module-size <reason>` in the first 20 lines."
                )
        elif loc >= args.soft:
            warnings.append(f"  {rel} = {loc} LoC (soft cap {args.soft}); consider splitting.")

    if warnings:
        print(f"check_module_size: {len(warnings)} soft-cap warning(s):", file=sys.stderr)
        for w in warnings:
            print(w, file=sys.stderr)

    if failures:
        print(f"check_module_size: {len(failures)} hard-cap violation(s):", file=sys.stderr)
        for f in failures:
            print(f, file=sys.stderr)
        return 1

    print(f"check_module_size: OK — {len(py_files)} modules under hard cap ({args.hard}).")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
