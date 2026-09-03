#!/usr/bin/env python3
"""site_pass_roster.py -- the pinned file roster for a scoped run's site pass.

Usage:
  site_pass_roster.py <repo-root> --scope DIR --json

Prints `{"scope": "<dir>", "paths": [...], "digest": "<sha256 hex>"}`: every
first-party source file under DIR by `coverage_ledger.first_party_files`'s
enumerator and filters (vendor/build, fixture corpora, test files, generated
files excluded), as repo-relative POSIX paths sorted by byte order. The digest
is sha256 over the paths joined by "\\n" and encoded UTF-8. Step 0 (main agent)
runs this when `--scope` is set and assigns the decoded object unchanged to
`discovery.site_pass_roster`; preflight re-emits and requires equality; G52
compares `site_pass.files[].path` to `paths` and re-derives `digest`.
Exit 2 without `--scope` -- there is no unscoped mode (SITE-PASS plan, rev 5).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from coverage_ledger import first_party_files


def roster_digest(paths: list[str]) -> str:
    return hashlib.sha256("\n".join(paths).encode("utf-8")).hexdigest()


def build_roster(repo_root: Path, scope_rel: str) -> dict:
    paths, _excluded, missing = first_party_files(repo_root, [scope_rel])
    if missing:
        raise FileNotFoundError(scope_rel)
    paths = sorted(paths, key=lambda p: p.encode("utf-8"))
    return {"scope": scope_rel, "paths": paths, "digest": roster_digest(paths)}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("repo_root", nargs="?", default=".")
    ap.add_argument("--scope", help="subdirectory of repo_root the run is narrowed to (required)")
    ap.add_argument("--json", action="store_true", help="emit JSON (the only output mode)")
    args = ap.parse_args(argv)
    repo_root = Path(args.repo_root)
    if not repo_root.is_dir():
        sys.stderr.write(f"site_pass_roster: repo root does not exist: {args.repo_root}\n")
        return 2
    if not args.scope:
        sys.stderr.write("site_pass_roster: --scope is required; there is no unscoped roster\n")
        return 2
    scope = Path(args.scope)
    scope_abs = scope if scope.is_absolute() else repo_root / scope
    if not scope_abs.is_dir():
        sys.stderr.write(f"site_pass_roster: --scope directory does not exist: {args.scope}\n")
        return 2
    try:
        scope_rel = scope_abs.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        sys.stderr.write(
            f"site_pass_roster: --scope must be a subdirectory of repo_root: {args.scope}\n"
        )
        return 2
    roster = build_roster(repo_root, scope_rel)
    json.dump(roster, sys.stdout, indent=1)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
