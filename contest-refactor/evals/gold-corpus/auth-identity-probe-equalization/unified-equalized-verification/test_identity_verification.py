#!/usr/bin/env python3
"""identity_verification's own bundled test suite (this variant).

Run directly: python3 test_identity_verification.py -- exits 0 on success.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from identity_verification import Account, reverify_for_sensitive_action, sign_in


def _directory() -> dict[str, Account]:
    account = Account("known-identity")
    account.set_credential("correct-credential")
    return {"known-identity": account}


def test_sign_in_accepts_correct_credential() -> None:
    directory = _directory()
    assert sign_in("known-identity", "correct-credential", directory) is True


def test_sign_in_rejects_wrong_credential() -> None:
    directory = _directory()
    assert sign_in("known-identity", "wrong-credential", directory) is False


def test_reverify_accepts_correct_credential() -> None:
    directory = _directory()
    assert reverify_for_sensitive_action("known-identity", "correct-credential", directory) is True


def test_reverify_rejects_wrong_credential() -> None:
    directory = _directory()
    assert reverify_for_sensitive_action("known-identity", "wrong-credential", directory) is False


def main() -> int:
    test_sign_in_accepts_correct_credential()
    test_sign_in_rejects_wrong_credential()
    test_reverify_accepts_correct_credential()
    test_reverify_rejects_wrong_credential()
    print("OK: test_identity_verification.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
