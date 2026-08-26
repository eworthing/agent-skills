#!/usr/bin/env python3
"""Hidden oracle battery for auth-identity-probe-equalization. Grader-only:
never shown to a candidate (listed in provenance.json's
grader_only_files).

Imports each variant's `identity_verification.py` fresh by file path
(every variant reuses the same module name, so plain
`import identity_verification` would collide) and runs the three checks
declared in provenance.json's `hidden_oracles`:

    known_identity_correct_credential_authenticates -- baseline: a real,
                                        correctly set credential
                                        authenticates through both entry
                                        points, and a wrong one does not.
                                        Holds in all four variants -- none
                                        of this pack's defects touch the
                                        known-identity path.
    equalization_work_matches       -- for each entry point, the work
                                        performed verifying an unknown
                                        identity must equal the work
                                        performed verifying a known
                                        identity with a wrong credential.
                                        Modeled as an exact integer work
                                        count rather than wall-clock time
                                        -- deterministic and immune to
                                        machine speed, though the channel
                                        it stands in for in the real world
                                        is elapsed time. Fails in
                                        dual-entry-inconsistent-
                                        equalization (one of its two entry
                                        points forgets to equalize) and in
                                        near-miss-guard-skips-equalization
                                        (a caller-side guard skips the
                                        correctly-written equalizing
                                        helper entirely for an unknown
                                        identity, on both entry points).
    unknown_identity_never_authenticates -- an identity that does not
                                        resolve to any account must never
                                        authenticate, regardless of what
                                        credential is supplied. Fails in
                                        mutant-unknown-identity-verifies,
                                        whose equalizing helper returns
                                        True instead of False once it has
                                        done the dummy work.

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
    "dual-entry-inconsistent-equalization",
    "unified-equalized-verification",
    "near-miss-guard-skips-equalization",
    "mutant-unknown-identity-verifies",
]
ENTRY_POINTS = ("sign_in", "reverify_for_sensitive_action")


def load_variant(name: str) -> types.ModuleType:
    path = PACK_DIR / name / "identity_verification.py"
    spec = importlib.util.spec_from_file_location(
        f"_gc_identity_verification_{name.replace('-', '_')}", path
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _directory(mod: types.ModuleType) -> dict:
    account = mod.Account("known-identity")
    account.set_credential("correct-credential")
    return {"known-identity": account}


def known_identity_correct_credential_authenticates(mod: types.ModuleType) -> bool:
    directory = _directory(mod)
    ok = True
    for entry_name in ENTRY_POINTS:
        entry = getattr(mod, entry_name)
        ok = ok and entry("known-identity", "correct-credential", directory) is True
        ok = ok and entry("known-identity", "wrong-credential", directory) is False
    return ok


def equalization_work_matches(mod: types.ModuleType) -> bool:
    directory = _directory(mod)
    ok = True
    for entry_name in ENTRY_POINTS:
        entry = getattr(mod, entry_name)
        mod.reset_work_counter()
        entry("nonexistent-identity", "any-guess", directory)
        unknown_cost = mod.work_performed()
        mod.reset_work_counter()
        entry("known-identity", "definitely-wrong", directory)
        known_wrong_cost = mod.work_performed()
        ok = ok and unknown_cost == known_wrong_cost
    return ok


def unknown_identity_never_authenticates(mod: types.ModuleType) -> bool:
    directory = _directory(mod)
    ok = True
    for entry_name in ENTRY_POINTS:
        entry = getattr(mod, entry_name)
        ok = ok and entry("nonexistent-identity", "any-guess", directory) is False
    return ok


CHECKS = {
    "known_identity_correct_credential_authenticates": known_identity_correct_credential_authenticates,
    "equalization_work_matches": equalization_work_matches,
    "unknown_identity_never_authenticates": unknown_identity_never_authenticates,
}

EXPECTATIONS = {
    "known_identity_correct_credential_authenticates": dict.fromkeys(VARIANTS, True),
    "equalization_work_matches": {
        "dual-entry-inconsistent-equalization": False,
        "unified-equalized-verification": True,
        "near-miss-guard-skips-equalization": False,
        "mutant-unknown-identity-verifies": True,
    },
    "unknown_identity_never_authenticates": {
        "dual-entry-inconsistent-equalization": True,
        "unified-equalized-verification": True,
        "near-miss-guard-skips-equalization": True,
        "mutant-unknown-identity-verifies": False,
    },
}


def main() -> int:
    modules = {v: load_variant(v) for v in VARIANTS}
    results = {name: {v: fn(mod) for v, mod in modules.items()} for name, fn in CHECKS.items()}

    for name, per_variant in results.items():
        print(f"=== {name} ===")
        for v, ok in per_variant.items():
            print(f"  {v}: {'OK' if ok else 'FAIL'}")

    failures = []
    for name, per_variant in results.items():
        for v, expected in EXPECTATIONS[name].items():
            if per_variant.get(v) != expected:
                failures.append(f"{name}/{v}: expected {expected}, got {per_variant.get(v)}")

    if failures:
        print("\nFAIL:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("\nOK: observed matrix matches declared expectations.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
