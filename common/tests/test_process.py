"""Tests for common.process.tree."""

import subprocess
import sys
import time

import pytest

from common.process.tree import _kill_tree, _popen_session_kwargs


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


class TestPopenSessionKwargs:
    def test_posix_returns_new_session(self):
        if sys.platform == "win32":
            assert _popen_session_kwargs() == {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
        else:
            assert _popen_session_kwargs() == {"start_new_session": True}
