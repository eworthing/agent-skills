#!/usr/bin/env python3
"""Hidden oracle battery for auth-challenge-preservation. Grader-only:
never shown to a candidate (listed in provenance.json's grader_only_files).

Same probe pattern as streaming-decoder-error-state's oracles.py:
`oracle_probe.swift` (grader-only) is copied to a scratch file literally
named `main.swift` and compiled against each variant's own
`challenge_chain.swift` in turn. The resulting binary takes one of
`single` / `chain` / `success` and prints the real `AuthOutcome` a live
`authenticateChain` call produces.

Runs four checks:

    matching_credential_authenticates -- CONTROL: the success path (a
                                 correct credential against a two-
                                 authenticator chain) is untouched by any
                                 of this pack's defects. Holds everywhere.
    single_authenticator_rejection_carries_its_challenge -- one
                                 authenticator, wrong credential: the
                                 rejection must carry exactly that
                                 authenticator's own challenge (scheme and
                                 parameter both correct). Fails for the RED
                                 variant (carries no challenge at all).
                                 Also fails for the mutant here already --
                                 its corruption is not chain-specific.
    chained_rejection_preserves_every_challenge_count -- two
                                 authenticators, wrong credential: the
                                 rejection's challenge COUNT must equal
                                 the number of authenticators tried (2).
                                 THE NEAR-MISS KILLER: fails only for the
                                 near-miss, which keeps just the most
                                 recently tried authenticator's challenge
                                 and silently drops every earlier one. The
                                 mutant keeps the right count (its defect
                                 is corrupted values, not a dropped
                                 entry), so this check alone does not
                                 accuse it.
    chained_rejection_challenge_values_uncorrupted -- two authenticators,
                                 wrong credential: every challenge that IS
                                 present in the rejection must be a real,
                                 unmodified authenticator challenge (its
                                 scheme non-empty and matching one of the
                                 authenticators actually tried). THE
                                 MUTANT KILLER: fails only for the mutant,
                                 whose recorded challenges are present and
                                 correctly counted, but each one has had
                                 its scheme name dropped. The near-miss's
                                 one surviving challenge is a real,
                                 uncorrupted value -- it just isn't all of
                                 them -- so this check alone does not
                                 accuse it. RED's True here is declared
                                 vacuous, not a verified pass: `all()` over
                                 zero challenges is trivially True, and
                                 RED already fails the other two checks.

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
    "unchallenged-rejection",
    "chain-preserves-every-challenge",
    "near-miss-last-challenge-only",
    "mutant-scheme-dropped-from-challenge",
]

REAL_CHALLENGES = {("alpha", "realm=vault-a"), ("beta", "realm=vault-b")}


def _swiftc(*args: str) -> None:
    result = subprocess.run(["swiftc", *args], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"swiftc failed: {' '.join(args)}\n{result.stdout}\n{result.stderr}")


def build_probe(variant: str, scratch_dir: Path) -> Path:
    main_path = scratch_dir / "main.swift"
    shutil.copyfile(PACK_DIR / "oracle_probe.swift", main_path)
    binary_path = scratch_dir / f"probe_{variant}"
    _swiftc(
        str(PACK_DIR / variant / "challenge_chain.swift"), str(main_path), "-o", str(binary_path)
    )
    return binary_path


def run_probe(binary: Path, mode: str) -> tuple[str | None, list[tuple[str, str]]]:
    """Returns (authenticated_identity_or_None, [(scheme, parameter), ...])."""
    result = subprocess.run([str(binary), mode], capture_output=True, text=True, check=True)
    lines = result.stdout.strip().splitlines()
    if lines[0].startswith("authenticated:"):
        return lines[0].removeprefix("authenticated:"), []
    count = int(lines[0].removeprefix("rejected:"))
    challenges = []
    for line in lines[1 : 1 + count]:
        scheme, _, parameter = line.partition("|")
        challenges.append((scheme, parameter))
    return None, challenges


def matching_credential_authenticates(binaries: dict[str, Path]) -> dict[str, str | None]:
    return {variant: run_probe(binary, "success")[0] for variant, binary in binaries.items()}


def single_authenticator_rejection_carries_its_challenge(
    binaries: dict[str, Path],
) -> dict[str, bool]:
    results = {}
    for variant, binary in binaries.items():
        _, challenges = run_probe(binary, "single")
        results[variant] = challenges == [("alpha", "realm=vault-a")]
    return results


def chained_rejection_preserves_every_challenge_count(binaries: dict[str, Path]) -> dict[str, bool]:
    results = {}
    for variant, binary in binaries.items():
        _, challenges = run_probe(binary, "chain")
        results[variant] = len(challenges) == 2
    return results


def chained_rejection_challenge_values_uncorrupted(
    binaries: dict[str, Path],
) -> dict[str, tuple[bool, int]]:
    """Returns (uncorrupted, challenge_count) per variant. `all()` over an
    empty list is vacuously True in Python -- a variant with zero
    challenges (unchallenged-rejection) passes this check by having
    nothing to corrupt, not by having verified anything. The count is
    returned alongside the bool so that vacuous case is declared where a
    grader reads it, not left as a bare pass indistinguishable from a
    real one.
    """
    results = {}
    for variant, binary in binaries.items():
        _, challenges = run_probe(binary, "chain")
        results[variant] = (all(c in REAL_CHALLENGES for c in challenges), len(challenges))
    return results


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="auth-challenge-oracles-") as tmp:
        scratch_dir = Path(tmp)
        binaries = {variant: build_probe(variant, scratch_dir) for variant in VARIANTS}

        success_results = matching_credential_authenticates(binaries)
        single_results = single_authenticator_rejection_carries_its_challenge(binaries)
        count_results = chained_rejection_preserves_every_challenge_count(binaries)
        value_results = chained_rejection_challenge_values_uncorrupted(binaries)

        print("=== matching_credential_authenticates (control) ===")
        for name, identity in success_results.items():
            print(f"  {name}: {identity}")
        print("=== single_authenticator_rejection_carries_its_challenge ===")
        for name, ok in single_results.items():
            print(f"  {name}: {ok}")
        print("=== chained_rejection_preserves_every_challenge_count ===")
        for name, ok in count_results.items():
            print(f"  {name}: {ok}")
        print("=== chained_rejection_challenge_values_uncorrupted ===")
        for name, (ok, count) in value_results.items():
            note = " (vacuous -- zero challenges to corrupt)" if count == 0 else ""
            print(f"  {name}: {ok}{note}")

        failures = []

        for name in VARIANTS:
            if success_results.get(name) != "alpha-user":
                failures.append(
                    f"{name}: matching_credential_authenticates must hold, "
                    f"got {success_results.get(name)!r}"
                )

        expected_single = {
            "unchallenged-rejection": False,
            "chain-preserves-every-challenge": True,
            "near-miss-last-challenge-only": True,
            "mutant-scheme-dropped-from-challenge": False,
        }
        for name, expected in expected_single.items():
            if single_results.get(name) != expected:
                failures.append(
                    f"{name}: expected single_authenticator_rejection_carries_its_challenge="
                    f"{expected}, got {single_results.get(name)}"
                )

        expected_count = {
            "unchallenged-rejection": False,
            "chain-preserves-every-challenge": True,
            "near-miss-last-challenge-only": False,
            "mutant-scheme-dropped-from-challenge": True,
        }
        for name, expected in expected_count.items():
            if count_results.get(name) != expected:
                failures.append(
                    f"{name}: expected chained_rejection_preserves_every_challenge_count="
                    f"{expected}, got {count_results.get(name)}"
                )

        # unchallenged-rejection's True is declared vacuous above (zero
        # challenges to corrupt), not a verified pass -- see the function
        # docstring. near-miss-last-challenge-only's True is real: the one
        # challenge it kept is an uncorrupted value.
        expected_values = {
            "unchallenged-rejection": True,
            "chain-preserves-every-challenge": True,
            "near-miss-last-challenge-only": True,
            "mutant-scheme-dropped-from-challenge": False,
        }
        for name, expected in expected_values.items():
            observed_ok, _count = value_results.get(name, (None, None))
            if observed_ok != expected:
                failures.append(
                    f"{name}: expected chained_rejection_challenge_values_uncorrupted="
                    f"{expected}, got {observed_ok}"
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
