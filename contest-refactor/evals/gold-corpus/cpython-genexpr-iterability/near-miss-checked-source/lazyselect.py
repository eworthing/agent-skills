"""LazySelect: a minimal lazy filtering wrapper over any iterable.

Iterability validation now lives in `CheckedSource`, a small reusable
wrapper, instead of being duplicated inline inside `LazySelect` itself.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator
from typing import Any


class CheckedSource:
    """Wraps an iterable and eagerly confirms it is safely (re-)iterable.

    Pulling this check out of LazySelect means any future lazy type in this
    module can reuse the same validation just by wrapping its source the
    same way, instead of re-implementing the check inline.
    """

    __slots__ = ("_iterable",)

    def __init__(self, iterable: Iterable[Any]) -> None:
        # Confirm `iterable` is iterable, and that the iterator it hands
        # back is itself iterable too (well-behaved iterators always are).
        iter(iter(iterable))
        self._iterable = iterable

    def __iter__(self) -> Iterator[Any]:
        return iter(self._iterable)


class LazySelect:
    """Lazily yields items from `source`, optionally filtered by `predicate`."""

    def __init__(
        self,
        source: Iterable[Any],
        predicate: Callable[[Any], bool] | None = None,
    ) -> None:
        self._source: Iterable[Any] = (
            source if isinstance(source, CheckedSource) else CheckedSource(source)
        )
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
