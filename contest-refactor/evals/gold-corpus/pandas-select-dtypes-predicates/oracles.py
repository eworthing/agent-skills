#!/usr/bin/env python3
"""Hidden oracle battery for pandas-select-dtypes-predicates. Grader-only:
never shown to a candidate (listed in provenance.json's grader_only_files).

Imports each variant's `coltable.py` fresh by file path (every variant reuses
the same module name, so plain `import coltable` would collide) and runs the
four oracles declared in provenance.json's `hidden_oracles`:

    selection_matches_baseline  -- THE DISCRIMINATOR. frozenset-predicate and
                                    per-type-callables must select identical
                                    columns for every include/exclude combo
                                    tried below. Must differ for
                                    near-miss-recollapsed and mutant-any-to-all.
    multi_type_include_nonempty -- an include list naming two types returns
                                    the union, never an empty result. Fails
                                    only against mutant-any-to-all, which
                                    requires a column to match every requested
                                    type's predicate instead of any one of
                                    them -- impossible when the two types are
                                    mutually exclusive kinds.
    special_case_type_matches   -- the "flag" type (a count-kind column
                                    marked flag=True) is still selected
                                    correctly by itself. Fails only against
                                    near-miss-recollapsed, which dropped the
                                    flag/count distinction when it collapsed
                                    back to a single kind-membership test.
    exclude_still_honored       -- exclude semantics survive in every variant
                                    for a plain type exclude.

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
    "frozenset-predicate",
    "per-type-callables",
    "near-miss-recollapsed",
    "mutant-any-to-all",
]
BASELINE = "frozenset-predicate"

# (include, exclude) combos exercised for every variant: no filter, each type
# alone, the count/flag pair (with and without an offsetting exclude), a
# cross-kind multi-type include, and a plain exclude.
COMBOS: list[tuple[tuple[str, ...] | None, tuple[str, ...] | None]] = [
    (None, None),
    (("count",), None),
    (("flag",), None),
    (("count", "flag"), None),
    (("real",), None),
    (("text",), None),
    (("count", "real"), None),
    (None, ("text",)),
    (("count", "flag"), ("flag",)),
]


def load_variant(name: str) -> types.ModuleType:
    path = PACK_DIR / name / "coltable.py"
    spec = importlib.util.spec_from_file_location(f"_gc_coltable_{name.replace('-', '_')}", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclass forward-ref resolution needs this
    spec.loader.exec_module(module)
    return module


def _build_table(module: types.ModuleType):
    Column = module.Column
    Coltable = module.Coltable
    columns = [
        Column("id", "count", (1, 2, 3)),
        Column("age", "count", (30, 40, 50)),
        Column("is_active", "count", (1, 0, 1), flag=True),
        Column("score", "real", (9.5, 8.1, 7.4)),
        Column("name", "text", ("a", "b", "c")),
    ]
    return Coltable(columns)


def _selected_names(table, include, exclude) -> list[str]:
    return sorted(c.name for c in table.select(include=include, exclude=exclude))


def selection_matches_baseline(tables: dict) -> dict[str, bool]:
    baseline = tables[BASELINE]
    results = {}
    for name, table in tables.items():
        results[name] = all(
            _selected_names(table, inc, exc) == _selected_names(baseline, inc, exc)
            for inc, exc in COMBOS
        )
    return results


def multi_type_include_nonempty(tables: dict) -> dict[str, bool]:
    return {
        name: len(table.select(include=("count", "real"))) > 0 for name, table in tables.items()
    }


def special_case_type_matches(tables: dict) -> dict[str, bool]:
    results = {}
    for name, table in tables.items():
        names = [c.name for c in table.select(include=("flag",))]
        results[name] = names == ["is_active"]
    return results


def exclude_still_honored(tables: dict) -> dict[str, bool]:
    expected = ["age", "id", "is_active", "score"]
    return {
        name: sorted(c.name for c in table.select(exclude=("text",))) == expected
        for name, table in tables.items()
    }


def main() -> int:
    modules = {name: load_variant(name) for name in VARIANTS}
    tables = {name: _build_table(module) for name, module in modules.items()}

    matches_baseline = selection_matches_baseline(tables)
    multi_nonempty = multi_type_include_nonempty(tables)
    special_case = special_case_type_matches(tables)
    exclude_honored = exclude_still_honored(tables)

    print("=== selection_matches_baseline (vs frozenset-predicate) ===")
    for name, ok in matches_baseline.items():
        print(f"  {name}: {'matches' if ok else 'DIFFERS'}")
    print("=== multi_type_include_nonempty (count+real) ===")
    for name, ok in multi_nonempty.items():
        print(f"  {name}: {'nonempty' if ok else 'EMPTY'}")
    print("=== special_case_type_matches (flag alone) ===")
    for name, ok in special_case.items():
        print(f"  {name}: {'correct' if ok else 'WRONG'}")
    print("=== exclude_still_honored (exclude text) ===")
    for name, ok in exclude_honored.items():
        print(f"  {name}: {'honored' if ok else 'IGNORED'}")

    failures = []

    expected_baseline = {
        "frozenset-predicate": True,
        "per-type-callables": True,
        "near-miss-recollapsed": False,
        "mutant-any-to-all": False,
    }
    for name, expected in expected_baseline.items():
        if matches_baseline.get(name) != expected:
            failures.append(
                f"{name}: expected selection_matches_baseline={expected}, "
                f"got {matches_baseline.get(name)}"
            )

    expected_multi = {
        "frozenset-predicate": True,
        "per-type-callables": True,
        "near-miss-recollapsed": True,
        "mutant-any-to-all": False,
    }
    for name, expected in expected_multi.items():
        if multi_nonempty.get(name) != expected:
            failures.append(
                f"{name}: expected multi_type_include_nonempty={expected}, "
                f"got {multi_nonempty.get(name)}"
            )

    expected_special = {
        "frozenset-predicate": True,
        "per-type-callables": True,
        "near-miss-recollapsed": False,
        "mutant-any-to-all": True,
    }
    for name, expected in expected_special.items():
        if special_case.get(name) != expected:
            failures.append(
                f"{name}: expected special_case_type_matches={expected}, "
                f"got {special_case.get(name)}"
            )

    for name in VARIANTS:
        if exclude_honored.get(name) is not True:
            failures.append(
                f"{name}: exclude_still_honored must hold, got {exclude_honored.get(name)}"
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
