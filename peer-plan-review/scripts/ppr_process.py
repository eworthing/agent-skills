"""
ppr_process.py — Process tree management helpers for peer-plan-review.

Extracted from run_review.py so both run_review.py and test_web_search.py
share a single source of truth for process lifecycle management.
"""

import contextlib
import os
import signal
import subprocess
import sys


def _kill_tree(proc):
    """Kill process and all descendants."""
    if sys.platform == "win32":
        subprocess.run(
            ["taskkill", "/T", "/F", "/PID", str(proc.pid)],
            capture_output=True,
        )
        proc.wait()
    else:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            proc.wait(timeout=5)
        except (subprocess.TimeoutExpired, ProcessLookupError):
            with contextlib.suppress(ProcessLookupError):
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        with contextlib.suppress(subprocess.TimeoutExpired):
            proc.wait(timeout=5)


def _popen_session_kwargs():
    """Return Popen kwargs for process-group isolation, per platform."""
    if sys.platform == "win32":
        return {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
    return {"start_new_session": True}
