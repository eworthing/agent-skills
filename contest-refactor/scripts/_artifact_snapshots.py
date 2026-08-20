from __future__ import annotations

from pathlib import Path

from _artifact_core import (
    _G28_ORPHAN_SECONDS,
    Issue,
    _find_git_root,
    _git_command,
    _load_json,
    _parse_iso_timestamp,
    _reference_now,
)

# Split out of _artifact_history.py (register D6 note): that file sat at 799
# lines against the 800-line hard cap (common/scripts/check_module_size.py),
# and closing loop-ownership P1s needed net-new lines for the
# out_of_plan_cleanup phase checks below. G28 is the half of the D6-named
# "G19/G28" pair that moves; G19 stays in _artifact_history.py at its pinned
# line 307 (scripts/_schema_compat_selftest.py asserts
# "_artifact_history.py:307" verbatim as the shipped optional-with-shape-
# gating precedent cited from references/output-format-migrations.md, a file
# outside this change's ownership — moving G19 too would break that pin for
# no offsetting benefit, since G28 alone frees enough headroom).
# _artifact_history.py re-exports check_g28_loop_state_freshness so its
# existing consumers (validate-artifact.py) are unaffected.

_CLEANUP_SUBPHASES = {"restoring", "committing", "done"}


def _check_g28_out_of_plan_cleanup_phase(loop_state: dict) -> list[Issue]:
    """G28 (out_of_plan_cleanup phase): checkpoint shape per
    output-format-state-schemas.md § Out-of-plan cleanup phase.

    This phase checkpoint is written by the loop subagent (not main, unlike
    the halt_success_panel phase) when Step 3 sub-step 6 finds a delta
    outside the Step 2 plan's predicted touch paths. It replaces the normal
    step_started/step_completed schema for the duration of the cleanup
    transaction, so none of the checks above apply to it.
    """
    issues: list[Issue] = []
    cleanup = loop_state.get("cleanup_state")
    if not isinstance(cleanup, dict):
        issues.append(
            Issue(
                "G28",
                "LOOP_STATE.cleanup_state must be an object when phase == 'out_of_plan_cleanup'",
            )
        )
        return issues

    planned = cleanup.get("planned_paths")
    if not isinstance(planned, dict):
        issues.append(
            Issue(
                "G28",
                "cleanup_state.planned_paths must be an object (path -> blob sha | null), "
                "copied from LOOP_STATE.pre_step3_blob_shas at detection time",
            )
        )

    unexpected = cleanup.get("unexpected_paths")
    if (
        not isinstance(unexpected, list)
        or not unexpected
        or not all(isinstance(p, str) and p for p in unexpected)
    ):
        issues.append(
            Issue(
                "G28",
                "cleanup_state.unexpected_paths must be a non-empty list of non-empty "
                "strings — it is the reason this phase exists; empty means nothing was "
                "out-of-plan and this checkpoint should never have been written",
            )
        )

    subphase = cleanup.get("cleanup_subphase")
    if subphase not in _CLEANUP_SUBPHASES:
        issues.append(
            Issue(
                "G28",
                f"cleanup_state.cleanup_subphase={subphase!r} must be one of "
                f"{sorted(_CLEANUP_SUBPHASES)}",
            )
        )

    draft = cleanup.get("halt_commit_draft")
    if (
        not isinstance(draft, dict)
        or not isinstance(draft.get("subject"), str)
        or not draft.get("subject")
    ):
        issues.append(
            Issue(
                "G28",
                "cleanup_state.halt_commit_draft.subject must be a non-empty string — "
                "resume matches HEAD's commit subject against it to detect a landed "
                "halt commit without a commit_attempted_sha field",
            )
        )

    return issues


def check_g28_loop_state_freshness(
    artifact_dir: Path,
    current_review: dict,
    project_config: dict | None = None,
) -> list[Issue]:
    """G28 (full): LOOP_STATE.json invariants per validation.md:113-120.
    Schema_version >= 3.

    Sub-checks:
    - loop-number consistency (loop_state.loop == current_review.loop)
    - checkpoint freshness (last_checkpoint_at not >24h before now)
    - step range (step_started ∈ 1..11, step_completed ∈ 0..11)
    - step ordering (step_started >= step_completed)
    - pre_step3_blob_shas covers loop_result.changed_paths
    - post-commit cleanup: LOOP_STATE.json must be absent when commit_attempted_sha
      matches git HEAD (requires project_config + git available)

    A non-null top-level `phase` field means LOOP_STATE.json is not this legacy
    mid-Step-3 checkpoint at all (see output-format-state-schemas.md § Panel phase
    and § Out-of-plan cleanup phase) — none of the checks above apply to it.
    `out_of_plan_cleanup` gets its own shape check; any other phase (e.g.
    `halt_success_panel`, written and resumed by main, not by this loop-side gate)
    is out of scope here and validated where it is created.
    """
    issues: list[Issue] = []
    if (current_review.get("schema_version") or 1) < 3:
        return issues
    loop_state_path = artifact_dir / "LOOP_STATE.json"
    if not loop_state_path.exists():
        return issues  # post-commit cleanup state is legal
    loop_state = _load_json(loop_state_path)
    if not isinstance(loop_state, dict):
        issues.append(
            Issue(
                "G28",
                "LOOP_STATE.json must be a JSON object",
            )
        )
        return issues

    phase = loop_state.get("phase")
    if phase is not None:
        if phase == "out_of_plan_cleanup":
            return _check_g28_out_of_plan_cleanup_phase(loop_state)
        return issues

    ls_loop = loop_state.get("loop")
    cr_loop = current_review.get("loop")
    if ls_loop != cr_loop:
        issues.append(
            Issue(
                "G28",
                f"LOOP_STATE.loop={ls_loop!r} must equal CURRENT_REVIEW.loop={cr_loop!r} "
                "(mismatch routes to --reset per Resume Precedence Matrix row 3)",
            )
        )

    step_started = loop_state.get("step_started")
    step_completed = loop_state.get("step_completed")
    if not isinstance(step_started, int) or step_started not in range(1, 12):
        issues.append(
            Issue(
                "G28",
                f"LOOP_STATE.step_started={step_started!r} must be int in 1..11",
            )
        )
    if not isinstance(step_completed, int) or step_completed not in range(12):
        issues.append(
            Issue(
                "G28",
                f"LOOP_STATE.step_completed={step_completed!r} must be int in 0..11",
            )
        )
    if (
        isinstance(step_started, int)
        and isinstance(step_completed, int)
        and step_started < step_completed
    ):
        issues.append(
            Issue(
                "G28",
                f"LOOP_STATE.step_started={step_started} < step_completed={step_completed} "
                "(step_started >= step_completed required)",
            )
        )

    last_checkpoint_raw = loop_state.get("last_checkpoint_at")
    last_checkpoint = _parse_iso_timestamp(last_checkpoint_raw)
    if last_checkpoint is None:
        issues.append(
            Issue(
                "G28",
                f"LOOP_STATE.last_checkpoint_at={last_checkpoint_raw!r} not ISO-8601 parseable",
            )
        )
    else:
        now = _reference_now()
        age_seconds = (now - last_checkpoint).total_seconds()
        if age_seconds > _G28_ORPHAN_SECONDS:
            issues.append(
                Issue(
                    "G28",
                    f"LOOP_STATE.last_checkpoint_at={last_checkpoint_raw!r} is "
                    f"{age_seconds / 3600:.1f}h old (>24h orphan threshold); "
                    "routes to --reset recommendation per Resume Precedence Matrix row 2",
                )
            )

    # pre_step3_blob_shas cross-check (artifact-only, no git required).
    # Per validation.md:118: empty pre_step3_blob_shas AND non-empty
    # loop_result.changed_paths = G28 failure (no restore source recorded).
    loop_result = current_review.get("loop_result") or {}
    changed_paths = loop_result.get("changed_paths") or []
    blob_shas = loop_state.get("pre_step3_blob_shas") or {}
    if changed_paths and not blob_shas:
        issues.append(
            Issue(
                "G28",
                f"LOOP_STATE.pre_step3_blob_shas is empty but loop_result.changed_paths "
                f"has {len(changed_paths)} entries; no restore source recorded "
                "(narrow revert would have no blob to checkout)",
            )
        )
    elif changed_paths and isinstance(blob_shas, dict):
        missing = [p for p in changed_paths if p not in blob_shas]
        if missing:
            issues.append(
                Issue(
                    "G28",
                    f"loop_result.changed_paths has {len(missing)} entries missing from "
                    f"LOOP_STATE.pre_step3_blob_shas: {missing[:3]}"
                    f"{'…' if len(missing) > 3 else ''}",
                )
            )

    # Post-commit cleanup invariant (requires project_config + git).
    # Per validation.md:117: after Step 3 sub-step 11.f, LOOP_STATE.json must
    # be absent. Presence after a successful commit (commit_attempted_sha
    # matches git HEAD) is a violation.
    if project_config is None:
        return issues
    commit_sha = loop_state.get("commit_attempted_sha")
    if not isinstance(commit_sha, str) or not commit_sha:
        return issues
    git_root = _find_git_root(artifact_dir)
    if git_root is None:
        return issues
    rc, head_sha = _git_command(git_root, "rev-parse", "HEAD")
    if rc != 0 or not head_sha.strip():
        return issues
    head_sha = head_sha.strip()
    if head_sha == commit_sha:
        issues.append(
            Issue(
                "G28",
                f"LOOP_STATE.json present after successful commit (commit_attempted_sha "
                f"== HEAD {head_sha[:12]}); sub-step 11.f cleanup did not run",
            )
        )
    return issues
