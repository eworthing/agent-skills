#!/usr/bin/env python3
"""Self-test for G46 (general remediation fields: finding_family/effort/repair_revalidation).

Unit-level coverage of `check_g46_general_remediation_fields` (backlog item 28, general half).
Mirrors `_g45_exhaustion_selftest.py`'s structure: load validate-artifact.py as a module, build
minimal `current_review` dicts, and assert issue counts directly against the shipped checker
(never a reimplementation).

Run: python3 scripts/_g46_remediation_fields_selftest.py   (exit 0 = pass, 1 = fail).
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL_ROOT = HERE.parent
sys.path.insert(0, str(HERE))

from _canon import load_canon

spec = importlib.util.spec_from_file_location(
    "validate_artifact", SKILL_ROOT / "scripts" / "validate-artifact.py"
)
va = importlib.util.module_from_spec(spec)
spec.loader.exec_module(va)
canon = load_canon(SKILL_ROOT)

failures: list[str] = []


def check(cond: bool, msg: str) -> None:
    if not cond:
        failures.append(msg)


HONEST_RV = {
    "outcome": "INVARIANT_HOLDS",
    "detail": "re-ran the deletion test against Core/NavigationStore.swift; single writer confirmed",
    "mechanically_testable": True,
    "drift_notes": None,
}

HONEST_LR = {
    "finding_family": "simplification",
    "effort": "small",
    "repair_revalidation": dict(HONEST_RV),
}


def g46(loop_result, schema_version=4):
    return len(
        va.check_g46_general_remediation_fields(
            {"schema_version": schema_version, "skill_rev": "9528774", "loop_result": loop_result},
            canon,
        )
    )


# ---- schema_version floor ----
check(
    g46({}, schema_version=3) == 0,
    "schema_version < 4 must raise NO G46 issue regardless of shape (gate is floored)",
)
check(
    g46({"finding_family": "bogus"}, schema_version=1) == 0,
    "schema_version 1 with a malformed loop_result must still raise NO G46 issue (floor first)",
)

# ---- presence, both directions ----
check(
    g46(None) == 0,
    "loop_result=null must raise NO G46 issue (a backlog item not yet picked up carries none "
    "of these fields; loop_result's own presence is rule #8's concern, not G46's)",
)
check(
    g46({}) == 3,
    "loop_result={} at v4 must raise exactly 3 G46 issues (finding_family, effort, "
    "repair_revalidation all missing)",
)
check(
    g46(dict(HONEST_LR)) == 0,
    "a fully honest loop_result must raise NO G46 issue (the GREEN baseline)",
)

# ---- non-dict loop_result root ----
check(
    g46("not-a-dict") == 0,
    "a non-dict loop_result has no other owner in this validator; G46 has nothing to check "
    "inside it and must raise no issue",
)

# ---- finding_family ----
check(
    g46({**HONEST_LR, "finding_family": None}) == 1,
    "finding_family=null must raise one G46 issue (required)",
)
check(
    g46({**HONEST_LR, "finding_family": ""}) == 1,
    "finding_family='' must raise one G46 issue (non-empty required)",
)
check(
    g46({**HONEST_LR, "finding_family": "refactor_vibes"}) == 1,
    "an out-of-canon finding_family must raise one G46 issue (membership)",
)
for family in canon.finding_families:
    check(
        g46({**HONEST_LR, "finding_family": family}) == 0,
        f"every canon finding_family value must be accepted; {family!r} raised an issue",
    )

# ---- effort ----
check(
    g46({**HONEST_LR, "effort": None}) == 1,
    "effort=null must raise one G46 issue (required)",
)
check(
    g46({**HONEST_LR, "effort": "gigantic"}) == 1,
    "an out-of-canon effort must raise one G46 issue (membership)",
)
for level in canon.effort_levels:
    check(
        g46({**HONEST_LR, "effort": level}) == 0,
        f"every canon effort_level value must be accepted; {level!r} raised an issue",
    )

# ---- repair_revalidation root shape ----
check(
    g46({**HONEST_LR, "repair_revalidation": None}) == 1,
    "repair_revalidation=null must raise one G46 issue (required, unlike risk_boundary_evidence)",
)
check(
    g46({**HONEST_LR, "repair_revalidation": "not-a-dict"}) == 1,
    "a non-dict repair_revalidation must raise one G46 issue",
)
check(
    g46({**HONEST_LR, "repair_revalidation": []}) == 1,
    "a list repair_revalidation must raise one G46 issue",
)

# ---- repair_revalidation.outcome ----
check(
    g46({**HONEST_LR, "repair_revalidation": {**HONEST_RV, "outcome": None}}) == 1,
    "outcome=null must raise one G46 issue (required)",
)
check(
    g46({**HONEST_LR, "repair_revalidation": {**HONEST_RV, "outcome": "MOSTLY_FINE"}}) == 1,
    "an out-of-canon outcome must raise one G46 issue (membership only; drift_notes coupling "
    "is not judged against an invalid outcome)",
)
for outcome in canon.repair_revalidation_outcomes:
    rv = {**HONEST_RV, "outcome": outcome}
    rv["drift_notes"] = None if outcome == "INVARIANT_HOLDS" else "real explanation of what moved"
    check(
        g46({**HONEST_LR, "repair_revalidation": rv}) == 0,
        f"every canon repair_revalidation outcome value, correctly paired with drift_notes, "
        f"must be accepted; {outcome!r} raised an issue",
    )

# ---- repair_revalidation.detail ----
for bad_detail in ("", "   ", None, 12):
    check(
        g46({**HONEST_LR, "repair_revalidation": {**HONEST_RV, "detail": bad_detail}}) == 1,
        f"repair_revalidation.detail={bad_detail!r} must raise one G46 issue",
    )

# ---- repair_revalidation.mechanically_testable ----
for bad_mt in (None, "true", 1, 0):
    check(
        g46({**HONEST_LR, "repair_revalidation": {**HONEST_RV, "mechanically_testable": bad_mt}})
        == 1,
        f"mechanically_testable={bad_mt!r} (non-bool) must raise one G46 issue",
    )
check(
    g46({**HONEST_LR, "repair_revalidation": {**HONEST_RV, "mechanically_testable": False}}) == 0,
    "mechanically_testable=False is a legal bool and must raise no G46 issue on its own",
)

# ---- D3: drift_notes coupling (the RED this fixture pair isolates) ----
for non_holds in ("INVARIANT_DRIFTED", "INVARIANT_REPLACED", "CONTRACT_REJECTED", "AUDIT_MOOT"):
    empty_rv = {**HONEST_RV, "outcome": non_holds, "drift_notes": ""}
    check(
        g46({**HONEST_LR, "repair_revalidation": empty_rv}) == 1,
        f"outcome={non_holds!r} with drift_notes='' must raise one G46 issue (RED: the coupling)",
    )
    null_rv = {**HONEST_RV, "outcome": non_holds, "drift_notes": None}
    check(
        g46({**HONEST_LR, "repair_revalidation": null_rv}) == 1,
        f"outcome={non_holds!r} with drift_notes=null must raise one G46 issue (RED: the coupling)",
    )
    real_rv = {**HONEST_RV, "outcome": non_holds, "drift_notes": "what actually moved"}
    check(
        g46({**HONEST_LR, "repair_revalidation": real_rv}) == 0,
        f"outcome={non_holds!r} with a real drift_notes must raise NO G46 issue (GREEN)",
    )

# One-directional per D3: outcome == INVARIANT_HOLDS never gates drift_notes either way.
check(
    g46(
        {
            **HONEST_LR,
            "repair_revalidation": {**HONEST_RV, "outcome": "INVARIANT_HOLDS", "drift_notes": None},
        }
    )
    == 0,
    "outcome=INVARIANT_HOLDS with drift_notes=null must raise NO G46 issue",
)
check(
    g46(
        {
            **HONEST_LR,
            "repair_revalidation": {
                **HONEST_RV,
                "outcome": "INVARIANT_HOLDS",
                "drift_notes": "stray note, not forbidden -- D3 is one-directional",
            },
        }
    )
    == 0,
    "outcome=INVARIANT_HOLDS with a stray non-empty drift_notes must raise NO G46 issue "
    "(D3 does not forbid this direction)",
)

if failures:
    print(f"_g46_remediation_fields_selftest: FAIL ({len(failures)})")
    for f in failures:
        print("  -", f)
    sys.exit(1)
print("_g46_remediation_fields_selftest: OK")
sys.exit(0)
