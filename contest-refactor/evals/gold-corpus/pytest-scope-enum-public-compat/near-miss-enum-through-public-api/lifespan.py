"""Fixture-lifetime helpers used by this package's request objects.

A fixture is torn down when the last thing at its "span" finishes: the one
step that asked for it, the suite it lives in, the file, a whole batch of
files, or the run. `Span` names the five spans and orders them; `higher`
and `next_up` are the two operations everything else needs, backed by one
ordered enum instead of a mapping copied at each call site.
"""

from __future__ import annotations

from enum import Enum
from functools import total_ordering


@total_ordering
class Span(Enum):
    """A fixture's lifetime, declared low to high."""

    Step = "step"
    Suite = "suite"
    File = "file"
    Batch = "batch"
    Run = "run"

    def __lt__(self, other: Span) -> bool:
        if self.__class__ is not other.__class__:
            return NotImplemented
        order = list(self.__class__)
        return order.index(self) < order.index(other)


SPANS = list(Span)


def span_from_value(value: str) -> Span:
    return Span(value)


def value_of(span: Span) -> str:
    return span.value


def higher(a: Span, b: Span) -> Span:
    """The longer-lived of two spans."""
    return a if a >= b else b


def next_up(span: Span) -> Span:
    """The next span out from `span`, or `span` itself if already at the top."""
    idx = SPANS.index(span)
    return span if idx == len(SPANS) - 1 else SPANS[idx + 1]


class Handle:
    """Ties a span to whatever object requested it at that span.

    `span` returns the same `Span` member the handle was built with --
    there is only one representation of a handle's span now, not an
    internal enum next to a separate public string.
    """

    def __init__(self, span: Span, target: object = None) -> None:
        self._span = span
        self.target = target

    @property
    def span(self) -> Span:
        return self._span
