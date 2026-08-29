#!/usr/bin/env python3
"""Selftest for hooks/precommit-validator (Tier-3 commit-boundary hook).

The hook's whole value is its decision table, so this exercises it end to end
against real payloads and real artifact directories -- not mocks of itself.

The invariant that matters: the hook must FAIL CLOSED (exit 2) when it cannot
establish that validation passed, and pass through (exit 0) when the tool call
is not a loop commit. A hook that fails open on its own breakage is worse than
no hook, because it reports nothing while enforcing nothing.

Run directly; exit 0 = pass.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
HOOK = SKILL_ROOT / "hooks" / "precommit-validator"
FIXTURES = SKILL_ROOT / "evals" / "fixtures"


def run(payload: dict, hook: Path = HOOK) -> tuple[int, str]:
    proc = subprocess.run(
        [str(hook)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.returncode, proc.stdout + proc.stderr


def payload(command: str, cwd: str) -> dict:
    return {
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": command},
        "cwd": cwd,
    }


def main() -> int:
    assert HOOK.is_file(), f"hook missing: {HOOK}"
    checks = 0

    with tempfile.TemporaryDirectory() as tmp:
        empty = Path(tmp) / "no-artifact"
        empty.mkdir()

        # 1. Not a commit -> pass through, silently.
        rc, _ = run(payload("ls -la", str(empty)))
        assert rc == 0, "a non-commit tool call must pass through"
        checks += 1

        # 2. A commit in a repo with no artifact is not a loop commit.
        rc, _ = run(payload("git commit -m 'unrelated'", str(empty)))
        assert rc == 0, "a commit with no CURRENT_REVIEW.json must pass through"
        checks += 1

        # 3. A commit over a FAILING artifact blocks, and returns the findings.
        bad = Path(tmp) / "failing"
        shutil.copytree(FIXTURES / "g43-convergence-pass-missing", bad)
        rc, out = run(payload("git commit -m 'loop 1: emit'", str(bad)))
        assert rc == 2, f"a failing artifact must block the commit (got {rc})"
        assert "BLOCKED" in out, "the block must say so"
        assert "G43" in out, "the validator's findings must reach the model"
        checks += 1

        # 4. The trust ceiling is stated on every block -- never let a block
        #    imply more assurance than a same-privilege control provides.
        assert "same-privilege" in out, "a block must state the trust ceiling"
        checks += 1

        # 5. Missing validator -> fail CLOSED, not open.
        broken_root = Path(tmp) / "broken"
        (broken_root / "hooks").mkdir(parents=True)
        (broken_root / "scripts").mkdir()
        shutil.copy(HOOK, broken_root / "hooks" / "precommit-validator")
        rc, out = run(
            payload("git commit -m 'x'", str(bad)), broken_root / "hooks" / "precommit-validator"
        )
        assert rc == 2, "a missing validator must fail closed"
        assert "validator missing" in out, "fail-closed must name the cause"
        checks += 1

        # 6. An unparseable payload must be LOUD. It allows the call (blocking
        #    every tool on a parse error would brick the session) but it must
        #    say the check did not run -- silence here would disable the hook
        #    invisibly if a provider changed its payload shape.
        proc = subprocess.run(
            [str(HOOK)], input='{"unexpected":1}', capture_output=True, text=True, check=False
        )
        assert proc.returncode == 0, "a parse failure must not brick the session"
        assert "DID NOT RUN" in proc.stderr, "a parse failure must announce itself"
        checks += 1

        # 7. Health check reports an unregistered hook distinctly from a failure.
        proc = subprocess.run([str(HOOK), "--health"], capture_output=True, text=True, check=False)
        assert "NO HOOK ACTIVE" in proc.stdout or "registered :" in proc.stdout
        assert "trust" in proc.stdout, "health must state the trust ceiling"
        checks += 1

        # 8. Health must NEVER imply a registered hook is firing. Measured
        #    2026-08-29: codex silently skips a registered-but-untrusted hook --
        #    it enforces nothing and reports nothing, so a health check that
        #    equates registration with activation is itself a silent pass.
        if "registered :" in proc.stdout and "NO HOOK ACTIVE" not in proc.stdout:
            assert "ACTIVE?" in proc.stdout and "UNKNOWN" in proc.stdout, (
                "health claims registration without flagging it is not activation"
            )
            assert "--probe" in proc.stdout, "health must point at the activation probe"
            checks += 1

    print(f"_precommit_hook_selftest: OK ({checks} assertions)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
