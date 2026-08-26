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
BOB = Principal("bob", "stamp-bob-1")


def test_first_sign_in_rotates_the_token() -> None:
    session = Session()
    sign_in(session, ALICE)
    assert session.token is not None


def test_reauth_gets_a_fresh_token_every_time() -> None:
    session = Session()
    sign_in(session, ALICE)
    token_after_first = session.token
    sign_in(session, ALICE)
    assert session.token != token_after_first


def test_different_principal_discards_prior_data() -> None:
    session = Session()
    sign_in(session, ALICE)
    session.data["cart"] = ["item"]
    sign_in(session, BOB)
    assert "cart" not in session.data, session.data
    assert session.principal_id == "bob"


def test_changed_credential_stamp_discards_the_session() -> None:
    session = Session()
    sign_in(session, ALICE)
    session.data["cart"] = ["item"]
    alice_after_password_change = Principal("alice", "stamp-alice-2")
    sign_in(session, alice_after_password_change)
    assert "cart" not in session.data, session.data
    assert session.credential_stamp == "stamp-alice-2"


def main() -> int:
    test_first_sign_in_rotates_the_token()
    test_reauth_gets_a_fresh_token_every_time()
    test_different_principal_discards_prior_data()
    test_changed_credential_stamp_discards_the_session()
    print("OK: test_sign_in.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
