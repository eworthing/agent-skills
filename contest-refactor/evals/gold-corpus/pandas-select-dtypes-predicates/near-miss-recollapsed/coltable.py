"""Coltable: a minimal typed column store with type-filtered selection.

select() keeps or drops columns by their declared type, using one
frozenset-membership test against `include` and one against `exclude`.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

KNOWN_KINDS = frozenset({"count", "real", "text"})


@dataclass(frozen=True)
class Column:
    """One column: a name, a storage kind, and its values."""

    name: str
    kind: str
    values: tuple
    flag: bool = False

    def __post_init__(self) -> None:
        if self.kind not in KNOWN_KINDS:
            raise ValueError(f"unknown column kind: {self.kind!r}")
        if self.flag and self.kind != "count":
            raise ValueError("flag=True only makes sense for kind='count'")


class Coltable:
    """A named collection of Columns, filterable by declared type."""

    def __init__(self, columns: Iterable[Column]) -> None:
        self._columns = list(columns)

    def select(
        self,
        include: Iterable[str] | None = None,
        exclude: Iterable[str] | None = None,
    ) -> list[Column]:
        """Columns whose type is in `include` (or all, if omitted) and not
        in `exclude`."""
        included = frozenset(include) if include is not None else None
        excluded = frozenset(exclude) if exclude is not None else frozenset()

        def matches(column: Column) -> bool:
            if included is not None and column.kind not in included:
                return False
            return column.kind not in excluded

        return [column for column in self._columns if matches(column)]
