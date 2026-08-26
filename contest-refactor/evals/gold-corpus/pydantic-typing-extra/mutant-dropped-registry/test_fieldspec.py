#!/usr/bin/env python3
"""fieldspec's own bundled test suite (this variant).

Run directly: python3 test_fieldspec.py -- exits 0 on success.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fieldspec import is_derived_annotation, is_derived_marker, stored_field_names
from markers_native import Derived as NativeDerived
from tags import Tagged

NAMESPACE = {"int": int, "Derived": NativeDerived, "Tagged": Tagged}


def test_plain_field_is_stored() -> None:
    names = stored_field_names({"total": "int"}, NAMESPACE)
    assert names == ["total"], names


def test_bare_derived_field_is_excluded() -> None:
    names = stored_field_names({"total": "int", "cached_total": "Derived[int]"}, NAMESPACE)
    assert names == ["total"], names


def test_tagged_wrapped_derived_field_is_excluded() -> None:
    names = stored_field_names(
        {"total": "int", "cached_total": 'Tagged[Derived[int], "cache"]'}, NAMESPACE
    )
    assert names == ["total"], names


def test_bare_forward_ref_derived_field_is_excluded() -> None:
    names = stored_field_names({"total": "int", "cached_total": "Derived[Missing]"}, NAMESPACE)
    assert names == ["total"], names


def test_is_derived_marker_and_annotation_agree_on_native_registry() -> None:
    assert is_derived_marker(NativeDerived[int])
    assert is_derived_annotation(NativeDerived[int])


def main() -> int:
    test_plain_field_is_stored()
    test_bare_derived_field_is_excluded()
    test_tagged_wrapped_derived_field_is_excluded()
    test_bare_forward_ref_derived_field_is_excluded()
    test_is_derived_marker_and_annotation_agree_on_native_registry()
    print("OK: test_fieldspec.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
