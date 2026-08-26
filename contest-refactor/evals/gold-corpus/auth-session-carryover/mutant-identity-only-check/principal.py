"""The signed-in party a session gets attached to."""

from __future__ import annotations


class Principal:
    def __init__(self, principal_id: object, credential_stamp: str) -> None:
        self.id = principal_id
        self.credential_stamp = credential_stamp
