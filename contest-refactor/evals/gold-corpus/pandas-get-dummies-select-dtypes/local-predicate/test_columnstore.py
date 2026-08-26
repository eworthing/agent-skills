#!/usr/bin/env python3
"""columnstore's own bundled test suite (this variant).

Run directly: python3 test_columnstore.py -- exits 0 on success.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from columnstore import Column, Packed, Table, encode_categoricals, should_encode


def _table() -> Table:
    return Table(
        [
            Column("name", "text", ["a", "b"]),
            Column("age", "number", [1, 2]),
            Column("grade", "choice", ["x", "y"]),
            Column("packed_name", Packed("text"), ["a", "b"]),
            Column("packed_grade", Packed("choice"), ["x", "y"]),
        ]
    )


def test_encodes_text_and_choice_including_packed() -> None:
    encoded = encode_categoricals(_table())
    assert set(encoded) == {"name", "grade", "packed_name", "packed_grade"}, encoded


def test_excludes_numbers() -> None:
    assert "age" not in encode_categoricals(_table())


def test_should_encode_unwraps_packed() -> None:
    assert should_encode(Column("x", Packed("choice"), []))
    assert not should_encode(Column("y", "number", []))


def main() -> int:
    test_encodes_text_and_choice_including_packed()
    test_excludes_numbers()
    test_should_encode_unwraps_packed()
    print("OK: test_columnstore.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
