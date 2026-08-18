#!/usr/bin/env python3
"""Self-test for G45 (exhaustion halt record shape + detection<->kind honesty coupling).

Unit-level coverage of `check_g45_exhaustion_record` (backlog item 17, Gap 14). Mirrors
`_handoff_shape_selftest.py`'s structure: load validate-artifact.py as a module, build minimal
`current_review` dicts, and assert issue counts directly against the shipped checker (never a
reimplementation).

Run: python3 scripts/_g45_exhaustion_selftest.py   (exit 0 = pass, 1 = fail).
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


HONEST = {
    "kind": "unknown",
    "detection_mode": "preventive_step_budget",
    "evidence": "step 12 of 12",
}


def g45(state, exhaustion, schema_version=4):
    return len(
        va.check_g45_exhaustion_record(
            {"schema_version": schema_version, "state": state, "exhaustion": exhaustion}, canon
        )
    )


# ---- schema_version floor ----
check(
    g45("HALT_EXHAUSTION", None, schema_version=3) == 0,
    "schema_version < 4 must raise NO G45 issue regardless of shape (gate is floored)",
)
check(
    g45("HALT_EXHAUSTION", {"kind": "bogus"}, schema_version=1) == 0,
    "schema_version 1 with a malformed exhaustion must still raise NO G45 issue (floor first)",
)

# ---- presence, both directions ----
check(
    g45("HALT_EXHAUSTION", None) == 1,
    "state=HALT_EXHAUSTION with exhaustion=null must raise one G45 issue (presence)",
)
check(
    g45("CONTINUE", dict(HONEST)) == 1,
    "exhaustion non-null on a non-HALT_EXHAUSTION state must raise one G45 issue (null-required)",
)
check(
    g45("HALT_LOOP_CAP", dict(HONEST)) == 1,
    "exhaustion non-null on the sibling HALT_LOOP_CAP must also raise one G45 issue (scoped to "
    "HALT_EXHAUSTION only)",
)
check(
    g45("CONTINUE", None) == 0,
    "exhaustion=null on a non-HALT_EXHAUSTION state must raise NO G45 issue",
)
check(
    g45("BOGUS_STATE", dict(HONEST)) == 0,
    "non-canon state must raise NO G45 issue (schema-enum check's job, not G45's)",
)

# ---- root type ----
check(
    g45("HALT_EXHAUSTION", "not-a-dict") == 1,
    "non-dict exhaustion root must raise one G45 issue",
)
check(
    g45("HALT_EXHAUSTION", ["kind", "unknown"]) == 1,
    "list exhaustion root must raise one G45 issue",
)

# ---- each required key missing ----
for missing_key in ("kind", "detection_mode", "evidence"):
    partial = {k: v for k, v in HONEST.items() if k != missing_key}
    check(
        g45("HALT_EXHAUSTION", partial) == 1,
        f"exhaustion missing {missing_key!r} must raise one G45 issue",
    )

# ---- each required key empty/non-string ----
for bad_key in ("kind", "detection_mode", "evidence"):
    for bad_value in ("", "   ", 12, None):
        mutated = dict(HONEST)
        mutated[bad_key] = bad_value
        n = g45("HALT_EXHAUSTION", mutated)
        check(
            n >= 1,
            f"exhaustion.{bad_key}={bad_value!r} must raise at least one G45 issue, got {n}",
        )

# ---- extra key ----
check(
    g45("HALT_EXHAUSTION", {**HONEST, "timestamp": "2026-08-18T00:00:00Z"}) == 1,
    "an extra key on exhaustion must raise one G45 issue",
)

# ---- out-of-canon kind / detection_mode ----
check(
    g45("HALT_EXHAUSTION", {**HONEST, "kind": "server_overload"}) >= 1,
    "an out-of-canon kind must raise at least one G45 issue (membership; may also trip coupling)",
)
check(
    g45("HALT_EXHAUSTION", {**HONEST, "detection_mode": "vibes"}) == 1,
    "an out-of-canon detection_mode must raise one G45 issue (membership only; not coupled to kind)",
)

# ---- D4 honesty coupling ----
check(
    g45("HALT_EXHAUSTION", {**HONEST, "kind": "context_pressure"}) == 1,
    "preventive_step_budget claiming kind=context_pressure must raise one G45 issue (RED: the coupling)",
)
check(
    g45("HALT_EXHAUSTION", {**HONEST, "kind": "spend_limit"}) == 1,
    "preventive_step_budget claiming kind=spend_limit must raise one G45 issue (RED: the coupling)",
)
check(
    g45(
        "HALT_EXHAUSTION",
        {"kind": "context_pressure", "detection_mode": "user_reported", "evidence": "user said so"},
    )
    == 0,
    "user_reported may claim context_pressure with no coupling issue (GREEN)",
)
check(
    g45(
        "HALT_EXHAUSTION",
        {"kind": "spend_limit", "detection_mode": "user_reported", "evidence": "user said so"},
    )
    == 0,
    "user_reported may claim spend_limit with no coupling issue (GREEN)",
)
check(
    g45(
        "HALT_EXHAUSTION",
        {"kind": "unknown", "detection_mode": "user_reported", "evidence": "user unsure"},
    )
    == 0,
    "user_reported may also claim unknown with no coupling issue (GREEN)",
)

# ---- honest GREEN ----
check(
    g45("HALT_EXHAUSTION", dict(HONEST)) == 0,
    "preventive_step_budget + kind=unknown + real evidence must raise NO G45 issue (the honest GREEN)",
)

if failures:
    print(f"_g45_exhaustion_selftest: FAIL ({len(failures)})")
    for f in failures:
        print("  -", f)
    sys.exit(1)
print("_g45_exhaustion_selftest: OK")
sys.exit(0)
