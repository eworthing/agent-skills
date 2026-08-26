"""Clustered: a minimal grouped-collection library over a list of records.

The plotting path forwards a key for every group -- but the group's
position in the sequence, not its own key. Legend labels come out
consistently wrong rather than missing.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any


class Lane:
    """A single-column group: one key, one list of values."""

    def __init__(self, key: Any, values: Iterable[Any]) -> None:
        self.key = key
        self.values = list(values)


class Panel:
    """A multi-column group: one key, several named columns."""

    def __init__(self, key: Any, columns: dict[str, Iterable[Any]]) -> None:
        self.key = key
        self.columns = {name: list(vals) for name, vals in columns.items()}


class Clustered:
    """Splits records (each a dict of column -> value) into groups by key."""

    def __init__(self, records: Iterable[dict], key: Callable[[dict], Any]) -> None:
        self._records = list(records)
        self._key = key

    def _buckets(self) -> dict[Any, list[dict]]:
        buckets: dict[Any, list[dict]] = {}
        for record in self._records:
            buckets.setdefault(self._key(record), []).append(record)
        return buckets

    def lanes(self, column: str) -> list[Lane]:
        """One Lane per key, holding only `column`'s values."""
        return [Lane(key, [r[column] for r in recs]) for key, recs in self._buckets().items()]

    def panels(self, columns: list[str]) -> list[Panel]:
        """One Panel per key, holding all of `columns`."""
        return [
            Panel(key, {c: [r[c] for r in recs] for c in columns})
            for key, recs in self._buckets().items()
        ]


def apply_general(groups: list, fn: Callable) -> list:
    """Still used for aggregation; unrelated to plotting."""
    results = []
    for group in groups:
        group.label = group.key
        results.append(fn(group))
    return results


def apply_plot(groups: list, fn: Callable) -> list:
    """Dedicated plotting path. Forwards a key for every group -- but the
    group's position in the sequence, not its own key."""
    return [fn(group, key=index) for index, group in enumerate(groups)]


def scatter(group, key: Any = None, legend: bool = True) -> Any:
    """Renders one group's scatter series. Returns the label used for the
    legend entry, or None if legend is off or no label could be found."""
    if not legend:
        return None
    if key is not None:
        return key
    return getattr(group, "label", None)


def plot_legend_labels(groups: list, legend: bool = True) -> list:
    return apply_plot(groups, lambda g, key=None: scatter(g, key=key, legend=legend))
