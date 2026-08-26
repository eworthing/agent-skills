#!/usr/bin/env python3
"""Hidden oracle battery for pandas-get-dummies-select-dtypes. Grader-only:
never shown to a candidate (listed in provenance.json's grader_only_files).

Imports each variant's `columnstore.py` fresh by file path (every variant
reuses the same module name, so plain `import columnstore` would collide)
and runs the four oracles declared in provenance.json's `hidden_oracles`:

    encodable_set_matches_baseline      -- the discriminator: the exact set
                                            of columns selected for encoding,
                                            across every column kind.
    wrapped_extension_columns_encoded   -- packed/extension text and choice
                                            columns must be selected.
    numeric_never_encoded               -- the numeric column must never be
                                            selected.
    no_dependency_on_selector_internals -- a structural (AST) check of
                                            whether encode_categoricals calls
                                            column_subset at all.

Run: python3 oracles.py
Exit 0 iff every observed result matches its declared expectation.
"""

from __future__ import annotations

import ast
import importlib.util
import sys
import types
from pathlib import Path

PACK_DIR = Path(__file__).resolve().parent
VARIANTS = [
    "alias-list-coupling",
    "local-predicate",
    "near-miss-widened-aliases",
    "mutant-drops-wrapped",
]


def load_variant(name: str) -> types.ModuleType:
    path = PACK_DIR / name / "columnstore.py"
    spec = importlib.util.spec_from_file_location(f"_gc_columnstore_{name.replace('-', '_')}", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _fixture_table(module: types.ModuleType):
    """One column of each of the six kinds the pack models: plain-object,
    masked/nullable, wrapped-extension string, wrapped-extension
    dictionary/categorical, native categorical, and numeric (never
    encodable)."""
    column, table, packed = module.Column, module.Table, module.Packed
    return table(
        [
            column("c_text", "text", ["a", "b"]),
            column("c_masked", "masked_text", ["c", None]),
            column("c_packed_text", packed("text"), ["d", "e"]),
            column("c_packed_choice", packed("choice"), ["x", "y"]),
            column("c_choice", "choice", ["x", "y"]),
            column("c_number", "number", [1, 2]),
        ]
    )


def encodable_set_matches_baseline(modules: dict[str, types.ModuleType]) -> dict[str, set[str]]:
    return {
        name: set(module.encode_categoricals(_fixture_table(module)))
        for name, module in modules.items()
    }


def wrapped_extension_columns_encoded(modules: dict[str, types.ModuleType]) -> dict[str, bool]:
    results = {}
    for name, module in modules.items():
        encoded = set(module.encode_categoricals(_fixture_table(module)))
        results[name] = {"c_packed_text", "c_packed_choice"} <= encoded
    return results


def numeric_never_encoded(modules: dict[str, types.ModuleType]) -> dict[str, bool]:
    results = {}
    for name, module in modules.items():
        encoded = set(module.encode_categoricals(_fixture_table(module)))
        results[name] = "c_number" not in encoded
    return results


def no_dependency_on_selector_internals(dirs: dict[str, Path]) -> dict[str, bool]:
    """True iff `encode_categoricals`'s own function body calls
    `column_subset` -- a structural (AST) fact about that one function, not
    a stylistic guess and not a whole-file scan (every variant still
    defines `column_subset` for general use elsewhere in the module)."""
    results = {}
    for name, variant_dir in dirs.items():
        source = (variant_dir / "columnstore.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        calls_selector = False
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "encode_categoricals":
                for inner in ast.walk(node):
                    if (
                        isinstance(inner, ast.Call)
                        and isinstance(inner.func, ast.Name)
                        and inner.func.id == "column_subset"
                    ):
                        calls_selector = True
        results[name] = calls_selector
    return results


def main() -> int:
    modules = {name: load_variant(name) for name in VARIANTS}
    dirs = {name: PACK_DIR / name for name in VARIANTS}

    baseline = encodable_set_matches_baseline(modules)
    wrapped = wrapped_extension_columns_encoded(modules)
    numeric = numeric_never_encoded(modules)
    dependency = no_dependency_on_selector_internals(dirs)

    print("=== encodable_set_matches_baseline ===")
    for name, cols in baseline.items():
        print(f"  {name}: {sorted(cols)}")
    print("=== wrapped_extension_columns_encoded ===")
    for name, ok in wrapped.items():
        print(f"  {name}: {'encoded' if ok else 'DROPPED'}")
    print("=== numeric_never_encoded ===")
    for name, ok in numeric.items():
        print(f"  {name}: {'excluded' if ok else 'OVER-MATCHED'}")
    print("=== no_dependency_on_selector_internals ===")
    for name, calls in dependency.items():
        print(f"  {name}: {'calls column_subset' if calls else 'local predicate only'}")

    failures = []

    baseline_set = baseline["alias-list-coupling"]
    if baseline["local-predicate"] != baseline_set:
        failures.append(
            "local-predicate: expected the same encodable set as alias-list-coupling "
            f"({sorted(baseline_set)}), got {sorted(baseline['local-predicate'])}"
        )
    if baseline["near-miss-widened-aliases"] == baseline_set:
        failures.append(
            "near-miss-widened-aliases: expected a DIFFERENT (over-matched) encodable "
            f"set than alias-list-coupling ({sorted(baseline_set)}), got the same set"
        )
    if baseline["mutant-drops-wrapped"] == baseline_set:
        failures.append(
            "mutant-drops-wrapped: expected a DIFFERENT (under-matched) encodable set "
            f"than alias-list-coupling ({sorted(baseline_set)}), got the same set"
        )

    expected_wrapped = {
        "alias-list-coupling": True,
        "local-predicate": True,
        "near-miss-widened-aliases": True,
        "mutant-drops-wrapped": False,
    }
    for name, expected in expected_wrapped.items():
        if wrapped.get(name) != expected:
            failures.append(
                f"{name}: expected wrapped_extension_columns_encoded={expected}, "
                f"got {wrapped.get(name)}"
            )

    expected_numeric = {
        "alias-list-coupling": True,
        "local-predicate": True,
        "near-miss-widened-aliases": False,
        "mutant-drops-wrapped": True,
    }
    for name, expected in expected_numeric.items():
        if numeric.get(name) != expected:
            failures.append(
                f"{name}: expected numeric_never_encoded={expected}, got {numeric.get(name)}"
            )

    expected_dependency = {
        "alias-list-coupling": True,
        "local-predicate": False,
        "near-miss-widened-aliases": True,
        "mutant-drops-wrapped": False,
    }
    for name, expected in expected_dependency.items():
        if dependency.get(name) != expected:
            failures.append(
                f"{name}: expected no_dependency_on_selector_internals call-flag="
                f"{expected}, got {dependency.get(name)}"
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
