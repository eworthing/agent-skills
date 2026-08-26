"""Attaching a signed-in principal to a session.

Every sign-in discards the session outright -- new token, empty data --
regardless of what, if anything, was previously stored in it.
"""

from __future__ import annotations

from principal import Principal
from session import Session


def sign_in(session: Session, principal: Principal) -> None:
    session.discard()
    session.principal_id = principal.id
    session.credential_stamp = principal.credential_stamp
