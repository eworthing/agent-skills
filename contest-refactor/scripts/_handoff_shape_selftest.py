#!/usr/bin/env python3
"""Self-test for G35 (halt_handoff object shape) + G36 (required non-null state) in validate-artifact.py.

Unit-level coverage of `check_g35_halt_handoff_shape` and `check_g36_required_state`, plus the codex-B1
disjointness case: on a HALT_STAGNATION/oscillation artifact with a non-dict handoff, ONLY G35 fires —
`check_g30_disposition_coverage` bails (it does not double-report or AttributeError). Mirrors
`_halt_tail_selftest.py`. Stdlib-only.

Run: python3 scripts/_handoff_shape_selftest.py   (exit 0 = pass, 1 = fail).
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL_ROOT = HERE.parent
sys.path.insert(0, str(HERE))

from _canon import load_canon  # noqa: E402

spec = importlib.util.spec_from_file_location("validate_artifact", SKILL_ROOT / "scripts" / "validate-artifact.py")
va = importlib.util.module_from_spec(spec)
spec.loader.exec_module(va)
canon = load_canon(SKILL_ROOT)

failures: list[str] = []


def check(cond: bool, msg: str) -> None:
    if not cond:
        failures.append(msg)


def act(kind, paths):
    return {"action_id": "a", "description": "d", "match_keywords": ["k"], "match_paths": paths, "match_kind": kind}


def g35(state, handoff):
    return len(va.check_g35_halt_handoff_shape({"state": state, "halt_handoff": handoff}, canon))


def g36(d):
    return len(va.check_g36_required_state(d, canon))


# ---- G35 root type ----
check(g35("HALT_LOOP_CAP", "stringy") == 1,
      "non-dict handoff on a handoff-state must raise one G35 issue (root type)")
check(g35("HALT_LOOP_CAP", ["x"]) == 1,
      "list handoff on a handoff-state must raise one G35 issue (root type)")
check(g35("CONTINUE", "stringy") == 0,
      "non-dict handoff on CONTINUE must raise NO G35 issue (G34 owns null-required; disjoint)")
check(g35("HALT_SUCCESS_candidate", {"text": "t", "expected_actions": []}) == 0,
      "dict handoff on HALT_SUCCESS_candidate must raise NO G35 issue (non-handoff state; G34's job)")
check(g35("BOGUS_STATE", "stringy") == 0,
      "non-canon state must raise NO G35 issue (G35 is state-scoped; schema-enum owns the foreign state)")
check(g35("HALT_LOOP_CAP", None) == 0,
      "absent (None) handoff on a handoff-state must raise NO G35 issue (absence is G34's presence concern)")

# ---- G35 text ----
check(g35("HALT_LOOP_CAP", {"text": "", "expected_actions": []}) == 1,
      "empty text must raise one G35 issue")
check(g35("HALT_LOOP_CAP", {"expected_actions": []}) == 1,
      "absent text key (-> None) must raise one G35 issue")

# ---- G35 expected_actions array ----
check(g35("HALT_LOOP_CAP", {"text": "t", "expected_actions": {}}) == 1,
      "non-list expected_actions must raise one G35 issue")
check(g35("HALT_LOOP_CAP", {"text": "t", "expected_actions": ["x"]}) == 1,
      "an expected_actions entry that is not a dict must raise one G35 issue")

# ---- G35 match_kind membership + path<->kind coupling ----
check(g35("HALT_LOOP_CAP", {"text": "t", "expected_actions": [act("first_of", [])]}) == 1,
      "non-canon match_kind must raise one G35 issue (membership)")
check(g35("HALT_LOOP_CAP", {"text": "t", "expected_actions": [act("all_of", [])]}) == 1,
      "all_of with empty match_paths must raise one G35 issue (coupling)")
check(g35("HALT_LOOP_CAP", {"text": "t", "expected_actions": [act("any_of", ["p"])]}) == 1,
      "any_of with non-empty match_paths must raise one G35 issue (coupling)")
check(g35("HALT_LOOP_CAP", {"text": "t", "expected_actions": [act("no_drift_expected", ["p"])]}) == 1,
      "no_drift_expected with non-empty match_paths must raise one G35 issue (coupling)")

# ---- G35 clean ----
check(g35("HALT_LOOP_CAP", {"text": "t", "expected_actions": []}) == 0,
      "valid handoff with empty expected_actions must raise no G35 issue")
check(g35("HALT_LOOP_CAP", {"text": "t", "expected_actions": [
    act("all_of", ["p"]), act("any_of", []), act("no_drift_expected", [])]}) == 0,
      "valid multi-action handoff (one of each match_kind) must raise no G35 issue")

# ---- G36 required state ----
check(g36({"state": None}) == 1, "state=None must raise one G36 issue")
check(g36({}) == 1, "absent state key must raise one G36 issue")
check(g36({"state": "CONTINUE"}) == 0, "a valid canon state must raise no G36 issue")
check(g36({"state": "BOGUS"}) == 0,
      "a non-null foreign state must raise NO G36 issue (membership is the schema-enum check's job)")

# ---- codex-B1: G30 single-owner on oscillation + non-dict handoff ----
serious = next(iter(va.SERIOUS_OR_WORSE))
eligible = next(iter(va.ELIGIBLE_BACKLOG_STATUSES))
osc = {"state": "HALT_STAGNATION", "halt_subtype": "oscillation", "halt_handoff": "stringy"}
registry = {"entries": [{"stable_id": "F-001", "severity": serious, "occurrences": [{"status": eligible}]}]}
check(len(va.check_g30_disposition_coverage(osc, registry)) == 0,
      "G30 must BAIL (zero issues) on a non-dict handoff so it does not double-fire with G35")
check(g35("HALT_STAGNATION", "stringy") == 1,
      "G35 must be the sole owner of the non-dict handoff on the oscillation path")

if failures:
    print(f"_handoff_shape_selftest: FAIL ({len(failures)})")
    for f in failures:
        print("  -", f)
    sys.exit(1)
print("_handoff_shape_selftest: OK")
sys.exit(0)
