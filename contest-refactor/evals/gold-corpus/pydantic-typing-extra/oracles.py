#!/usr/bin/env python3
"""Hidden oracle battery for pydantic-typing-extra. Grader-only: never shown
to a candidate (listed in provenance.json's grader_only_files).

Loads each variant's `fieldspec.py` fresh by module name -- every variant
reuses the same module names (`markers_native`, `markers_legacy`, `tags`,
`fieldspec`), so a stable sys.path + sys.modules dance is needed to avoid
one variant's modules leaking into the next -- and runs the five oracles
declared in provenance.json's `hidden_oracles`:

    wrapped_derived_field_excluded              -- a Tagged[Derived[int]]
                                                    field must be excluded
                                                    from stored_field_names.
                                                    Fails in
                                                    single-registry-check (no
                                                    Tagged concept at all)
                                                    and
                                                    near-miss-bare-form-predicate
                                                    (the call site never
                                                    unwraps Tagged).
    bare_unresolved_derived_field_excluded      -- a bare, unresolvable
                                                    forward-referenced
                                                    Derived[Missing] field
                                                    must be excluded.
                                                    THE DISCRIMINATOR for
                                                    near-miss-bare-form-predicate:
                                                    its call site has no
                                                    regex fallback at all.
    wrapped_unresolved_derived_field_excluded   -- both hazards stacked:
                                                    Tagged[Derived[Missing]].
                                                    Fails in
                                                    single-registry-check and
                                                    near-miss-bare-form-predicate.
    legacy_registry_bare_derived_field_excluded -- a bare, resolvable
                                                    Derived field sourced
                                                    from markers_legacy
                                                    (locally named "Legacy")
                                                    must be excluded. Fails
                                                    in single-registry-check
                                                    (only checks
                                                    markers_native) and
                                                    mutant-dropped-registry
                                                    (drops markers_legacy
                                                    from its lookup tuple).
    plain_field_always_stored                   -- a field with no Derived
                                                    marker anywhere in its
                                                    annotation must never be
                                                    excluded. Never fails --
                                                    a sanity check on the
                                                    battery itself.

Run: python3 oracles.py
Exit 0 iff every observed result matches its declared expectation.
"""

from __future__ import annotations

import importlib
import sys
import types
from pathlib import Path

PACK_DIR = Path(__file__).resolve().parent
VARIANTS = [
    "single-registry-check",
    "dual-registry-split",
    "near-miss-bare-form-predicate",
    "mutant-dropped-registry",
]
_SIBLING_MODULES = ["markers_native", "markers_legacy", "tags", "fieldspec"]


def load_variant(name: str) -> types.SimpleNamespace:
    """Import one variant's four sibling modules fresh, in isolation.

    Every variant reuses the same module names, so each load clears any
    stale entry from a previous variant, prepends this variant's directory
    to sys.path just long enough to resolve fieldspec.py's own plain
    `import markers_native` / `import markers_legacy` / `from tags import
    ...`, then clears sys.modules again so the next variant starts clean.
    """
    variant_dir = PACK_DIR / name
    for modname in _SIBLING_MODULES:
        sys.modules.pop(modname, None)
    sys.path.insert(0, str(variant_dir))
    try:
        modules = {modname: importlib.import_module(modname) for modname in _SIBLING_MODULES}
    finally:
        sys.path.remove(str(variant_dir))
        for modname in _SIBLING_MODULES:
            sys.modules.pop(modname, None)
    return types.SimpleNamespace(**modules)


def _namespace_for(mods: types.SimpleNamespace) -> dict[str, object]:
    return {
        "int": int,
        "Derived": mods.markers_native.Derived,
        "Legacy": mods.markers_legacy.Derived,
        "Tagged": mods.tags.Tagged,
    }


def _stored(mods: types.SimpleNamespace, annotations: dict[str, str]) -> list[str]:
    return mods.fieldspec.stored_field_names(annotations, _namespace_for(mods))


def wrapped_derived_field_excluded(variants: dict[str, types.SimpleNamespace]) -> dict[str, bool]:
    results = {}
    for name, mods in variants.items():
        names = _stored(mods, {"total": "int", "cached": 'Tagged[Derived[int], "cache"]'})
        results[name] = "cached" not in names
    return results


def bare_unresolved_derived_field_excluded(
    variants: dict[str, types.SimpleNamespace],
) -> dict[str, bool]:
    results = {}
    for name, mods in variants.items():
        names = _stored(mods, {"total": "int", "cached": "Derived[Missing]"})
        results[name] = "cached" not in names
    return results


def wrapped_unresolved_derived_field_excluded(
    variants: dict[str, types.SimpleNamespace],
) -> dict[str, bool]:
    results = {}
    for name, mods in variants.items():
        names = _stored(mods, {"total": "int", "cached": 'Tagged[Derived[Missing], "cache"]'})
        results[name] = "cached" not in names
    return results


def legacy_registry_bare_derived_field_excluded(
    variants: dict[str, types.SimpleNamespace],
) -> dict[str, bool]:
    results = {}
    for name, mods in variants.items():
        names = _stored(mods, {"total": "int", "cached": "Legacy[int]"})
        results[name] = "cached" not in names
    return results


def plain_field_always_stored(variants: dict[str, types.SimpleNamespace]) -> dict[str, bool]:
    results = {}
    for name, mods in variants.items():
        names = _stored(mods, {"total": "int", "label": "int"})
        results[name] = names == ["total", "label"]
    return results


def main() -> int:
    variants = {name: load_variant(name) for name in VARIANTS}

    wrapped = wrapped_derived_field_excluded(variants)
    bare_unresolved = bare_unresolved_derived_field_excluded(variants)
    wrapped_unresolved = wrapped_unresolved_derived_field_excluded(variants)
    legacy_bare = legacy_registry_bare_derived_field_excluded(variants)
    plain = plain_field_always_stored(variants)

    print("=== wrapped_derived_field_excluded ===")
    for name, ok in wrapped.items():
        print(f"  {name}: {'excluded' if ok else 'KEPT AS STORED'}")
    print("=== bare_unresolved_derived_field_excluded ===")
    for name, ok in bare_unresolved.items():
        print(f"  {name}: {'excluded' if ok else 'KEPT AS STORED'}")
    print("=== wrapped_unresolved_derived_field_excluded ===")
    for name, ok in wrapped_unresolved.items():
        print(f"  {name}: {'excluded' if ok else 'KEPT AS STORED'}")
    print("=== legacy_registry_bare_derived_field_excluded ===")
    for name, ok in legacy_bare.items():
        print(f"  {name}: {'excluded' if ok else 'KEPT AS STORED'}")
    print("=== plain_field_always_stored ===")
    for name, ok in plain.items():
        print(f"  {name}: {'stored' if ok else 'MISSING'}")

    failures = []

    expected_wrapped = {
        "single-registry-check": False,
        "dual-registry-split": True,
        "near-miss-bare-form-predicate": False,
        "mutant-dropped-registry": True,
    }
    for name, expected in expected_wrapped.items():
        if wrapped.get(name) != expected:
            failures.append(
                f"{name}: expected wrapped_derived_field_excluded={expected}, "
                f"got {wrapped.get(name)}"
            )

    expected_bare_unresolved = {
        "single-registry-check": True,
        "dual-registry-split": True,
        "near-miss-bare-form-predicate": False,
        "mutant-dropped-registry": True,
    }
    for name, expected in expected_bare_unresolved.items():
        if bare_unresolved.get(name) != expected:
            failures.append(
                f"{name}: expected bare_unresolved_derived_field_excluded={expected}, "
                f"got {bare_unresolved.get(name)}"
            )

    expected_wrapped_unresolved = {
        "single-registry-check": False,
        "dual-registry-split": True,
        "near-miss-bare-form-predicate": False,
        "mutant-dropped-registry": True,
    }
    for name, expected in expected_wrapped_unresolved.items():
        if wrapped_unresolved.get(name) != expected:
            failures.append(
                f"{name}: expected wrapped_unresolved_derived_field_excluded={expected}, "
                f"got {wrapped_unresolved.get(name)}"
            )

    expected_legacy_bare = {
        "single-registry-check": False,
        "dual-registry-split": True,
        "near-miss-bare-form-predicate": True,
        "mutant-dropped-registry": False,
    }
    for name, expected in expected_legacy_bare.items():
        if legacy_bare.get(name) != expected:
            failures.append(
                f"{name}: expected legacy_registry_bare_derived_field_excluded={expected}, "
                f"got {legacy_bare.get(name)}"
            )

    expected_plain = dict.fromkeys(VARIANTS, True)
    for name, expected in expected_plain.items():
        if plain.get(name) != expected:
            failures.append(
                f"{name}: expected plain_field_always_stored={expected}, got {plain.get(name)}"
            )

    if failures:
        print("\nFAIL:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("\nOK: observed matrix matches declared expectations.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
