"""Generic metadata wrapper, unrelated to any particular marker vocabulary.

`Tagged[SomeType, ...]` attaches extra metadata to `SomeType` without
changing what `SomeType` itself means. A record scanner that wants to
recognize a marker underneath a `Tagged[...]` wrapper has to unwrap it
first -- nothing about `Tagged` itself implies that any scanner does.
"""

from __future__ import annotations


class Tagged:
    """`Tagged[SomeType, *metadata]` -- subscripting builds a `_TaggedAlias`."""

    def __class_getitem__(cls, params: tuple[object, ...]) -> _TaggedAlias:
        tp, *metadata = params
        return _TaggedAlias(tp, tuple(metadata))


class _TaggedAlias:
    def __init__(self, tp: object, metadata: tuple[object, ...]) -> None:
        self.__tagged_type__ = tp
        self.__metadata__ = metadata

    def __repr__(self) -> str:
        return f"Tagged[{self.__tagged_type__!r}, {self.__metadata__!r}]"
