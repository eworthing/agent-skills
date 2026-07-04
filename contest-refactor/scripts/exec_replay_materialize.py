#!/usr/bin/env python3
"""Materialize a Layer-5 exec-fixture and print the Step-3-only dispatch (the host runs the loop).

Constructs the Step-3 entry conditions externally: the base commit is the **source only** (matching
a real fused loop, where Step-1+2's CURRENT_REVIEW.* are written but not committed until Step-3
sub-step 11); the seed artifacts are overlaid **uncommitted**. The grader then diffs base..HEAD,
cleanly separating the executor's source changes from the artifacts it commits. Runs no model — the
Step-3 executor is host-dispatched via the pinned evals/exec_step3_executor_prompt.md template.

Usage:
  exec_replay_materialize.py <fixture-id> [dest-dir] [--arm-model MODEL]
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
FIXTURES_DIR = SKILL_ROOT / "evals" / "exec-fixtures"
TEMPLATE_PATH = SKILL_ROOT / "evals" / "exec_step3_executor_prompt.md"
MANIFEST_PATH = SKILL_ROOT / "evals" / "exec_replay_baseline.json"
SEED_FILES = ("CURRENT_REVIEW.json", "CURRENT_REVIEW.md", "findings_registry.json")


def _git(repo: Path, *args: str) -> str:
    out = subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True
    )
    return out.stdout.strip()


def main(argv: list[str]) -> int:
    pos = [a for a in argv if not a.startswith("--")]
    arm_model = next((a.split("=", 1)[1] for a in argv if a.startswith("--arm-model=")), None)
    if "--arm-model" in argv:  # space form
        i = argv.index("--arm-model")
        if i + 1 < len(argv):
            arm_model = argv[i + 1]
            pos = [a for a in pos if a != arm_model]
    if not pos:
        sys.exit("usage: exec_replay_materialize.py <fixture-id> [dest-dir] [--arm-model MODEL]")
    fixture_id = pos[0]
    fdir = FIXTURES_DIR / fixture_id
    codebase = fdir / "codebase"
    seed_dir = fdir / "seed"
    exp_path = fdir / "expected.toml"
    if not codebase.is_dir():
        sys.exit(f"FAIL: fixture '{fixture_id}' has no codebase/ ({codebase})")
    expected = tomllib.loads(exp_path.read_text()) if exp_path.exists() else {}
    if arm_model is None:
        manifest = json.loads(MANIFEST_PATH.read_text()) if MANIFEST_PATH.exists() else {}
        arm_model = (manifest.get("prereg") or {}).get("arm_a_model", "claude-sonnet-4-6")

    if len(pos) >= 2:
        dest = Path(pos[1]).resolve()
        if dest.exists():
            sys.exit(f"FAIL: dest already exists: {dest}")
    else:
        dest = Path(tempfile.mkdtemp(prefix=f"exec-replay-{fixture_id}-"))
        dest.rmdir()

    # base commit = SOURCE ONLY
    shutil.copytree(codebase, dest)
    _git(dest, "init", "-q")
    _git(dest, "add", "-A")
    _git(
        dest,
        "-c",
        "user.name=exec-replay",
        "-c",
        "user.email=exec-replay@local",
        "commit",
        "-q",
        "-m",
        f"base: {fixture_id} source (pre-Step-1)",
    )
    base_sha = _git(dest, "rev-parse", "HEAD")

    # overlay the seeded Step-1+2 output UNCOMMITTED (in-flight working state)
    for name in SEED_FILES:
        src = seed_dir / name
        if src.exists():
            shutil.copy2(src, dest / name)

    lens = expected.get("lens", "(select per Step 0)")
    test_cmd = expected.get("test_command") or "(none configured; build oracle = swiftc -typecheck)"
    dispatch = TEMPLATE_PATH.read_text()
    for k, v in {
        "{{REPO}}": str(dest),
        "{{LENS}}": lens,
        "{{TEST_COMMAND}}": test_cmd,
        "{{ARM_MODEL}}": arm_model,
        "{{SKILL_DIR}}": str(SKILL_ROOT),
    }.items():
        dispatch = dispatch.replace(k, v)

    print(f"materialized exec-fixture '{fixture_id}' (kind={expected.get('kind')}) ->")
    print(f"  repo:     {dest}")
    print(f"  base_sha: {base_sha}")
    print(f"  arm:      {arm_model}")
    print()
    print("=== DISPATCH (host-run a Step-3-only executor with this verbatim prompt) ===")
    print(dispatch)
    print("=== GRADE (after the executor commits) ===")
    print(f"  python3 scripts/exec_replay_grade.py {fixture_id} {dest} {base_sha}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
