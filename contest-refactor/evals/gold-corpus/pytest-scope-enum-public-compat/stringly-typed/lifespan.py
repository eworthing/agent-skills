"""Fixture-lifetime helpers used by this package's request objects.

A fixture is torn down when the last thing at its "span" finishes: the one
step that asked for it, the suite it lives in, the file, a whole batch of
files, or the run. This module names the five spans and provides the two
operations that compare them: `higher`, which picks the longer-lived of two
spans, and `next_up`, which returns the next span out.
"""

from __future__ import annotations

STEP = "step"
SUITE = "suite"
FILE = "file"
BATCH = "batch"
RUN = "run"

SPANS = [STEP, SUITE, FILE, BATCH, RUN]


def span_from_value(value: str) -> str:
    return value


def value_of(span: str) -> str:
    return span


def higher(a: str, b: str) -> str:
    """The longer-lived of two spans."""
    # Each call site that needs to compare spans keeps its own copy of this
    # mapping -- there is no single place that owns the ordering.
    order = {STEP: 0, SUITE: 1, FILE: 2, BATCH: 3, RUN: 4}
    return a if order[a] >= order[b] else b


def next_up(span: str) -> str:
    """The next span out from `span`, or `span` itself if already at the top."""
    order = [STEP, SUITE, FILE, BATCH, RUN]
    idx = order.index(span)
    return span if idx == len(order) - 1 else order[idx + 1]


class Handle:
    """Ties a span to whatever object requested it at that span."""

    def __init__(self, span: str, target: object = None) -> None:
        self.span = span
        self.target = target
