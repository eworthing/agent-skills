#!/usr/bin/env python3
"""Hidden oracle battery for rope-chunk-stable-identity.
Grader-only: never shown to a candidate (listed in provenance.json's
grader_only_files).

Swift has no sibling-file import and `swiftc a.swift b.swift` only allows
top-level statements when the entry file is literally named `main.swift`.
Each variant already ships its own candidate-visible `main.swift` (its own
bundled test), so this harness's own entry point -- `oracle_probe.swift`,
grader-only -- is copied to a scratch file named `main.swift` and compiled
against each variant's `text_spool.swift` in turn, never against that
variant's own `main.swift`. The resulting binary is a tiny CLI:

    <binary> replace-and-diff <chunkSize> <items,comma,separated> <replaceIndex> <newText>

which is how this harness observes `Spool` and `diffSpools` uniformly
across variants whose internals differ.

Two scenarios feed all four checks:

    SCENARIO_BOUND -- 6 chunks of 8 characters each (48 characters total),
                  replace exactly one with distinct new text. Used by
                  single_chunk_edit_touches_one_chunk,
                  worst_case_compared_units_bounded, and
                  resulting_text_correct_after_replace.
    SCENARIO_COLLIDE -- 2 chunks holding different text, then the second is
                  replaced with text equal to the *first* chunk's original
                  text. Used by content_equal_chunks_are_distinguishable.

Runs four checks:

    single_chunk_edit_touches_one_chunk -- after SCENARIO_BOUND's replace,
                                     the diff must report exactly the one
                                     replaced index as changed. Passes for
                                     owned-segment-storage (real per-chunk
                                     identity) and, deliberately, for
                                     near-miss-content-derived-identity
                                     (content-derived identity still gives
                                     the right answer when nothing collides).
                                     Fails for plain-text-single-leaf, whose
                                     only identity token lives at the whole-
                                     leaf level, so every chunk in the leaf
                                     is reported changed. Fails for
                                     mutant-identity-reset-on-read, whose
                                     read-side bug hands out a fresh token to
                                     every chunk on every access, so every
                                     chunk looks new.
    content_equal_chunks_are_distinguishable -- SCENARIO_COLLIDE's replace
                                     must be reported as changing exactly
                                     the second chunk. This is the near-miss
                                     killer: near-miss-content-derived-identity
                                     derives identity from content, so the
                                     edited chunk's new text collides with
                                     the first chunk's identity and the edit
                                     is reported as no change at all.
                                     plain-text-single-leaf and
                                     mutant-identity-reset-on-read both fail
                                     this too, but by over-reporting (both
                                     chunks flagged) rather than under-
                                     reporting -- a different failure mode,
                                     still not "exactly the changed one".
    worst_case_compared_units_bounded -- SCENARIO_BOUND's instrumented
                                     compared-units count must stay at or
                                     below BOUND_UNITS. Passes only for
                                     owned-segment-storage, which only ever
                                     reads the bytes of chunks it already
                                     knows changed. Fails for
                                     plain-text-single-leaf (must re-derive
                                     and report the whole leaf) and
                                     near-miss-content-derived-identity
                                     (must hash every chunk on both sides to
                                     compute identity at all). Fails for
                                     mutant-identity-reset-on-read as a
                                     consequence of over-reporting every
                                     chunk as changed.
    resulting_text_correct_after_replace -- CONTROL: SCENARIO_BOUND's
                                     resulting joined text must match the
                                     expected post-replace text, identically
                                     across all four variants. Holds
                                     everywhere by design, including for
                                     mutant-identity-reset-on-read, since its
                                     defect lives entirely in the identity/
                                     diff layer, never in the stored text
                                     itself -- this is precisely why a test
                                     that only checks resulting content
                                     cannot see the mutant's defect.

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
    "plain-text-single-leaf",
    "owned-segment-storage",
    "near-miss-content-derived-identity",
    "mutant-identity-reset-on-read",
]

BOUND_UNITS = 20

SCENARIO_BOUND = (8, "chunk000,chunk001,chunk002,chunk003,chunk004,chunk005", 2, "REPLACED")
SCENARIO_COLLIDE = (8, "AAAAAAAA,BBBBBBBB", 1, "AAAAAAAA")

EXPECTED_BOUND_FINAL = "chunk000chunk001REPLACEDchunk003chunk004chunk005"


def _swiftc(*args: str) -> None:
    result = subprocess.run(["swiftc", *args], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"swiftc failed: {' '.join(args)}\n{result.stdout}\n{result.stderr}")


def build_probe(variant: str, scratch_dir: Path) -> Path:
    """Compile `variant`'s text_spool.swift against the grader-only probe
    (copied to scratch as main.swift, since swiftc only allows top-level
    statements in a file with that exact name)."""
    main_path = scratch_dir / "main.swift"
    shutil.copyfile(PACK_DIR / "oracle_probe.swift", main_path)
    binary_path = scratch_dir / f"probe_{variant}"
    _swiftc(str(PACK_DIR / variant / "text_spool.swift"), str(main_path), "-o", str(binary_path))
    return binary_path


def replace_and_diff(
    binary: Path, chunk_size: int, items: str, replace_index: int, new_text: str
) -> dict[str, str]:
    result = subprocess.run(
        [str(binary), "replace-and-diff", str(chunk_size), items, str(replace_index), new_text],
        capture_output=True,
        text=True,
        check=True,
    )
    parsed = {}
    for line in result.stdout.strip().splitlines():
        key, _, value = line.partition(": ")
        parsed[key] = value
    return parsed


def changed_indices(outcome: dict[str, str]) -> list[int]:
    raw = outcome["changed"]
    return [] if raw == "none" else [int(x) for x in raw.split(",")]


def single_chunk_edit_touches_one_chunk(binaries: dict[str, Path]) -> dict[str, list[int]]:
    return {
        variant: changed_indices(replace_and_diff(binary, *SCENARIO_BOUND))
        for variant, binary in binaries.items()
    }


def content_equal_chunks_are_distinguishable(binaries: dict[str, Path]) -> dict[str, list[int]]:
    return {
        variant: changed_indices(replace_and_diff(binary, *SCENARIO_COLLIDE))
        for variant, binary in binaries.items()
    }


def worst_case_compared_units_bounded(binaries: dict[str, Path]) -> dict[str, int]:
    return {
        variant: int(replace_and_diff(binary, *SCENARIO_BOUND)["compared"])
        for variant, binary in binaries.items()
    }


def resulting_text_correct_after_replace(binaries: dict[str, Path]) -> dict[str, bool]:
    return {
        variant: replace_and_diff(binary, *SCENARIO_BOUND)["final"] == EXPECTED_BOUND_FINAL
        for variant, binary in binaries.items()
    }


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="rope-chunk-identity-oracles-") as tmp:
        scratch_dir = Path(tmp)
        binaries = {variant: build_probe(variant, scratch_dir) for variant in VARIANTS}

        single_results = single_chunk_edit_touches_one_chunk(binaries)
        collide_results = content_equal_chunks_are_distinguishable(binaries)
        bound_results = worst_case_compared_units_bounded(binaries)
        control_results = resulting_text_correct_after_replace(binaries)

        print("=== single_chunk_edit_touches_one_chunk ===")
        for name, changed in single_results.items():
            print(f"  {name}: changed={changed}")
        print("=== content_equal_chunks_are_distinguishable ===")
        for name, changed in collide_results.items():
            print(f"  {name}: changed={changed}")
        print("=== worst_case_compared_units_bounded ===")
        for name, count in bound_results.items():
            print(f"  {name}: compared={count} (bound={BOUND_UNITS})")
        print("=== resulting_text_correct_after_replace (control) ===")
        for name, ok in control_results.items():
            print(f"  {name}: {'correct' if ok else 'WRONG TEXT'}")

        failures = []

        expected_single = {
            "plain-text-single-leaf": [0, 1, 2, 3, 4, 5],
            "owned-segment-storage": [2],
            "near-miss-content-derived-identity": [2],
            "mutant-identity-reset-on-read": [0, 1, 2, 3, 4, 5],
        }
        for name, expected in expected_single.items():
            if single_results.get(name) != expected:
                failures.append(
                    f"{name}: expected single_chunk_edit_touches_one_chunk={expected}, "
                    f"got {single_results.get(name)}"
                )

        expected_collide = {
            "plain-text-single-leaf": [0, 1],
            "owned-segment-storage": [1],
            "near-miss-content-derived-identity": [],
            "mutant-identity-reset-on-read": [0, 1],
        }
        for name, expected in expected_collide.items():
            if collide_results.get(name) != expected:
                failures.append(
                    f"{name}: expected content_equal_chunks_are_distinguishable={expected}, "
                    f"got {collide_results.get(name)}"
                )

        expected_bound_pass = {
            "plain-text-single-leaf": False,
            "owned-segment-storage": True,
            "near-miss-content-derived-identity": False,
            "mutant-identity-reset-on-read": False,
        }
        for name, expect_pass in expected_bound_pass.items():
            observed_pass = bound_results.get(name, BOUND_UNITS + 1) <= BOUND_UNITS
            if observed_pass != expect_pass:
                failures.append(
                    f"{name}: expected worst_case_compared_units_bounded pass={expect_pass}, "
                    f"got compared={bound_results.get(name)} (bound={BOUND_UNITS})"
                )

        for name in VARIANTS:
            if control_results.get(name) is not True:
                failures.append(
                    f"{name}: resulting_text_correct_after_replace must hold, "
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
