#!/usr/bin/env python3
"""Hidden oracle battery for auth-session-carryover. Grader-only: never
shown to a candidate (listed in provenance.json's grader_only_files).

Loads each variant's `sign_in.py` fresh by module name -- every variant
reuses the same module names (`session`, `principal`, `sign_in`), so a
stable sys.path + sys.modules dance is needed to avoid one variant's
modules leaking into the next -- and runs the four oracles declared in
provenance.json's `hidden_oracles`:

    cross_principal_data_is_not_carried_over    -- signing in as a second
                                                    principal over a first
                                                    principal's session must
                                                    not leave the first
                                                    principal's data
                                                    reachable. Fails in
                                                    no-rekey-sign-in (never
                                                    discards at all) and
                                                    near-miss-always-rekey
                                                    (rotates but never
                                                    discards).
    anonymous_data_is_retained_on_first_sign_in -- THE POSITIVE CONTRACT.
                                                    Signing in from a
                                                    session with no prior
                                                    principal must retain
                                                    whatever that session
                                                    already held. Never
                                                    fails -- pins the
                                                    opposite collapse
                                                    (always-discard) as
                                                    equally wrong, even
                                                    though none of the four
                                                    variants here take it.
    token_changes_when_it_must                  -- the session token must
                                                    actually change on a
                                                    first sign-in and on a
                                                    cross-principal sign-in.
                                                    Fails only in
                                                    no-rekey-sign-in, which
                                                    never rotates or
                                                    discards at all.
    credential_change_invalidates_session       -- THE MUTANT
                                                    DISCRIMINATOR. The same
                                                    principal, with a
                                                    credential stamp that no
                                                    longer matches what the
                                                    session has on file,
                                                    must have their old
                                                    session data discarded.
                                                    Fails in
                                                    no-rekey-sign-in,
                                                    near-miss-always-rekey,
                                                    AND
                                                    mutant-identity-only-check
                                                    (which only compares
                                                    principal identity, never
                                                    the credential stamp).
                                                    mutant-always-discard
                                                    passes this one -- it
                                                    discards unconditionally,
                                                    so a changed stamp is
                                                    caught along with
                                                    everything else.

    anonymous_data_is_retained_on_first_sign_in above is the mirror-image
    discriminator: it fails in mutant-always-discard, which discards on
    every sign-in including the very first one, clearing an anonymous
    session's data that the contract requires be retained. Together the
    two mutants are the pack's whole point in one pair: near-miss-always-rekey
    passes retention and fails carryover/credential-change; mutant-always-discard
    passes carryover/credential-change and fails retention. Only the real
    two-operation choice satisfies both.

Run: python3 oracles.py
Exit 0 iff every observed result matches its declared expectation.
"""

from __future__ import annotations

import importlib
import sys
import types
from pathlib import Path

PACK_DIR = Path(__file__).resolve().parent
VARIANTS = [
    "no-rekey-sign-in",
    "rekey-or-discard-sign-in",
    "near-miss-always-rekey",
    "mutant-identity-only-check",
    "mutant-always-discard",
]
_SIBLING_MODULES = ["session", "principal", "sign_in"]


def load_variant(name: str) -> types.SimpleNamespace:
    """Import one variant's three sibling modules fresh, in isolation."""
    variant_dir = PACK_DIR / name
    for modname in _SIBLING_MODULES:
        sys.modules.pop(modname, None)
    sys.path.insert(0, str(variant_dir))
    try:
        modules = {modname: importlib.import_module(modname) for modname in _SIBLING_MODULES}
    finally:
        sys.path.remove(str(variant_dir))
        for modname in _SIBLING_MODULES:
            sys.modules.pop(modname, None)
    return types.SimpleNamespace(**modules)


def _alice(mods: types.SimpleNamespace, stamp: str = "stamp-alice-1"):
    return mods.principal.Principal("alice", stamp)


def _bob(mods: types.SimpleNamespace):
    return mods.principal.Principal("bob", "stamp-bob-1")


def cross_principal_data_is_not_carried_over(
    variants: dict[str, types.SimpleNamespace],
) -> dict[str, bool]:
    results = {}
    for name, mods in variants.items():
        session = mods.session.Session()
        mods.sign_in.sign_in(session, _alice(mods))
        session.data["cart"] = ["item"]
        mods.sign_in.sign_in(session, _bob(mods))
        results[name] = "cart" not in session.data
    return results


def anonymous_data_is_retained_on_first_sign_in(
    variants: dict[str, types.SimpleNamespace],
) -> dict[str, bool]:
    results = {}
    for name, mods in variants.items():
        session = mods.session.Session()
        session.data["cart"] = ["item"]
        mods.sign_in.sign_in(session, _alice(mods))
        results[name] = session.data.get("cart") == ["item"]
    return results


def token_changes_when_it_must(variants: dict[str, types.SimpleNamespace]) -> dict[str, bool]:
    results = {}
    for name, mods in variants.items():
        session = mods.session.Session()
        mods.sign_in.sign_in(session, _alice(mods))
        first_ok = session.token is not None
        token_after_first = session.token
        mods.sign_in.sign_in(session, _bob(mods))
        cross_ok = session.token != token_after_first
        results[name] = first_ok and cross_ok
    return results


def credential_change_invalidates_session(
    variants: dict[str, types.SimpleNamespace],
) -> dict[str, bool]:
    results = {}
    for name, mods in variants.items():
        session = mods.session.Session()
        mods.sign_in.sign_in(session, _alice(mods))
        session.data["cart"] = ["item"]
        alice_after_password_change = _alice(mods, stamp="stamp-alice-2")
        mods.sign_in.sign_in(session, alice_after_password_change)
        results[name] = "cart" not in session.data
    return results


def main() -> int:
    variants = {name: load_variant(name) for name in VARIANTS}

    cross = cross_principal_data_is_not_carried_over(variants)
    retained = anonymous_data_is_retained_on_first_sign_in(variants)
    token_changes = token_changes_when_it_must(variants)
    credential_change = credential_change_invalidates_session(variants)

    print("=== cross_principal_data_is_not_carried_over ===")
    for name, ok in cross.items():
        print(f"  {name}: {'not carried over' if ok else 'CARRIED OVER'}")
    print("=== anonymous_data_is_retained_on_first_sign_in ===")
    for name, ok in retained.items():
        print(f"  {name}: {'retained' if ok else 'LOST'}")
    print("=== token_changes_when_it_must ===")
    for name, ok in token_changes.items():
        print(f"  {name}: {'changes' if ok else 'DOES NOT CHANGE'}")
    print("=== credential_change_invalidates_session ===")
    for name, ok in credential_change.items():
        print(f"  {name}: {'invalidated' if ok else 'SESSION SURVIVED'}")

    failures = []

    expected_cross = {
        "no-rekey-sign-in": False,
        "rekey-or-discard-sign-in": True,
        "near-miss-always-rekey": False,
        "mutant-identity-only-check": True,
        "mutant-always-discard": True,
    }
    for name, expected in expected_cross.items():
        if cross.get(name) != expected:
            failures.append(
                f"{name}: expected cross_principal_data_is_not_carried_over={expected}, "
                f"got {cross.get(name)}"
            )

    expected_retained = dict.fromkeys(VARIANTS, True)
    expected_retained["mutant-always-discard"] = False
    for name, expected in expected_retained.items():
        if retained.get(name) != expected:
            failures.append(
                f"{name}: expected anonymous_data_is_retained_on_first_sign_in={expected}, "
                f"got {retained.get(name)}"
            )

    expected_token = {
        "no-rekey-sign-in": False,
        "rekey-or-discard-sign-in": True,
        "near-miss-always-rekey": True,
        "mutant-identity-only-check": True,
        "mutant-always-discard": True,
    }
    for name, expected in expected_token.items():
        if token_changes.get(name) != expected:
            failures.append(
                f"{name}: expected token_changes_when_it_must={expected}, "
                f"got {token_changes.get(name)}"
            )

    expected_credential_change = {
        "no-rekey-sign-in": False,
        "rekey-or-discard-sign-in": True,
        "near-miss-always-rekey": False,
        "mutant-identity-only-check": False,
        "mutant-always-discard": True,
    }
    for name, expected in expected_credential_change.items():
        if credential_change.get(name) != expected:
            failures.append(
                f"{name}: expected credential_change_invalidates_session={expected}, "
                f"got {credential_change.get(name)}"
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
