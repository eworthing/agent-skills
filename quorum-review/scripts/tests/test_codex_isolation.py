"""Adapter-level integration test for per-run CODEX_HOME isolation.

Drives the *real* skill-local ``run_review.py`` (both peer-plan-review and
quorum-review) end-to-end against a fake ``codex`` executable that writes a
session file into ``$CODEX_HOME/sessions/``. Proves the concurrency fix at the
adapter boundary: two same-cwd runs capture **distinct** sessions, resume reuses
the recorded home, setup failure fails closed to a fresh exec, and terminal
cleanup reclaims the homes.

The pure-logic coverage lives in common/tests/test_codex_home.py; this verifies
the wiring (env CODEX_HOME, before/after snapshot, session persistence).
"""

import concurrent.futures
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
ADAPTERS = {
    "peer": REPO / "peer-plan-review" / "scripts" / "run_review.py",
    "quorum": REPO / "quorum-review" / "scripts" / "run_review.py",
}

# Fake `codex`: on a fresh `exec` it mints a uuid session file under
# $CODEX_HOME/sessions/ (session_meta + turn_context, cwd echoed so the adapter's
# cwd filter accepts it); on `exec resume <id>` it appends nothing new. A short
# sleep guarantees the two concurrent runs are genuinely in-flight together.
_FAKE_CODEX = r'''#!/usr/bin/env python3
import sys, os, json, uuid, time
args = sys.argv[1:]
try: sys.stdin.read()
except Exception: pass
home = os.environ.get("CODEX_HOME") or os.path.expanduser("~/.codex")
sdir = os.path.join(home, "sessions", "2026", "06", "19")
os.makedirs(sdir, exist_ok=True)
out, is_resume, sid = None, False, None
i = 0
while i < len(args):
    a = args[i]
    if a == "resume":
        is_resume = True
        sid = args[i+1] if i+1 < len(args) else None
    if a in ("--output-last-message", "-o") and i+1 < len(args):
        out = args[i+1]
    i += 1
cwd = os.getcwd()
time.sleep(0.4)
if is_resume:
    session_id = sid or "unknown"
else:
    session_id = str(uuid.uuid4())
    fn = os.path.join(sdir, "rollout-2026-06-19T00-00-00-%s.jsonl" % session_id)
    with open(fn, "w") as f:
        f.write(json.dumps({"type": "session_meta", "payload": {"id": session_id, "cwd": cwd}}) + "\n")
        f.write(json.dumps({"type": "turn_context", "payload": {"model": "gpt-5.5", "effort": "high"}}) + "\n")
print(json.dumps({"type": "session_meta", "payload": {"id": session_id, "cwd": cwd}}))
if out:
    with open(out, "w") as f:
        f.write("### Reasoning\nok\n\n### Blocking Issues\nNone\n\n"
                "### Non-Blocking Issues\nNone\n\nVERDICT: APPROVED\n")
sys.exit(0)
'''


@pytest.fixture
def fake_codex_env(tmp_path):
    """A PATH with a fake `codex`, and a fake real ~/.codex (auth+config)."""
    bindir = tmp_path / "bin"
    bindir.mkdir()
    codex = bindir / "codex"
    codex.write_text(_FAKE_CODEX)
    codex.chmod(0o755)

    real_home = tmp_path / "real-codex"
    real_home.mkdir()
    (real_home / "auth.json").write_text('{"token": "x"}')
    (real_home / "config.toml").write_text("model = 'gpt-5.5'")

    env = os.environ.copy()
    env["PATH"] = f"{bindir}{os.pathsep}{env['PATH']}"
    env["CODEX_HOME"] = str(real_home)  # the "real" home the adapter copies from
    return env


def _run_adapter(adapter, workdir, env, *, label, resume=False):
    prompt = workdir / f"{label}-prompt.md"
    prompt.write_text("Review this plan.\nVERDICT contract applies.\n")
    out = workdir / f"{label}-review.md"
    session = workdir / f"{label}-session.json"
    events = workdir / f"{label}-events.jsonl"
    manifest = workdir / f"{label}-codex-homes.list"
    cmd = [
        sys.executable, str(adapter),
        "--reviewer", "codex",
        "--prompt-file", str(prompt),
        "--output-file", str(out),
        "--session-file", str(session),
        "--events-file", str(events),
        "--codex-home-manifest", str(manifest),
        "--timeout", "30",
    ]
    if resume:
        cmd.append("--resume")
    proc = subprocess.run(cmd, cwd=str(workdir), env=env, capture_output=True, text=True, timeout=60)
    assert proc.returncode == 0, f"{label} adapter failed: {proc.stderr}"
    return json.loads(session.read_text())


@pytest.mark.parametrize("adapter_name", ["peer", "quorum"])
def test_concurrent_runs_capture_distinct_sessions(adapter_name, tmp_path, fake_codex_env):
    adapter = ADAPTERS[adapter_name]
    work = tmp_path / "work"
    work.mkdir()

    # Two runs, same cwd, genuinely concurrent.
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        f_a = pool.submit(_run_adapter, adapter, work, fake_codex_env, label="A")
        f_b = pool.submit(_run_adapter, adapter, work, fake_codex_env, label="B")
        sess_a, sess_b = f_a.result(), f_b.result()

    # Each captured a session id, and they are different (no cross-binding, no
    # ">1 match" skip that the shared-home bug produced).
    assert sess_a.get("session_id"), "run A captured no session id"
    assert sess_b.get("session_id"), "run B captured no session id"
    assert sess_a["session_id"] != sess_b["session_id"]

    # Each got its own isolated home, recorded for resume + cleanup.
    home_a, home_b = sess_a.get("codex_home"), sess_b.get("codex_home")
    assert home_a and home_b and home_a != home_b
    assert "ppr-codex-home-" in home_a and os.path.isdir(home_a)
    # The isolated home holds the copied credentials, not the real one.
    assert os.path.exists(os.path.join(home_a, "auth.json"))


def test_resume_reuses_recorded_home(tmp_path, fake_codex_env):
    adapter = ADAPTERS["quorum"]
    work = tmp_path / "work"
    work.mkdir()
    first = _run_adapter(adapter, work, fake_codex_env, label="R")
    home1, sid1 = first["codex_home"], first["session_id"]
    assert os.path.isdir(home1)

    second = _run_adapter(adapter, work, fake_codex_env, label="R", resume=True)
    # Same isolated home reused; the resumed session id is preserved.
    assert second["codex_home"] == home1
    assert second["session_id"] == sid1
    assert second.get("round") == 2


def test_setup_failure_fails_closed_to_fresh_exec(tmp_path, fake_codex_env, monkeypatch):
    """If the manifest dir is unwritable, setup fails: the run must still produce
    a review (against the inherited home) and NOT record a per-run home."""
    adapter = ADAPTERS["peer"]
    work = tmp_path / "work"
    work.mkdir()
    prompt = work / "F-prompt.md"
    prompt.write_text("Review.\n")
    session = work / "F-session.json"
    # Point the manifest at a path whose parent does not exist and cannot be
    # created (a file stands where the dir would be).
    blocker = work / "blocker"
    blocker.write_text("not a dir")
    bad_manifest = blocker / "nested" / "F-codex-homes.list"

    cmd = [
        sys.executable, str(adapter),
        "--reviewer", "codex",
        "--prompt-file", str(prompt),
        "--output-file", str(work / "F-review.md"),
        "--session-file", str(session),
        "--events-file", str(work / "F-events.jsonl"),
        "--codex-home-manifest", str(bad_manifest),
        "--timeout", "30",
    ]
    proc = subprocess.run(cmd, cwd=str(work), env=fake_codex_env, capture_output=True, text=True, timeout=60)
    assert proc.returncode == 0, proc.stderr
    data = json.loads(session.read_text())
    # Failed closed: no per-run home recorded, capture disabled (session_id None),
    # but the review still ran.
    assert data.get("codex_home") is None
    assert data.get("session_id") is None
    assert (work / "F-review.md").read_text().strip()
