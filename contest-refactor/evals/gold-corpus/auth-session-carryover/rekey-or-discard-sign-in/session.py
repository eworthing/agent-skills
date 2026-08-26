"""A minimal session store: a rotatable token plus an arbitrary data
mapping, the way application code stashes things in a session unrelated to
who is signed into it (a shopping cart, a wizard's in-progress state).
"""

from __future__ import annotations

import itertools

_next_token = itertools.count(1)


class Session:
    def __init__(self) -> None:
        self.token: int | None = None
        self.data: dict[str, object] = {}
        self.principal_id: object = None
        self.credential_stamp: str | None = None

    def rotate_token(self) -> None:
        """A new token, same data -- defeats session fixation without
        losing whatever the caller already stored in this session."""
        self.token = next(_next_token)

    def discard(self) -> None:
        """A new token AND a clean data mapping -- nothing from before
        this call survives."""
        self.token = next(_next_token)
        self.data = {}
        self.principal_id = None
        self.credential_stamp = None
