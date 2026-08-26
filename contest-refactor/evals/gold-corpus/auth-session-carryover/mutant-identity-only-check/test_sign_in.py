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


def test_anonymous_data_is_retained_on_first_sign_in() -> None:
    session = Session()
    session.data["cart"] = ["item"]
    sign_in(session, ALICE)
    assert session.data.get("cart") == ["item"], session.data


def test_reauth_same_principal_leaves_token_alone() -> None:
    session = Session()
    sign_in(session, ALICE)
    token_after_first = session.token
    sign_in(session, ALICE)
    assert session.token == token_after_first


def test_different_principal_discards_prior_data() -> None:
    session = Session()
    sign_in(session, ALICE)
    session.data["cart"] = ["item"]
    sign_in(session, BOB)
    assert "cart" not in session.data, session.data
    assert session.principal_id == "bob"


def main() -> int:
    test_first_sign_in_rotates_the_token()
    test_anonymous_data_is_retained_on_first_sign_in()
    test_reauth_same_principal_leaves_token_alone()
    test_different_principal_discards_prior_data()
    print("OK: test_sign_in.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
