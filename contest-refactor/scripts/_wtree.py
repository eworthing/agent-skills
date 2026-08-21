#!/usr/bin/env python3
"""Source-scoped working-tree fingerprints for the execution-evidence ledger (item 14).

Two entry points over one primitive (a throwaway git index):

- ``source_tree_fingerprint(repo)`` — fingerprint of the WORKING TREE's source content:
  seed the throwaway index from the real one when present (stat-cache reuse on large
  repos), ``git add -A``, drop the six bookkeeping paths, ``git write-tree``.
- ``source_tree_fingerprint_at(repo, commit)`` — fingerprint of a COMMIT's source
  content: ``git read-tree <commit>`` into an empty throwaway index, drop the six
  bookkeeping paths, ``git write-tree``. Never stages the working tree — the two entry
  points deliberately disagree on a dirty tree.

"Source-scoped" means the six loop-bookkeeping paths are excluded — the same carve-out
``changed_paths`` uses (SKILL.md Step 3 sub-step 6). Tests run at sub-step 3; bookkeeping
is written at sub-steps 6-10 before the sub-step-11 commit, so a FULL-tree fingerprint
recorded at test time could never equal the commit-time tree. Excluding bookkeeping makes
"the code under test" the invariant: an untracked source file or a source edit changes the
fingerprint; committing identical content or bookkeeping churn does not.

The real index is never touched. Note: ``git add -A`` honors ``.gitignore``, so
ignored-file changes are outside the attestation boundary by design (Tier 1).
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

# The six loop-bookkeeping paths — single source of truth for the source-scope carve-out.
BOOKKEEPING_PATHS: frozenset[str] = frozenset(
    {
        "CURRENT_REVIEW.md",
        "CURRENT_REVIEW.json",
        "REVIEW_HISTORY.md",
        "REVIEW_HISTORY.json",
        "findings_registry.json",
        "LOOP_STATE.json",
    }
)


def _git(repo: Path, *args: str, index_file: Path) -> str:
    env = dict(os.environ)
    env["GIT_INDEX_FILE"] = str(index_file)
    out = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )
    return out.stdout.strip()


def _real_index_path(repo: Path) -> Path:
    out = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "--git-path", "index"],
        check=True,
        capture_output=True,
        text=True,
    )
    p = Path(out.stdout.strip())
    # --git-path output is relative to the repo root in an ordinary checkout; a linked
    # worktree may already return an absolute path.
    return p if p.is_absolute() else repo / p


def _drop_bookkeeping_and_write(repo: Path, index_file: Path) -> str:
    # --force-remove with all six paths unconditionally: absent entries succeed, and it
    # does not carry `git rm --cached`'s safety refusal when the indexed content differs
    # from both the worktree and HEAD (which a historical index legitimately does).
    _git(
        repo,
        "update-index",
        "--force-remove",
        "--",
        *sorted(BOOKKEEPING_PATHS),
        index_file=index_file,
    )
    return _git(repo, "write-tree", index_file=index_file)


def source_tree_fingerprint(repo: Path | str) -> str:
    """Fingerprint the working tree's source content (bookkeeping excluded)."""
    repo = Path(repo).resolve()
    with tempfile.TemporaryDirectory(prefix="wtree-") as td:
        index_file = Path(td) / "index"
        real_index = _real_index_path(repo)
        if real_index.is_file():
            shutil.copy2(real_index, index_file)
        _git(repo, "add", "-A", index_file=index_file)
        return _drop_bookkeeping_and_write(repo, index_file)


def source_tree_fingerprint_at(repo: Path | str, commit: str) -> str:
    """Fingerprint a commit's source content (bookkeeping excluded).

    MUST NOT stage the working tree: the index is seeded from the commit alone, so the
    result reflects the commit, never uncommitted edits.
    """
    repo = Path(repo).resolve()
    with tempfile.TemporaryDirectory(prefix="wtree-at-") as td:
        index_file = Path(td) / "index"
        _git(repo, "read-tree", commit, index_file=index_file)
        return _drop_bookkeeping_and_write(repo, index_file)
