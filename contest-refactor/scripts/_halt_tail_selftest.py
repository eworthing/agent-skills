#!/usr/bin/env python3
"""Self-test for G34 (HALT-tail emit invariants) in validate-artifact.py.

Unit-level coverage of `check_g34_halt_tail_invariants` over BOTH directions of every per-state
presence contract (rules #11/#17/#18 presence halves) plus the canon-state guard and the
schema_version >= 3 boundary. Mirrors `_risk_evidence_selftest.py` (G33). Stdlib-only.

Run: python3 scripts/_halt_tail_selftest.py   (exit 0 = pass, 1 = fail).
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


HH = {"state": "X", "halt_subtype": None, "text": "handoff text", "expected_actions": []}


def art(state, *, version=3, subtype=None, reason=None, handoff=None, drop_state=False):
    d = {"schema_version": version}
    if not drop_state:
        d["state"] = state
    d["halt_subtype"] = subtype
    d["unresolved_reason"] = reason
    d["halt_handoff"] = handoff
    return d


def n_issues(d):
    return len(va.check_g34_halt_tail_invariants(d, canon))


# ---- required-when: a halt state missing a field G34 requires -> issue ----
check(
    n_issues(art("HALT_STAGNATION", subtype=None, reason="r", handoff=HH)) == 1,
    "HALT_STAGNATION with null halt_subtype must raise exactly one G34 issue (rule #17)",
)
check(
    n_issues(art("HALT_STAGNATION", subtype="user_decision", reason=None, handoff=HH)) == 1,
    "HALT_STAGNATION with null unresolved_reason must raise one G34 issue (rule #11)",
)
check(
    n_issues(art("HALT_LOOP_CAP", subtype=None, reason="r", handoff=None)) == 1,
    "HALT_LOOP_CAP with null halt_handoff must raise one G34 issue (rule #18 presence)",
)
check(
    n_issues(art("HALT_LOOP_CAP", subtype=None, reason=None, handoff=HH)) == 1,
    "HALT_LOOP_CAP with null unresolved_reason must raise one G34 issue (rule #11)",
)

# ---- forbidden-present (null-otherwise half): a non-halt/exempt state carrying a field -> issue ----
check(
    n_issues(art("HALT_SUCCESS_candidate", subtype=None, reason=None, handoff=HH)) == 1,
    "HALT_SUCCESS_candidate carrying a non-null halt_handoff must raise one G34 issue (candidate is exempt)",
)
check(
    n_issues(art("CONTINUE", subtype="no_progress", reason=None, handoff=None)) == 1,
    "CONTINUE carrying a non-null halt_subtype must raise one G34 issue (rule #17 null-otherwise)",
)
check(
    n_issues(art("CONTINUE", subtype=None, reason="leftover", handoff=None)) == 1,
    "CONTINUE carrying a non-null unresolved_reason must raise one G34 issue (rule #11 null-otherwise)",
)

# ---- clean by-state contracts -> no issue ----
check(
    n_issues(art("HALT_SUCCESS_candidate", subtype=None, reason=None, handoff=None)) == 0,
    "valid HALT_SUCCESS_candidate (all null) must raise no G34 issue",
)
check(
    n_issues(
        art(
            "HALT_STAGNATION",
            subtype="user_decision",
            reason="needs a product decision",
            handoff=HH,
        )
    )
    == 0,
    "valid HALT_STAGNATION/user_decision must raise no G34 issue",
)
check(
    n_issues(art("HALT_LOOP_CAP", subtype=None, reason="cap hit", handoff=HH)) == 0,
    "valid HALT_LOOP_CAP must raise no G34 issue",
)
check(
    n_issues(art("HALT_SUCCESS", subtype=None, reason=None, handoff=HH)) == 0,
    "valid terminal HALT_SUCCESS (handoff present, subtype/reason null) must raise no G34 issue",
)
check(
    n_issues(art("CONTINUE", subtype=None, reason=None, handoff=None)) == 0,
    "valid CONTINUE (all null) must raise no G34 issue",
)
check(
    n_issues(
        art(
            "HALT_STAGNATION",
            subtype="verification_blocked",
            reason="challenger unavailable",
            handoff=HH,
        )
    )
    == 0,
    "HALT_STAGNATION/verification_blocked (canon subtype) must raise no G34 issue",
)

# ---- guard: invalid/missing state is owned by check_schema_enums, not G34 ----
check(
    n_issues(art("BOGUS_STATE", subtype="no_progress", reason="x", handoff=HH)) == 0,
    "a non-canon state must raise no G34 issue (schema-enum check owns it)",
)
check(
    n_issues(art(None, drop_state=True, subtype="no_progress")) == 0,
    "a missing state must raise no G34 issue (G34 only skips it)",
)

# ---- version boundary: G34 must not fire below schema_version 3 ----
check(
    n_issues(art("HALT_STAGNATION", version=2, subtype=None, reason=None, handoff=None)) == 0,
    "G34 must not fire below schema_version 3 even on a clear violation",
)
check(
    n_issues(art("HALT_STAGNATION", version=4, subtype=None, reason="r", handoff=HH)) == 1,
    "G34 must fire at schema_version 4",
)

if failures:
    print(f"_halt_tail_selftest: FAIL ({len(failures)})")
    for f in failures:
        print("  -", f)
    sys.exit(1)
print("_halt_tail_selftest: OK")
sys.exit(0)
