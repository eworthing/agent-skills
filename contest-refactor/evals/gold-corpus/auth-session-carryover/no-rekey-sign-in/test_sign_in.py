#!/usr/bin/env python3
"""sign_in's own bundled test suite (this variant).

Run directly: python3 test_sign_in.py -- exits 0 on success.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from principal import Principal
from session import Session
from sign_in import sign_in

ALICE = Principal("alice", "stamp-alice-1")


def test_sign_in_records_the_principal() -> None:
    session = Session()
    sign_in(session, ALICE)
    assert session.principal_id == "alice", session.principal_id


def test_sign_in_records_the_credential_stamp() -> None:
    session = Session()
    sign_in(session, ALICE)
    assert session.credential_stamp == "stamp-alice-1", session.credential_stamp


def main() -> int:
    test_sign_in_records_the_principal()
    test_sign_in_records_the_credential_stamp()
    print("OK: test_sign_in.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
