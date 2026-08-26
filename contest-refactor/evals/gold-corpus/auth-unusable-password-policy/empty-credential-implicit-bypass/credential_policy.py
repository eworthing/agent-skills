"""Credential storage and verification for accounts that may or may not
have a local credential of their own (an account provisioned by an
external identity source has none).
"""

from __future__ import annotations


def mark_no_local_credential() -> str:
    """The stored value for an account with no local credential of its
    own."""
    return ""


def set_credential(raw: str) -> str:
    """Encode `raw` into a storable credential value."""
    return "$enc$" + raw[::-1]


def verify_credential(stored: str, supplied: str) -> bool:
    """True if `supplied` matches the credential `stored` encodes.

    An account with no local credential has nothing to compare against --
    treat that as nothing being required.
    """
    if not stored:
        return not supplied
    return set_credential(supplied) == stored
