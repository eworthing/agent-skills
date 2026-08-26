"""Identity verification for a claimed identity against a directory of
accounts. If the identity does not resolve to any account, verification
still performs the same amount of work before reporting failure --
otherwise how long verification takes reveals whether the identity exists
at all.
"""

from __future__ import annotations

_WORK_COUNTER = {"count": 0}


def reset_work_counter() -> None:
    _WORK_COUNTER["count"] = 0


def work_performed() -> int:
    return _WORK_COUNTER["count"]


def _hash_work(raw: str) -> str:
    """Stand-in for a real one-way hash. Costs exactly one unit of work."""
    _WORK_COUNTER["count"] += 1
    return "$h$" + raw[::-1]


class Account:
    """One account's identity and stored credential."""

    def __init__(self, identity: str) -> None:
        self.identity = identity
        self.credential: str | None = None

    def set_credential(self, raw: str) -> None:
        self.credential = _hash_work(raw)

    def verify(self, supplied: str) -> bool:
        return _hash_work(supplied) == self.credential


def verify_with_equalized_work(account: Account | None, supplied: str) -> bool:
    """Verify `supplied` against `account`.

    If `account` is None -- the claimed identity did not resolve to
    anything -- this still performs one unit of the same work before
    reporting failure, so a caller cannot tell "no such identity" apart
    from "wrong credential" by how much work happened.
    """
    if account is None:
        _hash_work(supplied)
        return False
    return account.verify(supplied)


def sign_in(identity: str, supplied: str, directory: dict[str, Account]) -> bool:
    account = directory.get(identity)
    return verify_with_equalized_work(account, supplied)


def reverify_for_sensitive_action(
    identity: str, supplied: str, directory: dict[str, Account]
) -> bool:
    account = directory.get(identity)
    return verify_with_equalized_work(account, supplied)
