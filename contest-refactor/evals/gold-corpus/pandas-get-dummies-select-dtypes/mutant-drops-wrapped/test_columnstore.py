#!/usr/bin/env python3
"""columnstore's own bundled test suite (this variant).

Run directly: python3 test_columnstore.py -- exits 0 on success.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from columnstore import Column, Table, encode_categoricals


def _table() -> Table:
    return Table(
        [
            Column("name", "text", ["a", "b"]),
            Column("age", "number", [1, 2]),
            Column("grade", "choice", ["x", "y"]),
        ]
    )


def test_encodes_text_and_choice() -> None:
    encoded = encode_categoricals(_table())
    assert set(encoded) == {"name", "grade"}, encoded


def test_excludes_numbers() -> None:
    assert "age" not in encode_categoricals(_table())


def main() -> int:
    test_encodes_text_and_choice()
    test_excludes_numbers()
    print("OK: test_columnstore.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
