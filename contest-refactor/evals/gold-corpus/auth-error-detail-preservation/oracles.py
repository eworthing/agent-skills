#!/usr/bin/env python3
"""Hidden oracle battery for auth-error-detail-preservation. Grader-only:
never shown to a candidate (listed in provenance.json's grader_only_files).

Same probe pattern as the other Swift packs in this corpus:
`oracle_probe.swift` (grader-only) is copied to a scratch file literally
named `main.swift` and compiled against each variant's own
`error_detail.swift` in turn. The resulting binary takes `fail` or
`succeed` and prints what a caller downstream of `withErrorMiddleware`
actually recovers from a real thrown-and-caught error, field by field --
not what the middleware's own bundled suite asserts.

Runs five checks against the `fail` scenario (an original failure with a
known reason, challenge, identifier, and source), plus one control:

    operation_succeeds_without_raising -- CONTROL: the success path (the
                                 guarded operation returns normally) is
                                 untouched by any of this pack's defects.
                                 Holds everywhere.
    reason_and_challenge_survive     -- the two pieces a human reads in a
                                 log. Fails only for the RED variant,
                                 which discards everything.
    identifier_matches_original      -- the recovered identifier equals
                                 the original failure's exact identifier.
                                 Fails for RED (missing), the near-miss
                                 (dropped), AND the mutant (present but
                                 wrong) -- three different reasons to fail
                                 the same strict check.
    identifier_is_present            -- the recovered identifier is
                                 non-nil, regardless of whether it is
                                 correct. THE NEAR-MISS-VS-MUTANT
                                 DISCRIMINATOR: combined with
                                 identifier_matches_original, this
                                 distinguishes "dropped" (near-miss: both
                                 fail) from "present but wrong" (mutant:
                                 this passes, the strict check does not).
    source_location_matches_original -- the recovered source location
                                 equals the original. Fails for RED and
                                 the near-miss (both drop it); holds for
                                 the mutant, whose only corruption is the
                                 identifier.

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
    "generic-error-on-catch",
    "middleware-forwards-original-failure",
    "near-miss-reason-and-challenge-only",
    "mutant-identifier-from-wrapper",
]

ORIGINAL = {
    "reason": "no credential was supplied",
    "challenge": "vault-token",
    "identifier": "auth.credential.missing",
    "source": "vault_gate.swift:42",
}


def _swiftc(*args: str) -> None:
    result = subprocess.run(["swiftc", *args], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"swiftc failed: {' '.join(args)}\n{result.stdout}\n{result.stderr}")


def build_probe(variant: str, scratch_dir: Path) -> Path:
    main_path = scratch_dir / "main.swift"
    shutil.copyfile(PACK_DIR / "oracle_probe.swift", main_path)
    binary_path = scratch_dir / f"probe_{variant}"
    _swiftc(str(PACK_DIR / variant / "error_detail.swift"), str(main_path), "-o", str(binary_path))
    return binary_path


def run_probe(binary: Path, mode: str) -> dict[str, str]:
    result = subprocess.run([str(binary), mode], capture_output=True, text=True, check=True)
    fields: dict[str, str] = {}
    for line in result.stdout.strip().splitlines():
        key, _, value = line.partition(":")
        fields[key] = value
    return fields


def recovered_fields(binaries: dict[str, Path]) -> dict[str, dict[str, str]]:
    return {variant: run_probe(binary, "fail") for variant, binary in binaries.items()}


def operation_succeeds_without_raising(binaries: dict[str, Path]) -> dict[str, str]:
    return {
        variant: run_probe(binary, "succeed").get("result", "")
        for variant, binary in binaries.items()
    }


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="auth-error-detail-oracles-") as tmp:
        scratch_dir = Path(tmp)
        binaries = {variant: build_probe(variant, scratch_dir) for variant in VARIANTS}

        fields = recovered_fields(binaries)
        success_results = operation_succeeds_without_raising(binaries)

        reason_and_challenge = {
            v: f["reason"] == ORIGINAL["reason"] and f["challenge"] == ORIGINAL["challenge"]
            for v, f in fields.items()
        }
        identifier_matches = {
            v: f["identifier"] == ORIGINAL["identifier"] for v, f in fields.items()
        }
        identifier_present = {v: f["identifier"] != "MISSING" for v, f in fields.items()}
        source_matches = {v: f["source"] == ORIGINAL["source"] for v, f in fields.items()}

        print("=== operation_succeeds_without_raising (control) ===")
        for name, result in success_results.items():
            print(f"  {name}: {result}")
        print("=== recovered fields (fail scenario) ===")
        for name, f in fields.items():
            print(f"  {name}: {f}")
        print("=== reason_and_challenge_survive ===")
        for name, ok in reason_and_challenge.items():
            print(f"  {name}: {ok}")
        print("=== identifier_matches_original ===")
        for name, ok in identifier_matches.items():
            print(f"  {name}: {ok}")
        print("=== identifier_is_present ===")
        for name, ok in identifier_present.items():
            print(f"  {name}: {ok}")
        print("=== source_location_matches_original ===")
        for name, ok in source_matches.items():
            print(f"  {name}: {ok}")

        failures = []

        for name in VARIANTS:
            if success_results.get(name) != "ok":
                failures.append(
                    f"{name}: operation_succeeds_without_raising must hold, got {success_results.get(name)!r}"
                )

        expected_reason_and_challenge = {
            "generic-error-on-catch": False,
            "middleware-forwards-original-failure": True,
            "near-miss-reason-and-challenge-only": True,
            "mutant-identifier-from-wrapper": True,
        }
        for name, expected in expected_reason_and_challenge.items():
            if reason_and_challenge.get(name) != expected:
                failures.append(
                    f"{name}: expected reason_and_challenge_survive={expected}, "
                    f"got {reason_and_challenge.get(name)}"
                )

        expected_identifier_matches = {
            "generic-error-on-catch": False,
            "middleware-forwards-original-failure": True,
            "near-miss-reason-and-challenge-only": False,
            "mutant-identifier-from-wrapper": False,
        }
        for name, expected in expected_identifier_matches.items():
            if identifier_matches.get(name) != expected:
                failures.append(
                    f"{name}: expected identifier_matches_original={expected}, "
                    f"got {identifier_matches.get(name)}"
                )

        expected_identifier_present = {
            "generic-error-on-catch": False,
            "middleware-forwards-original-failure": True,
            "near-miss-reason-and-challenge-only": False,
            "mutant-identifier-from-wrapper": True,
        }
        for name, expected in expected_identifier_present.items():
            if identifier_present.get(name) != expected:
                failures.append(
                    f"{name}: expected identifier_is_present={expected}, "
                    f"got {identifier_present.get(name)}"
                )

        expected_source_matches = {
            "generic-error-on-catch": False,
            "middleware-forwards-original-failure": True,
            "near-miss-reason-and-challenge-only": False,
            "mutant-identifier-from-wrapper": True,
        }
        for name, expected in expected_source_matches.items():
            if source_matches.get(name) != expected:
                failures.append(
                    f"{name}: expected source_location_matches_original={expected}, "
                    f"got {source_matches.get(name)}"
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
