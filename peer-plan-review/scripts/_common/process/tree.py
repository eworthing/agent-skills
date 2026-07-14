"""
tree.py — Process tree management helpers.

Ported verbatim from peer-plan-review/scripts/ppr_process.py. Provides:
- _kill_tree(proc): kill a process and all descendants, with SIGTERM
  then SIGKILL escalation.
- drain_process(proc, timeout): bounded pipe drain after a kill, preserving
  partial output.
- _popen_session_kwargs(): platform-correct Popen kwargs for
  process-group isolation, so _kill_tree can reach descendants.
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
        with contextlib.suppress(subprocess.TimeoutExpired):
            proc.wait(timeout=5)
    else:
        # Capture the pgid ONCE, before SIGTERM: once the direct child is
        # reaped, getpgid raises and the group can no longer be targeted —
        # leaving SIGTERM-ignoring group members alive holding the pipes.
        # If getpgid already fails (zombie/reaped child — macOS refuses
        # zombies), fall back to proc.pid: _popen_session_kwargs made the
        # child a group leader, so its group id IS its pid, and the group
        # outlives the leader while members remain. A truly gone group makes
        # killpg raise ProcessLookupError, which is suppressed.
        try:
            pgid = os.getpgid(proc.pid)
        except ProcessLookupError:
            pgid = proc.pid
        with contextlib.suppress(ProcessLookupError):
            os.killpg(pgid, signal.SIGTERM)
        with contextlib.suppress(subprocess.TimeoutExpired):
            proc.wait(timeout=5)
        # Unconditional SIGKILL to the captured group: a fast-exiting child
        # + a SIGTERM-ignoring group member previously escaped escalation
        # and could hang the caller's drain forever.
        with contextlib.suppress(ProcessLookupError):
            os.killpg(pgid, signal.SIGKILL)
        with contextlib.suppress(subprocess.TimeoutExpired):
            proc.wait(timeout=5)


def _to_text(value):
    """Normalize a communicate()/TimeoutExpired payload to str.

    TimeoutExpired.output/.stderr may be bytes even under text-mode Popen.
    """
    if isinstance(value, bytes):
        return value.decode("utf-8", "replace")
    return value or ""


def drain_process(proc, timeout=30):
    """Bounded drain of a killed process's pipes.

    Returns ``(stdout, stderr, timed_out)``. A bare ``proc.communicate()``
    after ``_kill_tree`` can still hang if a pipe fd survived the kill (e.g.
    inherited by a process outside the group); this caps the drain, preserves
    the partial data carried by the second ``TimeoutExpired``, closes the
    pipes, and finishes with a bounded reap.
    """
    stdout, stderr = "", ""
    timed_out = False
    try:
        out, err = proc.communicate(timeout=timeout)
        stdout, stderr = _to_text(out), _to_text(err)
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        stdout = _to_text(exc.output) or stdout
        stderr = _to_text(exc.stderr) or stderr
        for stream in (proc.stdin, proc.stdout, proc.stderr):
            if stream is not None:
                with contextlib.suppress(OSError):
                    stream.close()
        with contextlib.suppress(subprocess.TimeoutExpired):
            proc.wait(timeout=5)
    return stdout, stderr, timed_out


def _popen_session_kwargs():
    """Return Popen kwargs for process-group isolation, per platform."""
    if sys.platform == "win32":
        return {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
    return {"start_new_session": True}
