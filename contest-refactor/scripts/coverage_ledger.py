#!/usr/bin/env python3
"""coverage_ledger.py — what a converged run actually cited, and what it never touched.

Backlog item 24, slice B. Design note:
analysis/contest-refactor/ITEM24-COVERAGE-UNIT-DESIGN-2026-08-19.md

THE QUESTION THIS ANSWERS. A run reaches HALT_SUCCESS or HALT_LOOP_CAP with a
converged scorecard, and a reader cannot tell from the artifact whether that means
"the repository is sound" or "the parts it happened to look at are sound". Measured
on this repo's own 15-loop dogfood run: findings cite 23 distinct files, and nothing
anywhere records what was examined.

CITATION, NOT EXAMINATION -- and the distinction is the whole design. A loop may read
far more than it cites. Nothing in the committed record can tell the two apart, and
closing that gap would require the model to self-report what it read: exactly the
unverifiable evidence item 14's host-attestation work concluded we cannot trust. So
this reports the lower bound that IS derivable, and labels it `measure: "citation"`
in its own output so the number can never be quoted as something stronger. An uncited
file is not proof of neglect; a high uncited count is a question worth asking at halt
time, which is more than the artifact offers today.

DERIVED, NEVER STORED (design note §5, after alibaba): `cited + uncited` is asserted
equal to the denominator on every run. A stored terminal flag can disagree with the
parts it summarises; a derived one cannot.

BOUND TO A RECORDED REVISION, NEVER A SEARCHED ONE (§4). Staleness compares blob shas
at the sha the citation was written against. Where no revision was recorded the loop
is reported under `revision.unavailable_loops` and contributes no staleness -- it is
never resolved at HEAD. Two prototypes during item 26a manufactured findings by
guessing a revision (a HEAD fallback, then a commit-subject grep); that is the rule
those failures bought.

Report-only: exit 0 always, 2 for plumbing. Nothing here gates a loop, and every
number is candidate evidence under `promotion_allowed: false` like the other audits.

Usage:
    coverage_ledger.py <repo-root> [--json PATH] [--quiet]
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

# Path/test filters come from the shared SSOT (_fs_filters.py), not audit_boundaries:
# that module's own copies are narrower (Python-only test suffixes, fewer ignored
# dirs) and audit_suppressions.py depends on that narrower behavior directly, so
# they were left alone rather than folded in here. The generated-file check stays
# on audit_boundaries: its `_pb2.py`/`_pb2_grpc.py` filename check has no equivalent
# in _fs_filters, and this module never had a bug report about generated files.
from _fs_filters import is_ignored_path, is_test_file, normalize_roots  # noqa: E402
from audit_boundaries import _is_generated_file  # noqa: E402

# Language-agnostic source set. Deliberately excludes .md: documentation is not the
# architecture under review, and mixing it into the denominator would make the ratio
# meaningless. Citations that land outside this set are reported separately.
SOURCE_EXTS = frozenset(
    {
        ".py",
        ".swift",
        ".ts",
        ".tsx",
        ".js",
        ".jsx",
        ".go",
        ".rs",
        ".java",
        ".kt",
        ".rb",
        ".m",
        ".mm",
        ".c",
        ".h",
        ".cc",
        ".cpp",
        ".hpp",
        ".cs",
        ".php",
        ".scala",
    }
)

_LEADING_PATH = re.compile(r"^\s*(?P<path>[^\s:*?\[\]]+\.[A-Za-z0-9_]+)")

# Corpora that exist to be GRADED, not reviewed: eval fixtures are deliberately
# defective source, so counting them as unreviewed inflates the miss, and counting
# them as reviewable would ask the Critic to fix planted bugs. Measured on this repo:
# 138 of 244 scanned files were fixture corpus, turning a real 6.6% into a
# meaningless 2.9%. Same documented restraint as IGNORE_DIRS' `tests` entry -- a
# project with a genuine app directory named `fixtures` is over-excluded, and the
# typed count below makes that visible rather than silent.
FIXTURE_DIRS = frozenset(
    {
        "evals",
        "eval",
        "fixtures",
        "fixture",
        "testdata",
        "__fixtures__",
        "golden",
        "snapshots",
        "corpus",
    }
)


# ponytail: aliased to the shared `_fs_filters.is_test_file` (extension-aware for
# the languages audit_hotspots.py scans) rather than the generic stem-suffix
# heuristic this used to be. A stem-suffix test file in an extension this module
# scans but audit_hotspots doesn't (.rb, .m/.mm/.c/.cc/.cpp/.hpp, .cs, .php, .scala)
# is no longer caught by filename alone. Upgrade: extend is_test_file with those
# suffixes if a real miss surfaces. Name kept (not inlined) for
# _artifact_coverage_citation.py's import surface and the call site below.
_is_test_name = is_test_file


class InvalidSourceRoot(ValueError):
    """A declared source_roots entry is absolute or escapes the repo via '..'."""


def _validate_source_root(root_rel: str) -> None:
    """Reject absolute or '..'-escaping roots up front, before any filesystem walk.

    `base / "/abs/path"` silently collapses to `/abs/path` in pathlib -- it does
    NOT raise, it just rebases to the wrong path. An escaping `..` root resolves
    outside `base` too, and later crashes `relative_to()` with an uncaught
    ValueError once a file under it is found. Both are caught here instead, with
    a message naming the offending root.
    """
    if Path(root_rel).is_absolute() or ".." in Path(root_rel).parts:
        raise InvalidSourceRoot(f"source_roots entries must be repo-relative: {root_rel}")


def first_party_files(
    repo_root: Path, source_roots: list[str]
) -> tuple[list[str], dict[str, int], list[str]]:
    """(included, excluded-by-typed-reason, missing-roots) for source files under
    the declared roots.

    Exclusions are COUNTED, never silently dropped: a denominator that shrinks without
    saying how is the survivor-metric hazard the trial-validity work named, and it
    flatters the result in the same direction every time. A declared root that isn't
    a directory is the same hazard under a different name, so it is both counted
    (excluded["missing_root"]) and named (the third return value).
    """
    out: set[str] = set()
    excluded: dict[str, int] = {}
    missing: list[str] = []

    def drop(reason: str) -> None:
        excluded[reason] = excluded.get(reason, 0) + 1

    # Resolve the base once and derive roots from it: on macOS a tmpdir under /var
    # resolves to /private/var, so resolving the root but not the base makes every
    # relative_to() raise. Caught by the tmpdir selftest.
    base = repo_root.resolve()
    for root_rel in source_roots or ["."]:
        _validate_source_root(root_rel)
        root = (base / root_rel).resolve()
        if not root.is_dir():
            drop("missing_root")
            missing.append(root_rel)
            continue
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix not in SOURCE_EXTS:
                continue
            rel_parts = path.relative_to(base).parts
            if is_ignored_path(rel_parts):
                drop("vendor_or_build")
                continue
            if any(part in FIXTURE_DIRS for part in rel_parts[:-1]):
                drop("fixture_corpus")
                continue
            if _is_test_name(path.name):
                drop("test_file")
                continue
            if _is_generated_file(path):
                drop("generated")
                continue
            out.add(path.relative_to(base).as_posix())
    return sorted(out), excluded, missing


def source_roots(repo_root: Path) -> list[str]:
    """Enumerate top-level source roots by walking the same universe the ledger
    denominator uses (declared roots = ["."]) -- so the enumerator and the
    denominator derive from one pass and cannot disagree with each other.

    ponytail: the X -> X/Sources refinement assumes SwiftPM layout (a package
    manifest at X/, sources under X/Sources/). Manifest parsing is the accurate
    upgrade path; out of scope for v1.
    """
    included, _, _ = first_party_files(repo_root, ["."])
    base = repo_root.resolve()
    components: set[str] = set()
    for rel in included:
        parts = Path(rel).parts
        if len(parts) < 2:
            continue  # a loose top-level file contributes no root component
        top = parts[0]
        if top != "Sources" and (base / top / "Sources").is_dir():
            components.add(f"{top}/Sources")
        else:
            components.add(top)
    return normalize_roots(list(components)) if components else ["."]


def cited_paths(history: dict) -> dict[str, int]:
    """Repo-relative path -> the earliest loop that cited it."""
    first: dict[str, int] = {}
    for entry in history.get("loops") or []:
        loop = entry.get("loop")
        for finding in entry.get("findings") or []:
            for ev in finding.get("evidence") or []:
                if not isinstance(ev, str):
                    continue
                m = _LEADING_PATH.match(ev)
                if not m:
                    continue
                path = m.group("path")
                if isinstance(loop, int) and (path not in first or loop < first[path]):
                    first[path] = loop
    return first


def split_runs(history: dict) -> list[list[dict]]:
    """Group loop entries into runs.

    A run boundary is where the loop counter fails to advance -- `--reset` restarts it
    at 1, so REVIEW_HISTORY.json legitimately holds several runs with overlapping loop
    numbers -- or where a non-null `run_id` changes. Both rules are needed: `run_id` is
    null on 14 of the 15 loops in this repo's own history, so grouping by it alone would
    collapse everything into one run, and a run_id that merely appears or disappears is
    not a boundary on its own.
    """
    runs: list[list[dict]] = []
    current: list[dict] = []
    prev_loop: int | None = None
    prev_rid: str | None = None
    for entry in history.get("loops") or []:
        if not isinstance(entry, dict):
            continue
        loop, rid = entry.get("loop"), entry.get("run_id")
        if current:
            changed_rid = rid is not None and prev_rid is not None and rid != prev_rid
            stalled = isinstance(loop, int) and isinstance(prev_loop, int) and loop <= prev_loop
            if changed_rid or stalled:
                runs.append(current)
                current = []
        current.append(entry)
        prev_loop, prev_rid = loop, (rid if rid is not None else prev_rid)
    if current:
        runs.append(current)
    return runs


def _blob_sha(repo: Path, rev: str, path: str) -> str | None:
    proc = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", f"{rev}:{path}"],
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.stdout.strip() if proc.returncode == 0 else None


def compute_ledger(
    repo_root: Path, history: dict, registry: dict | None, loop_shas: dict[int, str]
) -> dict:
    loops = history.get("loops") or []
    source_roots: list[str] = []
    for entry in loops:
        roots = (entry.get("discovery") or {}).get("source_roots") or []
        for r in roots:
            if r not in source_roots:
                source_roots.append(r)

    denominator, excluded, missing_roots = first_party_files(repo_root, source_roots)
    denom_set = set(denominator)
    first_cite = cited_paths(history)

    cited = sorted(p for p in first_cite if p in denom_set)
    outside = sorted(p for p in first_cite if p not in denom_set)
    uncited = sorted(denom_set - set(cited))

    # Staleness: blob at the recorded revision vs the working tree's HEAD. A loop with
    # no recorded revision contributes nothing and is named instead.
    stale: list[str] = []
    unavailable: list[int] = []
    for path in cited:
        loop = first_cite[path]
        rev = loop_shas.get(loop)
        if rev is None:
            if loop not in unavailable:
                unavailable.append(loop)
            continue
        then, now = _blob_sha(repo_root, rev, path), _blob_sha(repo_root, "HEAD", path)
        if then is not None and now is not None and then != now:
            stale.append(path)

    # Cross-check only entries whose first sighting is inside the history being
    # measured. findings_registry.json outlives REVIEW_HISTORY.json -- `--reset` keeps
    # the registry while history restarts -- so comparing every entry against this
    # history's citations reports the LIFETIME MISMATCH as review inconsistency. Live
    # example (BenchHype, 2026-08-19): 13 entries with first_seen_loop up to 10 against
    # a 1-loop history produced 9 "inconsistencies", none of them real.
    #
    # Residual ambiguity, stated rather than hidden: loop numbers repeat across runs
    # (the counter restarts at 1), so an old entry's first_seen_loop can collide with a
    # new run's. Closing that needs run_id on both sides, and run_id is null on 14 of 15
    # loops in the corpus. This is strictly better than unscoped, not exact.
    history_loops = {e.get("loop") for e in loops if isinstance(e.get("loop"), int)}
    in_scope: list[str] = []
    out_of_scope: list[str] = []
    inconsistent: list[str] = []
    for entry in (registry or {}).get("entries") or []:
        sid, primary = entry.get("stable_id"), entry.get("primary_file")
        if not primary or not sid:
            continue
        seen_at = entry.get("first_seen_loop")
        # A MISSING first_seen_loop stays in scope. We cannot prove such an entry is
        # out of scope, and dropping unprovable cases silently is the same
        # survivor-metric hazard the typed exclusions above exist to avoid. Only a
        # first sighting demonstrably outside this history is set aside.
        last_at = entry.get("last_seen_loop")
        # Two independent out-of-scope signals, both from data already present:
        # a first sighting not in this history, or a LAST sighting beyond its highest
        # loop -- an entry that reached loop 2 cannot belong to a 1-loop history.
        # Found on the live BenchHype run: F-003 (last_seen_loop=2 vs a 1-loop history)
        # was reported as a review inconsistency until this rule set it aside.
        max_loop = max(history_loops) if history_loops else None
        beyond = isinstance(last_at, int) and max_loop is not None and last_at > max_loop
        if (isinstance(seen_at, int) and seen_at not in history_loops) or beyond:
            out_of_scope.append(sid)
            continue
        in_scope.append(sid)
        if primary not in first_cite:
            inconsistent.append(sid)

    # Per run: what THIS run cited, and what it cited FIRST. A cumulative figure
    # cannot answer "what did this run cover", which is the question a diagnostic run
    # is asking; `first_cited_here` is the marginal contribution over everything
    # earlier runs had already reached.
    per_run: list[dict] = []
    seen_before: set[str] = set()
    for i, run in enumerate(split_runs(history)):
        rid = next((e.get("run_id") for e in run if e.get("run_id")), None)
        nums = [e.get("loop") for e in run if isinstance(e.get("loop"), int)]
        here = sorted(p for p in cited_paths({"loops": run}) if p in denom_set)
        first_here = [p for p in here if p not in seen_before]
        seen_before.update(here)
        per_run.append(
            {
                "index": i,
                "run_id": rid,
                "loops": len(run),
                "loop_range": [min(nums), max(nums)] if nums else None,
                "cited": len(here),
                "first_cited_here": len(first_here),
            }
        )

    # Included denominator files under each declared root -- consumed by the halt
    # handoff's per-root coverage disclosure. A missing root naturally counts 0
    # (nothing was walked under it).
    per_root: dict[str, int] = {}
    for root in source_roots:
        root_norm = root.rstrip("/")
        if root_norm in ("", "."):
            per_root[root] = len(denominator)
        else:
            prefix = root_norm + "/"
            per_root[root] = sum(1 for f in denominator if f == root_norm or f.startswith(prefix))

    total = len(denominator)
    return {
        "schema": "coverage-ledger/1",
        "promotion_allowed": False,
        # Load-bearing label: this is a lower bound on attention, not a claim about
        # what was read. See the module docstring.
        "measure": "citation",
        "repo_root": str(repo_root),
        "source_roots": source_roots,
        "loops": len(loops),
        "denominator": {
            "count": total,
            "files": denominator,
            # scanned == included + excluded, derived on every run (design note §5)
            "excluded_by_reason": excluded,
            "missing_roots": missing_roots,
            "scanned": total + sum(excluded.values()),
        },
        "per_root": per_root,
        "sets": {
            "cited": cited,
            "uncited": uncited,
            "stale": sorted(stale),
            "outside_denominator": outside,
        },
        "totals": {
            "cited": len(cited),
            "uncited": len(uncited),
            "cited_pct": round(100.0 * len(cited) / total, 1) if total else None,
        },
        "per_run": per_run,
        "revision": {"unavailable_loops": sorted(unavailable)},
        "registry_crosscheck": {
            "checked": len(in_scope),
            "inconsistent": sorted(inconsistent),
            # entries whose first sighting predates this history -- not judged
            "out_of_scope": len(out_of_scope),
        },
    }


def _load(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def observation_shas(registry: dict | None) -> dict[int, str]:
    """loop -> observation sha, from the registry only. Never searched, never HEAD."""
    out: dict[int, str] = {}
    for entry in (registry or {}).get("entries") or []:
        for occ in entry.get("occurrences") or []:
            sha, loop = occ.get("sha"), occ.get("loop")
            if (
                occ.get("status") == "open"
                and isinstance(loop, int)
                and sha
                and not str(sha).startswith("<")
            ):
                out.setdefault(loop, sha)
        seen, sha = entry.get("first_seen_loop"), entry.get("first_seen_sha")
        if isinstance(seen, int) and sha and not str(sha).startswith("<"):
            out.setdefault(seen, sha)
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Citation-coverage ledger (reports; never gates)")
    ap.add_argument("repo_root", type=Path)
    ap.add_argument("--json", type=Path, default=None)
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument(
        "--list-source-roots",
        action="store_true",
        help="print the enumerated source roots (one per line) and exit; needs no history",
    )
    args = ap.parse_args(argv)

    if not args.repo_root.is_dir():
        sys.stderr.write(f"error: not a directory: {args.repo_root}\n")
        return 2

    if args.list_source_roots:
        for root in source_roots(args.repo_root):
            print(root)
        return 0

    history = _load(args.repo_root / "REVIEW_HISTORY.json")
    if history is None:
        sys.stderr.write("error: no readable REVIEW_HISTORY.json — nothing to measure\n")
        return 2
    registry = _load(args.repo_root / "findings_registry.json")

    try:
        led = compute_ledger(args.repo_root, history, registry, observation_shas(registry))
    except InvalidSourceRoot as exc:
        sys.stderr.write(f"error: {exc}\n")
        return 2
    if args.json is not None:
        try:
            args.json.write_text(json.dumps(led, indent=2) + "\n", encoding="utf-8")
        except OSError as exc:
            sys.stderr.write(f"error: could not write --json output: {exc}\n")
            return 2
    if not args.quiet:
        t = led["totals"]
        print(
            f"[coverage-ledger measure=citation] {t['cited']}/{led['denominator']['count']} "
            f"source files cited ({t['cited_pct']}%) across {led['loops']} loop(s); "
            f"stale={len(led['sets']['stale'])} "
            f"registry-inconsistent={len(led['registry_crosscheck']['inconsistent'])}"
        )
        if len(led["per_run"]) > 1:
            last = led["per_run"][-1]
            print(
                f"  latest run (loops {last['loop_range']}): cited {last['cited']}, "
                f"{last['first_cited_here']} not reached by any earlier run"
            )
        if led["revision"]["unavailable_loops"]:
            print(f"  no recorded revision for loop(s): {led['revision']['unavailable_loops']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
