#!/usr/bin/env python3
"""audit_cochange.py — candidate-evidence for change-coupled, structurally distant files.

Mines git history for files/modules that change together but live far apart in the
directory tree. Output is **candidate evidence for human calibration only** — it is
NOT a finding, NOT a score, and NOT a loop gate.

Doctrine boundary (Method.md Meta-Rule 1): every pair record carries
`promotion_allowed: false`. A coupling smell requires a human to investigate whether
the co-change reflects a necessary invariant (e.g. a shared contract) or an accidental
entanglement. This tool surfaces the signal; the Critic decides what it means.

Supported stacks for `static_dependency`:
  - Python: shells to audit_boundaries.py if available; infers "present/none" from AST.
  - All other stacks (Swift, TypeScript, Go, …): reports "unavailable" — NEVER fabricated.

Usage:
    audit_cochange.py [<repo-dir>] [--max-commits 3000] [--since "24 months ago"]
                      [--format json|md] [-o OUT]

Exit codes:
  0 = ran (possibly empty — no .git, shallow clone, or insufficient history)
  2 = usage error
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from collections import defaultdict
from itertools import combinations
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_SCHEMA_VERSION = "1"

# Commits touching more than this many files are treated as "mass change" and
# excluded from pair co-change counting (still counted in total commit scan).
_DEFAULT_MAX_FILES_PER_COMMIT = 8

# Minimum co-change occurrences before a pair is considered a candidate.
_MIN_COCHANGE = 3

# Minimum directory distance (>0 means files are in different directories).
_MIN_DIR_DISTANCE = 1

# Commit message patterns that indicate non-semantic mass changes — pairs from
# these commits are excluded from co-change counting.
_NOISE_MSG_RE = re.compile(
    r"(fmt|format|lint|prettier|black|rustfmt|release|version\s+bump"
    r"|lockfile|codemod|rename[-\s]only|generated|vendor)",
    re.IGNORECASE,
)

# Glob-style path prefixes / suffixes treated as generated/vendored/lockfiles.
_GENERATED_PATTERNS = (
    "dist/",
    "vendor/",
    ".git/",
    "node_modules/",
    "__pycache__/",
    ".venv/",
    "build/",
)
_GENERATED_SUFFIXES = (
    ".lock",
    ".g.dart",
    ".g.swift",
    ".generated.swift",
    ".generated.ts",
    ".generated.js",
    ".pb.go",
    "_pb2.py",
    "_pb2_grpc.py",
    ".min.js",
    ".min.css",
)

# File extensions that indicate Python source (for static dep resolution).
_PYTHON_EXTS = frozenset({".py"})

# File extensions that indicate Swift source (dep graph unavailable).
_SWIFT_EXTS = frozenset({".swift"})


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------


def _git_available() -> bool:
    return shutil.which("git") is not None


def _git_run(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, encoding="utf-8")


def _has_git_dir(repo: Path) -> bool:
    r = _git_run(["rev-parse", "--git-dir"], cwd=repo)
    return r.returncode == 0


def _is_shallow(repo: Path) -> bool:
    r = _git_run(["rev-parse", "--is-shallow-repository"], cwd=repo)
    return r.returncode == 0 and r.stdout.strip() == "true"


def _repo_head(repo: Path) -> str:
    r = _git_run(["rev-parse", "--short", "HEAD"], cwd=repo)
    return r.stdout.strip() if r.returncode == 0 else "unknown"


def _log_commits(repo: Path, max_commits: int, since: str) -> list[tuple[str, str, list[str]]]:
    """Return list of (sha, subject, [changed_files]) — merge commits excluded.

    Uses --diff-filter=d to skip deleted files (renames handled separately via
    --find-renames). Each entry is one non-merge commit within the window.
    """
    # %x1e (record separator) starts each commit so the per-commit block is
    # unambiguous regardless of the blank line git inserts between a commit's
    # header and its --name-only file list. %H = hash, %x00 = NUL, %s = subject.
    log_fmt = "%x1e%H%x00%s"
    r = _git_run(
        [
            "log",
            "--no-merges",
            "--find-renames",
            "--diff-filter=ACDMRT",
            f"--max-count={max_commits}",
            f"--since={since}",
            f"--format={log_fmt}",
            "--name-only",
        ],
        cwd=repo,
    )
    if r.returncode != 0:
        return []

    commits: list[tuple[str, str, list[str]]] = []
    # One record per commit, delimited by the leading \x1e. Within a record the
    # first line is "<sha>\0<subject>"; every remaining non-blank line is a file.
    for record in r.stdout.split("\x1e"):
        record = record.strip("\n")
        if not record:
            continue
        head, _, rest = record.partition("\n")
        sha, _, subject = head.partition("\x00")
        if not sha:
            continue
        files = [f.strip() for f in rest.splitlines() if f.strip()]
        commits.append((sha, subject, files))
    return commits


# ---------------------------------------------------------------------------
# Filters
# ---------------------------------------------------------------------------


def _is_generated(path: str) -> bool:
    for prefix in _GENERATED_PATTERNS:
        if path.startswith(prefix) or "/" + prefix in path:
            return True
    return any(path.endswith(suffix) for suffix in _GENERATED_SUFFIXES)


def _is_noise_commit(subject: str) -> bool:
    return bool(_NOISE_MSG_RE.search(subject))


# ---------------------------------------------------------------------------
# Directory distance
# ---------------------------------------------------------------------------


def _dir_distance(a: str, b: str) -> int:
    """Number of directory components that differ between two file paths.

    Files in the same directory → 0.
    Files one level apart (siblings) → effectively 1 distinct prefix each.
    Uses the length of the symmetric-difference of directory part sets.

    Examples:
      src/orders/checkout.ts, src/orders/cart.ts  → same dir → 0
      src/orders/checkout.ts, src/billing/pay.ts  → dirs differ → distance 2
    """
    parts_a = Path(a).parent.parts
    parts_b = Path(b).parent.parts
    # Walk shared prefix length
    shared = 0
    for pa, pb in zip(parts_a, parts_b, strict=False):
        if pa == pb:
            shared += 1
        else:
            break
    dist_a = len(parts_a) - shared
    dist_b = len(parts_b) - shared
    return dist_a + dist_b


# ---------------------------------------------------------------------------
# Static dependency (Python only; all other stacks → "unavailable")
# ---------------------------------------------------------------------------


def _has_python_sources(files: list[str]) -> bool:
    return any(Path(f).suffix in _PYTHON_EXTS for f in files)


def _has_swift_sources(files: list[str]) -> bool:
    return any(Path(f).suffix in _SWIFT_EXTS for f in files)


def _module_tuple(rel: Path) -> tuple[str, ...]:
    """Repo-relative ``.py`` path → its fully-qualified module tuple.

    Drops the file suffix and a trailing ``__init__`` (a package's module is its
    directory): ``src/billing/policy.py`` → ``("src", "billing", "policy")``.
    """
    parts = rel.with_suffix("").parts
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return parts


def _imported_modules(path: Path, rel: Path) -> set[tuple[str, ...]]:
    """Fully-qualified module tuples imported by the file at ``path`` (repo-relative ``rel``).

    Absolute and relative imports both resolve to *absolute* tuples so a target module
    tuple can be matched by EXACT equality (which is what prevents the same-top-level
    false-positive class). For ``from a.b import c`` both ``("a","b")`` and ``("a","b","c")``
    are emitted — the leaf may be a submodule. Relative imports resolve against the
    importer's own package; ``node.module`` is ``None`` for ``from . import x`` (so we never
    ``None.split``), and an illegal over-deep relative import clamps to an empty base rather
    than slicing the package tuple from the right.
    """
    import ast as _ast  # local import — stdlib, never absent

    try:
        tree = _ast.parse(path.read_text(encoding="utf-8", errors="replace"), filename=str(path))
    except (OSError, SyntaxError, ValueError):
        return set()

    pkg = rel.parent.parts  # package directories of this module
    mods: set[tuple[str, ...]] = set()
    for node in _ast.walk(tree):
        if isinstance(node, _ast.Import):
            for alias in node.names:
                mods.add(tuple(alias.name.split(".")))
        elif isinstance(node, _ast.ImportFrom):
            mod_parts = tuple(node.module.split(".")) if node.module else ()
            # relative: drop (level-1) trailing package components, clamped at 0;
            # absolute (level 0): no base. node.module is None for `from . import x`.
            base = pkg[: max(0, len(pkg) - (node.level - 1))] if node.level else ()
            prefix = (*base, *mod_parts)
            if prefix:
                mods.add(prefix)
            for alias in node.names:
                mods.add((*prefix, alias.name))
    return mods


def _infer_static_dep_python(repo: Path, lhs: str, rhs: str) -> str:
    """Returns 'present', 'none', or 'unavailable' for a Python pair.

    Detects a DIRECT module/file import in either direction by exact module-tuple
    match. It is NOT package-re-export, dynamic-import, or ``src``-import-root aware:
    a 'none' means "no *direct* import between these two files", not "no relationship".
    """
    lhs_mod = _module_tuple(Path(lhs))
    rhs_mod = _module_tuple(Path(rhs))
    if not lhs_mod or not rhs_mod:
        return "unavailable"

    lhs_imports = _imported_modules(repo / lhs, Path(lhs))
    rhs_imports = _imported_modules(repo / rhs, Path(rhs))

    if rhs_mod in lhs_imports or lhs_mod in rhs_imports:
        return "present"
    return "none"


def _resolve_static_dep(repo: Path, lhs: str, rhs: str) -> str:
    lhs_ext = Path(lhs).suffix
    rhs_ext = Path(rhs).suffix
    if lhs_ext in _PYTHON_EXTS and rhs_ext in _PYTHON_EXTS:
        return _infer_static_dep_python(repo, lhs, rhs)
    # Swift, TypeScript, Go, etc. — no dep graph available
    return "unavailable"


# ---------------------------------------------------------------------------
# Core analysis
# ---------------------------------------------------------------------------


def _analyse(
    repo: Path,
    max_commits: int,
    since: str,
    max_files_per_commit: int = _DEFAULT_MAX_FILES_PER_COMMIT,
) -> dict:
    """Return the full result dict (schema_version, pairs, summary, …)."""

    unavailable_reason: str | None = None

    if not _git_available():
        unavailable_reason = "git not found on PATH"
    elif not _has_git_dir(repo):
        unavailable_reason = "not a git repository (no .git)"
    elif _is_shallow(repo):
        unavailable_reason = "shallow clone — full history unavailable"

    head = _repo_head(repo) if unavailable_reason is None else "unavailable"

    base: dict = {
        "schema_version": _SCHEMA_VERSION,
        "note": (
            "CANDIDATE EVIDENCE ONLY — not a finding. Pairs require human investigation "
            "before any promotion_allowed field is set. See promotion_allowed: false."
        ),
        "repo_head": head,
        "analysis_window": {"max_commits": max_commits, "since": since},
        "filters": {
            "max_files_per_commit": max_files_per_commit,
            "min_cochange": _MIN_COCHANGE,
            "min_dir_distance": _MIN_DIR_DISTANCE,
        },
    }

    if unavailable_reason is not None:
        base["summary"] = {"candidate_pairs": 0, "note": unavailable_reason}
        base["pairs"] = []
        return base

    commits = _log_commits(repo, max_commits, since)

    qualifying: list[tuple[str, str, list[str]]] = []
    for sha, subject, files in commits:
        if _is_noise_commit(subject):
            continue
        clean = [f for f in files if not _is_generated(f)]
        if not clean:
            continue
        qualifying.append((sha, subject, clean))

    if len(qualifying) < 2:
        base["summary"] = {
            "candidate_pairs": 0,
            "note": "insufficient qualifying commits (< 2)",
        }
        base["pairs"] = []
        return base

    # Count co-changes and which commits each pair appeared in
    cochange_counts: dict[tuple[str, str], int] = defaultdict(int)
    supporting: dict[tuple[str, str], list[str]] = defaultdict(list)
    file_counts: dict[str, int] = defaultdict(int)

    for sha, _subject, clean in qualifying:
        # Skip mass-change commits for pair signal
        if len(clean) > max_files_per_commit:
            continue
        for f in clean:
            file_counts[f] += 1
        for a, b in combinations(sorted(clean), 2):
            key = (a, b)
            cochange_counts[key] += 1
            supporting[key].append(sha)

    # Build candidate pairs
    pairs: list[dict] = []
    pair_id = 0
    for (lhs, rhs), count in cochange_counts.items():
        if count < _MIN_COCHANGE:
            continue
        dist = _dir_distance(lhs, rhs)
        if dist < _MIN_DIR_DISTANCE:
            continue
        n_lhs = file_counts[lhs]
        n_rhs = file_counts[rhs]
        union = n_lhs + n_rhs - count
        jaccard = count / union if union > 0 else 0.0
        conf_rhs_given_lhs = count / n_lhs if n_lhs > 0 else 0.0  # P(rhs changes | lhs changed)
        conf_lhs_given_rhs = count / n_rhs if n_rhs > 0 else 0.0  # P(lhs changes | rhs changed)

        # Determine granularity by file extensions
        exts = {Path(lhs).suffix, Path(rhs).suffix}
        if exts <= _SWIFT_EXTS:
            granularity = "swift-file"
        elif exts <= _PYTHON_EXTS:
            granularity = "python-module"
        else:
            granularity = "file"

        dep = _resolve_static_dep(repo, lhs, rhs)
        pair_id += 1
        pairs.append(
            {
                "id": f"cochange-{pair_id:04d}",
                "lhs": lhs,
                "rhs": rhs,
                "granularity": granularity,
                "cochange_count": count,
                "jaccard": round(jaccard, 4),
                "confidences": {
                    "lhs_given_rhs": round(conf_lhs_given_rhs, 4),
                    "rhs_given_lhs": round(conf_rhs_given_lhs, 4),
                },
                "directory_distance": dist,
                "static_dependency": dep,
                "classification": "candidate",
                "promotion_allowed": False,
                "supporting_commits": supporting[(lhs, rhs)][:20],  # cap at 20
            }
        )

    # Sort by co-change count descending, then jaccard descending
    pairs.sort(key=lambda p: (-p["cochange_count"], -p["jaccard"]))

    base["summary"] = {
        "qualifying_commits_scanned": len(qualifying),
        "candidate_pairs": len(pairs),
    }
    base["pairs"] = pairs
    return base


# ---------------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------------


def _format_json(result: dict) -> str:
    return json.dumps(result, indent=2)


def _format_md(result: dict) -> str:
    lines: list[str] = [
        "# Change-Coupling Candidate Report",
        "",
        "> **CANDIDATE EVIDENCE ONLY** — not a finding. All pairs require human",
        "> investigation before any coupling claim is made.",
        "",
        f"**repo_head:** {result.get('repo_head', 'unknown')}  ",
        f"**schema_version:** {result.get('schema_version')}  ",
    ]
    window = result.get("analysis_window", {})
    lines.append(
        f"**window:** since={window.get('since')}, max_commits={window.get('max_commits')}  "
    )
    summary = result.get("summary", {})
    lines += [
        "",
        f"**candidate_pairs:** {summary.get('candidate_pairs', 0)}",
    ]
    if "note" in summary:
        lines.append(f"**note:** {summary['note']}")
    pairs = result.get("pairs", [])
    if not pairs:
        lines += ["", "_No candidate pairs found._"]
        return "\n".join(lines)
    lines += [
        "",
        "## Candidate Pairs",
        "",
        "| id | lhs | rhs | cochange | jaccard | dir_dist | static_dep |",
        "|---|---|---|---|---|---|---|",
    ]
    for p in pairs:
        lines.append(
            f"| {p['id']} | {p['lhs']} | {p['rhs']} "
            f"| {p['cochange_count']} | {p['jaccard']:.4f} "
            f"| {p['directory_distance']} | {p['static_dependency']} |"
        )
    lines += [
        "",
        "_promotion_allowed: false for all pairs above._",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Mine git history for change-coupled, structurally distant file pairs. "
            "Output is candidate evidence only — never a finding or a loop gate."
        )
    )
    parser.add_argument(
        "repo_dir",
        nargs="?",
        default=".",
        help="Repository root (default: cwd)",
    )
    parser.add_argument(
        "--max-commits",
        type=int,
        default=3000,
        metavar="N",
        help="Cap on commits scanned (default 3000)",
    )
    parser.add_argument(
        "--since",
        default="24 months ago",
        metavar="DATE",
        help='Start of history window (git date string, default "24 months ago")',
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
        print(f"audit_cochange: not a directory: {repo}", file=sys.stderr)
        return 2

    result = _analyse(repo, max_commits=args.max_commits, since=args.since)

    text = _format_json(result) if args.fmt == "json" else _format_md(result)

    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    else:
        print(text)

    return 0


if __name__ == "__main__":
    sys.exit(main())
