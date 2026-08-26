#!/usr/bin/env python3
"""Hidden oracle battery for auth-empty-password-policy-restraint.
Grader-only: never shown to a candidate (listed in provenance.json's
grader_only_files).

Swift has no sibling-file import and `swiftc a.swift b.swift` only allows
top-level statements when the entry file is literally named `main.swift`.
Each variant already ships its own candidate-visible `main.swift` (its own
bundled test), so this harness's own entry point -- `oracle_probe.swift`,
grader-only -- is copied to a scratch file named `main.swift` and compiled
against each variant's `credential_authenticator.swift` in turn, never
against that variant's own `main.swift`. The resulting binary is a tiny
CLI (`probe none` / `probe some <username> <password>`) that prints the
authenticated username or "nil", against a fixed two-account directory
(kiosk: "", morgan: "hunter2") built into the probe itself.

Runs two checks:

    ordinary_account_and_missing_credential_behavior -- CONTROL: an
                                 ordinary account's correct password
                                 authenticates, its wrong password does
                                 not, and a request carrying no
                                 credential at all never authenticates.
                                 Holds in both variants -- universal-
                                 empty-rejection's one behavioral
                                 difference from the accepted variant is
                                 scoped to an empty *supplied* password
                                 specifically; it does not touch an
                                 ordinary non-empty password or a
                                 missing credential at all.
    kiosk_empty_password_authenticates -- the pack's one measured fact:
                                 an account deliberately provisioned
                                 with no password authenticates when an
                                 empty password is supplied for it.
                                 Holds for authenticator-owned-empty-
                                 acceptance. Fails for universal-empty-
                                 rejection, whose blanket empty-password
                                 guard runs ahead of any per-account
                                 check and rejects this legitimate
                                 account along with everyone else's empty
                                 guesses.

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
RED = "universal-empty-rejection"
GREEN = "authenticator-owned-empty-acceptance"
VARIANTS = [RED, GREEN]


def _swiftc(*args: str) -> None:
    result = subprocess.run(["swiftc", *args], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"swiftc failed: {' '.join(args)}\n{result.stdout}\n{result.stderr}")


def build_probe(variant: str, scratch_dir: Path) -> Path:
    """Compile `variant`'s credential_authenticator.swift against the
    grader-only probe (copied to scratch as main.swift, since swiftc only
    allows top-level statements in a file with that exact name)."""
    main_path = scratch_dir / "main.swift"
    shutil.copyfile(PACK_DIR / "oracle_probe.swift", main_path)
    binary_path = scratch_dir / f"probe_{variant}"
    _swiftc(
        str(PACK_DIR / variant / "credential_authenticator.swift"),
        str(main_path),
        "-o",
        str(binary_path),
    )
    return binary_path


def probe_none(binary: Path) -> str:
    result = subprocess.run([str(binary), "none"], capture_output=True, text=True, check=True)
    return result.stdout.strip()


def probe_some(binary: Path, username: str, password: str) -> str:
    result = subprocess.run(
        [str(binary), "some", username, password], capture_output=True, text=True, check=True
    )
    return result.stdout.strip()


def ordinary_account_and_missing_credential_behavior(binaries: dict[str, Path]) -> dict[str, bool]:
    results: dict[str, bool] = {}
    for variant, binary in binaries.items():
        correct = probe_some(binary, "morgan", "hunter2") == "morgan"
        wrong = probe_some(binary, "morgan", "wrong") == "nil"
        missing = probe_none(binary) == "nil"
        results[variant] = correct and wrong and missing
    return results


def kiosk_empty_password_authenticates(binaries: dict[str, Path]) -> dict[str, bool]:
    return {
        variant: probe_some(binary, "kiosk", "") == "kiosk" for variant, binary in binaries.items()
    }


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="credential-authenticator-oracles-") as tmp:
        scratch_dir = Path(tmp)
        binaries = {variant: build_probe(variant, scratch_dir) for variant in VARIANTS}

        control_results = ordinary_account_and_missing_credential_behavior(binaries)
        kiosk_results = kiosk_empty_password_authenticates(binaries)

        print("=== ordinary_account_and_missing_credential_behavior (control) ===")
        for name, ok in control_results.items():
            print(f"  {name}: {'OK' if ok else 'FAIL'}")
        print("=== kiosk_empty_password_authenticates ===")
        for name, ok in kiosk_results.items():
            print(f"  {name}: {'authenticates' if ok else 'REJECTED'}")

        failures: list[str] = []

        for name in VARIANTS:
            if control_results.get(name) is not True:
                failures.append(
                    "ordinary_account_and_missing_credential_behavior must hold for "
                    f"{name}, got {control_results.get(name)}"
                )

        expected_kiosk = {RED: False, GREEN: True}
        for name, expected in expected_kiosk.items():
            if kiosk_results.get(name) != expected:
                failures.append(
                    f"{name}: expected kiosk_empty_password_authenticates={expected}, "
                    f"got {kiosk_results.get(name)}"
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
