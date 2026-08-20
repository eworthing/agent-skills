"""Residual and scorecard-coherence gates: G5 (forward + converse), G37, G43.

G43's convergence-pass record is the third: a dimension that keeps reporting "nothing
to do" must keep proposing something new to have found nothing about.

Carved out of _artifact_halt.py when G37's trigger widened past that module's LoC
headroom. The split is independently correct: these three gates all answer "is this
scorecard internally coherent about what it is NOT claiming", which is a different
question from _artifact_halt.py's "is this halt state well-formed".
"""

from __future__ import annotations

import re

import _ruleset_epoch
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

    G5's forward half ("every score >= 9.5 names the residual blocking 10") is mechanized
    separately by `check_g5_forward_residual_fields` below. This is the converse only, and
    it had zero violations across the 65-artifact corpus at the time it landed, so it
    rejects only genuinely incoherent artifacts.

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
        else:  # score >= 10
            issues.append(
                Issue(
                    "G5",
                    f"dimension {dim!r} score={score} carries {', '.join(populated)}; a 10 means no "
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

    Trigger: state in {HALT_LOOP_CAP, HALT_STAGNATION, HALT_EXHAUSTION}, EVERY subtype, ANY
    backlog. Widened from the original closed set (HALT_STAGNATION/no_backlog, or HALT_LOOP_CAP
    with an empty backlog). That set assumed a non-empty backlog explains the sub-9.5 gaps --
    true only for the dimensions the backlog actually names. The production artifact that
    motivated the widening ended HALT_LOOP_CAP with two backlog items naming architecture_quality
    and concurrency, while data_flow sat at 7.5 with residual_disposition, residual_blocking_10
    and residual_blocker_kind all null and no backlog item naming it. It validated clean.
    HALT_EXHAUSTION (backlog item 17) joined the trigger set for the same reason: a run that
    dies mid-loop at 8.0 on three dimensions strands them exactly like a cap halt does -- running
    out of budget is not an account for the gap any more than reaching the loop cap is.

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
    if state not in ("HALT_LOOP_CAP", "HALT_STAGNATION", "HALT_EXHAUSTION"):
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


_FORWARD_REQUIRED_FIELDS = ("residual_blocking_10", "residual_rationale_or_backlog_ref")


def check_g5_forward_residual_fields(current_review: dict) -> list[Issue]:
    """G5 forward half (rule #12): every score in [9.5, 10) names the residual blocking 10.

    Complements `check_g5_sub95_residual_fields` above: that function rejects residual
    fields OUTSIDE [9.5, 10); this rejects their ABSENCE INSIDE it. Together the two pin
    the range exactly -- residual fields live at [9.5, 10) and nowhere else.

    Only `residual_blocking_10` and `residual_rationale_or_backlog_ref` are required
    non-null here. `residual_disposition` is deliberately not checked by this function:
    G21-scorecard already requires `residual_disposition == "accepted"` on every
    HALT_SUCCESS(_candidate) dimension in [9.5, 10), and G37 account (b) is intentionally
    unimplemented, so a scorecard entry naming a residual and rationale but leaving
    disposition null (e.g. a mid-loop CONTINUE dimension not yet dispositioned) is not
    itself a forward-half violation.

    Previously a Critic checklist item only: mechanizing it used to break
    `halt-loop-cap-clean`, an expected-pass fixture that violated it on all 9 dimensions.
    That fixture (and its six siblings in the same shape) has since been repaired to carry
    both fields on every 9.5-and-above dimension, so the forward half is now mechanized.
    """
    issues: list[Issue] = []
    scorecard = current_review.get("scorecard") or {}
    if not isinstance(scorecard, dict):
        return issues  # scorecard shape is check_schema_enums / G21's concern

    for dim, score, entry in _scored_dimensions(scorecard):
        if not (9.5 <= score < 10):
            continue
        missing = [f for f in _FORWARD_REQUIRED_FIELDS if entry.get(f) is None]
        if missing:
            issues.append(
                Issue(
                    "G5",
                    f"dimension {dim!r} score={score} is in [9.5, 10) but missing "
                    f"{', '.join(missing)}; rule #12 requires every 9.5-and-above dimension "
                    f"to name the residual blocking 10 -- either supply both fields or move "
                    f"the score outside [9.5, 10)",
                )
            )
    return issues


# --- G43: convergence-pass coverage -------------------------------------------------

_G43_STATES = ("CONTINUE", "HALT_LOOP_CAP", "HALT_STAGNATION")
_G43_LOOP_FLOOR = 4  # loop 1's delta is "SAME" by definition; see the gate docstring
_CLEAN_STREAK_OWING_A_FRESH_PROPOSAL = 3
_SPT_QUESTIONS = {"Q1", "Q2", "Q3", "Q4", "Q5", "structural_gate"}


def _prior_loops(current_review: dict, history: dict | None) -> list[dict]:
    """The two most recent archived loops strictly older than this one.

    Filtering on `e.loop < current.loop` and prepending the current artifact's own delta
    reads correctly under BOTH timings with no branch: at Step-1 emit the history holds
    loops 1..N-1, and against a completed artifact G18 requires it to hold 1..N with
    loops[-1] == CURRENT_REVIEW.json.
    """
    loops = (history or {}).get("loops") or []
    try:
        current_loop = int(current_review.get("loop"))
    except (TypeError, ValueError):
        return []
    older = [
        entry
        for entry in loops
        if isinstance(entry, dict)
        and isinstance(entry.get("loop"), int)
        and entry["loop"] < current_loop
    ]
    older.sort(key=lambda e: e["loop"])
    return older[-2:]


def _proposal_target(record: dict) -> tuple | None:
    """The structured identity of a proposed fix: (fix_kind, target_path, target_symbol).

    Deliberately NOT a hash of the prose. A production finding -- "Free-form residual
    wording defeats candidate recurrence" -- established that hashing free-form text is
    defeatable, because a reword yields a new hash while meaning the same thing. `note`
    and `clean_rationale` are excluded for exactly that reason: a loop obliged to propose
    something new must change the target or the kind, not the wording.
    """
    fix = record.get("proposed_fix")
    if not isinstance(fix, dict):
        return None
    return (fix.get("fix_kind"), fix.get("target_path"), fix.get("target_symbol"))


def _records_by_dim(review: dict) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for record in review.get("convergence_pass") or []:
        if isinstance(record, dict) and isinstance(record.get("dimension"), str):
            out.setdefault(record["dimension"], record)
    return out


def _clean_streak(dim: str, current: dict, priors: list[dict]) -> int:
    """Consecutive loops ending at this one whose record for `dim` was a clean.

    Bounded by the two-loop lookback, so it saturates at 3 and never reports the true
    length of a longer streak -- hence "at least N" in the messages. Widening the lookback
    would buy a bigger number and no extra discrimination: the threshold is 3.
    """
    streak = 0
    for review in [current, *reversed(priors)]:
        record = _records_by_dim(review).get(dim)
        if record is None or record.get("outcome") != "clean":
            break
        streak += 1
    return streak


def check_g43_convergence_pass(
    current_review: dict, history: dict | None, canon=None
) -> list[Issue]:
    """G43: a convergence pass must be recorded, and a repeated clean must propose anew.

    Two passes re-test a stalled dimension each loop -- the Stalled-Dimension Sweep (for a
    sub-9.5 dimension whose delta has been SAME for three or more loops) and the Adversarial
    Pass on Accepted Residuals (for a 9.5-accepted dimension, every loop). Both were prose
    obligations with no gate, and their outcomes across 55 production loops tracked their
    contracts exactly: the Adversarial Pass demands a newly proposed smallest fix plus the
    SPT question it failed, and produced three structurally distinct candidates; the Sweep
    permits "a named candidate OR an explicit clean", and decayed to a bare "explicit clean."
    while the same file stayed the named blocker for 40 of 40 loops with no movement.

    Both runs that had the Sweep were fully COMPLIANT with it. That is why this gate keys on
    repetition, not presence: a gate that merely required the record would have passed every
    failing loop.

    A dimension is owed a record when it is stalled sub-9.5 or 9.5-accepted. It is accounted
    by a convergence_pass[] record naming it, or by a backlog[] item whose score_impact names
    it (it was filed, so the failure mode cannot apply). Once a dimension has answered "clean"
    for three consecutive loops, its record must also carry a `proposed_fix` whose
    (fix_kind, target_path, target_symbol) differs from the prior loop's, plus the
    `spt_question_failed` that rejected it. Rewording `note` or `clean_rationale` changes
    nothing.

    Floor: schema_version >= 4 AND loop >= 4. Loop 1's delta is "SAME" by definition, so at
    loop 4 the three observations are loops 4/3/2 and loop 2's is the first real one -- firing
    at loop 3 would count a definitional SAME as evidence of a stall.

    Epoch-scoped (backlog item [I1]): this requirement was added 2026-08-06, after artifacts
    already existed on disk (this skill's own dogfood run among them). It applies only to
    artifacts `_ruleset_epoch` classifies at-or-after CURRENT -- see that module for the
    skill_rev-based classifier and why a marker-less artifact is never retroactively failed.
    """
    issues: list[Issue] = []
    if (current_review.get("schema_version") or 1) < 4:
        return issues
    if not _ruleset_epoch.applies("G43_CONVERGENCE_PASS", current_review, history):
        return issues
    loop = current_review.get("loop")
    if isinstance(loop, bool) or not isinstance(loop, int) or loop < _G43_LOOP_FLOOR:
        return issues
    if current_review.get("state") not in _G43_STATES:
        return issues

    scorecard = current_review.get("scorecard") or {}
    if not isinstance(scorecard, dict):
        return issues

    priors = _prior_loops(current_review, history)
    records = _records_by_dim(current_review)
    fix_kinds = set((canon.extra.get("fix_kinds") if canon is not None else None) or ())

    # --- shape check: every record present must be well-formed, trigger or not ---
    for record in current_review.get("convergence_pass") or []:
        issues.extend(_check_record_shape(record, scorecard, current_review, fix_kinds))

    if len(priors) < 2:
        return issues  # history shape is G18's business; too little to judge a stall

    backlog_dims = _dims_named_by_backlog(current_review.get("backlog"))

    for dim, score, entry in _scored_dimensions(scorecard):
        stalled_sweep = score < 9.5 and _all_same(dim, current_review, priors)
        adversarial = score >= 9.5 and entry.get("residual_disposition") == "accepted"
        if not (stalled_sweep or adversarial):
            continue
        if dim in backlog_dims:
            continue  # it was filed; the restatement failure mode cannot apply

        record = records.get(dim)
        if record is None:
            pass_name = "stalled_sweep" if stalled_sweep else "adversarial"
            issues.append(
                Issue(
                    "G43",
                    f"dimension {dim!r} is owed a {pass_name} convergence pass "
                    f"({'sub-9.5 and SAME for 3 loops' if stalled_sweep else '9.5 with an accepted residual'}) "
                    f"but convergence_pass[] carries no record for it, and no backlog item names it",
                )
            )
            continue

        if record.get("outcome") != "clean":
            continue
        streak = _clean_streak(dim, current_review, priors)
        if streak < _CLEAN_STREAK_OWING_A_FRESH_PROPOSAL:
            continue

        target = _proposal_target(record)
        if target is None or not all(target):
            issues.append(
                Issue(
                    "G43",
                    f"dimension {dim!r} has answered 'clean' for at least {streak} consecutive loops; "
                    f"the record must carry a structured proposed_fix (fix_kind, target_path, "
                    f"target_symbol) naming what was tried and rejected. A clean repeated without "
                    f"a fresh proposal is a restatement, not an investigation",
                )
            )
            continue
        if record.get("spt_question_failed") not in _SPT_QUESTIONS:
            issues.append(
                Issue(
                    "G43",
                    f"dimension {dim!r} proposed a fix on a {streak}-loop clean streak but did not "
                    f"name the Simplify Pressure Test question that rejected it "
                    f"(spt_question_failed ∈ {sorted(_SPT_QUESTIONS)})",
                )
            )
        prior_record = _records_by_dim(priors[-1]).get(dim) or {}
        prior_target = _proposal_target(prior_record)
        if prior_target is not None and prior_target == target:
            issues.append(
                Issue(
                    "G43",
                    f"dimension {dim!r} repeated the SAME proposed_fix target as the prior loop "
                    f"{prior_target!r} on a {streak}-loop clean streak. Novelty is judged on "
                    f"(fix_kind, target_path, target_symbol), never on the prose: rewording `note` "
                    f"or `clean_rationale` does not make a proposal new",
                )
            )
    return issues


def _all_same(dim: str, current_review: dict, priors: list[dict]) -> bool:
    """True when `dim`'s delta is 'SAME' across this loop and both priors."""
    for review in [current_review, *priors]:
        entry = (review.get("scorecard") or {}).get(dim)
        if not isinstance(entry, dict) or entry.get("delta") != "SAME":
            return False
    return True


def _check_record_shape(
    record, scorecard: dict, current_review: dict, fix_kinds: set[str]
) -> list[Issue]:
    """Shape of one convergence_pass[] record, independent of whether it was owed."""
    issues: list[Issue] = []
    if not isinstance(record, dict):
        return [
            Issue("G43", f"convergence_pass[] entry must be an object, got {type(record).__name__}")
        ]

    dim = record.get("dimension")
    if not isinstance(dim, str) or dim not in scorecard:
        issues.append(
            Issue(
                "G43", f"convergence_pass[] dimension {dim!r} is not a dimension of this scorecard"
            )
        )
    if record.get("pass") not in ("stalled_sweep", "adversarial"):
        issues.append(
            Issue(
                "G43",
                f"convergence_pass[] entry for {dim!r} has pass={record.get('pass')!r}; "
                f"expected 'stalled_sweep' or 'adversarial'",
            )
        )
    outcome = record.get("outcome")
    if outcome not in ("candidate", "clean"):
        issues.append(
            Issue(
                "G43",
                f"convergence_pass[] entry for {dim!r} has outcome={outcome!r}; "
                f"expected 'candidate' or 'clean'",
            )
        )
    surface = record.get("surface_walked")
    if not isinstance(surface, str) or not surface.strip():
        issues.append(
            Issue(
                "G43",
                f"convergence_pass[] entry for {dim!r} must name the surface_walked it actually "
                f"read; an unnamed surface is the fake-clean the Sweep's own prose rejects",
            )
        )
    if outcome == "candidate":
        stable_id = record.get("finding_stable_id")
        known = {
            f.get("stable_id")
            for f in (current_review.get("findings") or [])
            if isinstance(f, dict)
        }
        if stable_id not in known:
            issues.append(
                Issue(
                    "G43",
                    f"convergence_pass[] entry for {dim!r} claims a candidate but "
                    f"finding_stable_id={stable_id!r} is not in this loop's findings[]. A named "
                    f"candidate routes through the evidence chain, not through prose",
                )
            )
    elif outcome == "clean":
        rationale = record.get("clean_rationale")
        if not isinstance(rationale, str) or not rationale.strip():
            issues.append(
                Issue(
                    "G43",
                    f"convergence_pass[] entry for {dim!r} is a clean with no clean_rationale; "
                    f"'nothing found' is fake-clean reward, not a rationale",
                )
            )
    fix = record.get("proposed_fix")
    if isinstance(fix, dict) and fix_kinds and fix.get("fix_kind") not in fix_kinds:
        issues.append(
            Issue(
                "G43",
                f"convergence_pass[] entry for {dim!r} has fix_kind={fix.get('fix_kind')!r}; "
                f"expected one of {sorted(fix_kinds)} (canon/fix-kinds.toml)",
            )
        )
    return issues
