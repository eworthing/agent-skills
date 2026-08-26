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


def test_immediate_iterability_check() -> None:
    """Verify that the outermost source gets an immediate check for
    iterability: constructing a LazySelect over something that isn't
    iterable fails right away, before any iteration is attempted."""
    try:
        LazySelect(6)  # 6 is not iterable
    except TypeError:
        pass
    else:
        raise AssertionError("expected TypeError at construction for a non-iterable source")


def main() -> int:
    test_filters_with_predicate()
    test_passes_through_without_predicate()
    test_immediate_iterability_check()
    print("OK: test_lazyselect.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
