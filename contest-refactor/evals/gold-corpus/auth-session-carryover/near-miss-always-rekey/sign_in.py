"""Attaching a signed-in principal to a session.

Every sign-in gets a new session token, defeating session fixation
regardless of who -- if anyone -- was previously signed into the session.
"""

from __future__ import annotations

from principal import Principal
from session import Session


def sign_in(session: Session, principal: Principal) -> None:
    session.rotate_token()
    session.principal_id = principal.id
    session.credential_stamp = principal.credential_stamp
