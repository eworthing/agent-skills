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


def test_public_span_compares_as_string() -> None:
    for value in VALUES:
        handle = Handle(span_from_value(value))
        assert handle.span == value, handle.span


def test_public_span_works_as_a_dict_key() -> None:
    handle = Handle(span_from_value("run"))
    lookup = {handle.span: "ok"}
    assert lookup.get("run") == "ok", lookup


def test_step_orders_below_suite() -> None:
    step, suite = span_from_value("step"), span_from_value("suite")
    assert higher(step, suite) == suite


def test_batch_orders_below_run() -> None:
    batch, run = span_from_value("batch"), span_from_value("run")
    assert higher(batch, run) == run


def main() -> int:
    test_next_up_clamps_at_the_top()
    test_next_up_moves_forward()
    test_handle_carries_its_target()
    test_public_span_compares_as_string()
    test_public_span_works_as_a_dict_key()
    test_step_orders_below_suite()
    test_batch_orders_below_run()
    print("OK: test_lifespan.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
