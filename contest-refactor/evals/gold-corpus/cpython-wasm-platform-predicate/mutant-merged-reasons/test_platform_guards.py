#!/usr/bin/env python3
"""Guarded test suite exercising platsupport's skip machinery.

Run directly: python3 test_platform_guards.py -- exits 0 on success.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from platsupport import MAINLAND, collect_skips, is_driftplane, is_gearshift, is_tideline, skip_if


@skip_if(is_driftplane, "sandboxed runtimes only expose an in-memory temp directory")
def test_shared_temp_writable():
    """A path under the platform's shared/writable temp area should be a usable real path."""


@skip_if(is_driftplane, "sandboxed runtimes cannot fork a new process")
def test_process_fork():
    """Forking a child process should hand back a distinct, waitable process handle."""


@skip_if(is_driftplane, "sandboxed runtimes cap a single allocation below the desktop default")
def test_large_page_alloc():
    """A single large allocation at the platform's default cap should succeed."""


@skip_if(is_tideline, "tideline has no user accounts")
def test_user_account_lookup():
    """The current user's account name should resolve to a non-empty string."""


@skip_if(is_tideline, "tideline path collapse for '..' segments does not match POSIX resolution")
def test_dotdot_path_resolution():
    """Collapsing a path with an embedded '..' segment should match POSIX resolution."""


@skip_if(
    is_gearshift,
    "gearshift's virtual filesystem does not preserve symlink targets across a rebuild",
)
def test_symlink_target_preserved():
    """A symlink's target should survive a filesystem image rebuild."""


@skip_if(is_driftplane, "not supported on a sandboxed runtime platform")
def test_unix_socket_creation():
    """Creating a unix-domain socket and binding it to a path should succeed."""


@skip_if(is_driftplane, "not supported on a sandboxed runtime platform")
def test_bare_thread_spawn():
    """Spawning a bare OS thread and joining it should complete without error."""


ALL_TESTS = [
    test_shared_temp_writable,
    test_process_fork,
    test_large_page_alloc,
    test_user_account_lookup,
    test_dotdot_path_resolution,
    test_symlink_target_preserved,
    test_unix_socket_creation,
    test_bare_thread_spawn,
]


def main() -> int:
    skipped = collect_skips(MAINLAND, ALL_TESTS)
    assert skipped == {}, f"mainland should skip nothing, got {skipped}"
    for test in ALL_TESTS:
        if test.__name__ not in skipped:
            test()
    print("OK: test_platform_guards.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
