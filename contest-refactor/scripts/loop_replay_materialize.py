#!/usr/bin/env python3
"""Materialize a loop-replay fixture into a throwaway git repo (Layer 4).

Copies evals/loop-fixtures/<id>/codebase/ into a fresh dir, makes it a clean committed
git repo (so the loop's own commits and `git diff` behave byte-identically to a real run),
and prints the dispatch + grade commands for the host. It runs no model — the loop itself
is host-dispatched (verbatim references/trust-model.md loop-subagent template), matching the
Layer 2/3 manual posture. The grader (loop_replay_grade.py) then checks the emitted artifact.

Usage:
  loop_replay_materialize.py <fixture-id> [dest-dir]

  dest-dir  where to materialize (default: a fresh temp dir). Must not already exist.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
FIXTURES_DIR = SKILL_ROOT / "evals" / "loop-fixtures"


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True)


def main(argv: list[str]) -> int:
    if not argv:
        sys.exit("usage: loop_replay_materialize.py <fixture-id> [dest-dir]")
    fixture_id = argv[0]
    fdir = FIXTURES_DIR / fixture_id
    codebase = fdir / "codebase"
    exp_path = fdir / "expected.toml"
    if not codebase.is_dir():
        sys.exit(f"FAIL: fixture '{fixture_id}' has no codebase/ ({codebase})")
    expected = tomllib.loads(exp_path.read_text()) if exp_path.exists() else {}

    if len(argv) >= 2:
        dest = Path(argv[1]).resolve()
        if dest.exists():
            sys.exit(f"FAIL: dest already exists: {dest}")
    else:
        dest = Path(tempfile.mkdtemp(prefix=f"loop-replay-{fixture_id}-"))
        dest.rmdir()  # mkdtemp made it; copytree wants to create it

    shutil.copytree(codebase, dest)
    _git(dest, "init", "-q")
    _git(dest, "add", "-A")
    # deterministic identity so the replay doesn't depend on host git config
    _git(dest, "-c", "user.name=loop-replay", "-c", "user.email=loop-replay@local",
         "commit", "-q", "-m", f"base: {fixture_id} fixture")

    lens = expected.get("lens", "(select per Step 0)")
    test_cmd = expected.get("test_command") or "(none configured)"
    smell = expected.get("smell", "(see expected.toml)")

    print(f"materialized fixture '{fixture_id}' ->")
    print(f"  {dest}")
    print()
    print("DISPATCH (host-run, one loop):")
    print(f"  Run ONE contest-refactor loop against the repo above using the verbatim")
    print(f"  references/trust-model.md § Loop Isolation loop-subagent template.")
    print(f"  Step-0 context to seed: lens={lens}; test command={test_cmd}.")
    print(f"  Planted debt to catch: {smell}")
    print()
    print("GRADE (after the loop emits CURRENT_REVIEW.json):")
    print(f"  python3 scripts/loop_replay_grade.py {fixture_id} {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
