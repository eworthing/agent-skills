#!/usr/bin/env python3
"""credential_policy's own bundled test suite (this variant).

Run directly: python3 test_credential_policy.py -- exits 0 on success.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from credential_policy import mark_no_local_credential, set_credential, verify_credential


def test_correct_credential_verifies() -> None:
    stored = set_credential("correct horse battery staple")
    assert verify_credential(stored, "correct horse battery staple") is True


def test_wrong_credential_fails() -> None:
    stored = set_credential("correct horse battery staple")
    assert verify_credential(stored, "wrong guess") is False


def test_no_local_credential_marker_exists() -> None:
    marker = mark_no_local_credential()
    assert isinstance(marker, str)


def main() -> int:
    test_correct_credential_verifies()
    test_wrong_credential_fails()
    test_no_local_credential_marker_exists()
    print("OK: test_credential_policy.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
