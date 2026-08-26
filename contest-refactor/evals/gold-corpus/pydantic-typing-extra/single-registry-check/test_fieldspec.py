#!/usr/bin/env python3
"""fieldspec's own bundled test suite (this variant).

Run directly: python3 test_fieldspec.py -- exits 0 on success.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fieldspec import is_derived, stored_field_names
from markers_legacy import Derived as LegacyDerived
from markers_native import Derived as NativeDerived

NAMESPACE = {"int": int, "Derived": NativeDerived, "Legacy": LegacyDerived}


def test_plain_field_is_stored() -> None:
    names = stored_field_names({"total": "int"}, NAMESPACE)
    assert names == ["total"], names


def test_bare_derived_field_is_excluded() -> None:
    names = stored_field_names({"total": "int", "cached_total": "Derived[int]"}, NAMESPACE)
    assert names == ["total"], names


def test_bare_forward_ref_derived_field_is_excluded() -> None:
    names = stored_field_names({"total": "int", "cached_total": "Derived[Missing]"}, NAMESPACE)
    assert names == ["total"], names


def test_is_derived_recognizes_bare_and_parametrized() -> None:
    assert is_derived(NativeDerived)
    assert is_derived(NativeDerived[int])


def main() -> int:
    test_plain_field_is_stored()
    test_bare_derived_field_is_excluded()
    test_bare_forward_ref_derived_field_is_excluded()
    test_is_derived_recognizes_bare_and_parametrized()
    print("OK: test_fieldspec.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
