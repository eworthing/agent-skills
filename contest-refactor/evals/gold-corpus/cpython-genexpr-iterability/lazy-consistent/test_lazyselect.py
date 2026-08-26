#!/usr/bin/env python3
"""LazySelect's own bundled test suite (this variant).

Run directly: python3 test_lazyselect.py -- exits 0 on success.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lazyselect import LazySelect


def test_filters_with_predicate() -> None:
    result = list(LazySelect(range(10), lambda x: x % 2 == 0))
    assert result == [0, 2, 4, 6, 8], result


def test_passes_through_without_predicate() -> None:
    result = list(LazySelect(range(5)))
    assert result == [0, 1, 2, 3, 4], result


def test_iterability_check_is_lazy() -> None:
    """Replaces the old "immediate iterability check" test: constructing a
    LazySelect over something that isn't iterable no longer fails at
    construction. It fails once you actually iterate, matching every other
    lazy pipeline in this module (see CHANGES.md)."""
    obj = LazySelect(6)  # building it is always fine, regardless of `source`
    try:
        list(obj)
    except TypeError:
        pass
    else:
        raise AssertionError("expected TypeError once iteration begins")


def main() -> int:
    test_filters_with_predicate()
    test_passes_through_without_predicate()
    test_iterability_check_is_lazy()
    print("OK: lazy-consistent test_lazyselect.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
