"""Coltable: a minimal typed column store with type-filtered selection.

select() keeps or drops columns by their declared type. Each requested type
name is turned into its own small predicate, and a column is kept if all of
the requested-type predicates accept it.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
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


def _type_predicate(type_name: str) -> Callable[[Column], bool]:
    """One column-type name -> the callable that recognizes it.

    "count" and "flag" both live on kind="count" columns, distinguished by
    the `flag` attribute, so each gets its own rule here. "real" and "text"
    just compare kind directly.
    """
    if type_name == "flag":
        return lambda column: column.kind == "count" and column.flag
    if type_name == "count":
        return lambda column: column.kind == "count" and not column.flag
    return lambda column: column.kind == type_name


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
        in `exclude`. Type names are "count", "flag", "real", "text"."""
        include_checks = (
            [_type_predicate(name) for name in include] if include is not None else None
        )
        exclude_checks = [_type_predicate(name) for name in exclude] if exclude is not None else []

        def matches(column: Column) -> bool:
            if include_checks is not None and not all(check(column) for check in include_checks):
                return False
            return not any(check(column) for check in exclude_checks)

        return [column for column in self._columns if matches(column)]
