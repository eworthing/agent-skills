"""Tests for common.process.tree."""

import contextlib
import os
import signal
import subprocess
import sys
import textwrap
import time
from unittest import mock

import pytest
from common.process.tree import _kill_tree, _popen_session_kwargs, drain_process


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX-specific process group semantics")
class TestKillTreePosix:
    def test_kills_child_and_grandchild(self):
        # Spawn a parent that sleeps for a long time. _kill_tree should reap it.
        proc = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(60)"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            **_popen_session_kwargs(),
        )
        # Confirm it's running before killing.
        time.sleep(0.05)
        assert proc.poll() is None
        _kill_tree(proc)
        # After _kill_tree, the process must no longer be alive.
        assert proc.poll() is not None

    def test_sigkill_reaches_group_after_fast_child_exit(self):
        """Regression: a fast-exiting direct child + a SIGTERM-ignoring group
        member escaped SIGKILL escalation (the pgid was re-derived after the
        child was gone, so the group could no longer be targeted)."""
        parent_code = textwrap.dedent(
            """
            import subprocess, sys
            code = (
                "import signal, time; "
                "signal.signal(signal.SIGTERM, signal.SIG_IGN); "
                "print('ready', flush=True); "
                "time.sleep(60)"
            )
            child = subprocess.Popen([sys.executable, "-c", code], stdout=subprocess.PIPE)
            child.stdout.readline()  # SIGTERM handler installed
            print(child.pid, flush=True)
            """
        )
        proc = subprocess.Popen(
            [sys.executable, "-c", parent_code],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            encoding="utf-8",
            **_popen_session_kwargs(),
        )
        grandchild_pid = int(proc.stdout.readline().strip())
        try:
            # Let the parent exit on its own; deliberately no poll()/wait() —
            # mirrors the caller state right after TimeoutExpired.
            time.sleep(0.2)
            _kill_tree(proc)
            deadline = time.time() + 5
            alive = True
            while time.time() < deadline:
                try:
                    os.kill(grandchild_pid, 0)
                except ProcessLookupError:
                    alive = False
                    break
                time.sleep(0.05)
            assert not alive, "SIGTERM-ignoring group member survived _kill_tree"
        finally:
            with contextlib.suppress(ProcessLookupError):
                os.kill(grandchild_pid, signal.SIGKILL)


class TestDrainProcess:
    def test_normal_drain_returns_text(self):
        proc = mock.MagicMock()
        proc.communicate.return_value = ("out", "err")
        assert drain_process(proc) == ("out", "err", False)

    def test_none_streams_normalize_to_empty(self):
        proc = mock.MagicMock()
        proc.communicate.return_value = (None, None)
        assert drain_process(proc) == ("", "", False)

    def test_second_timeout_preserves_byte_partial_output(self):
        """TimeoutExpired.output/.stderr may be bytes even under text-mode
        Popen — the partial data must be decoded and preserved, the pipes
        closed, and the final wait bounded."""
        proc = mock.MagicMock()
        proc.communicate.side_effect = subprocess.TimeoutExpired(
            cmd=["reviewer"], timeout=30, output=b"partial \xff", stderr=b"errbytes"
        )
        stdout, stderr, timed_out = drain_process(proc)
        assert timed_out
        assert stdout == "partial �"
        assert stderr == "errbytes"
        proc.stdout.close.assert_called_once()
        proc.stderr.close.assert_called_once()
        proc.wait.assert_called_once_with(timeout=5)


class TestPopenSessionKwargs:
    def test_posix_returns_new_session(self):
        if sys.platform == "win32":
            assert _popen_session_kwargs() == {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
        else:
            assert _popen_session_kwargs() == {"start_new_session": True}
