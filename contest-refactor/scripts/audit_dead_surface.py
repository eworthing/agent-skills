#!/usr/bin/env python3
"""audit_dead_surface.py — zero-production-reference Swift declarations.

Candidate DD-16 (`docs/contest-refactor-detection-domains.md`), OCR-GAP-
REMEDIATION-PLAN-2026-09-03 wave W2. `simplicity` is a scored dimension and
the loop already sweeps this by hand for `public` decls with zero cross-
module callers (`audit-public-surface.sh`); this aid widens the same idea to
enum cases, protocol requirements, and intra-module members at every access
level.

Declaration candidate set: enum cases; named `func`/`var` protocol
requirements (`subscript`/`init` excluded -- their use sites carry no member
name a lexical rule can count); type-member `var`/`let`/`func`/`static ...`/
computed properties declared directly in a type body or a type extension.
Excluded: locals, closure params, `init`s, anything nested inside a
`#Preview` block or a `PreviewProvider` type, and `@objc`/`@IBAction`/
`@IBOutlet`/`@main`-attributed members.

Reference counting is lexical and deliberately conservative: any bare
occurrence of the name counts (a shadowed or overloaded name is never
flagged -- false negatives are accepted, false positives are the enemy),
except enum cases, which require a leading `.` and exclude pattern
positions (`case .name`, `.name:`/`.name,` list continuations). Parsing and
counting both live in `_dead_surface_refs.py`.

Output rows exist ONLY for declarations with zero production references,
split by where their only references (if any) live: `dead` (none anywhere),
`test_only`, `preview_only`. EVERY ROW IS CANDIDATE EVIDENCE
(`promotion_allowed: false`) -- Method re-derives before it can become a
finding (Meta-Rule 1).

`--scope DIR` narrows only which files contribute DECLARATION candidates
(rows). Reference counting (production, test, preview) always sweeps every
Swift file in the repo's source roots, regardless of `--scope`: a
declaration in scope can be referenced from a file outside it, and a
scope-narrowed reference sweep would silently miss that and over-report
dead surface.

Usage:
  scripts/audit_dead_surface.py [<repo-root>] [--scope DIR]
                                 [--access public|internal|all] [--json]

Exit codes: 0 = reported ok/partial/absent, 2 = usage error.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import _dead_surface_refs as refs  # noqa: E402
import coverage_ledger  # noqa: E402
from _fs_filters import (  # noqa: E402
    _EXACT_CASE_IGNORE_DIRS,
    IGNORE_DIRS,
    is_ignored_path,
    is_test_file,
)

_TEST_WALK_IGNORE_DIRS = IGNORE_DIRS - {"tests", "test"}


def _is_ignored_for_test_walk(parts: tuple[str, ...]) -> bool:
    for part in parts:
        if part.lower() in _TEST_WALK_IGNORE_DIRS or part in _EXACT_CASE_IGNORE_DIRS:
            return True
    return any(part.startswith(".") for part in parts[:-1])


def _discover(repo_root: Path) -> tuple[list[Path], list[Path]]:
    """(production_swift_files, test_swift_files) across the WHOLE repo --
    the reference-counting universe. NEVER narrowed by `--scope`: a
    declaration in scope can be referenced from a file outside it, and a
    scope-narrowed sweep would silently miss that reference and over-report
    dead surface. `--scope` only narrows which of these files contribute
    DECLARATION candidates (see `_scope_filter`). Production roots come from
    coverage_ledger's source-root enumerator (skips fixture/vendor trees);
    test files are swept from the whole repo root directly since Tests/
    dirs are usually siblings of Sources/, not beneath it.
    """
    prod_roots = [(repo_root / r).resolve() for r in coverage_ledger.source_roots(repo_root)]

    production: list[Path] = []
    seen: set[Path] = set()
    for root in prod_roots:
        if not root.is_dir():
            continue
        for p in root.rglob("*.swift"):
            if not p.is_file() or p in seen:
                continue
            rel = p.relative_to(repo_root).parts
            if is_ignored_path(rel) or is_test_file(p.name):
                continue
            seen.add(p)
            production.append(p)

    tests: list[Path] = []
    for p in repo_root.rglob("*.swift"):
        if not p.is_file():
            continue
        parts = p.relative_to(repo_root).parts
        under_test_dir = any(
            q.lower() in ("tests", "test") or q.endswith("Tests") for q in parts[:-1]
        )
        if not (is_test_file(p.name) or under_test_dir):
            continue
        if _is_ignored_for_test_walk(parts):
            continue
        tests.append(p)

    return sorted(production), sorted(tests)


def _scope_filter(repo_root: Path, scope: str | None, production: list[Path]) -> list[Path]:
    """Which production files contribute DECLARATION candidates. Everything
    else in `production` still feeds reference counting -- see `_discover`."""
    if not scope:
        return production
    scope_dir = (repo_root / scope).resolve()
    return [p for p in production if p.is_relative_to(scope_dir)]


def _access_allowed(row_access: str, mode: str) -> bool:
    if mode == "all":
        return True
    if mode == "internal":
        return row_access in ("public", "open", "internal")
    return row_access in ("public", "open")


def audit(repo_root: Path, scope: str | None, access: str) -> dict:
    # Resolve once, here, so a caller passing an unresolved tmpdir (macOS
    # /var -> /private/var) never trips relative_to() below.
    repo_root = repo_root.resolve()
    production, test_paths = _discover(repo_root)
    if not production and not test_paths:
        return {
            "schema_version": 1,
            "status": "absent",
            "promotion_allowed": False,
            "coverage": {
                "files_scanned": 0,
                "files_failed": 0,
                "test_files_scanned": 0,
                "reference_files": 0,
            },
            "rows": [],
        }
    decl_files = _scope_filter(repo_root, scope, production)

    texts: dict[str, str] = {}
    failed = 0
    for p in production + test_paths:
        rel = p.relative_to(repo_root).as_posix()
        try:
            texts[rel] = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            failed += 1

    test_rel = {p.relative_to(repo_root).as_posix() for p in test_paths}
    decl_rel = {p.relative_to(repo_root).as_posix() for p in decl_files}
    corpus = refs.build_corpus(texts)  # always the full repo, never scope-narrowed

    rows: list[dict] = []
    for path, pf in corpus.parsed.items():
        if path in test_rel or path not in decl_rel:
            continue  # declarations are harvested from in-scope production files only
        for decl in pf.decls:
            if not _access_allowed(decl.access, access):
                continue
            prod, test_n, preview_n = refs.count_references(decl, corpus, test_rel)
            if prod > 0:
                continue
            status = "test_only" if test_n > 0 else "preview_only" if preview_n > 0 else "dead"
            rows.append(
                {
                    "kind": decl.kind,
                    "path": decl.path,
                    "line": decl.line,
                    "type_name": decl.type_name,
                    "name": decl.name,
                    "access": decl.access,
                    "references_production": prod,
                    "references_in_tests": test_n,
                    "references_in_previews": preview_n,
                    "status": status,
                }
            )

    rows.sort(key=lambda r: (r["path"], r["line"], r["name"]))
    return {
        "schema_version": 1,
        "status": "partial" if failed else "ok",
        "promotion_allowed": False,
        "coverage": {
            "files_scanned": len(decl_files),
            "files_failed": failed,
            "test_files_scanned": len(test_paths),
            "reference_files": len(production) + len(test_paths),
        },
        "rows": rows,
    }


def _render_markdown(doc: dict) -> str:
    c = doc["coverage"]
    out = [
        f"# dead-surface aid (candidate evidence, promotion_allowed: false) "
        f"— status: {doc['status']}",
        f"  files scanned: {c['files_scanned']}  failed: {c['files_failed']}  "
        f"test files: {c['test_files_scanned']}  reference sweep: {c['reference_files']}",
    ]
    if doc["rows"]:
        out.append("")
        out.append("| kind | type | name | access | file:line | prod | test | preview | status |")
        out.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
        for r in doc["rows"]:
            out.append(
                f"| {r['kind']} | {r['type_name']} | {r['name']} | {r['access']} | "
                f"{r['path']}:{r['line']} | {r['references_production']} | "
                f"{r['references_in_tests']} | {r['references_in_previews']} | {r['status']} |"
            )
    else:
        out.append("")
        out.append("no dead surface found")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("repo_root", nargs="?", default=".", help="repo root to audit")
    ap.add_argument(
        "--scope",
        help="optional subdirectory of repo_root: narrows which files contribute "
        "declarations, not where references are counted",
    )
    ap.add_argument("--access", choices=["public", "internal", "all"], default="all")
    ap.add_argument("--json", action="store_true", help="emit JSON instead of a markdown table")
    args = ap.parse_args(argv)

    repo_root = Path(args.repo_root).resolve()
    if not repo_root.is_dir():
        sys.stderr.write(f"audit_dead_surface: not a directory: {repo_root}\n")
        return 2
    if args.scope:
        scope_dir = (repo_root / args.scope).resolve()
        if not scope_dir.is_dir():
            sys.stderr.write(
                f"audit_dead_surface: --scope directory does not exist: {args.scope}\n"
            )
            return 2
        if not scope_dir.is_relative_to(repo_root):
            sys.stderr.write(
                f"audit_dead_surface: --scope must be a subdirectory of repo_root: {args.scope}\n"
            )
            return 2

    sys.stderr.write("audit_dead_surface: lexical Swift scan, no ast-grep dependency\n")
    doc = audit(repo_root, args.scope, args.access)
    if args.json:
        print(json.dumps(doc, indent=2))
    else:
        print(_render_markdown(doc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
