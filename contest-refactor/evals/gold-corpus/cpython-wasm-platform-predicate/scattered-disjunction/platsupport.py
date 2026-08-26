"""Platform-guard helpers used by this package's test suite.

Provides platform identity checks for two sandboxed runtime platforms
(gearshift, tideline) plus an ordinary reference platform (mainland), and a
small skip_if/collect_skips pair for expressing "this test does not apply
on platform X, because Y" without pulling in a full test framework.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable

GEARSHIFT = "gearshift"
TIDELINE = "tideline"
MAINLAND = "mainland"


def is_gearshift(platform: str) -> bool:
    return platform == GEARSHIFT


def is_tideline(platform: str) -> bool:
    return platform == TIDELINE


def skip_if(predicate: Callable[[str], bool], reason: str):
    """Attach a (predicate, reason) guard to a test function.

    Guards stack -- a function may carry more than one -- and the first
    guard whose predicate matches wins the reported reason.
    """

    def decorator(func):
        guards = list(getattr(func, "__skip_guards__", ()))
        guards.append((predicate, reason))
        func.__skip_guards__ = guards
        return func

    return decorator


def collect_skips(platform: str, tests: Iterable) -> dict[str, str]:
    """Return {test_name: reason} for every test that would skip on `platform`."""
    skipped: dict[str, str] = {}
    for test in tests:
        for predicate, reason in getattr(test, "__skip_guards__", ()):
            if predicate(platform):
                skipped[test.__name__] = reason
                break
    return skipped
