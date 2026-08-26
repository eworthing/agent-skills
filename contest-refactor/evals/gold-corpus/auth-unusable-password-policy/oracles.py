#!/usr/bin/env python3
"""Hidden oracle battery for auth-unusable-password-policy. Grader-only:
never shown to a candidate (listed in provenance.json's
grader_only_files).

Imports each variant's `credential_policy.py` fresh by file path (every
variant reuses the same module name, so plain `import credential_policy`
would collide) and runs the four checks below:

    ordinary_credential_round_trips           -- baseline: a real,
                                                  correctly set credential
                                                  verifies for the right
                                                  guess and rejects a
                                                  wrong one. Holds in both
                                                  variants -- this pack has
                                                  no near_miss/mutant to
                                                  fail it.
    no_credential_rejects_empty_supplied      -- an account with no local
                                                  credential must reject
                                                  an empty supplied value.
                                                  Fails in
                                                  empty-credential-
                                                  implicit-bypass, whose
                                                  empty-stored shortcut
                                                  treats an empty supplied
                                                  value as a match.
    no_credential_rejects_marker_as_supplied  -- an account with no local
                                                  credential must reject
                                                  the marker value itself
                                                  supplied as a guess.
                                                  Degenerates to the same
                                                  case as the check above
                                                  in the RED variant
                                                  (whose marker IS the
                                                  empty string), and is
                                                  the specific case this
                                                  pack's restraint story
                                                  is about in the accepted
                                                  variant.
    no_credential_markers_are_unique          -- two no-local-credential
                                                  markers for two
                                                  different accounts must
                                                  differ. Fails in
                                                  empty-credential-
                                                  implicit-bypass, whose
                                                  marker is always the
                                                  same empty string;
                                                  demonstrates that the
                                                  random suffix in the
                                                  accepted variant is
                                                  doing real work, not
                                                  decoration.

Run: python3 oracles.py
Exit 0 iff every observed result matches its declared expectation.
"""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

PACK_DIR = Path(__file__).resolve().parent
VARIANTS = ["empty-credential-implicit-bypass", "sentinel-marked-no-credential"]


def load_variant(name: str) -> types.ModuleType:
    path = PACK_DIR / name / "credential_policy.py"
    spec = importlib.util.spec_from_file_location(
        f"_gc_credential_policy_{name.replace('-', '_')}", path
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def ordinary_credential_round_trips(mod: types.ModuleType) -> bool:
    stored = mod.set_credential("correct horse battery staple")
    return (
        mod.verify_credential(stored, "correct horse battery staple") is True
        and mod.verify_credential(stored, "wrong guess") is False
    )


def no_credential_rejects_empty_supplied(mod: types.ModuleType) -> bool:
    marker = mod.mark_no_local_credential()
    return mod.verify_credential(marker, "") is False


def no_credential_rejects_marker_as_supplied(mod: types.ModuleType) -> bool:
    marker = mod.mark_no_local_credential()
    return mod.verify_credential(marker, marker) is False


def no_credential_markers_are_unique(mod: types.ModuleType) -> bool:
    return mod.mark_no_local_credential() != mod.mark_no_local_credential()


CHECKS = {
    "ordinary_credential_round_trips": ordinary_credential_round_trips,
    "no_credential_rejects_empty_supplied": no_credential_rejects_empty_supplied,
    "no_credential_rejects_marker_as_supplied": no_credential_rejects_marker_as_supplied,
    "no_credential_markers_are_unique": no_credential_markers_are_unique,
}

EXPECTATIONS = {
    "ordinary_credential_round_trips": dict.fromkeys(VARIANTS, True),
    "no_credential_rejects_empty_supplied": {
        "empty-credential-implicit-bypass": False,
        "sentinel-marked-no-credential": True,
    },
    "no_credential_rejects_marker_as_supplied": {
        "empty-credential-implicit-bypass": False,
        "sentinel-marked-no-credential": True,
    },
    "no_credential_markers_are_unique": {
        "empty-credential-implicit-bypass": False,
        "sentinel-marked-no-credential": True,
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
