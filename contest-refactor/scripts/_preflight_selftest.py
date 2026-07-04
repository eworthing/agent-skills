#!/usr/bin/env python3
"""Self-test: preflight.py fails fast on a knowably-bad run BEFORE any subagent spawn.

contest-refactor dispatches its Critic/Architect/Execution work into fresh subagents.
If the scope dir, the discovered test command, or a configured base ref is bad, the
run should die in the main agent with a clear message — not three layers deep inside a
spawned agent (mattpocock-skills@2e64732). preflight.py is that gate.

No pytest in this repo (pyproject configures only ruff), so this standalone check runs
the CLI as a subprocess against throwaway tempdirs (and a throwaway git repo for the
base-ref case) and asserts on exit codes + stderr.

Cases:
  - healthy (real dir + resolvable test cmd)   -> exit 0
  - missing scope dir                          -> non-zero, names the scope dir
  - unresolvable test command                  -> non-zero, names the test command
  - base ref: HEAD in a real repo -> exit 0;  bogus ref -> non-zero, names the ref

Run: python3 scripts/_preflight_selftest.py   (exit 0 = pass, 1 = fail)
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

PREFLIGHT = Path(__file__).with_name("preflight.py")


def _run(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(PREFLIGHT), *args],
        capture_output=True,
        text=True,
        cwd=str(cwd) if cwd else None,
    )


def _init_repo(root: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.email=t@t",
            "-c",
            "user.name=t",
            "commit",
            "--allow-empty",
            "-q",
            "-m",
            "init",
        ],
        cwd=root,
        check=True,
    )


def main() -> int:
    if not PREFLIGHT.is_file():
        print(f"FAIL: preflight script missing: {PREFLIGHT}")
        return 1

    failures: list[str] = []
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        scope = base / "src"
        scope.mkdir()

        # 1) healthy: existing dir + a test command whose binary resolves.
        p = _run([str(scope), "--test-cmd", f"{sys.executable} -m pytest"])
        if p.returncode != 0:
            failures.append(f"healthy: expected exit 0, got {p.returncode}\n{p.stderr.rstrip()}")

        # 2) missing scope dir.
        p = _run([str(base / "nope")])
        if p.returncode == 0:
            failures.append("missing-dir: expected non-zero exit, got 0")
        elif "scope" not in p.stderr.lower():
            failures.append(f"missing-dir: message should name the scope dir\n{p.stderr.rstrip()}")

        # 3) unresolvable test command.
        p = _run([str(scope), "--test-cmd", "definitely-not-a-real-binary-xyz run"])
        if p.returncode == 0:
            failures.append("bad-test-cmd: expected non-zero exit, got 0")
        elif "test command" not in p.stderr.lower():
            failures.append(
                f"bad-test-cmd: message should name the test command\n{p.stderr.rstrip()}"
            )

        # 4) base ref resolution (real temp git repo).
        if shutil.which("git"):
            repo = base / "repo"
            repo.mkdir()
            _init_repo(repo)
            p = _run([str(repo), "--base-ref", "HEAD"], cwd=repo)
            if p.returncode != 0:
                failures.append(
                    f"good-ref: HEAD should resolve, got {p.returncode}\n{p.stderr.rstrip()}"
                )
            p = _run([str(repo), "--base-ref", "no-such-ref-zzz"], cwd=repo)
            if p.returncode == 0:
                failures.append("bad-ref: expected non-zero exit, got 0")
            elif "ref" not in p.stderr.lower():
                failures.append(f"bad-ref: message should name the ref\n{p.stderr.rstrip()}")
        else:
            print("note: git not found — skipping base-ref cases")

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    print(
        "OK: preflight — healthy inputs pass; missing scope dir, unresolvable test "
        "command, and bogus base ref each fail fast with a clear message"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
