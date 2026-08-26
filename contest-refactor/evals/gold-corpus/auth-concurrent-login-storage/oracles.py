#!/usr/bin/env python3
"""Hidden oracle battery for auth-concurrent-login-storage.
Grader-only: never shown to a candidate (listed in provenance.json's
grader_only_files).

Swift has no sibling-file import and `swiftc a.swift b.swift` only allows
top-level statements when the entry file is literally named `main.swift`.
Each variant already ships its own candidate-visible `main.swift` (its own
bundled test), so this harness's own entry point -- `oracle_probe.swift`,
grader-only -- is copied to a scratch file named `main.swift` and compiled
against each variant's `login_registry.swift` in turn, never against that
variant's own `main.swift`. The resulting binary drives a scripted sequence
of begin/commit/retrieve tokens (see oracle_probe.swift's own header for the
token grammar) against one shared LoginRegistry, letting this harness model
two logical callers -- storing two different login kinds -- interleaving
their reads and writes in a fixed, deterministic order. There is no real
concurrency anywhere in this pack: the "interleaving" is just which order
this harness issues begin/commit calls in.

Runs three checks:

    ordinary_login_round_trips -- CONTROL: a single caller stores one
                                 login kind and retrieves it; a kind that
                                 was never stored retrieves as nothing.
                                 Holds in every variant -- none of this
                                 pack's three defects touch a single,
                                 uninterrupted store.
    both_kinds_retrievable_without_interleaving -- two callers each store
                                 a different kind, one fully completing
                                 (begin then commit) before the other
                                 begins. Holds for every variant whose
                                 defect is genuinely interleaving-
                                 dependent (unsynchronized-shared-map,
                                 per-kind-lock-shared-map-race) -- with no
                                 actual interleaving, their stale-snapshot
                                 read-modify-write never has anything
                                 stale to read. Fails only for
                                 mutant-misrouted-storage-key, whose wrong-
                                 key bug fires regardless of ordering.
    both_kinds_retrievable_under_scripted_interleaving -- the two callers'
                                 steps interleaved: both begin (each
                                 capturing whatever it captures) before
                                 either commits. Holds only for
                                 atomic-commit-per-login, whose commit
                                 never depends on a stale snapshot taken
                                 at begin time. Fails for
                                 unsynchronized-shared-map and
                                 per-kind-lock-shared-map-race (the second
                                 commit's stale snapshot overwrites the
                                 first commit's write), and, honestly,
                                 also for mutant-misrouted-storage-key
                                 (whose unrelated wrong-key bug fires here
                                 too, for a different reason than the
                                 other two).

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
RED = "unsynchronized-shared-map"
GREEN = "atomic-commit-per-login"
NEAR_MISS = "per-kind-lock-shared-map-race"
MUTANT = "mutant-misrouted-storage-key"
VARIANTS = [RED, GREEN, NEAR_MISS, MUTANT]

PRIMARY = 0
SECONDARY = 1


def _swiftc(*args: str) -> None:
    result = subprocess.run(["swiftc", *args], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"swiftc failed: {' '.join(args)}\n{result.stdout}\n{result.stderr}")


def build_probe(variant: str, scratch_dir: Path) -> Path:
    """Compile `variant`'s login_registry.swift against the grader-only
    probe (copied to scratch as main.swift, since swiftc only allows
    top-level statements in a file with that exact name)."""
    main_path = scratch_dir / "main.swift"
    shutil.copyfile(PACK_DIR / "oracle_probe.swift", main_path)
    binary_path = scratch_dir / f"probe_{variant}"
    _swiftc(
        str(PACK_DIR / variant / "login_registry.swift"), str(main_path), "-o", str(binary_path)
    )
    return binary_path


def run_probe(binary: Path, tokens: list[str]) -> list[str]:
    result = subprocess.run([str(binary), *tokens], capture_output=True, text=True, check=True)
    raw = result.stdout.strip("\n")
    return raw.split("\n") if raw else []


def retrieved_values(tokens: list[str], lines: list[str]) -> list[str]:
    """The output lines that correspond to `retrieve:` tokens, in order."""
    return [
        line for token, line in zip(tokens, lines, strict=True) if token.startswith("retrieve:")
    ]


# ---------------------------------------------------------------------------
# ordinary_login_round_trips (control)
# ---------------------------------------------------------------------------

CONTROL_TOKENS = [
    f"begin:A:{PRIMARY}:alice-token",
    "commit:A",
    f"retrieve:{PRIMARY}",
    f"retrieve:{SECONDARY}",
]
CONTROL_EXPECTED = ["alice-token", "nil"]


def ordinary_login_round_trips(binaries: dict[str, Path]) -> dict[str, bool]:
    return {
        variant: retrieved_values(CONTROL_TOKENS, run_probe(binary, CONTROL_TOKENS))
        == CONTROL_EXPECTED
        for variant, binary in binaries.items()
    }


# ---------------------------------------------------------------------------
# both_kinds_retrievable_without_interleaving
# ---------------------------------------------------------------------------

SEQUENTIAL_TOKENS = [
    f"begin:A:{PRIMARY}:alice-token",
    "commit:A",
    f"begin:B:{SECONDARY}:bob-token",
    "commit:B",
    f"retrieve:{PRIMARY}",
    f"retrieve:{SECONDARY}",
]
BOTH_RETRIEVABLE_EXPECTED = ["alice-token", "bob-token"]


def both_kinds_retrievable_without_interleaving(binaries: dict[str, Path]) -> dict[str, bool]:
    return {
        variant: retrieved_values(SEQUENTIAL_TOKENS, run_probe(binary, SEQUENTIAL_TOKENS))
        == BOTH_RETRIEVABLE_EXPECTED
        for variant, binary in binaries.items()
    }


# ---------------------------------------------------------------------------
# both_kinds_retrievable_under_scripted_interleaving
# ---------------------------------------------------------------------------

INTERLEAVED_TOKENS = [
    f"begin:A:{PRIMARY}:alice-token",
    f"begin:B:{SECONDARY}:bob-token",
    "commit:B",
    "commit:A",
    f"retrieve:{PRIMARY}",
    f"retrieve:{SECONDARY}",
]


def both_kinds_retrievable_under_scripted_interleaving(
    binaries: dict[str, Path],
) -> dict[str, bool]:
    return {
        variant: retrieved_values(INTERLEAVED_TOKENS, run_probe(binary, INTERLEAVED_TOKENS))
        == BOTH_RETRIEVABLE_EXPECTED
        for variant, binary in binaries.items()
    }


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="login-registry-oracles-") as tmp:
        scratch_dir = Path(tmp)
        binaries = {variant: build_probe(variant, scratch_dir) for variant in VARIANTS}

        control_results = ordinary_login_round_trips(binaries)
        sequential_results = both_kinds_retrievable_without_interleaving(binaries)
        interleaved_results = both_kinds_retrievable_under_scripted_interleaving(binaries)

        print("=== ordinary_login_round_trips (control) ===")
        for name, ok in control_results.items():
            print(f"  {name}: {'OK' if ok else 'FAIL'}")
        print("=== both_kinds_retrievable_without_interleaving ===")
        for name, ok in sequential_results.items():
            print(f"  {name}: {'OK' if ok else 'FAIL'}")
        print("=== both_kinds_retrievable_under_scripted_interleaving ===")
        for name, ok in interleaved_results.items():
            print(f"  {name}: {'OK' if ok else 'FAIL'}")

        failures: list[str] = []

        for name in VARIANTS:
            if control_results.get(name) is not True:
                failures.append(
                    f"{name}: ordinary_login_round_trips must hold, got {control_results.get(name)}"
                )

        expected_sequential = {RED: True, GREEN: True, NEAR_MISS: True, MUTANT: False}
        for name, expected in expected_sequential.items():
            if sequential_results.get(name) != expected:
                failures.append(
                    f"{name}: expected both_kinds_retrievable_without_interleaving={expected}, "
                    f"got {sequential_results.get(name)}"
                )

        expected_interleaved = {RED: False, GREEN: True, NEAR_MISS: False, MUTANT: False}
        for name, expected in expected_interleaved.items():
            if interleaved_results.get(name) != expected:
                failures.append(
                    f"{name}: expected both_kinds_retrievable_under_scripted_interleaving={expected}, "
                    f"got {interleaved_results.get(name)}"
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
