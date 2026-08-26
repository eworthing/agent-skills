"""columnstore: a minimal typed column store over plain Python lists.

Each column carries a `kind` tag: a short string ("text", "masked_text",
"choice", "number") for a plain column, or a `Packed` wrapper around one of
those same strings for a column stored in a memory-packed extension
format. `column_subset` is the general-purpose way to pick columns by
kind; encoding reuses it with a list of the kinds worth one-hot encoding.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any


class Packed:
    """A memory-packed column format that still holds `primitive` values."""

    __slots__ = ("primitive",)

    def __init__(self, primitive: str) -> None:
        self.primitive = primitive


class Column:
    """One named column: its `kind` tag and its values."""

    def __init__(self, name: str, kind: str | Packed, values: Iterable[Any]) -> None:
        self.name = name
        self.kind = kind
        self.values = list(values)


class Table:
    """An ordered set of columns, all the same length."""

    def __init__(self, columns: Iterable[Column]) -> None:
        self.columns = list(columns)


def column_subset(table: Table, include: Iterable[str]) -> list[Column]:
    """Columns whose kind -- after unwrapping a Packed kind to the
    primitive it packs -- matches one of the aliases in `include`.

    A caller that only knows about primitive alias strings ("text",
    "number", ...) still finds packed columns of the matching primitive,
    without needing to know Packed exists.
    """
    wanted = set(include)
    result = []
    for col in table.columns:
        alias = col.kind.primitive if isinstance(col.kind, Packed) else col.kind
        if alias in wanted:
            result.append(col)
    return result


def encode_categoricals(table: Table) -> list[str]:
    """Names of the columns to run one-hot encoding over. Widened to also
    catch numeric flag/indicator columns that behave like a small set of
    choices."""
    return [
        c.name for c in column_subset(table, include=["text", "masked_text", "choice", "number"])
    ]
