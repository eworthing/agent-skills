"""Attaching a signed-in principal to a session."""

from __future__ import annotations

from principal import Principal
from session import Session


def sign_in(session: Session, principal: Principal) -> None:
    session.principal_id = principal.id
    session.credential_stamp = principal.credential_stamp
