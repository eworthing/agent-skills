"""LazySelect: a minimal lazy filtering wrapper over any iterable.

Building a LazySelect is meant to be cheap and side-effect-free: constructing
one and never consuming it should always be safe. Consuming it (iterating)
re-reads `source` fresh every time, so the same LazySelect can be iterated
more than once as long as `source` itself supports that.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator
from typing import Any


class LazySelect:
    """Lazily yields items from `source`, optionally filtered by `predicate`.

    Construction never touches `source`. Like every other lazy pipeline in
    this module, whatever is wrong with `source` -- not iterable, already
    exhausted, whatever -- only surfaces once you actually pull a value out
    of this object, not when you build it.
    """

    def __init__(
        self,
        source: Iterable[Any],
        predicate: Callable[[Any], bool] | None = None,
    ) -> None:
        self._source = source
        self._predicate = predicate

    def __iter__(self) -> Iterator[Any]:
        it = iter(self._source)
        predicate = self._predicate
        while True:
            try:
                item = next(it)
            except StopIteration:
                return
            if predicate is None or predicate(item):
                yield item
