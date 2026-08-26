#!/usr/bin/env python3
"""Hidden oracle battery for swift-collections-ordered-replace-primitive.
Grader-only: never shown to a candidate (listed in provenance.json's
grader_only_files).

Swift has no sibling-file import and `swiftc a.swift b.swift` only allows
top-level statements when the entry file is literally named `main.swift`.
Each variant already ships its own candidate-visible `main.swift` (its own
bundled test), so this harness's own entry point -- `oracle_probe.swift`,
grader-only -- is copied to a scratch file named `main.swift` and compiled
against each variant's `ordered_replace.swift` in turn, never against that
variant's own `main.swift`. The resulting binary is a tiny CLI:

    <binary> roster-replace <old> <new> <items>
    <binary> ledger-replace <old> <new> <newValue> <items> <values>

which is how this harness observes `Roster.replace` and `Ledger.replaceLabel`
uniformly across variants whose internals differ.

Runs four checks:

    diagnostic_wording_preserved      -- Ledger's own duplicate-key and
                                     not-found diagnostics ("label already in use:
                                     '<label>'" / "no entry at that position")
                                     must survive a replaceLabel call.
                                     Fails only for
                                     near-miss-delegates-to-roster-replace,
                                     whose replaceLabel delegates to
                                     Roster's public replace and gets
                                     Roster's own wording ("member already
                                     present" / "position outside roster")
                                     back instead.
    lookup_work_count                 -- an ordinary successful
                                     replaceLabel call must resolve the
                                     label's position exactly once. Fails
                                     only for
                                     near-miss-delegates-to-roster-replace,
                                     which resolves it a second time (count
                                     2) after Roster.replace has already
                                     resolved it once internally, because
                                     delegating to the public method loses
                                     the already-resolved position the
                                     caller still needs for its own
                                     values-array move.
    replace_semantics_preserved       -- after an ordinary successful
                                     replaceLabel call, both the labels and
                                     the paired values must land in exactly
                                     the expected final order. Fails only
                                     for mutant-reordered-move-primitive,
                                     whose shared moveIntoPlace primitive
                                     performs its three steps in the wrong
                                     order and silently drops the new
                                     member instead of retaining it.
    ordinary_replace_matches_across_non_mutant_variants -- CONTROL: a
                                     second, independent replaceLabel
                                     scenario must produce identical
                                     results across
                                     duplicated-inline-move,
                                     shared-move-primitive, and
                                     near-miss-delegates-to-roster-replace
                                     (mutant-reordered-move-primitive is
                                     deliberately excluded -- it is known
                                     to diverge, and
                                     replace_semantics_preserved is the
                                     check that catches it). Holds
                                     everywhere by design: a baseline that
                                     would fail if this fixture itself were
                                     broken in a way that made the other
                                     three oracles' results meaningless.

Run: python3 oracles.py
Exit 0 iff every observed result matches its declared expectation.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

PACK_DIR = Path(__file__).resolve().parent
VARIANTS = [
    "duplicated-inline-move",
    "shared-move-primitive",
    "near-miss-delegates-to-roster-replace",
    "mutant-reordered-move-primitive",
]
NON_MUTANT_VARIANTS = [
    "duplicated-inline-move",
    "shared-move-primitive",
    "near-miss-delegates-to-roster-replace",
]


def _swiftc(*args: str) -> None:
    result = subprocess.run(["swiftc", *args], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"swiftc failed: {' '.join(args)}\n{result.stdout}\n{result.stderr}")


def build_probe(variant: str, scratch_dir: Path) -> Path:
    """Compile `variant`'s ordered_replace.swift against the grader-only
    probe (copied to scratch as main.swift, since swiftc only allows
    top-level statements in a file with that exact name)."""
    main_path = scratch_dir / "main.swift"
    shutil.copyfile(PACK_DIR / "oracle_probe.swift", main_path)
    binary_path = scratch_dir / f"probe_{variant}"
    _swiftc(
        str(PACK_DIR / variant / "ordered_replace.swift"), str(main_path), "-o", str(binary_path)
    )
    return binary_path


def run_probe(binary: Path, *args: str) -> list[str]:
    result = subprocess.run([str(binary), *args], capture_output=True, text=True, check=True)
    return result.stdout.strip().splitlines()


def ledger_replace(
    binary: Path, old: str, new: str, new_value: int, items: list[str], values: list[int]
) -> dict[str, str]:
    lines = run_probe(
        binary,
        "ledger-replace",
        old,
        new,
        str(new_value),
        ",".join(items),
        ",".join(str(v) for v in values),
    )
    parsed = {}
    for line in lines:
        key, _, value = line.partition(": ")
        parsed[key] = value
    return parsed


def diagnostic_wording_preserved(binaries: dict[str, Path]) -> dict[str, bool]:
    results = {}
    for variant, binary in binaries.items():
        duplicate = ledger_replace(binary, "A", "B", 9, ["A", "B", "C"], [1, 2, 3])
        missing = ledger_replace(binary, "Z", "Q", 9, ["A", "B", "C"], [1, 2, 3])
        ok = duplicate["outcome"] == "trapped:label already in use: 'B'"
        ok = ok and missing["outcome"] == "trapped:no entry at that position"
        results[variant] = ok
    return results


def lookup_work_count(binaries: dict[str, Path]) -> dict[str, int]:
    results = {}
    for variant, binary in binaries.items():
        outcome = ledger_replace(binary, "B", "X", 99, ["A", "B", "C", "D"], [1, 2, 3, 4])
        results[variant] = int(outcome["lookups"])
    return results


def replace_semantics_preserved(binaries: dict[str, Path]) -> dict[str, bool]:
    results = {}
    for variant, binary in binaries.items():
        outcome = ledger_replace(binary, "B", "X", 99, ["A", "B", "C", "D"], [1, 2, 3, 4])
        ok = outcome["outcome"] == "success"
        ok = ok and outcome["items"] == "A,X,C,D"
        ok = ok and outcome["values"] == "1,99,3,4"
        results[variant] = ok
    return results


def ordinary_replace_matches_across_non_mutant_variants(
    binaries: dict[str, Path],
) -> dict[str, bool]:
    baselines = {
        variant: ledger_replace(binaries[variant], "Q", "Z", 99, ["P", "Q", "R"], [10, 20, 30])
        for variant in NON_MUTANT_VARIANTS
    }
    reference = baselines[NON_MUTANT_VARIANTS[0]]
    return {
        variant: (result["items"] == reference["items"] and result["values"] == reference["values"])
        for variant, result in baselines.items()
    }


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="swift-ordered-replace-oracles-") as tmp:
        scratch_dir = Path(tmp)
        binaries = {variant: build_probe(variant, scratch_dir) for variant in VARIANTS}

        diagnostic_results = diagnostic_wording_preserved(binaries)
        lookup_results = lookup_work_count(binaries)
        semantics_results = replace_semantics_preserved(binaries)
        control_results = ordinary_replace_matches_across_non_mutant_variants(binaries)

        print("=== diagnostic_wording_preserved ===")
        for name, ok in diagnostic_results.items():
            print(f"  {name}: {'preserved' if ok else 'WRONG WORDING'}")
        print("=== lookup_work_count ===")
        for name, count in lookup_results.items():
            print(f"  {name}: {count}")
        print("=== replace_semantics_preserved ===")
        for name, ok in semantics_results.items():
            print(f"  {name}: {'correct' if ok else 'CORRUPTED'}")
        print("=== ordinary_replace_matches_across_non_mutant_variants (control) ===")
        for name, ok in control_results.items():
            print(f"  {name}: {'matches' if ok else 'DIVERGES'}")

        failures = []

        expected_diagnostic = {
            "duplicated-inline-move": True,
            "shared-move-primitive": True,
            "near-miss-delegates-to-roster-replace": False,
            "mutant-reordered-move-primitive": True,
        }
        for name, expected in expected_diagnostic.items():
            if diagnostic_results.get(name) != expected:
                failures.append(
                    f"{name}: expected diagnostic_wording_preserved={expected}, "
                    f"got {diagnostic_results.get(name)}"
                )

        expected_lookups = {
            "duplicated-inline-move": 1,
            "shared-move-primitive": 1,
            "near-miss-delegates-to-roster-replace": 2,
            "mutant-reordered-move-primitive": 1,
        }
        for name, expected in expected_lookups.items():
            if lookup_results.get(name) != expected:
                failures.append(
                    f"{name}: expected lookup_work_count={expected}, got {lookup_results.get(name)}"
                )

        expected_semantics = {
            "duplicated-inline-move": True,
            "shared-move-primitive": True,
            "near-miss-delegates-to-roster-replace": True,
            "mutant-reordered-move-primitive": False,
        }
        for name, expected in expected_semantics.items():
            if semantics_results.get(name) != expected:
                failures.append(
                    f"{name}: expected replace_semantics_preserved={expected}, "
                    f"got {semantics_results.get(name)}"
                )

        for name in NON_MUTANT_VARIANTS:
            if control_results.get(name) is not True:
                failures.append(
                    f"{name}: ordinary_replace_matches_across_non_mutant_variants must hold, "
                    f"got {control_results.get(name)}"
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
