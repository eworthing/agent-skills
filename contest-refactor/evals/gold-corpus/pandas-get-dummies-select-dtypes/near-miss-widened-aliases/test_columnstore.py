#!/usr/bin/env python3
"""columnstore's own bundled test suite (this variant).

Run directly: python3 test_columnstore.py -- exits 0 on success.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from columnstore import Column, Packed, Table, encode_categoricals


def _table() -> Table:
    return Table(
        [
            Column("name", "text", ["a", "b"]),
            Column("grade", "choice", ["x", "y"]),
            Column("packed_name", Packed("text"), ["a", "b"]),
            Column("flag", "number", [0, 1]),
        ]
    )


def test_encodes_text_and_choice_including_packed() -> None:
    encoded = encode_categoricals(_table())
    assert {"name", "grade", "packed_name"} <= set(encoded), encoded


def test_flag_column_gets_encoded_too() -> None:
    # Flag/indicator columns behave like a small set of choices, same as
    # text/choice columns.
    assert "flag" in encode_categoricals(_table())


def main() -> int:
    test_encodes_text_and_choice_including_packed()
    test_flag_column_gets_encoded_too()
    print("OK: test_columnstore.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
