#!/usr/bin/env python3
"""Fail-fast precondition gate, run BEFORE the first subagent is dispatched.

contest-refactor runs its Critic/Architect/Execution work in fresh subagents. A bad
input — a scope dir that isn't there, a test command whose binary doesn't resolve, a
base ref that doesn't exist — should abort here, in the main agent, with one clear
message, instead of failing opaquely two layers deep inside a spawned agent
(mattpocock-skills@2e64732: "A bad ref or empty diff should fail here — not inside two
parallel sub-agents.").

This is prevention only. It does NOT touch the post-spawn idle-recovery path
(trust-model.md HALT routing, added in 4c3e98e); that cure is unchanged. Stdlib-only,
Python 3.11+.

Usage:
    preflight.py <scope-dir> [--test-cmd "CMD ..."] [--base-ref REF]

    <scope-dir>        source/scope directory that must exist before review starts
    --test-cmd "CMD"   discovered test/build command; its leading binary must resolve
    --base-ref REF     optional base ref; must `git rev-parse --verify` in the CWD

Exit codes: 0 = every precondition passed; 1 = one or more failed (each printed to
stderr); 2 = usage error.
"""

from __future__ import annotations

import argparse
import shlex
import shutil
import subprocess
import sys
from pathlib import Path


def _test_command_resolves(test_cmd: str) -> tuple[bool, str]:
    """The leading token of the test command must be a binary on PATH or an
    existing executable file. We check only the launcher, not the whole pipeline —
    this is a sanity gate, not a shell."""
    try:
        tokens = shlex.split(test_cmd)
    except ValueError as exc:
        return False, f"test command is not parseable: {exc}"
    if not tokens:
        return False, "test command is empty"
    launcher = tokens[0]
    if "/" in launcher or "\\" in launcher:
        p = Path(launcher)
        if p.is_file():
            return True, ""
        return False, f"test command launcher not found: {launcher}"
    if shutil.which(launcher):
        return True, ""
    return False, f"test command launcher not on PATH: {launcher}"


def _base_ref_resolves(base_ref: str) -> tuple[bool, str]:
    if shutil.which("git") is None:
        return False, "base ref given but `git` is not available"
    proc = subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", f"{base_ref}^{{commit}}"],
        capture_output=True,
        text=True,
    )
    if proc.returncode == 0:
        return True, ""
    return False, f"base ref does not resolve: {base_ref}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Fail-fast precondition gate before subagent dispatch."
    )
    parser.add_argument("scope_dir", help="source/scope directory that must exist")
    parser.add_argument("--test-cmd", help="discovered test/build command to sanity-check")
    parser.add_argument("--base-ref", help="optional base ref to verify with git rev-parse")
    args = parser.parse_args(argv)

    failures: list[str] = []

    if not Path(args.scope_dir).is_dir():
        failures.append(f"scope directory does not exist: {args.scope_dir}")

    if args.test_cmd:
        ok, msg = _test_command_resolves(args.test_cmd)
        if not ok:
            failures.append(msg)

    if args.base_ref:
        ok, msg = _base_ref_resolves(args.base_ref)
        if not ok:
            failures.append(msg)

    if failures:
        for f in failures:
            print(f"preflight: FAIL: {f}", file=sys.stderr)
        print(
            "preflight: aborting before any subagent dispatch — fix the above and re-run.",
            file=sys.stderr,
        )
        return 1

    print("preflight: OK — scope dir, test command, and base ref all resolve.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
