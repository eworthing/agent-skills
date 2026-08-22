#!/usr/bin/env python3
"""Selftest for _wtree.py (item 14): source-scoped fingerprints, both entry points.

Every case runs against throwaway git repos; the real repo is never touched. Cases per
the peer-approved plan, including the codex-B4 regression (fingerprint-at an older
commit whose bookkeeping file differs from both HEAD and the worktree — the
`git rm --cached` predecessor refused exactly there).
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

from _wtree import BOOKKEEPING_PATHS, source_tree_fingerprint, source_tree_fingerprint_at


def _git(repo: Path, *args: str) -> str:
    out = subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True
    )
    return out.stdout.strip()


def _mkrepo(td: Path) -> Path:
    repo = td / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@t")
    _git(repo, "config", "user.name", "t")
    (repo / "src").mkdir()
    (repo / "src" / "a.txt").write_text("alpha v1\n")
    (repo / "CURRENT_REVIEW.json").write_text('{"loop": 1}\n')
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "c1")
    return repo


def main() -> int:
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="wtree-selftest-") as td_s:
        td = Path(td_s)
        repo = _mkrepo(td)
        base = source_tree_fingerprint(repo)
        head = _git(repo, "rev-parse", "HEAD")

        # Both entry points agree on a clean committed tree.
        if source_tree_fingerprint_at(repo, head) != base:
            failures.append("clean committed tree: worktree and commit paths must agree")

        # Untracked source file changes the fingerprint.
        (repo / "src" / "new.txt").write_text("untracked\n")
        if source_tree_fingerprint(repo) == base:
            failures.append("untracked source file must change the fingerprint")
        (repo / "src" / "new.txt").unlink()

        # EVERY bookkeeping path, named LITERALLY. Only CURRENT_REVIEW.json was ever
        # exercised individually, so shrinking BOOKKEEPING_PATHS passed. Note the
        # first fix attempted here was itself vacuous: it looped over
        # BOOKKEEPING_PATHS, so a mutation shrinking the constant shrank the loop
        # too and still passed -- an oracle derived from the implementation it is
        # meant to check. The expected set is therefore written out in full; the
        # test must know what belongs there independently of the code.
        expected_bookkeeping = {
            "CURRENT_REVIEW.md",
            "CURRENT_REVIEW.json",
            "REVIEW_HISTORY.md",
            "REVIEW_HISTORY.json",
            "findings_registry.json",
            "LOOP_STATE.json",
        }
        if set(BOOKKEEPING_PATHS) != expected_bookkeeping:
            failures.append(
                f"BOOKKEEPING_PATHS changed: {sorted(set(BOOKKEEPING_PATHS) ^ expected_bookkeeping)} "
                "differ. Every entry is excluded from the source fingerprint, so dropping one makes "
                "normal loop bookkeeping register as source drift; adding one hides real drift."
            )
        for name in sorted(expected_bookkeeping):
            target = repo / name
            existed = target.exists()
            before = source_tree_fingerprint(repo)
            target.write_text('{"bookkeeping": "churn"}\n')
            if source_tree_fingerprint(repo) != before:
                failures.append(
                    f"bookkeeping path {name!r} changed the source fingerprint; it must be "
                    "excluded like every other entry in BOOKKEEPING_PATHS"
                )
            if not existed:
                target.unlink()

        # Bookkeeping churn does not.
        for name in sorted(BOOKKEEPING_PATHS):
            (repo / name).write_text('{"churn": true}\n')
        if source_tree_fingerprint(repo) != base:
            failures.append("bookkeeping churn must not change the fingerprint")
        for name in sorted(BOOKKEEPING_PATHS):
            if name != "CURRENT_REVIEW.json":
                (repo / name).unlink()
        (repo / "CURRENT_REVIEW.json").write_text('{"loop": 1}\n')

        # Committing identical content does not change the worktree fingerprint.
        _git(repo, "commit", "-q", "--allow-empty", "-m", "c2-empty")
        if source_tree_fingerprint(repo) != base:
            failures.append("identical-content commit must not change the fingerprint")

        # Deletion changes it.
        (repo / "src" / "a.txt").unlink()
        if source_tree_fingerprint(repo) == base:
            failures.append("source deletion must change the fingerprint")
        (repo / "src" / "a.txt").write_text("alpha v1\n")

        # Rename changes it.
        (repo / "src" / "a.txt").rename(repo / "src" / "b.txt")
        if source_tree_fingerprint(repo) == base:
            failures.append("source rename must change the fingerprint")
        (repo / "src" / "b.txt").rename(repo / "src" / "a.txt")

        # Staged-but-uncommitted change: INCLUDED by the worktree path, EXCLUDED by the
        # commit path — asserted in both directions.
        (repo / "src" / "a.txt").write_text("alpha v2 staged\n")
        _git(repo, "add", "src/a.txt")
        staged_wt = source_tree_fingerprint(repo)
        staged_at = source_tree_fingerprint_at(repo, "HEAD")
        if staged_wt == base:
            failures.append("staged change must be included by the worktree path")
        if staged_at != base:
            failures.append("staged change must be excluded by the commit path")
        _git(repo, "restore", "--staged", "src/a.txt")
        (repo / "src" / "a.txt").write_text("alpha v1\n")

        # Real index byte-identical before/after both entry points.
        index = repo / ".git" / "index"
        before = index.read_bytes()
        source_tree_fingerprint(repo)
        source_tree_fingerprint_at(repo, "HEAD")
        if index.read_bytes() != before:
            failures.append("the real index must be byte-identical before/after")

        # Subdirectory invocation agrees with root invocation (cwd-independence).
        cwd = Path.cwd()
        try:
            os.chdir(repo / "src")
            if source_tree_fingerprint(repo) != base:
                failures.append("subdirectory invocation must agree with root invocation")
        finally:
            os.chdir(cwd)

        # codex-B4 regression: fingerprint-at an older commit whose bookkeeping file
        # differs from BOTH current HEAD and the worktree.
        old_head = _git(repo, "rev-parse", "HEAD")
        (repo / "CURRENT_REVIEW.json").write_text('{"loop": 2}\n')
        (repo / "src" / "a.txt").write_text("alpha v3\n")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-qm", "c3")
        (repo / "CURRENT_REVIEW.json").write_text('{"loop": 3, "dirty": true}\n')
        try:
            old_fp = source_tree_fingerprint_at(repo, old_head)
        except subprocess.CalledProcessError as exc:
            failures.append(
                f"fingerprint-at an older commit with divergent bookkeeping must succeed "
                f"(got: {exc.stderr.strip()[:120]!r})"
            )
        else:
            if old_fp != base:
                failures.append(
                    "fingerprint-at the older commit must equal the base fingerprint "
                    "(same source content)"
                )

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    print("OK: _wtree — source-scoped, cwd-independent, index-safe, both entry points")
    return 0


if __name__ == "__main__":
    sys.exit(main())
