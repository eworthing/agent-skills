"""LazySelect: a minimal lazy filtering wrapper over any iterable.

Building a LazySelect is meant to be cheap and side-effect-free: constructing
one and never consuming it should always be safe.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator
from typing import Any


class LazySelect:
    """Lazily yields items from `source`, optionally filtered by `predicate`."""

    def __init__(
        self,
        source: Iterable[Any],
        predicate: Callable[[Any], bool] | None = None,
    ) -> None:
        # __iter__ was calling iter(source) itself every time, on top of the
        # validation this used to do up front -- that's the same work twice.
        # Compute the iterator once, here, and reuse it below instead of
        # asking `source` for a fresh one on every pass.
        self._source = iter(source)
        self._predicate = predicate

    def __iter__(self) -> Iterator[Any]:
        predicate = self._predicate
        while True:
            try:
                item = next(self._source)
            except StopIteration:
                return
            if predicate is None or predicate(item):
                yield item
