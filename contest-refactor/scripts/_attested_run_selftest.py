#!/usr/bin/env python3
"""Selftest for attested_run.py (item 14): subprocesses the SHIPPED script, never a
reimplementation (the item-16 acceptance rule, commit 58cbbfe — a selftest that
reimplements the wrapper's exit-code capture would recreate the self-reported-oracle
problem this item closes).

Every wrapper subprocess runs under a temp CONTEST_REFACTOR_HOME; the final assertion
proves the real home state was untouched.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
WRAPPER = SCRIPTS / "attested_run.py"


def _git(repo: Path, *args: str) -> str:
    out = subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True
    )
    return out.stdout.strip()


def _mkrepo(td: Path) -> Path:
    repo = td / "repo"
    (repo / "src").mkdir(parents=True)
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@t")
    _git(repo, "config", "user.name", "t")
    (repo / "src" / "a.txt").write_text("alpha\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "base")
    return repo


def _run(home: Path, cwd: Path, *args: str, timeout: int = 60) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["CONTEST_REFACTOR_HOME"] = str(home)
    return subprocess.run(
        [sys.executable, str(WRAPPER), *args],
        cwd=cwd,
        env=env,
        capture_output=True,
        timeout=timeout,
    )


def _records(home: Path) -> list[dict]:
    ledger = home / "attestation-ledger.jsonl"
    if not ledger.is_file():
        return []
    return [json.loads(line) for line in ledger.read_text().splitlines() if line.strip()]


def _home_snapshot() -> tuple[bool, bytes, bytes]:
    real = Path.home() / ".contest-refactor"
    ledger = real / "attestation-ledger.jsonl"
    trust = real / "verify-trust.json"
    return (
        real.exists(),
        ledger.read_bytes() if ledger.is_file() else b"",
        trust.read_bytes() if trust.is_file() else b"",
    )


def main() -> int:
    failures: list[str] = []
    real_before = _home_snapshot()

    with tempfile.TemporaryDirectory(prefix="attested-selftest-") as td_s:
        td = Path(td_s)
        repo = _mkrepo(td)
        home = td / "state-home"  # does not exist yet: mkdir-on-first-use is under test

        # Passing child + record shape + mkdir-on-first-use.
        before_call = datetime.now(UTC)
        r = _run(home, repo, "--run-id", "run-t-1", "--", "echo", "hello")
        after_call = datetime.now(UTC)
        if r.returncode != 0:
            failures.append(f"passing child: wrapper exit {r.returncode}, want 0")
        recs = _records(home)
        if len(recs) != 1:
            failures.append(f"passing child: {len(recs)} records, want 1")
        else:
            rec = recs[0]
            if rec["exit_status"] != 0 or rec["attestation_status"] != "consistency_check":
                failures.append(
                    f"passing child: bad record {rec['exit_status']}/{rec['attestation_status']}"
                )
            if rec["run_id"] != "run-t-1" or rec["repo_root"] != str(repo.resolve()):
                failures.append("passing child: run_id/repo_root not recorded faithfully")
            # Digest matches an independent hash of the same bytes (stdout tee'd through).
            if rec["stdout_digest"] != hashlib.sha256(b"hello\n").hexdigest():
                failures.append("stdout_digest must match an independent sha256 of the bytes")
            if rec["stdout_digest"] == rec["stderr_digest"]:
                failures.append("stdout/stderr digests must be separate (stderr was empty)")
            # Timestamp from the wrapper clock, inside the observed call window (row 9).
            ts = datetime.fromisoformat(rec["timestamp"])
            if not (before_call <= ts <= after_call):
                failures.append("timestamp must fall inside the observed call window")
            if b"hello" not in r.stdout:
                failures.append("child stdout must be tee'd through live")

        # Failing child: exit propagated + recorded; ledger append-only.
        first_bytes = (home / "attestation-ledger.jsonl").read_bytes()
        r = _run(home, repo, "--run-id", "run-t-1", "--", "bash", "-c", "exit 7")
        if r.returncode != 7:
            failures.append(f"failing child: wrapper exit {r.returncode}, want 7")
        recs = _records(home)
        if len(recs) != 2 or recs[1]["exit_status"] != 7:
            failures.append("failing child: exit_status 7 not recorded as second record")
        if not (home / "attestation-ledger.jsonl").read_bytes().startswith(first_bytes):
            failures.append("ledger must be append-only (prior lines byte-identical)")

        # Signal death: 128+n, signal name recorded.
        r = _run(home, repo, "--run-id", "run-t-1", "--", "bash", "-c", "kill -TERM $$")
        if r.returncode != 128 + 15:
            failures.append(f"signal death: wrapper exit {r.returncode}, want 143")
        recs = _records(home)
        if recs[-1].get("signal") != "SIGTERM" or recs[-1]["exit_status"] != -15:
            failures.append(
                f"signal death: record {recs[-1].get('signal')}/{recs[-1]['exit_status']}"
            )

        # Mid-run tree edit: record degraded to unavailable.
        r = _run(home, repo, "--run-id", "run-t-1", "--", "bash", "-c", "echo drift >> src/a.txt")
        if r.returncode != 0:
            failures.append(f"mid-run edit: wrapper exit {r.returncode}, want 0")
        recs = _records(home)
        if recs[-1]["attestation_status"] != "unavailable":
            failures.append("mid-run tree edit must degrade the record to unavailable")
        if b"unavailable" not in r.stdout:
            failures.append("mid-run degrade must be announced on stdout")
        _git(repo, "checkout", "--", "src/a.txt")

        # Flood both streams past pipe-buffer capacity: completes without deadlock (B5).
        flood = "head -c 262144 /dev/zero | tr '\\0' 'a' >&1; head -c 262144 /dev/zero | tr '\\0' 'b' >&2"
        try:
            r = _run(home, repo, "--run-id", "run-t-1", "--", "bash", "-c", flood, timeout=60)
        except subprocess.TimeoutExpired:
            failures.append("stream flood deadlocked (pipe readers not concurrent)")
        else:
            recs = _records(home)
            if r.returncode != 0 or recs[-1]["stdout_digest"] == recs[-1]["stderr_digest"]:
                failures.append("stream flood: bad exit or non-distinct digests")

        # shlex round-trip: a command with embedded quotes pins and hashes identically.
        quoted = ["bash", "-c", "echo 'quoted arg'"]
        r = _run(home, repo, "--trust", "--", *quoted)
        if r.returncode != 0:
            failures.append(f"trust pin: exit {r.returncode}, want 0")
        r = _run(home, repo, "--run-id", "run-t-1", "--", *quoted)
        trust = json.loads((home / "verify-trust.json").read_text())
        pin = trust[str(repo.resolve())]
        recs = _records(home)
        if recs[-1]["command_sha256"] != pin["command_sha256"]:
            failures.append("shlex canonical form must hash identically at pin and run time")
        if recs[-1]["command"] != pin["command"]:
            failures.append("canonical command string must round-trip through the pin")

        # --trust from a subdirectory refused.
        r = _run(home, repo / "src", "--trust", "--", "echo", "x")
        if r.returncode != 2:
            failures.append(f"--trust from subdir: exit {r.returncode}, want 2 (refused)")

        # Usage errors: empty command / missing run-id => exit 2, nothing recorded.
        n = len(_records(home))
        r = _run(home, repo, "--run-id", "run-t-1", "--")
        if r.returncode != 2:
            failures.append(f"empty command: exit {r.returncode}, want 2")
        r = _run(home, repo, "--", "echo", "x")
        if r.returncode != 2:
            failures.append(f"missing run-id: exit {r.returncode}, want 2")
        if len(_records(home)) != n:
            failures.append("usage errors must record nothing")

        # Unwritable ledger => exit 3 (run happened, uncitable). Ledger path is a dir.
        home2 = td / "state-home-2"
        (home2 / "attestation-ledger.jsonl").mkdir(parents=True)
        r = _run(home2, repo, "--run-id", "run-t-1", "--", "echo", "x")
        if r.returncode != 3:
            failures.append(f"unwritable ledger: exit {r.returncode}, want 3")

        # After-fingerprint failure => no record + exit 3 (child destroys .git).
        repo2 = _mkrepo(td / "r2")
        home3 = td / "state-home-3"
        r = _run(home3, repo2, "--run-id", "run-t-1", "--", "rm", "-rf", ".git")
        if r.returncode != 3:
            failures.append(f"after-fingerprint failure: exit {r.returncode}, want 3")
        if _records(home3):
            failures.append("after-fingerprint failure must record nothing")

    real_after = _home_snapshot()
    if real_after != real_before:
        failures.append("the real ~/.contest-refactor state must be untouched by this selftest")

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    print("OK: attested_run — true-child oracle, degrade/refuse/uncitable paths, home-isolated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
