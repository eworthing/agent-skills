#!/usr/bin/env python3
"""LazySelect's own bundled test suite (this variant).

Run directly: python3 test_lazyselect.py -- exits 0 on success.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lazyselect import CheckedSource, LazySelect


def test_filters_with_predicate() -> None:
    result = list(LazySelect(range(10), lambda x: x % 2 == 0))
    assert result == [0, 2, 4, 6, 8], result


def test_passes_through_without_predicate() -> None:
    result = list(LazySelect(range(5)))
    assert result == [0, 1, 2, 3, 4], result


def test_checked_source_validates_eagerly() -> None:
    """CheckedSource is the one place iterability is checked now; it still
    checks immediately, same as LazySelect did before this refactor -- moving
    the check doesn't change when it fires."""
    try:
        CheckedSource(6)  # 6 is not iterable
    except TypeError:
        pass
    else:
        raise AssertionError("expected TypeError building a CheckedSource over a non-iterable")


def test_lazyselect_wraps_transparently() -> None:
    checked = CheckedSource([1, 2, 3])
    assert list(LazySelect(checked)) == [1, 2, 3]


def main() -> int:
    test_filters_with_predicate()
    test_passes_through_without_predicate()
    test_checked_source_validates_eagerly()
    test_lazyselect_wraps_transparently()
    print("OK: test_lazyselect.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
