#!/usr/bin/env python3
"""lifespan's own bundled test suite (this variant).

Run directly: python3 test_lifespan.py -- exits 0 on success.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lifespan import SPANS, Handle, higher, next_up, span_from_value

VALUES = ["step", "suite", "file", "batch", "run"]


def test_next_up_clamps_at_the_top() -> None:
    top = SPANS[-1]
    assert next_up(top) == top, next_up(top)


def test_next_up_moves_forward() -> None:
    first = SPANS[0]
    assert next_up(first) != first


def test_handle_carries_its_target() -> None:
    sentinel = object()
    handle = Handle(span_from_value("step"), target=sentinel)
    assert handle.target is sentinel


def test_public_span_is_a_plain_string() -> None:
    for value in VALUES:
        handle = Handle(span_from_value(value))
        assert handle.span == value, handle.span


def test_ordering_matches_declared_low_to_high() -> None:
    spans = [span_from_value(v) for v in VALUES]
    for i, lo in enumerate(spans):
        for hi in spans[i + 1 :]:
            assert higher(lo, hi) == hi, (lo, hi)
            assert higher(hi, lo) == hi, (lo, hi)


def main() -> int:
    test_next_up_clamps_at_the_top()
    test_next_up_moves_forward()
    test_handle_carries_its_target()
    test_public_span_is_a_plain_string()
    test_ordering_matches_declared_low_to_high()
    print("OK: test_lifespan.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
