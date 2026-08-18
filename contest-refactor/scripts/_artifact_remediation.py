"""_artifact_remediation.py — G46: general remediation-record fields (backlog item 28, general half).

New module rather than an addition to an existing `_artifact_*.py` file:
`_artifact_core.py` (653 LoC) and `_artifact_halt.py` (575 LoC) both already sit inside the
600-line soft-cap warning band (`common/scripts/check_module_size.py`), and `_artifact_residual.py`
answers a different question ("is this scorecard internally coherent about what it is NOT
claiming") than G46 does ("is this loop's remediation record shaped honestly"). A dedicated
module also leaves room for the DEFERRED family-conditional half of item 28 (disposition,
fix_kind readable from loop_result) to land beside G46 later without crowding a module that is
already tight — same reasoning as `_artifact_transitions.py`'s split for item 12.

G46 validates three fields on `loop_result`, present together iff `loop_result` itself is
present (rule #8: loop_result exists iff Step 3 sub-step 4 ran, i.e. a fix was actually
attempted this loop — a backlog item still waiting its turn never has a loop_result and so
never carries these fields either):
  - finding_family  ∈ canon.finding_families (discriminant for a future family-conditional
                      pass — deferred, see canon/remediation-fields.toml header)
  - effort          ∈ canon.effort_levels
  - repair_revalidation  object mirroring loop_result.risk_boundary_evidence's shape
                      (G33): {outcome, detail, mechanically_testable, drift_notes}.
                      outcome ∈ canon.repair_revalidation_outcomes; drift_notes is
                      non-empty whenever outcome != "INVARIANT_HOLDS" (design note §4 D3 —
                      mechanized from the start; center-audit shipped this
                      described-but-unenforced in v2.5.0 and had to patch it in v2.5.1).

Unlike risk_boundary_evidence (optional — null unless a Meta-Rule-4 boundary was crossed),
these three fields are REQUIRED whenever loop_result is present: every attempted repair has a
family, a cost, and a revalidation outcome, whereas most repairs cross no risk boundary at all.
"""

from __future__ import annotations

from _artifact_core import Issue

_INVARIANT_HOLDS = "INVARIANT_HOLDS"


def check_g46_general_remediation_fields(current_review: dict, canon) -> list[Issue]:
    """G46: finding_family / effort / repair_revalidation shape, gated on loop_result presence.

    Runs only at schema_version >= 4 (the fields are new at v4, matching G45's floor). Returns
    silently below the floor and when `loop_result` is absent or not a dict — the latter is not
    double-reported here because a malformed non-dict `loop_result` has no other owner in this
    validator today; this gate simply has nothing to check inside it.
    """
    issues: list[Issue] = []
    if (current_review.get("schema_version") or 1) < 4:
        return issues
    lr = current_review.get("loop_result")
    if not isinstance(lr, dict):
        return issues

    family = lr.get("finding_family")
    if not (isinstance(family, str) and family.strip()):
        issues.append(Issue("G46", "loop_result.finding_family is required (non-empty string)"))
    elif family not in set(canon.finding_families):
        issues.append(
            Issue(
                "G46",
                f"loop_result.finding_family {family!r} not in canon "
                f"{sorted(canon.finding_families)}",
            )
        )

    effort = lr.get("effort")
    if not (isinstance(effort, str) and effort.strip()):
        issues.append(Issue("G46", "loop_result.effort is required (non-empty string)"))
    elif effort not in set(canon.effort_levels):
        issues.append(
            Issue(
                "G46",
                f"loop_result.effort {effort!r} not in canon {sorted(canon.effort_levels)}",
            )
        )

    issues.extend(_check_repair_revalidation(lr.get("repair_revalidation"), canon))
    return issues


def _check_repair_revalidation(rv, canon) -> list[Issue]:
    if rv is None:
        return [Issue("G46", "loop_result.repair_revalidation is required (not null)")]
    if not isinstance(rv, dict):
        return [
            Issue(
                "G46",
                f"loop_result.repair_revalidation must be an object; got {type(rv).__name__}",
            )
        ]

    issues: list[Issue] = []
    outcome = rv.get("outcome")
    if not (isinstance(outcome, str) and outcome.strip()):
        issues.append(Issue("G46", "repair_revalidation.outcome is required (non-empty string)"))
        outcome = None
    elif outcome not in set(canon.repair_revalidation_outcomes):
        issues.append(
            Issue(
                "G46",
                f"repair_revalidation.outcome {outcome!r} not in canon "
                f"{sorted(canon.repair_revalidation_outcomes)}",
            )
        )

    detail = rv.get("detail")
    if not (isinstance(detail, str) and detail.strip()):
        issues.append(
            Issue(
                "G46",
                "repair_revalidation.detail required (non-empty string, what was actually "
                "re-checked)",
            )
        )

    mechanically_testable = rv.get("mechanically_testable")
    if not isinstance(mechanically_testable, bool):
        issues.append(
            Issue(
                "G46",
                f"repair_revalidation.mechanically_testable must be a bool; got "
                f"{type(mechanically_testable).__name__}",
            )
        )

    # drift_notes coupling (design note §4 D3): non-empty whenever outcome != INVARIANT_HOLDS.
    # One-directional, exactly as decided -- D3 says nothing about outcome == INVARIANT_HOLDS,
    # so a HOLDS record with a stray drift_notes string is not this gate's business. Only
    # judged once outcome is a known-valid, non-null string -- an already-invalid outcome
    # doesn't get a second, derivative complaint about drift_notes.
    drift_notes = rv.get("drift_notes")
    drift_notes_present = isinstance(drift_notes, str) and drift_notes.strip()
    if (
        outcome is not None
        and outcome in set(canon.repair_revalidation_outcomes)
        and outcome != _INVARIANT_HOLDS
        and not drift_notes_present
    ):
        issues.append(
            Issue(
                "G46",
                f"repair_revalidation.drift_notes required (non-empty string) when "
                f"outcome={outcome!r} != {_INVARIANT_HOLDS!r}",
            )
        )
    return issues
