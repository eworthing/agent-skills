#!/usr/bin/env python3
"""repo_map.py — advisory import-graph / public-surface map for first-party codebases.

Produces an ephemeral Step-0 discovery map: per top-level package — public surface,
fan-in, fan-out, and import edges. Output is **CANDIDATE EVIDENCE ONLY** consumed
in-loop. It is NOT a finding, NOT a score, and NOT a loop gate.

Doctrine boundary (Method.md Meta-Rule 1): every module record and the top-level output
carry `promotion_allowed: false`. The map surfaces candidates (high fan-in modules,
cross-module coupling, import cycles); the Critic re-derives any judgment. The map is
NEVER persisted into output-format-state-schemas.md.

Auto-engage: when first_party_file_count > 300 (same filter as audit_boundaries.py).
Below threshold the loop relies on existing advisory audits. The first-party file count
is ALWAYS recorded in the output so the auto-engage decision is reproducible.

The first-party file filters and the AST import graph are IMPORTED from the sibling
scripts/audit_boundaries.py (single source of truth): IGNORE_DIRS, _is_test_file,
_is_generated_file, _collect_py_files, _source_root, _package_of, _imported_top_levels,
and _strongly_connected_components. repo_map.py runs as a script from scripts/, so the
sibling import resolves; nothing is kept mirrored (no drift hazard).

Supported stacks: Python only (v1). Unsupported stacks emit an empty result and exit 0
(a Swift/TypeScript extension would use ast-grep/language-server tooling — not in v1).

Usage:
    repo_map.py [<repo-dir>] [--format json|md] [-o OUT]

Exit codes:
  0 = ran (possibly empty — no Python sources found, or unsupported stack)
  2 = usage error (bad path)
"""

from __future__ import annotations

import argparse
import ast
import json
import shutil
import subprocess
import sys
from pathlib import Path

# Single source of truth for the first-party file filters + AST import graph. Resolves
# because repo_map.py is always executed as a script from scripts/ (its own dir is on
# sys.path[0]); the sibling has a guarded __main__, so importing it has no side effects.
import audit_boundaries as _ab

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_SCHEMA_VERSION = "1"

# First-party source-file count above which the map auto-engages at Step 0.
_AUTO_ENGAGE_THRESHOLD = 300


# ---------------------------------------------------------------------------
# Public-surface extraction
# ---------------------------------------------------------------------------


def _public_names(path: Path) -> list[str]:
    """Top-level names defined in a .py file that do not start with '_'.

    Covers functions, async functions, classes, and module-level assignments
    (annotated or unannotated). Private / dunder names are excluded.
    """
    try:
        tree = ast.parse(
            path.read_text(encoding="utf-8", errors="replace"), filename=str(path)
        )
    except (SyntaxError, ValueError, OSError):
        return []
    names: list[str] = []
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if not node.name.startswith("_"):
                names.append(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and not target.id.startswith("_"):
                    names.append(target.id)
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name) and not node.target.id.startswith("_"):
                names.append(node.target.id)
    return sorted(set(names))


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------


def _build_graph(
    files: list[Path], source_root: Path
) -> tuple[dict[str, set[str]], dict[str, list[str]], dict[str, list[Path]]]:
    """Return (package→imports, package→public_names, package→files).

    Imports are first-party only (cross-package, same-package imports excluded).
    """
    first_party = {_ab._package_of(f, source_root) for f in files}

    pkg_files: dict[str, list[Path]] = {pkg: [] for pkg in first_party}
    for f in files:
        pkg_files[_ab._package_of(f, source_root)].append(f)

    graph: dict[str, set[str]] = {pkg: set() for pkg in first_party}
    pub: dict[str, list[str]] = {pkg: [] for pkg in first_party}

    for f in files:
        pkg = _ab._package_of(f, source_root)
        try:
            tree = ast.parse(
                f.read_text(encoding="utf-8", errors="replace"), filename=str(f)
            )
        except (SyntaxError, ValueError, OSError):
            continue  # unparseable file → skip; never crash the audit

        for top in _ab._imported_top_levels(tree):
            if top in first_party and top != pkg:  # cross-package, first-party only
                graph[pkg].add(top)

        # Accumulate public surface per package
        for name in _public_names(f):
            if name not in pub[pkg]:
                pub[pkg].append(name)

    for pkg in pub:
        pub[pkg] = sorted(set(pub[pkg]))

    return graph, pub, pkg_files


# ---------------------------------------------------------------------------
# Cycle detection (SCC imported from audit_boundaries.py)
# ---------------------------------------------------------------------------


def _find_cycles(graph: dict[str, set[str]]) -> list[list[str]]:
    cycles: list[list[str]] = []
    for comp in _ab._strongly_connected_components(graph):
        # multi-package SCC, or a rare single-package self-cycle
        if len(comp) > 1 or (len(comp) == 1 and comp[0] in graph[comp[0]]):
            cycles.append(comp)
    return sorted(cycles, key=lambda c: (len(c), c))


# ---------------------------------------------------------------------------
# Git head
# ---------------------------------------------------------------------------


def _repo_head(repo: Path) -> str:
    if shutil.which("git") is None:
        return "unavailable"
    r = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=repo,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return r.stdout.strip() if r.returncode == 0 else "unavailable"


# ---------------------------------------------------------------------------
# Core analysis
# ---------------------------------------------------------------------------


def _analyse(repo: Path) -> dict:
    """Return the full advisory map dict."""
    source_root = _ab._source_root(repo)
    files = _ab._collect_py_files(source_root)

    note = (
        "CANDIDATE EVIDENCE ONLY — not a finding, not a score, not a loop gate. "
        "The map surfaces import coupling and public surface as candidates; "
        "the Critic re-derives any judgment. See promotion_allowed: false."
    )

    base: dict = {
        "schema_version": _SCHEMA_VERSION,
        "note": note,
        "promotion_allowed": False,
        "repo_head": _repo_head(repo),
        "first_party_file_count": len(files),
        "auto_engage_threshold": _AUTO_ENGAGE_THRESHOLD,
        "auto_engage": len(files) > _AUTO_ENGAGE_THRESHOLD,
    }

    if not files:
        base["modules"] = []
        base["import_edges"] = []
        base["cycles"] = []
        base["summary"] = {
            "note": "no first-party Python sources found (Python-only v1; unsupported stacks emit nothing)"
        }
        return base

    graph, pub, pkg_files = _build_graph(files, source_root)
    cycles = _find_cycles(graph)

    # Fan-in: count how many packages import each package
    fan_in: dict[str, int] = {pkg: 0 for pkg in graph}
    imported_by: dict[str, list[str]] = {pkg: [] for pkg in graph}
    for pkg, imports in graph.items():
        for dep in imports:
            fan_in[dep] = fan_in.get(dep, 0) + 1
            imported_by[dep].append(pkg)

    modules: list[dict] = []
    for pkg in sorted(graph):
        rel_files = sorted(
            str(f.relative_to(source_root)) for f in pkg_files.get(pkg, [])
        )
        modules.append({
            "module": pkg,
            "files": rel_files,
            "public_surface": pub.get(pkg, []),
            "fan_in": fan_in.get(pkg, 0),
            "fan_out": len(graph[pkg]),
            "imports": sorted(graph[pkg]),
            "imported_by": sorted(imported_by.get(pkg, [])),
            "promotion_allowed": False,
        })

    edges: list[dict] = [
        {"from": pkg, "to": dep, "promotion_allowed": False}
        for pkg in sorted(graph)
        for dep in sorted(graph[pkg])
    ]

    base["modules"] = modules
    base["import_edges"] = edges
    base["cycles"] = cycles
    base["summary"] = {
        "module_count": len(modules),
        "edge_count": len(edges),
        "cycle_count": len(cycles),
    }
    return base


# ---------------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------------


def _format_json(result: dict) -> str:
    return json.dumps(result, indent=2)


def _format_md(result: dict) -> str:
    lines: list[str] = [
        "# Repo-Map Candidate Report",
        "",
        "> **CANDIDATE EVIDENCE ONLY** — not a finding. All signals require Critic",
        "> investigation before any coupling claim is made.",
        "",
        f"**repo_head:** {result.get('repo_head', 'unknown')}  ",
        f"**schema_version:** {result.get('schema_version')}  ",
        f"**first_party_file_count:** {result.get('first_party_file_count', 0)}  ",
        (
            f"**auto_engage:** {result.get('auto_engage')} "
            f"(threshold: {result.get('auto_engage_threshold')})  "
        ),
    ]

    summary_note = result.get("summary", {}).get("note")
    if summary_note:
        lines += ["", f"_{summary_note}_"]
        return "\n".join(lines)

    cycles = result.get("cycles", [])
    if cycles:
        lines += [
            "",
            "## Detected Cycles (candidate coupling signal)",
            "",
            "| packages in cycle | size |",
            "|---|---|",
        ]
        for comp in cycles:
            lines.append(f"| {' ↔ '.join(comp)} | {len(comp)} |")

    modules = result.get("modules", [])
    if not modules:
        lines += ["", "_No first-party Python modules found._"]
        return "\n".join(lines)

    # Sort by fan-in descending so highest-coupling modules appear first
    modules_sorted = sorted(modules, key=lambda m: (-m["fan_in"], m["module"]))
    lines += [
        "",
        "## Module Map",
        "",
        "| module | fan_in | fan_out | public_surface (sample) | files |",
        "|---|---|---|---|---|",
    ]
    for m in modules_sorted:
        surface = m["public_surface"]
        sample = ", ".join(surface[:5])
        if len(surface) > 5:
            sample += f" … (+{len(surface) - 5})"
        lines.append(
            f"| {m['module']} | {m['fan_in']} | {m['fan_out']} "
            f"| {sample} | {len(m['files'])} |"
        )

    lines += [
        "",
        "_promotion_allowed: false for all module records above._",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build an advisory import-graph / public-surface map for first-party Python "
            "modules. Output is candidate evidence only — never a finding or a loop gate."
        )
    )
    parser.add_argument(
        "repo_dir",
        nargs="?",
        default=".",
        help="Repository root (default: cwd)",
    )
    parser.add_argument(
        "--format",
        choices=["json", "md"],
        default="json",
        dest="fmt",
        help="Output format: json (default) or md",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=None,
        metavar="OUT",
        help="Write output to file (default: stdout)",
    )
    args = parser.parse_args(argv)

    repo = Path(args.repo_dir).resolve()
    if not repo.is_dir():
        print(f"repo_map: not a directory: {repo}", file=sys.stderr)
        return 2

    result = _analyse(repo)
    text = _format_json(result) if args.fmt == "json" else _format_md(result)

    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    else:
        print(text)

    return 0


if __name__ == "__main__":
    sys.exit(main())
