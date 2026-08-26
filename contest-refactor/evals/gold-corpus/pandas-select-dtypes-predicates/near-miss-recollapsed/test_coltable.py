#!/usr/bin/env python3
"""Coltable's own bundled test suite (this variant).

Run directly: python3 test_coltable.py -- exits 0 on success.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from coltable import Coltable, Column

COLUMNS = [
    Column("id", "count", (1, 2, 3)),
    Column("age", "count", (30, 40, 50)),
    Column("is_active", "count", (1, 0, 1), flag=True),
    Column("score", "real", (9.5, 8.1, 7.4)),
    Column("name", "text", ("a", "b", "c")),
]


def test_no_filter_returns_every_column() -> None:
    names = {c.name for c in Coltable(COLUMNS).select()}
    assert names == {"id", "age", "is_active", "score", "name"}, names


def test_real_selects_only_real_columns() -> None:
    names = {c.name for c in Coltable(COLUMNS).select(include=["real"])}
    assert names == {"score"}, names


def test_exclude_drops_matching_type() -> None:
    names = {c.name for c in Coltable(COLUMNS).select(exclude=["text"])}
    assert names == {"id", "age", "is_active", "score"}, names


def main() -> int:
    test_no_filter_returns_every_column()
    test_real_selects_only_real_columns()
    test_exclude_drops_matching_type()
    print("OK: test_coltable.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
