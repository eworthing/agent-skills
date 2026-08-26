#!/usr/bin/env python3
"""Hidden oracle battery for cpython-wasm-platform-predicate. Grader-only:
never shown to a candidate (listed in provenance.json's grader_only_files).

Each variant ships two coupled files, `platsupport.py` (platform flags +
skip_if/collect_skips) and `test_platform_guards.py` (`from platsupport
import ...`, plus `ALL_TESTS`). Every variant reuses the same two module
names, so `load_variant` pins both into `sys.modules` under their plain
names before exec'ing `test_platform_guards.py` -- that way its internal
`from platsupport import ...` binds to *this* variant's platsupport, not a
previously loaded one -- then pops both names so the next variant starts
clean.

Runs the four oracles declared in provenance.json's `hidden_oracles`:

    skip_set_matches_baseline    -- THE DISCRIMINATOR. For every platform,
                                     the set of skipped test names must match
                                     shared-flag's. Must differ for
                                     near-miss-collapse-all (it over-skips on
                                     both wasm-family platforms). Holds for
                                     mutant-merged-reasons, which changes
                                     reasons but not skip sets -- this oracle
                                     alone cannot catch it.
    platform_specific_tests_still_run -- the pack's centre. The three
                                     single-platform guards must still let
                                     their test run on the *other*
                                     wasm-family platform. Fails only against
                                     near-miss-collapse-all.
    skip_reasons_preserved        -- the two dual-guard tests must report
                                     shared-flag's own per-platform reason,
                                     not a merged/generic one. Fails only
                                     against mutant-merged-reasons.
    non_wasm_platform_unaffected  -- mainland (the ordinary platform) skips
                                     nothing, in every variant. A control.

Run: python3 oracles.py
Exit 0 iff every observed result matches its declared expectation.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

PACK_DIR = Path(__file__).resolve().parent
VARIANTS = [
    "scattered-disjunction",
    "shared-flag",
    "near-miss-collapse-all",
    "mutant-merged-reasons",
]
BASELINE = "shared-flag"
PLATFORMS = ["gearshift", "tideline", "mainland"]

# (test_name, platform_it_must_still_run_on) -- each names a single-platform
# guard's test and the *other* wasm-family platform, which never had the
# limitation the guard names.
PLATFORM_SPECIFIC_CHECKS = [
    ("test_user_account_lookup", "gearshift"),
    ("test_dotdot_path_resolution", "gearshift"),
    ("test_symlink_target_preserved", "tideline"),
]

# (test_name, platform) pairs carrying a platform-specific reason in
# shared-flag that a correct variant must preserve verbatim.
REASON_CHECKS = [
    ("test_unix_socket_creation", "gearshift"),
    ("test_unix_socket_creation", "tideline"),
    ("test_bare_thread_spawn", "gearshift"),
    ("test_bare_thread_spawn", "tideline"),
]


def load_variant(name: str):
    sys.modules.pop("platsupport", None)
    sys.modules.pop("test_platform_guards", None)

    plat_spec = importlib.util.spec_from_file_location(
        "platsupport", PACK_DIR / name / "platsupport.py"
    )
    assert plat_spec is not None and plat_spec.loader is not None
    plat_mod = importlib.util.module_from_spec(plat_spec)
    sys.modules["platsupport"] = plat_mod
    plat_spec.loader.exec_module(plat_mod)

    test_spec = importlib.util.spec_from_file_location(
        "test_platform_guards", PACK_DIR / name / "test_platform_guards.py"
    )
    assert test_spec is not None and test_spec.loader is not None
    test_mod = importlib.util.module_from_spec(test_spec)
    sys.modules["test_platform_guards"] = test_mod
    test_spec.loader.exec_module(test_mod)

    skips_by_platform = {p: plat_mod.collect_skips(p, test_mod.ALL_TESTS) for p in PLATFORMS}

    sys.modules.pop("platsupport", None)
    sys.modules.pop("test_platform_guards", None)
    return skips_by_platform


def skip_set_matches_baseline(skip_maps: dict) -> dict[str, bool]:
    baseline = skip_maps[BASELINE]
    return {
        variant: all(set(platforms[p].keys()) == set(baseline[p].keys()) for p in PLATFORMS)
        for variant, platforms in skip_maps.items()
    }


def platform_specific_tests_still_run(skip_maps: dict) -> dict[str, bool]:
    return {
        variant: all(name not in platforms[platform] for name, platform in PLATFORM_SPECIFIC_CHECKS)
        for variant, platforms in skip_maps.items()
    }


def skip_reasons_preserved(skip_maps: dict) -> dict[str, bool]:
    baseline = skip_maps[BASELINE]
    results = {}
    for variant, platforms in skip_maps.items():
        results[variant] = all(
            platforms[platform].get(name) == baseline[platform].get(name)
            for name, platform in REASON_CHECKS
        )
    return results


def non_wasm_platform_unaffected(skip_maps: dict) -> dict[str, bool]:
    return {variant: platforms["mainland"] == {} for variant, platforms in skip_maps.items()}


def main() -> int:
    skip_maps = {variant: load_variant(variant) for variant in VARIANTS}

    matches_baseline = skip_set_matches_baseline(skip_maps)
    specific_still_run = platform_specific_tests_still_run(skip_maps)
    reasons_preserved = skip_reasons_preserved(skip_maps)
    non_wasm_ok = non_wasm_platform_unaffected(skip_maps)

    print("=== skip_set_matches_baseline (vs shared-flag) ===")
    for name, ok in matches_baseline.items():
        print(f"  {name}: {'matches' if ok else 'DIFFERS'}")
    print("=== platform_specific_tests_still_run ===")
    for name, ok in specific_still_run.items():
        print(f"  {name}: {'still runs' if ok else 'OVER-SKIPPED'}")
    print("=== skip_reasons_preserved (vs shared-flag) ===")
    for name, ok in reasons_preserved.items():
        print(f"  {name}: {'preserved' if ok else 'MERGED/CHANGED'}")
    print("=== non_wasm_platform_unaffected (mainland) ===")
    for name, ok in non_wasm_ok.items():
        print(f"  {name}: {'unaffected' if ok else 'SKIPPED SOMETHING'}")

    failures = []

    expected_baseline = {
        "scattered-disjunction": True,
        "shared-flag": True,
        "near-miss-collapse-all": False,
        "mutant-merged-reasons": True,
    }
    for name, expected in expected_baseline.items():
        if matches_baseline.get(name) != expected:
            failures.append(
                f"{name}: expected skip_set_matches_baseline={expected}, "
                f"got {matches_baseline.get(name)}"
            )

    expected_specific = {
        "scattered-disjunction": True,
        "shared-flag": True,
        "near-miss-collapse-all": False,
        "mutant-merged-reasons": True,
    }
    for name, expected in expected_specific.items():
        if specific_still_run.get(name) != expected:
            failures.append(
                f"{name}: expected platform_specific_tests_still_run={expected}, "
                f"got {specific_still_run.get(name)}"
            )

    expected_reasons = {
        "scattered-disjunction": True,
        "shared-flag": True,
        "near-miss-collapse-all": True,
        "mutant-merged-reasons": False,
    }
    for name, expected in expected_reasons.items():
        if reasons_preserved.get(name) != expected:
            failures.append(
                f"{name}: expected skip_reasons_preserved={expected}, "
                f"got {reasons_preserved.get(name)}"
            )

    for name in VARIANTS:
        if non_wasm_ok.get(name) is not True:
            failures.append(
                f"{name}: non_wasm_platform_unaffected must hold, got {non_wasm_ok.get(name)}"
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
