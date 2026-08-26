#!/usr/bin/env python3
"""Hidden oracle battery for auth-login-redirect-target. Grader-only: never
shown to a candidate (listed in provenance.json's grader_only_files).

Loads each variant's `redirect_target.py` fresh by module name -- every
variant reuses the same module names (`request`, `gate`, `gate_scan`,
`redirect_target`), so a stable sys.path + sys.modules dance is needed to
avoid one variant's modules leaking into the next -- and runs the four
oracles declared in provenance.json's `hidden_oracles`:

    same_host_target_is_relative_with_query   -- a hostless (same-service)
                                                  sign-in endpoint must get
                                                  a relative return target,
                                                  query string included.
                                                  Fails only in
                                                  bare-relative-target,
                                                  which drops the query
                                                  string.
    cross_host_entry_gets_absolute_target     -- a sign-in endpoint on a
                                                  different host must get
                                                  the request's full
                                                  absolute URL as the
                                                  return target, not a bare
                                                  path. THE NEAR-MISS
                                                  DISCRIMINATOR: fails in
                                                  bare-relative-target and
                                                  near-miss-always-relative,
                                                  which are indistinguishable
                                                  from the correct behavior
                                                  in every same-host
                                                  scenario.
    spoofed_forwarded_host_never_leaks_into_target -- THE MUTANT
                                                  DISCRIMINATOR. A request
                                                  whose client-claimed
                                                  forwarded host doesn't
                                                  match the sign-in
                                                  endpoint's own (real)
                                                  host must never produce a
                                                  return target pointing at
                                                  that claimed host. Fails
                                                  only in
                                                  mutant-trusts-forwarded-host,
                                                  which builds its notion of
                                                  "the current URL" from the
                                                  unvalidated forwarded-host
                                                  claim instead of the
                                                  request's real host.
    entry_endpoint_reflectable_without_reparsing -- gate_scan.py's reading
                                                  of the entry endpoint and
                                                  return-parameter name
                                                  staple, off a view wrapped
                                                  by gate.require_sign_in,
                                                  must match what the
                                                  decorator was actually
                                                  called with. THE SECOND
                                                  MUTANT DISCRIMINATOR: fails
                                                  in mutant-unstapled-view,
                                                  whose gate.py never staples
                                                  entry_url/return_param_name
                                                  onto the wrapper at all --
                                                  its request.py and
                                                  redirect_target.py are
                                                  otherwise byte-identical to
                                                  scoped-absolute-target,
                                                  demonstrating that deleting
                                                  the "unused" staple really
                                                  does break gate_scan.py's
                                                  reflective read of it,
                                                  rather than merely being
                                                  asserted to.

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
    "bare-relative-target",
    "scoped-absolute-target",
    "near-miss-always-relative",
    "mutant-trusts-forwarded-host",
    "mutant-unstapled-view",
]
_SIBLING_MODULES = ["request", "gate_scan", "redirect_target", "gate"]


def load_variant(name: str) -> types.SimpleNamespace:
    """Import one variant's four sibling modules fresh, in isolation."""
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


def same_host_target_is_relative_with_query(
    variants: dict[str, types.SimpleNamespace],
) -> dict[str, bool]:
    results = {}
    for name, mods in variants.items():
        request = mods.request.Request(
            scheme="https", host="app.example", path="/private/report", query="year=2026"
        )
        target = mods.redirect_target.redirect_target_for(request, "/sign-in/")
        results[name] = target == "/private/report?year=2026"
    return results


def cross_host_entry_gets_absolute_target(
    variants: dict[str, types.SimpleNamespace],
) -> dict[str, bool]:
    results = {}
    for name, mods in variants.items():
        request = mods.request.Request(
            scheme="https", host="app.example", path="/private/report", query="year=2026"
        )
        target = mods.redirect_target.redirect_target_for(
            request, "https://accounts.other.example/sign-in/"
        )
        results[name] = target == "https://app.example/private/report?year=2026"
    return results


def spoofed_forwarded_host_never_leaks_into_target(
    variants: dict[str, types.SimpleNamespace],
) -> dict[str, bool]:
    results = {}
    for name, mods in variants.items():
        request = mods.request.Request(
            scheme="https",
            host="app.example",
            path="/private/report",
            query="year=2026",
            forwarded_host="evil.example",
        )
        target = mods.redirect_target.redirect_target_for(request, "https://app.example/sign-in/")
        results[name] = "evil.example" not in target
    return results


def entry_endpoint_reflectable_without_reparsing(
    variants: dict[str, types.SimpleNamespace],
) -> dict[str, bool]:
    results = {}
    for name, mods in variants.items():

        @mods.gate.require_sign_in(entry_url="/custom-sign-in/", return_param_name="dest")
        def view(request):
            return "view ran"

        entry = mods.gate_scan.entry_endpoint_for(view)
        param = mods.gate_scan.return_param_name_for(view)
        results[name] = entry == "/custom-sign-in/" and param == "dest"
    return results


def main() -> int:
    variants = {name: load_variant(name) for name in VARIANTS}

    same_host = same_host_target_is_relative_with_query(variants)
    cross_host = cross_host_entry_gets_absolute_target(variants)
    spoofed = spoofed_forwarded_host_never_leaks_into_target(variants)
    reflect = entry_endpoint_reflectable_without_reparsing(variants)

    print("=== same_host_target_is_relative_with_query ===")
    for name, ok in same_host.items():
        print(f"  {name}: {'correct' if ok else 'WRONG TARGET'}")
    print("=== cross_host_entry_gets_absolute_target ===")
    for name, ok in cross_host.items():
        print(f"  {name}: {'correct' if ok else 'WRONG TARGET'}")
    print("=== spoofed_forwarded_host_never_leaks_into_target ===")
    for name, ok in spoofed.items():
        print(f"  {name}: {'contained' if ok else 'LEAKED OFF-HOST'}")
    print("=== entry_endpoint_reflectable_without_reparsing ===")
    for name, ok in reflect.items():
        print(f"  {name}: {'reflects correctly' if ok else 'WRONG STAPLE'}")

    failures = []

    expected_same_host = {
        "bare-relative-target": False,
        "scoped-absolute-target": True,
        "near-miss-always-relative": True,
        "mutant-trusts-forwarded-host": True,
        "mutant-unstapled-view": True,
    }
    for name, expected in expected_same_host.items():
        if same_host.get(name) != expected:
            failures.append(
                f"{name}: expected same_host_target_is_relative_with_query={expected}, "
                f"got {same_host.get(name)}"
            )

    expected_cross_host = {
        "bare-relative-target": False,
        "scoped-absolute-target": True,
        "near-miss-always-relative": False,
        "mutant-trusts-forwarded-host": True,
        "mutant-unstapled-view": True,
    }
    for name, expected in expected_cross_host.items():
        if cross_host.get(name) != expected:
            failures.append(
                f"{name}: expected cross_host_entry_gets_absolute_target={expected}, "
                f"got {cross_host.get(name)}"
            )

    expected_spoofed = {
        "bare-relative-target": True,
        "scoped-absolute-target": True,
        "near-miss-always-relative": True,
        "mutant-trusts-forwarded-host": False,
        "mutant-unstapled-view": True,
    }
    for name, expected in expected_spoofed.items():
        if spoofed.get(name) != expected:
            failures.append(
                f"{name}: expected spoofed_forwarded_host_never_leaks_into_target={expected}, "
                f"got {spoofed.get(name)}"
            )

    expected_reflect = dict.fromkeys(VARIANTS, True)
    expected_reflect["mutant-unstapled-view"] = False
    for name, expected in expected_reflect.items():
        if reflect.get(name) != expected:
            failures.append(
                f"{name}: expected entry_endpoint_reflectable_without_reparsing={expected}, "
                f"got {reflect.get(name)}"
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
