#!/usr/bin/env python3
"""Tier-1 execution-evidence wrapper (item 14): run the test command as a true child.

The wrapper is the literal parent process of the test/build command, so what it records
cannot be a claim: ``exit_status`` is the child's real returncode, the source-tree
fingerprints come from the wrapper's own ``git`` invocations before and after the run,
and ``timestamp`` is the wrapper's process clock. This defeats the lazy/wrong-result
fabrication cases (a loop reporting a run that never happened, or reporting pass on a
fail). It does NOT defeat a same-privilege forger who hand-writes a matching record —
that is Tier 2 (privilege separation), deliberately out of scope; every record this
wrapper writes carries ``attestation_status: "consistency_check"``, never ``"attested"``.

Modes:
  attested_run.py --trust -- <command...>          # human-run, one-time command pin
  attested_run.py --run-id <id> -- <command...>    # the wrapped run

State lives under ``$CONTEST_REFACTOR_HOME`` (default ``~/.contest-refactor``), never in
the target repo tree — an in-tree write would enter ``changed_paths`` and halt the loop
via Step 3's out-of-plan gate. One loop is single-writer, but the ledger is global across
repos, so two concurrent loops on different repos ARE two writers to one file: the single
``O_APPEND`` ``os.write`` keeps lines whole in practice, and a partial write is treated
as a ledger-write failure (exit 3).
# ponytail: no file locking — revisit with real locking only on observed corruption.

Exit codes: child's returncode (128+N on signal death) for a recorded run; 2 = usage /
pre-spawn failure, nothing recorded; 3 = the run happened but could not be recorded
(uncitable — G47 fails an unresolved event regardless; the exit code is best-effort
only, a child could also exit 3).
"""

from __future__ import annotations

import hashlib
import json
import os
import shlex
import signal as signal_mod
import subprocess
import sys
import tempfile
import threading
import uuid
from datetime import UTC, datetime
from pathlib import Path

from _wtree import source_tree_fingerprint

LEDGER_NAME = "attestation-ledger.jsonl"
TRUST_NAME = "verify-trust.json"


def state_root() -> Path:
    override = os.environ.get("CONTEST_REFACTOR_HOME")
    return Path(override) if override else Path.home() / ".contest-refactor"


def ledger_path() -> Path:
    return state_root() / LEDGER_NAME


def trust_path() -> Path:
    return state_root() / TRUST_NAME


def canonical_command(argv: list[str]) -> str:
    return shlex.join(argv)


def command_sha256(command: str) -> str:
    return hashlib.sha256(command.encode("utf-8")).hexdigest()


def _repo_toplevel(cwd: Path) -> Path:
    out = subprocess.run(
        ["git", "-C", str(cwd), "rev-parse", "--show-toplevel"],
        check=True,
        capture_output=True,
        text=True,
    )
    return Path(out.stdout.strip()).resolve()


def _tee_and_digest(pipe, sink) -> threading.Thread:
    digest = hashlib.sha256()

    def _pump() -> None:
        for chunk in iter(lambda: pipe.read(65536), b""):
            digest.update(chunk)
            sink.write(chunk)
            sink.flush()
        pipe.close()

    thread = threading.Thread(target=_pump, daemon=True)
    thread.digest = digest  # type: ignore[attr-defined]
    thread.start()
    return thread


def _write_trust(repo_root: Path, command: str) -> None:
    root = state_root()
    root.mkdir(parents=True, exist_ok=True)
    path = trust_path()
    store: dict = {}
    if path.is_file():
        store = json.loads(path.read_text(encoding="utf-8"))
    store[str(repo_root)] = {
        "command": command,
        "command_sha256": command_sha256(command),
        "pinned_at": datetime.now(UTC).isoformat(),
    }
    fd, tmp = tempfile.mkstemp(dir=root, prefix=".trust-")
    try:
        os.write(fd, (json.dumps(store, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
    finally:
        os.close(fd)
    tmp_path = Path(tmp)
    tmp_path.chmod(0o600)
    tmp_path.replace(path)


def _append_ledger(record: dict) -> None:
    root = state_root()
    root.mkdir(parents=True, exist_ok=True)
    line = (json.dumps(record, ensure_ascii=False) + "\n").encode("utf-8")
    fd = os.open(ledger_path(), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    try:
        written = os.write(fd, line)
    finally:
        os.close(fd)
    if written != len(line):
        raise OSError(f"partial ledger write ({written}/{len(line)} bytes)")


def _split_args(argv: list[str]) -> tuple[list[str], list[str]]:
    if "--" not in argv:
        return argv, []
    i = argv.index("--")
    return argv[:i], argv[i + 1 :]


def main(argv: list[str]) -> int:
    opts, cmd = _split_args(argv)
    if not cmd:
        print("attested-run: usage error — no command after `--`", file=sys.stderr)
        return 2

    command = canonical_command(cmd)

    if "--trust" in opts:
        cwd = Path.cwd().resolve()
        try:
            repo_root = _repo_toplevel(cwd)
        except subprocess.CalledProcessError:
            print("attested-run: --trust must run inside a git repository", file=sys.stderr)
            return 2
        if cwd != repo_root:
            print(
                f"attested-run: --trust must run from the repo toplevel ({repo_root}), not {cwd}",
                file=sys.stderr,
            )
            return 2
        _write_trust(repo_root, command)
        print(f"attested-run: pinned {command_sha256(command)} for {repo_root}")
        return 0

    run_id = None
    if "--run-id" in opts:
        i = opts.index("--run-id")
        if i + 1 < len(opts):
            run_id = opts[i + 1]
    if not run_id:
        print(
            "attested-run: usage error — --run-id <id> is required and non-empty", file=sys.stderr
        )
        return 2

    cwd = Path.cwd().resolve()
    try:
        repo_root = _repo_toplevel(cwd)
    except subprocess.CalledProcessError:
        print("attested-run: not inside a git repository", file=sys.stderr)
        return 2

    try:
        wtree_before = source_tree_fingerprint(repo_root)
    except subprocess.CalledProcessError as exc:
        print(f"attested-run: pre-run fingerprint failed: {exc.stderr.strip()}", file=sys.stderr)
        return 2

    started = datetime.now(UTC)
    child = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    # One reader thread per stream: sequential reads deadlock once both pipe buffers fill.
    t_out = _tee_and_digest(child.stdout, sys.stdout.buffer)
    t_err = _tee_and_digest(child.stderr, sys.stderr.buffer)
    child.wait()
    t_out.join()
    t_err.join()

    exit_status = child.returncode
    sig_name = None
    if exit_status < 0:
        try:
            sig_name = signal_mod.Signals(-exit_status).name
        except ValueError:
            sig_name = f"SIG{-exit_status}"

    try:
        wtree_after = source_tree_fingerprint(repo_root)
    except subprocess.CalledProcessError as exc:
        print(
            f"attested-run: post-run fingerprint failed — run happened but is not "
            f"citable: {exc.stderr.strip()}",
            file=sys.stderr,
        )
        return 3

    status = "consistency_check"
    if wtree_after != wtree_before:
        status = "unavailable"
        print(
            "attested-run: source tree changed during the run — record degraded to "
            "attestation_status=unavailable (certifies nothing)"
        )

    record = {
        "event_id": uuid.uuid4().hex,
        "run_id": run_id,
        "command": command,
        "command_sha256": command_sha256(command),
        "repo_root": str(repo_root),
        "invoked_from": str(cwd),
        "wtree": wtree_before,
        "wtree_after": wtree_after,
        "timestamp": started.isoformat(),
        "exit_status": exit_status,
        "signal": sig_name,
        "stdout_digest": t_out.digest.hexdigest(),  # type: ignore[attr-defined]
        "stderr_digest": t_err.digest.hexdigest(),  # type: ignore[attr-defined]
        "attestation_status": status,
    }
    try:
        _append_ledger(record)
    except OSError as exc:
        print(
            f"attested-run: ledger write failed — run happened but is not citable: {exc}",
            file=sys.stderr,
        )
        return 3

    print(f"attested-run: event {record['event_id']} exit {exit_status}")
    if exit_status < 0:
        return 128 + (-exit_status)
    return exit_status


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
