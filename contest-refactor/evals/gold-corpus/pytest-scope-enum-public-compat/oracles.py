#!/usr/bin/env python3
"""Hidden oracle battery for pytest-scope-enum-public-compat. Grader-only:
never shown to a candidate (listed in provenance.json's grader_only_files).

Imports each variant's `lifespan.py` fresh by file path (every variant reuses
the same module name, so plain `import lifespan` would collide) and runs the
four oracles declared in provenance.json's `hidden_oracles`:

    public_scope_compares_as_string    -- THE DISCRIMINATOR. A Handle's
                                           public `.span` must compare equal
                                           to the plain string value it was
                                           built from, for every span value.
                                           Fails in
                                           near-miss-enum-through-public-api,
                                           whose `.span` returns the enum
                                           member itself -- the comparison
                                           returns False, it does not raise.
    scope_ordering_preserved           -- every pairwise `higher()` result
                                           matches the declared low-to-high
                                           order (step < suite < file <
                                           batch < run). Identical in
                                           stringly-typed and
                                           enum-with-compat-property. Fails
                                           in mutant-ordering-by-name, which
                                           orders by member name instead of
                                           declaration position.
    higher_scope_and_next_scope_match_baseline -- higher()/next_up() return
                                           what stringly-typed's own index
                                           arithmetic returned, for every
                                           input pair. Fails only against
                                           mutant-ordering-by-name.
    internal_type_is_the_enum          -- the internal span attribute really
                                           is the Span enum, not a plain
                                           string -- i.e. the refactor
                                           happened at all. Fails in
                                           stringly-typed, which has no
                                           internal/public split to begin
                                           with.

Run: python3 oracles.py
Exit 0 iff every observed result matches its declared expectation.
"""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

PACK_DIR = Path(__file__).resolve().parent
VARIANTS = [
    "stringly-typed",
    "enum-with-compat-property",
    "near-miss-enum-through-public-api",
    "mutant-ordering-by-name",
]
BASELINE = "stringly-typed"
VALUES = ["step", "suite", "file", "batch", "run"]


def load_variant(name: str) -> types.ModuleType:
    path = PACK_DIR / name / "lifespan.py"
    spec = importlib.util.spec_from_file_location(f"_gc_lifespan_{name.replace('-', '_')}", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # Span's __lt__ forward-ref resolution needs this
    spec.loader.exec_module(module)
    return module


def public_scope_compares_as_string(modules: dict) -> dict[str, bool]:
    results = {}
    for name, mod in modules.items():
        ok = True
        for value in VALUES:
            handle = mod.Handle(mod.span_from_value(value))
            if handle.span != value:
                ok = False
        results[name] = ok
    return results


def scope_ordering_preserved(modules: dict) -> dict[str, bool]:
    results = {}
    for name, mod in modules.items():
        spans = [mod.span_from_value(v) for v in VALUES]
        ok = True
        for i, lo in enumerate(spans):
            for hi in spans[i + 1 :]:
                if mod.higher(lo, hi) != hi or mod.higher(hi, lo) != hi:
                    ok = False
        results[name] = ok
    return results


def higher_scope_and_next_scope_match_baseline(modules: dict) -> dict[str, bool]:
    baseline = modules[BASELINE]
    results = {}
    for name, mod in modules.items():
        ok = True
        for value in VALUES:
            base_next = baseline.value_of(baseline.next_up(baseline.span_from_value(value)))
            mod_next = mod.value_of(mod.next_up(mod.span_from_value(value)))
            if base_next != mod_next:
                ok = False
        for i, a in enumerate(VALUES):
            for b in VALUES[i + 1 :]:
                base_higher = baseline.value_of(
                    baseline.higher(baseline.span_from_value(a), baseline.span_from_value(b))
                )
                mod_higher = mod.value_of(
                    mod.higher(mod.span_from_value(a), mod.span_from_value(b))
                )
                if base_higher != mod_higher:
                    ok = False
        results[name] = ok
    return results


def internal_type_is_the_enum(modules: dict) -> dict[str, bool]:
    results = {}
    for name, mod in modules.items():
        span_cls = getattr(mod, "Span", None)
        handle = mod.Handle(mod.span_from_value("step"))
        internal = getattr(handle, "_span", None)
        results[name] = span_cls is not None and isinstance(internal, span_cls)
    return results


def main() -> int:
    modules = {variant: load_variant(variant) for variant in VARIANTS}

    public_compat = public_scope_compares_as_string(modules)
    ordering = scope_ordering_preserved(modules)
    baseline_match = higher_scope_and_next_scope_match_baseline(modules)
    internal_enum = internal_type_is_the_enum(modules)

    print("=== public_scope_compares_as_string ===")
    for name, ok in public_compat.items():
        print(f"  {name}: {'compares as string' if ok else 'DOES NOT COMPARE AS STRING'}")
    print("=== scope_ordering_preserved ===")
    for name, ok in ordering.items():
        print(f"  {name}: {'preserved' if ok else 'BROKEN'}")
    print("=== higher_scope_and_next_scope_match_baseline (vs stringly-typed) ===")
    for name, ok in baseline_match.items():
        print(f"  {name}: {'matches' if ok else 'DIFFERS'}")
    print("=== internal_type_is_the_enum ===")
    for name, ok in internal_enum.items():
        print(f"  {name}: {'is the enum' if ok else 'is NOT the enum'}")

    failures = []

    expected_public_compat = {
        "stringly-typed": True,
        "enum-with-compat-property": True,
        "near-miss-enum-through-public-api": False,
        "mutant-ordering-by-name": True,
    }
    for name, expected in expected_public_compat.items():
        if public_compat.get(name) != expected:
            failures.append(
                f"{name}: expected public_scope_compares_as_string={expected}, "
                f"got {public_compat.get(name)}"
            )

    expected_ordering = {
        "stringly-typed": True,
        "enum-with-compat-property": True,
        "near-miss-enum-through-public-api": True,
        "mutant-ordering-by-name": False,
    }
    for name, expected in expected_ordering.items():
        if ordering.get(name) != expected:
            failures.append(
                f"{name}: expected scope_ordering_preserved={expected}, got {ordering.get(name)}"
            )

    expected_baseline_match = {
        "stringly-typed": True,
        "enum-with-compat-property": True,
        "near-miss-enum-through-public-api": True,
        "mutant-ordering-by-name": False,
    }
    for name, expected in expected_baseline_match.items():
        if baseline_match.get(name) != expected:
            failures.append(
                f"{name}: expected higher_scope_and_next_scope_match_baseline={expected}, "
                f"got {baseline_match.get(name)}"
            )

    expected_internal_enum = {
        "stringly-typed": False,
        "enum-with-compat-property": True,
        "near-miss-enum-through-public-api": True,
        "mutant-ordering-by-name": True,
    }
    for name, expected in expected_internal_enum.items():
        if internal_enum.get(name) != expected:
            failures.append(
                f"{name}: expected internal_type_is_the_enum={expected}, "
                f"got {internal_enum.get(name)}"
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
