"""Residual and scorecard-coherence gates: G5 (converse), G37, G43.

Carved out of _artifact_halt.py when G37's trigger widened past that module's LoC
headroom. The split is independently correct: these three gates all answer "is this
scorecard internally coherent about what it is NOT claiming", which is a different
question from _artifact_halt.py's "is this halt state well-formed".
"""

from __future__ import annotations

import re

from _artifact_core import Issue

# Only "structural_anchor_unmet" licenses keeping a dimension below 9.5. The promotion
# triggers mean the 9-anchor IS met, so the dimension must be promoted to 9.5 with
# residual_disposition: "accepted" -- see references/method-critic.md § Residual Accounting Pass.
_STRUCTURAL_KIND = "structural_anchor_unmet"
_PROMOTION_TRIGGER_KINDS = {"ceremony", "framework_constrained", "cosmetic", "adr_carved_out"}

# Deliberately PERMISSIVE, and deliberately not _G39_ENTRY_RE. G39 owns the strict
# `<dim> <signed delta>` shape of score_impact; G37 only needs best-effort attribution and
# must not double-report a shape error G39 already owns. So `"data_flow +0.5 once verified"`
# (a G39 failure) still attributes to data_flow here and only G39 speaks. Genuinely free
# prose attributes to nothing and both gates fire -- honest, because such an artifact really
# does carry no machine attribution.
_DIM_PREFIX_RE = re.compile(r"^\s*([a-z_]+)")

_RESIDUAL_FIELDS = (
    "residual_blocking_10",
    "residual_disposition",
    "residual_rationale_or_backlog_ref",
)


def _scored_dimensions(scorecard: dict) -> list[tuple[str, float, dict]]:
    """(dim, score, entry) for every dimension carrying a numeric score."""
    out: list[tuple[str, float, dict]] = []
    for dim, entry in scorecard.items():
        if not isinstance(entry, dict):
            continue
        try:
            score = float(entry.get("score"))
        except (TypeError, ValueError):
            continue
        out.append((dim, score, entry))
    return out


def _dims_named_by_backlog(backlog) -> set[str]:
    """Dimension ids any backlog item's score_impact refers to (best-effort)."""
    named: set[str] = set()
    for item in backlog or []:
        if not isinstance(item, dict):
            continue
        impact = item.get("score_impact")
        if not isinstance(impact, str):
            continue
        for entry in impact.split(";"):
            match = _DIM_PREFIX_RE.match(entry)
            if match:
                named.add(match.group(1))
    return named


def check_g5_sub95_residual_fields(current_review: dict) -> list[Issue]:
    """G5 converse (rule #12): a score below 9.5, or exactly 10, carries no residual fields.

    G5's forward half ("every score >= 9.5 names the residual blocking 10") stays a Critic
    checklist item -- mechanizing it would break `halt-loop-cap-clean`, an expected-pass
    fixture that violates it on all 9 dimensions, and that is separate work. This is the
    converse only, and it had zero violations across the 65-artifact corpus at the time it
    landed, so it rejects only genuinely incoherent artifacts.

    The production shape it exists for: `test_strategy: 8.5` carrying
    `residual_disposition: "accepted"`. The rubric puts an accepted residual at 9.5 -- a
    score below that is not accepting a residual, it is deferring one, and no gate said so.

    Not schema-floored: rule #12 predates every schema version.
    """
    issues: list[Issue] = []
    scorecard = current_review.get("scorecard") or {}
    if not isinstance(scorecard, dict):
        return issues  # scorecard shape is check_schema_enums / G21's concern

    for dim, score, entry in _scored_dimensions(scorecard):
        if 9.5 <= score < 10:
            continue  # the forward half's territory, deliberately unmechanized
        populated = [f for f in _RESIDUAL_FIELDS if entry.get(f) is not None]
        if not populated:
            continue
        if score < 9.5:
            issues.append(
                Issue(
                    "G5",
                    f"dimension {dim!r} score={score} < 9.5 carries {', '.join(populated)} "
                    f"(residual_disposition={entry.get('residual_disposition')!r}); the rubric puts an "
                    f"accepted residual at 9.5 -- either raise the score to 9.5 with a named residual, "
                    f"or null the residual fields and account for the gap via the backlog or "
                    f"residual_blocker_kind",
                )
            )
        else:  # score == 10
            issues.append(
                Issue(
                    "G5",
                    f"dimension {dim!r} score=10 carries {', '.join(populated)}; a 10 means no "
                    f"source-backed residual exists (G6). A named residual and a 10 cannot both be true",
                )
            )
    return issues


def check_g37_terminal_residual_accounting(current_review: dict) -> list[Issue]:
    """G37: no terminal scorecard may strand a sub-9.5 dimension.

    Every dimension scoring < 9.5 at a terminal must be accounted for by exactly one of:
      (a) a backlog[] item whose score_impact names it -- there is queued work for it; or
      (c) residual_blocker_kind == "structural_anchor_unmet" -- a named structural ceiling.

    Account (b), residual_disposition == "accepted", is deliberately NOT implemented here:
    an "accepted" disposition below 9.5 is itself the violation and is owned by G5's
    converse. Do not "restore" it -- doing so would license the exact incoherence G5 rejects.

    Trigger: state in {HALT_LOOP_CAP, HALT_STAGNATION}, EVERY subtype, ANY backlog.
    Widened from the original closed set (HALT_STAGNATION/no_backlog, or HALT_LOOP_CAP with an
    empty backlog). That set assumed a non-empty backlog explains the sub-9.5 gaps -- true only
    for the dimensions the backlog actually names. The production artifact that motivated the
    widening ended HALT_LOOP_CAP with two backlog items naming architecture_quality and
    concurrency, while data_flow sat at 7.5 with residual_disposition, residual_blocking_10 and
    residual_blocker_kind all null and no backlog item naming it. It validated clean.

    Bypasses: CONTINUE (not a terminal), HALT_DRY_RUN (G23's documented bypass -- the dry run
    halts before Step 3 evidence exists), and HALT_SUCCESS(_candidate), where G21 already
    requires 10-or-9.5-accepted on every dimension. Keeping G37 out of the success states also
    preserves _g37_selftest.py's isolation harness against check_g21_scorecard.
    Schema_version >= 4.
    """
    issues: list[Issue] = []
    if (current_review.get("schema_version") or 1) < 4:
        return issues
    state = current_review.get("state")
    if state not in ("HALT_LOOP_CAP", "HALT_STAGNATION"):
        return issues

    scorecard = current_review.get("scorecard") or {}
    if not isinstance(scorecard, dict):
        return issues  # scorecard shape is check_schema_enums / G21's concern

    backlog = current_review.get("backlog") or []
    backlog_dims = _dims_named_by_backlog(backlog)
    subtype = current_review.get("halt_subtype")
    terminal = f"{state}/{subtype}" if subtype else state

    for dim, score, entry in _scored_dimensions(scorecard):
        if score >= 9.5:
            continue
        if dim in backlog_dims:
            continue  # (a) queued work names it
        kind = entry.get("residual_blocker_kind")
        if kind == _STRUCTURAL_KIND:
            continue  # (c) a named structural ceiling
        if kind in _PROMOTION_TRIGGER_KINDS:
            issues.append(
                Issue(
                    "G37",
                    f"{terminal} dimension {dim!r} score={score} < 9.5 cites promotion-trigger "
                    f"residual_blocker_kind={kind!r}; the Residual Accounting Pass requires promoting it "
                    f"to 9.5 with residual_disposition='accepted' (only 'structural_anchor_unmet' "
                    f"licenses keeping a dimension below 9.5 at a terminal)",
                )
            )
        elif kind is None:
            issues.append(
                Issue(
                    "G37",
                    f"{terminal} dimension {dim!r} score={score} < 9.5 is unaccounted: no backlog[] "
                    f"item's score_impact names it and residual_blocker_kind is not "
                    f"'structural_anchor_unmet'. A terminal scorecard may not strand a dimension -- "
                    f"file it to the backlog, tag the structural blocker, or promote to 9.5-accepted",
                )
            )
        # any other non-null value is an unknown enum token -- owned by check_schema_enums
    return issues
