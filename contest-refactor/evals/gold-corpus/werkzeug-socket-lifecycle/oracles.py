#!/usr/bin/env python3
"""Hidden oracle battery for werkzeug-socket-lifecycle. Grader-only: never
shown to a candidate (listed in provenance.json's grader_only_files).

Imports each variant's `service_listener.py` fresh by file path (every
variant reuses the same module name, so plain `import service_listener`
would collide) and runs the three oracles declared in provenance.json's
`hidden_oracles`:

    no_descriptor_leak_on_adopt   -- THE DISCRIMINATOR for the RED shape. A
                                     descriptor that was open before a
                                     provision-then-adopt round trip must be
                                     the only one still open afterward --
                                     the placeholder a Service creates on
                                     construction must not survive being
                                     replaced by an adopted listener. Fails
                                     in helper-and-eager-service, whose
                                     placeholder is only overwritten, never
                                     closed.
    reuse_matches_legacy_default  -- a freshly provisioned listener's
                                     reuse_enabled must match what the
                                     pre-consolidation helper always set
                                     (True). Fails in near-miss-dropped-
                                     reuse, which folds every other
                                     responsibility into Service but never
                                     calls set_reuse.
    handoff_yields_live_descriptor -- the descriptor id start_with_handoff
                                     returns for a successor must belong to
                                     a still-open listener, i.e. be
                                     non-negative. Fails in mutant-handoff-
                                     close-before-read, which closes the
                                     listener before reading descriptor_id
                                     instead of after.

Run: python3 oracles.py
Exit 0 iff every observed result matches its declared expectation.
"""

from __future__ import annotations

import importlib.util
import sys
import types
from itertools import count
from pathlib import Path

PACK_DIR = Path(__file__).resolve().parent
VARIANTS = [
    "helper-and-eager-service",
    "consolidated-service-ownership",
    "near-miss-dropped-reuse",
    "mutant-handoff-close-before-read",
]

# Distinct port ranges per oracle so calls never collide, even though each
# variant module already has its own isolated globals.
_leak_ports = count(20001)
_reuse_ports = count(21001)
_handoff_ports = count(22001)


def load_variant(name: str) -> types.ModuleType:
    path = PACK_DIR / name / "service_listener.py"
    spec = importlib.util.spec_from_file_location(
        f"_gc_service_listener_{name.replace('-', '_')}", path
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def no_descriptor_leak_on_adopt(mod: types.ModuleType) -> bool:
    endpoint = ("oracle-leak", next(_leak_ports))
    baseline = len(mod._OPEN_DESCRIPTORS)
    prepared = mod.provision_listener(endpoint)
    service = mod.start_service(endpoint, adopt=prepared)
    service.close()
    return len(mod._OPEN_DESCRIPTORS) == baseline


def reuse_matches_legacy_default(mod: types.ModuleType) -> bool:
    endpoint = ("oracle-reuse", next(_reuse_ports))
    listener = mod.provision_listener(endpoint)
    result = listener.reuse_enabled is True
    listener.close()
    return result


def handoff_yields_live_descriptor(mod: types.ModuleType) -> bool:
    endpoint = ("oracle-handoff", next(_handoff_ports))
    descriptor_id = mod.start_with_handoff(endpoint)
    return descriptor_id >= 0


def main() -> int:
    modules = {variant: load_variant(variant) for variant in VARIANTS}

    leak_results = {name: no_descriptor_leak_on_adopt(mod) for name, mod in modules.items()}
    reuse_results = {name: reuse_matches_legacy_default(mod) for name, mod in modules.items()}
    handoff_results = {name: handoff_yields_live_descriptor(mod) for name, mod in modules.items()}

    print("=== no_descriptor_leak_on_adopt ===")
    for name, ok in leak_results.items():
        print(f"  {name}: {'no leak' if ok else 'LEAKED A DESCRIPTOR'}")
    print("=== reuse_matches_legacy_default ===")
    for name, ok in reuse_results.items():
        print(f"  {name}: {'reuse enabled' if ok else 'REUSE NOT ENABLED'}")
    print("=== handoff_yields_live_descriptor ===")
    for name, ok in handoff_results.items():
        print(f"  {name}: {'live descriptor' if ok else 'DEAD DESCRIPTOR HANDED OFF'}")

    failures = []

    expected_leak = {
        "helper-and-eager-service": False,
        "consolidated-service-ownership": True,
        "near-miss-dropped-reuse": True,
        "mutant-handoff-close-before-read": True,
    }
    for name, expected in expected_leak.items():
        if leak_results.get(name) != expected:
            failures.append(
                f"{name}: expected no_descriptor_leak_on_adopt={expected}, "
                f"got {leak_results.get(name)}"
            )

    expected_reuse = {
        "helper-and-eager-service": True,
        "consolidated-service-ownership": True,
        "near-miss-dropped-reuse": False,
        "mutant-handoff-close-before-read": True,
    }
    for name, expected in expected_reuse.items():
        if reuse_results.get(name) != expected:
            failures.append(
                f"{name}: expected reuse_matches_legacy_default={expected}, "
                f"got {reuse_results.get(name)}"
            )

    expected_handoff = {
        "helper-and-eager-service": True,
        "consolidated-service-ownership": True,
        "near-miss-dropped-reuse": True,
        "mutant-handoff-close-before-read": False,
    }
    for name, expected in expected_handoff.items():
        if handoff_results.get(name) != expected:
            failures.append(
                f"{name}: expected handoff_yields_live_descriptor={expected}, "
                f"got {handoff_results.get(name)}"
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
