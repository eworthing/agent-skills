#!/usr/bin/env python3
"""Hidden oracle battery for config-precedence-duplicate-authority.
Grader-only: never shown to a candidate (listed in provenance.json's
grader_only_files).

Loads each variant's `settings.py` fresh by module name -- every variant
reuses the same module name, so a sys.path + sys.modules dance is needed to
stop one variant leaking into the next -- and runs the three oracles declared
in provenance.json's `hidden_oracles`:

    value_and_reported_source_agree -- THE DISCRIMINATOR for duplicate
                                       authority. Whatever layer a value
                                       actually came from is the layer the
                                       reported source must name. Fails in
                                       two-owners-drifted (its source walk
                                       tests truthiness, so an explicitly
                                       empty override reads as absent) and in
                                       near-miss-shared-presence-only (its
                                       source walk carries its own copy of
                                       the layer order, and that copy puts
                                       user ahead of project). Both are the
                                       same defect: the question "which layer
                                       owns this key" is answered in two
                                       places.
    env_outranks_project            -- the declared layer order. Fails only
                                       in mutant-reordered-precedence, which
                                       resolves consistently but against the
                                       wrong order, so no agreement check can
                                       see it.
    default_when_no_layer_carries   -- CONTROL. With no layer carrying the
                                       key, the built-in default answers and
                                       reports itself. Holds everywhere;
                                       pins the floor case so a variant
                                       cannot pass the two oracles above by
                                       degenerating.

Note the pairing: agreement and order are independent failures. A resolver
can be perfectly self-consistent and still wrong (the mutant), and a resolver
can have the right order and still disagree with itself (the near-miss). One
oracle alone would certify half the corpus of variants here.

Run: python3 oracles.py
Exit 0 iff every observed result matches its declared expectation.
"""

from __future__ import annotations

import importlib
import sys
import types
from pathlib import Path

PACK_DIR = Path(__file__).resolve().parent

RED = "two-owners-drifted"
GREEN = "single-resolver"
NEAR_MISS = "near-miss-shared-presence-only"
MUTANT = "mutant-reordered-precedence"
VARIANTS = [RED, GREEN, NEAR_MISS, MUTANT]

DEFAULTS = {"retries": "3", "mode": "fast"}

#: (label, env, project, user). Every combination a layer walk can disagree
#: on, including the two that ordinary truthiness gets wrong: an explicitly
#: empty override and a literal "0".
AGREEMENT_CASES = [
    ("empty env override", {"retries": ""}, {}, {}),
    ("zero string in project", {}, {"retries": "0"}, {}),
    ("empty user override", {}, {}, {"retries": ""}),
    ("project and user both carry", {}, {"retries": "5"}, {"retries": "7"}),
    ("env and user both carry", {"retries": "9"}, {}, {"retries": "7"}),
    ("all three carry", {"retries": "9"}, {"retries": "5"}, {"retries": "7"}),
    ("env beats project", {"retries": "9"}, {"retries": "5"}, {}),
]


def load_variant(name: str) -> types.ModuleType:
    """Import one variant's settings module fresh, in isolation."""
    sys.modules.pop("settings", None)
    sys.path.insert(0, str(PACK_DIR / name))
    try:
        return importlib.import_module("settings")
    finally:
        sys.path.pop(0)
        sys.modules.pop("settings", None)


def value_and_reported_source_agree(mod: types.ModuleType) -> bool:
    for _label, env, project, user in AGREEMENT_CASES:
        value = mod.effective_value("retries", env, project, user, DEFAULTS)
        source = mod.describe_source("retries", env, project, user, DEFAULTS)
        layers = {"env": env, "project": project, "user": user}
        if source == "default":
            if any("retries" in layer for layer in layers.values()):
                return False
            continue
        if source not in layers:
            return False
        if "retries" not in layers[source] or layers[source]["retries"] != value:
            return False
    return True


def env_outranks_project(mod: types.ModuleType) -> bool:
    value = mod.effective_value("retries", {"retries": "9"}, {"retries": "5"}, {}, DEFAULTS)
    user_case = mod.effective_value("retries", {}, {"retries": "5"}, {"retries": "7"}, DEFAULTS)
    return value == "9" and user_case == "5"


def default_when_no_layer_carries(mod: types.ModuleType) -> bool:
    return (
        mod.effective_value("retries", {}, {}, {}, DEFAULTS) == "3"
        and mod.describe_source("retries", {}, {}, {}, DEFAULTS) == "default"
    )


def main() -> int:
    mods = {name: load_variant(name) for name in VARIANTS}

    agree = {n: value_and_reported_source_agree(m) for n, m in mods.items()}
    order = {n: env_outranks_project(m) for n, m in mods.items()}
    floor = {n: default_when_no_layer_carries(m) for n, m in mods.items()}

    print("=== value_and_reported_source_agree ===")
    for n, ok in agree.items():
        print(f"  {n}: {'agrees' if ok else 'REPORTS THE WRONG LAYER'}")
    print("=== env_outranks_project ===")
    for n, ok in order.items():
        print(f"  {n}: {'declared order' if ok else 'ORDER CHANGED'}")
    print("=== default_when_no_layer_carries (control) ===")
    for n, ok in floor.items():
        print(f"  {n}: {'default answers' if ok else 'FLOOR CASE BROKEN'}")

    failures: list[str] = []

    expected_agree = {RED: False, GREEN: True, NEAR_MISS: False, MUTANT: True}
    for n, expected in expected_agree.items():
        if agree.get(n) != expected:
            failures.append(
                f"{n}: expected value_and_reported_source_agree={expected}, got {agree.get(n)}"
            )

    expected_order = {RED: True, GREEN: True, NEAR_MISS: True, MUTANT: False}
    for n, expected in expected_order.items():
        if order.get(n) != expected:
            failures.append(f"{n}: expected env_outranks_project={expected}, got {order.get(n)}")

    for n in VARIANTS:
        if floor.get(n) is not True:
            failures.append(f"{n}: default_when_no_layer_carries must hold, got {floor.get(n)}")

    if failures:
        print("\nFAIL:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("\nOK: observed matrix matches declared expectations.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
