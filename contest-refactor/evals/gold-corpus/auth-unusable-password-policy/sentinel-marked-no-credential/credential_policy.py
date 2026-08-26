"""Credential storage and verification for accounts that may or may not
have a local credential of their own (an account provisioned by an
external identity source has none).

An account with no local credential of its own stores a sentinel instead
of a nullable column or a separate flag: a prefix character no encoded
credential can ever start with, followed by a run of random characters.
"""

from __future__ import annotations

import secrets
import string

NO_LOCAL_CREDENTIAL_PREFIX = "~"
NO_LOCAL_CREDENTIAL_SUFFIX_LENGTH = 26

_SUFFIX_ALPHABET = string.ascii_letters + string.digits


def is_credential_usable(stored: str | None) -> bool:
    """True if `stored` was not produced by mark_no_local_credential()."""
    return stored is not None and not stored.startswith(NO_LOCAL_CREDENTIAL_PREFIX)


def mark_no_local_credential() -> str:
    """The stored value for an account with no local credential of its
    own.

    Two such accounts get two different stored values -- the random
    suffix keeps the column from revealing which other accounts are also
    externally managed.
    """
    suffix = "".join(
        secrets.choice(_SUFFIX_ALPHABET) for _ in range(NO_LOCAL_CREDENTIAL_SUFFIX_LENGTH)
    )
    return NO_LOCAL_CREDENTIAL_PREFIX + suffix


def set_credential(raw: str) -> str:
    """Encode `raw` into a storable credential value.

    Never starts with NO_LOCAL_CREDENTIAL_PREFIX, so an encoded credential
    and a no-local-credential marker can never be mistaken for each
    other.
    """
    return "$enc$" + raw[::-1]


def verify_credential(stored: str | None, supplied: str) -> bool:
    """True if `supplied` matches the credential `stored` encodes.

    Checked before any comparison happens: an unusable `stored` value
    (nothing local to compare against) never proceeds to a comparison at
    all, regardless of what `supplied` is.
    """
    if not is_credential_usable(stored):
        return False
    return set_credential(supplied) == stored
