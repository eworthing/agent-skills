#!/usr/bin/env python3
"""Self-test for G28's out_of_plan_cleanup phase checkpoint shape.

(Why: output-format-state-schemas.md § Out-of-plan cleanup phase;
scripts/_artifact_snapshots.py's _check_g28_out_of_plan_cleanup_phase.)

LOOP_STATE.json carries `phase: "out_of_plan_cleanup"` while Step 3 restores
every planned delta to baseline and commits a HALT_STAGNATION/user_decision
review-artifacts-only halt after a delta outside the Step 2 plan's predicted
touch paths is found. This checkpoint schema is unrelated to the legacy
step_started/step_completed mid-Step-3 schema, so G28 branches to a
dedicated shape check the moment `phase` is present — this test pins that
branch plus each required field of `cleanup_state`.

Covers, per the task's minimum bar: a valid checkpoint (silent), each field
missing (fires), and a bad cleanup_subphase value (fires). Also pins the
generic `phase` guard (an unrelated phase, e.g. `halt_success_panel`, must
not be validated against either schema) and a same-artifact regression
check that the legacy (no `phase`) checkpoint schema is unaffected by the
split from _artifact_history.py.

Run: python3 scripts/_g28_cleanup_phase_selftest.py   (exit 0 = pass, 1 = fail)
"""

from __future__ import annotations

import copy
import json
import os
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from _artifact_snapshots import check_g28_loop_state_freshness

# Pins _reference_now() so the legacy-schema regression case's fixed
# last_checkpoint_at never ages past the 24h orphan threshold.
os.environ["CONTEST_REFACTOR_NOW"] = "2026-05-12T14:31:05Z"

CURRENT_REVIEW = {"schema_version": 4, "loop": 3}

VALID_CLEANUP = {
    "schema_version": 1,
    "phase": "out_of_plan_cleanup",
    "cleanup_state": {
        "planned_paths": {"Core/NavigationStore.swift": "9b2a13c4" * 5},
        "unexpected_paths": ["Core/GeneratedCache.tmp"],
        "cleanup_subphase": "restoring",
        "halt_commit_draft": {
            "subject": "loop 3: halt — out-of-plan changes require disposition; "
            "finding F1 (stable_id F-001) carried_forward"
        },
    },
}


def _run(loop_state: dict) -> list[str]:
    with tempfile.TemporaryDirectory() as td:
        artifact_dir = Path(td)
        (artifact_dir / "LOOP_STATE.json").write_text(json.dumps(loop_state))
        issues = check_g28_loop_state_freshness(artifact_dir, copy.deepcopy(CURRENT_REVIEW))
        return [f"{i.rule}: {i.message}" for i in issues]


def main() -> int:
    failures: list[str] = []

    # --- valid checkpoint: silent ---
    if _run(VALID_CLEANUP):
        failures.append(f"valid checkpoint fired: {_run(VALID_CLEANUP)}")

    # --- each cleanup_state field missing/malformed: fires ---
    cases = {
        "cleanup_state missing entirely": lambda ls: ls.pop("cleanup_state"),
        "cleanup_state not a dict": lambda ls: ls.__setitem__("cleanup_state", "nope"),
        "planned_paths missing": lambda ls: ls["cleanup_state"].pop("planned_paths"),
        "planned_paths not a dict": lambda ls: ls["cleanup_state"].__setitem__(
            "planned_paths", ["a", "b"]
        ),
        "unexpected_paths missing": lambda ls: ls["cleanup_state"].pop("unexpected_paths"),
        "unexpected_paths empty": lambda ls: ls["cleanup_state"].__setitem__(
            "unexpected_paths", []
        ),
        "unexpected_paths has an empty string": lambda ls: ls["cleanup_state"].__setitem__(
            "unexpected_paths", [""]
        ),
        "cleanup_subphase missing": lambda ls: ls["cleanup_state"].pop("cleanup_subphase"),
        "cleanup_subphase bad value": lambda ls: ls["cleanup_state"].__setitem__(
            "cleanup_subphase", "reticulating"
        ),
        "halt_commit_draft missing": lambda ls: ls["cleanup_state"].pop("halt_commit_draft"),
        "halt_commit_draft.subject missing": lambda ls: ls["cleanup_state"][
            "halt_commit_draft"
        ].pop("subject"),
        "halt_commit_draft.subject empty": lambda ls: ls["cleanup_state"][
            "halt_commit_draft"
        ].__setitem__("subject", ""),
    }
    for label, mutate in cases.items():
        broken = copy.deepcopy(VALID_CLEANUP)
        mutate(broken)
        issues = _run(broken)
        if not issues:
            failures.append(f"{label}: expected G28 to fire, got silence")
        elif any(i.split(":")[0] != "G28" for i in issues):
            failures.append(f"{label}: fired a non-G28 rule: {issues}")

    # --- every valid cleanup_subphase value passes ---
    for subphase in ("restoring", "committing", "done"):
        variant = copy.deepcopy(VALID_CLEANUP)
        variant["cleanup_state"]["cleanup_subphase"] = subphase
        issues = _run(variant)
        if issues:
            failures.append(f"cleanup_subphase={subphase!r} fired: {issues}")

    # --- generic phase guard: an unrelated phase is not validated against either schema ---
    other_phase = {
        "schema_version": 1,
        "phase": "halt_success_panel",
        "panel_state": {"sub_phase": "members"},
    }
    issues = _run(other_phase)
    if issues:
        failures.append(f"unrelated phase 'halt_success_panel' should be silent here: {issues}")

    # --- regression: legacy (no phase) checkpoint schema unaffected by the module split ---
    legacy = {
        "schema_version": 1,
        "loop": 3,
        "step_started": 5,
        "step_completed": 4,
        "started_at": "2026-05-12T14:30:22Z",
        "last_checkpoint_at": "2026-05-12T14:31:05Z",
        "pre_step3_blob_shas": {},
    }
    if _run(legacy):
        failures.append(f"legacy well-formed checkpoint fired: {_run(legacy)}")
    legacy_bad = copy.deepcopy(legacy)
    legacy_bad["loop"] = 99
    if not _run(legacy_bad):
        failures.append("legacy loop-mismatch checkpoint did not fire (regression in the move)")

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    print(
        f"OK: G28 out_of_plan_cleanup phase selftest — "
        f"{len(cases) + 6} cases, legacy schema + phase guard unaffected"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
