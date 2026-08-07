"""G32: HALT_SUCCESS independent-challenge gate -- v4 single-challenger contract plus
the v5 panel extension (Tier 1 of Recommendation 1, plans/rec1-panel-certification.md).

Carved out of _artifact_halt.py when the panel work needed room the module's 800-line
cap did not have -- mirrors the G37 -> _artifact_residual.py split done earlier this
session. Same gate id, same concern; v5 extends WHAT counts as an independent
challenge (three staged challengers instead of one), not the gate's purpose.

Stateless and single-artifact only. Anything temporal or cross-artifact --
protocol_digest comparison, candidate_binding copy-forward immutability,
resume/rollback routing -- is out of scope; the plan flags this exact mistake three
times and this module holds the line (routing/resume logic owns it, with its own
behavioral tests).
"""

from __future__ import annotations

import re

from _artifact_core import Issue
from candidate_fingerprint import candidate_fingerprint

_V5_MEMBER_OUTCOMES = {"held", "broke", "unavailable"}
_V5_AGGREGATE_OUTCOMES = {"held", "broke", "blocked", "pending"}
_V5_RETRY_CAUSES = {"timeout", "spawn_error", "malformed_json", "budget_exhausted"}
_V5_RETRY_ATTEMPT_OUTCOMES = {"ok", "timeout", "spawn_error", "malformed_json", "budget_exhausted"}
_V5_NORMALIZATION_MARKERS = {"pending_user_decision", "deferred_by_pending_registry_decision"}
_V5_PROTOCOL_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]+$")

# A findings[] entry minus the two main-assigned ids (stable_id, loop_local_id).
_RAW_FINDING_STRING_FIELDS = (
    "title",
    "why_it_matters",
    "what_is_wrong",
    "why_weakens_submission",
    "minimal_correction_path",
)


def _g32(msg: str) -> Issue:
    return Issue("G32", msg)


def _check_attempts_shape(attempts, ctx: str) -> list[Issue]:
    """Attempts[] shape + the new_finding/simplicity|domain_modeling diversity arm.

    Shared by v4's single challenge (ctx="halt_success_challenge") and v5's
    per-member attempts (ctx="...panel[N]") -- the plan reuses "the v4 diversity
    rule per member" verbatim, so one function serves both call sites.
    """
    issues: list[Issue] = []
    if not isinstance(attempts, list) or len(attempts) == 0:
        issues.append(_g32(f"{ctx}.attempts must be a non-empty list"))
        return issues
    has_diversity_arm = False
    for i, attempt in enumerate(attempts):
        if not isinstance(attempt, dict):
            issues.append(_g32(f"{ctx}.attempts[{i}] must be an object"))
            continue
        for field in ("arm", "target", "what_tried", "why_failed"):
            value = attempt.get(field)
            if not isinstance(value, str) or not value.strip():
                issues.append(_g32(f"{ctx}.attempts[{i}].{field} must be non-empty"))
        arm = attempt.get("arm")
        if isinstance(arm, str) and arm not in {"new_finding", "residual_refutation"}:
            issues.append(_g32(f"{ctx}.attempts[{i}].arm={arm!r} invalid"))
        if arm == "new_finding" and attempt.get("target") in {"simplicity", "domain_modeling"}:
            has_diversity_arm = True
    if not has_diversity_arm:
        issues.append(_g32(f"{ctx}.attempts needs a new_finding arm on simplicity/domain_modeling"))
    return issues


def check_g32_halt_success_challenge(current_review: dict) -> list[Issue]:
    """G32: HALT_SUCCESS terminal state (v4+) requires an independent challenge.

    schema_version == 4 (unchanged, single-challenger contract): on HALT_SUCCESS,
    halt_success_challenge is non-null with outcome=='held', a non-empty
    challenger_model, diverse attempts[], a non-empty reason, and binding.run_id /
    .source_rev matching the top-level fields. On HALT_SUCCESS_candidate the
    challenge is null and run_id/source_rev/candidate_fingerprint are non-null. For
    either state candidate_fingerprint must equal the canonical digest.

    schema_version >= 5 (Tier 1 panel certification, plans/rec1-panel-certification.md):
    a panel of 3 staged challengers replaces the single challenger. The
    HALT_SUCCESS_candidate rules are unchanged from v4 (same code path below, at
    every v4+ version -- the panel only changes a TERMINAL challenge's shape). On
    HALT_SUCCESS the challenge is required non-null and is the panel record (see
    _check_v5_panel_record). A panel record is also PERMITTED (null legal too) on
    CONTINUE and HALT_STAGNATION/{user_decision,verification_blocked}; every other
    state requires null (see _check_v5_non_terminal_state).

    schema_version < 4: G32 does not fire.
    """
    issues: list[Issue] = []
    schema_version = current_review.get("schema_version") or 1
    if schema_version < 4:
        return issues  # legacy v3 HALT_SUCCESS without a challenge stays valid

    state = current_review.get("state")

    # v5 opens panel-permitted states beyond {HALT_SUCCESS, HALT_SUCCESS_candidate}
    # that v4 has no shape for at all (v4 returns early below for every other state).
    if schema_version >= 5 and state not in ("HALT_SUCCESS", "HALT_SUCCESS_candidate"):
        return _check_v5_non_terminal_state(current_review, state)

    if state not in ("HALT_SUCCESS", "HALT_SUCCESS_candidate"):
        return issues

    top_run_id = current_review.get("run_id")
    top_source_rev = current_review.get("source_rev")
    top_fingerprint = current_review.get("candidate_fingerprint")
    challenge = current_review.get("halt_success_challenge")

    expected_fingerprint = candidate_fingerprint(current_review)
    if top_fingerprint != expected_fingerprint:
        issues.append(
            _g32(f"candidate_fingerprint={top_fingerprint!r} != canonical {expected_fingerprint!r}")
        )

    if state == "HALT_SUCCESS_candidate":
        # Unchanged from v4 at every v4+ schema version -- the panel changes only
        # the shape of a TERMINAL HALT_SUCCESS's challenge, not the candidate.
        if challenge is not None:
            issues.append(
                _g32("state=HALT_SUCCESS_candidate must have halt_success_challenge=null")
            )
        if not top_run_id:
            issues.append(_g32("state=HALT_SUCCESS_candidate requires run_id non-null (v4+)"))
        if not top_source_rev:
            issues.append(_g32("state=HALT_SUCCESS_candidate requires source_rev non-null (v4+)"))
        if not top_fingerprint:
            issues.append(
                _g32("state=HALT_SUCCESS_candidate requires candidate_fingerprint non-null (v4+)")
            )
        return issues

    # state == "HALT_SUCCESS" (terminal)
    if schema_version >= 5:
        if challenge is None:
            issues.append(
                _g32(
                    "state=HALT_SUCCESS at v5 requires halt_success_challenge non-null (panel of 3)"
                )
            )
            return issues
        if not isinstance(challenge, dict):
            issues.append(
                _g32(f"halt_success_challenge must be an object, got {type(challenge).__name__}")
            )
            return issues
        issues.extend(
            _check_v5_panel_record(
                current_review,
                challenge,
                state,
                None,
                top_run_id=top_run_id,
                top_source_rev=top_source_rev,
                top_fingerprint=top_fingerprint,
            )
        )
        return issues

    # schema_version == 4: single-challenger contract below, unchanged.
    if challenge is None:
        issues.append(_g32("state=HALT_SUCCESS at v4+ requires halt_success_challenge non-null"))
        return issues
    if not isinstance(challenge, dict):
        issues.append(
            _g32(f"halt_success_challenge must be an object, got {type(challenge).__name__}")
        )
        return issues

    outcome = challenge.get("outcome")
    if outcome == "broke":
        issues.append(
            _g32("halt_success_challenge.outcome='broke' with state=HALT_SUCCESS is illegal")
        )
    elif outcome != "held":
        issues.append(_g32(f"halt_success_challenge.outcome={outcome!r} must be 'held'"))

    challenger_model = challenge.get("challenger_model")
    if not isinstance(challenger_model, str) or not challenger_model.strip():
        issues.append(_g32("halt_success_challenge.challenger_model must be non-empty"))

    issues.extend(_check_attempts_shape(challenge.get("attempts"), "halt_success_challenge"))

    reason = challenge.get("reason")
    if not isinstance(reason, str) or not reason.strip():
        issues.append(_g32("halt_success_challenge.reason must be non-empty"))

    binding = challenge.get("binding")
    if not isinstance(binding, dict):
        issues.append(_g32("halt_success_challenge.binding must be an object"))
    else:
        candidate_commit_sha = binding.get("candidate_commit_sha")
        if not isinstance(candidate_commit_sha, str) or not candidate_commit_sha.strip():
            issues.append(
                _g32("halt_success_challenge.binding.candidate_commit_sha must be non-empty")
            )
        binding_run_id = binding.get("run_id")
        if binding_run_id != top_run_id:
            issues.append(
                _g32(f"binding.run_id={binding_run_id!r} != top-level run_id={top_run_id!r}")
            )
        binding_source_rev = binding.get("source_rev")
        if binding_source_rev != top_source_rev:
            issues.append(
                _g32(
                    f"binding.source_rev={binding_source_rev!r} != top-level source_rev={top_source_rev!r}"
                )
            )

    return issues


def _check_v5_non_terminal_state(current_review: dict, state) -> list[Issue]:
    """schema_version >= 5, state not in {HALT_SUCCESS, HALT_SUCCESS_candidate}.

    A panel record is PERMITTED (null also legal -- a halt can have non-panel
    causes) on CONTINUE and HALT_STAGNATION/{user_decision,verification_blocked}.
    Every other state requires null; v4 never validated this field on these states
    at all (it returned early), so this is territory the panel work opens up.
    """
    subtype = current_review.get("halt_subtype")
    challenge = current_review.get("halt_success_challenge")
    permitted = state == "CONTINUE" or (
        state == "HALT_STAGNATION" and subtype in ("user_decision", "verification_blocked")
    )
    if not permitted:
        if challenge is not None:
            return [
                _g32(
                    f"state={state!r} subtype={subtype!r} at v5 requires halt_success_challenge=null"
                )
            ]
        return []
    if challenge is None:
        return []  # a halt can have non-panel causes
    if not isinstance(challenge, dict):
        return [_g32(f"halt_success_challenge must be an object, got {type(challenge).__name__}")]
    return _check_v5_panel_record(current_review, challenge, state, subtype)


def _check_v5_panel_record(
    current_review: dict,
    challenge: dict,
    state,
    subtype,
    *,
    top_run_id=None,
    top_source_rev=None,
    top_fingerprint=None,
) -> list[Issue]:
    """Full v5 panel shape + aggregate/state coupling.

    Shared by the HALT_SUCCESS terminal path (top_run_id/top_source_rev/
    top_fingerprint supplied, so candidate_binding equality is checked) and the
    CONTINUE / HALT_STAGNATION permitted-but-not-required paths (unsupplied --
    those top-level fields are absent by construction outside HALT_SUCCESS, per
    output-format-json-rules.md:191, so equality is never checked there).
    """
    issues: list[Issue] = []

    rps = challenge.get("required_panel_size")
    if rps != 3:
        issues.append(_g32(f"required_panel_size={rps!r} must be 3 (fixed in v5)"))

    aggregate = challenge.get("outcome")
    if aggregate not in _V5_AGGREGATE_OUTCOMES:
        issues.append(
            _g32(f"outcome={aggregate!r} (aggregate) not in {sorted(_V5_AGGREGATE_OUTCOMES)}")
        )

    digest = challenge.get("protocol_digest")
    if not (isinstance(digest, str) and _V5_PROTOCOL_DIGEST_RE.match(digest)):
        # Shape only -- G32 is a stateless single-artifact validator; the resume
        # router is what compares digests across artifacts.
        issues.append(_g32(f"protocol_digest={digest!r} must match 'sha256:<lowercase hex>'"))

    issues.extend(
        _check_v5_candidate_binding(
            challenge.get("candidate_binding"), state, top_run_id, top_source_rev, top_fingerprint
        )
    )

    panel = challenge.get("panel")
    if not isinstance(panel, list) or not panel:
        issues.append(_g32("panel must be a non-empty array"))
        return issues

    n = len(panel)
    if n not in (1, 3):
        issues.append(_g32(f"panel has {n} entries; the staged launch produces 1 or 3"))
    elif n == 1:
        member1_outcome = panel[0].get("outcome") if isinstance(panel[0], dict) else None
        if member1_outcome not in ("broke", "unavailable"):
            # A single-entry panel is legal only when member 1 broke or was
            # unavailable -- the staged launch never reaches members 2/3 otherwise.
            issues.append(_g32(f"panel has 1 entry but member 1 outcome={member1_outcome!r}"))
    else:  # n == 3
        member1_outcome = panel[0].get("outcome") if isinstance(panel[0], dict) else None
        if member1_outcome != "held":
            # The converse of the staged rule: members 2/3 launch only after
            # member 1 held. A 3-entry panel recording member 1 broke/unavailable
            # describes an execution the staged launch cannot produce.
            issues.append(
                _g32(
                    f"panel has 3 entries but member 1 outcome={member1_outcome!r}; "
                    "members 2/3 launch only after member 1 held"
                )
            )

    for index, member in enumerate(panel, start=1):
        ctx = f"panel[{index - 1}]"
        if not isinstance(member, dict):
            issues.append(_g32(f"{ctx} must be an object"))
            continue
        if member.get("member_index") != index:
            issues.append(
                _g32(f"{ctx}.member_index={member.get('member_index')!r} must be {index}")
            )
        issues.extend(_check_v5_member(member, ctx))
        issues.extend(_check_v5_break_evidence(member, current_review, aggregate, ctx))

    members = [m for m in panel if isinstance(m, dict)]
    issues.extend(_check_v5_aggregate_coupling(current_review, challenge, state, subtype, members))
    return issues


def _check_v5_candidate_binding(
    binding, state, top_run_id, top_source_rev, top_fingerprint
) -> list[Issue]:
    """Shape required on every path; equality against the artifact's top-level
    run_id/source_rev/candidate_fingerprint ONLY when state == HALT_SUCCESS --
    those fields are absent by construction on every other v5-permitted state, so
    comparing there would compare against fields missing for a structural reason.
    """
    if not isinstance(binding, dict):
        return [_g32("candidate_binding must be an object")]
    issues: list[Issue] = []
    for field in ("run_id", "source_rev", "candidate_commit_sha", "candidate_fingerprint"):
        value = binding.get(field)
        if not isinstance(value, str) or not value.strip():
            issues.append(_g32(f"candidate_binding.{field} must be non-empty"))
    if state == "HALT_SUCCESS":
        for field, top_value in (
            ("run_id", top_run_id),
            ("source_rev", top_source_rev),
            ("candidate_fingerprint", top_fingerprint),
        ):
            binding_value = binding.get(field)
            if binding_value != top_value:
                issues.append(
                    _g32(f"candidate_binding.{field}={binding_value!r} != top-level {top_value!r}")
                )
    return issues


def _check_v5_member(member: dict, ctx: str) -> list[Issue]:
    """Per-member shape independent of aggregate outcome: challenger_model,
    outcome enum, reason, attempts[] (v4 diversity rule reused), the v5 retry
    envelope (rule #25 + budget_exhausted), and token_usage arithmetic.
    break_evidence/normalization are aggregate-dependent -- see
    _check_v5_break_evidence.
    """
    issues: list[Issue] = []
    challenger_model = member.get("challenger_model")
    if not isinstance(challenger_model, str) or not challenger_model.strip():
        issues.append(_g32(f"{ctx}.challenger_model must be non-empty"))

    outcome = member.get("outcome")
    if outcome not in _V5_MEMBER_OUTCOMES:
        issues.append(_g32(f"{ctx}.outcome={outcome!r} not in {sorted(_V5_MEMBER_OUTCOMES)}"))

    reason = member.get("reason")
    if not isinstance(reason, str) or not reason.strip():
        issues.append(_g32(f"{ctx}.reason must be non-empty"))

    issues.extend(_check_attempts_shape(member.get("attempts"), ctx))
    issues.extend(_check_v5_retry_envelope(member, ctx))
    issues.extend(_check_v5_token_usage(member.get("token_usage"), ctx))
    return issues


def _check_v5_retry_envelope(member: dict, ctx: str) -> list[Issue]:
    """Rule #25's envelope shape plus the v5-specific budget_exhausted value in
    both enums -- the member session budget (plan § Cost) produces exhaustion
    records the v4 enum cannot represent.

    Not shared with check_g27_retry_envelope: G27 (implementation_review) never
    validates individual retry_attempts[] entry shape at all, only length and the
    first entry's outcome. v5's contract is stricter (every entry checked, per
    the plan's schema block), so sharing would loosen G27 or over-constrain it.
    """
    issues: list[Issue] = []
    retry_count = member.get("retry_count")
    retry_cause = member.get("retry_cause")
    retry_attempts = member.get("retry_attempts")

    if retry_count not in (1, 2):
        issues.append(_g32(f"{ctx}.retry_count={retry_count!r} not in {{1, 2}}"))
        return issues
    if not isinstance(retry_attempts, list):
        issues.append(_g32(f"{ctx}.retry_attempts must be a list"))
        return issues

    if retry_count == 1:
        if retry_cause is not None:
            issues.append(
                _g32(f"{ctx}.retry_count=1 requires retry_cause=null, got {retry_cause!r}")
            )
        if len(retry_attempts) != 1:
            issues.append(
                _g32(f"{ctx}.retry_count=1 requires 1 retry_attempts, got {len(retry_attempts)}")
            )
    else:  # retry_count == 2
        if retry_cause not in _V5_RETRY_CAUSES:
            issues.append(
                _g32(f"{ctx}.retry_cause={retry_cause!r} not in {sorted(_V5_RETRY_CAUSES)}")
            )
        if len(retry_attempts) != 2:
            issues.append(
                _g32(f"{ctx}.retry_count=2 requires 2 retry_attempts, got {len(retry_attempts)}")
            )
        elif isinstance(retry_attempts[0], dict):
            first_outcome = retry_attempts[0].get("outcome")
            if first_outcome != retry_cause:
                issues.append(
                    _g32(
                        f"{ctx}.retry_attempts[0].outcome={first_outcome!r} != retry_cause={retry_cause!r}"
                    )
                )

    for i, attempt in enumerate(retry_attempts):
        entry_ctx = f"{ctx}.retry_attempts[{i}]"
        if not isinstance(attempt, dict):
            issues.append(_g32(f"{entry_ctx} must be an object"))
            continue
        attempt_no = attempt.get("attempt")
        if not isinstance(attempt_no, int) or isinstance(attempt_no, bool):
            issues.append(_g32(f"{entry_ctx}.attempt must be an int"))
        outcome = attempt.get("outcome")
        if outcome not in _V5_RETRY_ATTEMPT_OUTCOMES:
            issues.append(
                _g32(f"{entry_ctx}.outcome={outcome!r} not in {sorted(_V5_RETRY_ATTEMPT_OUTCOMES)}")
            )
        error = attempt.get("error")
        if "error" not in attempt or not (error is None or isinstance(error, str)):
            issues.append(_g32(f"{entry_ctx}.error must be a string or null"))
        duration = attempt.get("duration_ms")
        if not isinstance(duration, int) or isinstance(duration, bool) or duration < 0:
            issues.append(_g32(f"{entry_ctx}.duration_ms must be a non-negative int"))
    return issues


def _check_v5_token_usage(usage, ctx: str) -> list[Issue]:
    """null OR {input_tokens, output_tokens, total_tokens} all non-negative ints
    with total == input + output. Aggregated across every transport attempt for
    the member, not just the successful one (plan § Cost)."""
    if usage is None:
        return []
    if not isinstance(usage, dict):
        return [_g32(f"{ctx}.token_usage must be an object or null")]
    issues: list[Issue] = []
    values: dict[str, int] = {}
    for field in ("input_tokens", "output_tokens", "total_tokens"):
        value = usage.get(field)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            issues.append(_g32(f"{ctx}.token_usage.{field}={value!r} must be a non-negative int"))
        else:
            values[field] = value
    if (
        len(values) == 3
        and values["total_tokens"] != values["input_tokens"] + values["output_tokens"]
    ):
        issues.append(_g32(f"{ctx}.token_usage.total_tokens != input_tokens + output_tokens"))
    return issues


def _check_v5_break_evidence(
    member: dict, current_review: dict, aggregate, ctx: str
) -> list[Issue]:
    """break_evidence: non-null iff outcome == 'broke'. Two forms:
      - NORMALIZED (every route except aggregate 'pending'): {finding_stable_id, spt}.
      - RAW (only under aggregate 'pending'): {finding, spt} + a normalization marker.
    normalization is null everywhere else (and only a 'broke' member ever carries one).
    """
    issues: list[Issue] = []
    outcome = member.get("outcome")
    evidence = member.get("break_evidence")
    normalization = member.get("normalization")

    if outcome != "broke":
        if evidence is not None:
            issues.append(_g32(f"{ctx}.break_evidence must be null when outcome={outcome!r}"))
        if normalization is not None:
            issues.append(_g32(f"{ctx}.normalization must be null when outcome != 'broke'"))
        return issues

    if normalization is not None and aggregate != "pending":
        issues.append(_g32(f"{ctx}.normalization must be null outside aggregate 'pending'"))

    if evidence is None:
        issues.append(_g32(f"{ctx}.break_evidence is required when outcome=='broke'"))
        return issues
    if not isinstance(evidence, dict):
        issues.append(
            _g32(f"{ctx}.break_evidence must be an object, got {type(evidence).__name__}")
        )
        return issues

    if aggregate == "pending":
        issues.extend(_check_v5_raw_break_evidence(evidence, normalization, ctx))
    else:
        issues.extend(_check_v5_normalized_break_evidence(evidence, current_review, ctx))
    return issues


def _check_v5_normalized_break_evidence(
    evidence: dict, current_review: dict, ctx: str
) -> list[Issue]:
    """{finding_stable_id, spt}. Required on every route except aggregate
    'pending' -- main has already registry-matched/allocated and written
    findings[] by the time this record exists."""
    issues: list[Issue] = []
    stable_id = evidence.get("finding_stable_id")
    known = {
        f.get("stable_id") for f in (current_review.get("findings") or []) if isinstance(f, dict)
    }
    if not isinstance(stable_id, str) or not stable_id.strip():
        issues.append(_g32(f"{ctx}.break_evidence.finding_stable_id must be non-empty"))
    elif stable_id not in known:
        issues.append(
            _g32(f"{ctx}.break_evidence.finding_stable_id={stable_id!r} not in findings[]")
        )
    issues.extend(_check_v5_spt(evidence.get("spt"), ctx))
    return issues


def _check_v5_raw_break_evidence(evidence: dict, normalization, ctx: str) -> list[Issue]:
    """{finding, spt}, permitted ONLY under aggregate 'pending', paired with a
    normalization marker naming which side of row 0 this member is on."""
    issues: list[Issue] = []
    if normalization not in _V5_NORMALIZATION_MARKERS:
        issues.append(
            _g32(
                f"{ctx}.normalization={normalization!r} not in {sorted(_V5_NORMALIZATION_MARKERS)}"
            )
        )
    finding = evidence.get("finding")
    if not isinstance(finding, dict):
        issues.append(_g32(f"{ctx}.break_evidence.finding must be an object (raw Evidence Chain)"))
    else:
        if "stable_id" in finding:
            issues.append(
                _g32(f"{ctx}.break_evidence.finding must not carry stable_id (main assigns it)")
            )
        if "loop_local_id" in finding:
            issues.append(
                _g32(f"{ctx}.break_evidence.finding must not carry loop_local_id (main assigns it)")
            )
        issues.extend(_check_v5_raw_finding_evidence_chain(finding, ctx))
    issues.extend(_check_v5_spt(evidence.get("spt"), ctx))
    return issues


def _check_v5_raw_finding_evidence_chain(finding: dict, ctx: str) -> list[Issue]:
    """Every required Finding field except the two main-assigned ids -- mirrors
    check_per_finding_evidence_chain in _artifact_core.py, applied to one
    unnumbered finding rather than findings[]."""
    issues: list[Issue] = []
    for field in _RAW_FINDING_STRING_FIELDS:
        value = finding.get(field)
        if not isinstance(value, str) or not value.strip():
            issues.append(_g32(f"{ctx}.break_evidence.finding.{field} must be non-empty"))
    evidence = finding.get("evidence")
    if not isinstance(evidence, list) or not any(
        isinstance(item, str) and item.strip() for item in evidence
    ):
        issues.append(_g32(f"{ctx}.break_evidence.finding.evidence[] must be a non-empty list"))
    return issues


def _check_v5_spt(spt, ctx: str) -> list[Issue]:
    """spt.result must be 'passed' -- proof the break DID pass the Simplify
    Pressure Test. Not spt_question_failed: that field is "which question
    REJECTED it" (output-format-json.md:274, method.md:106) -- semantically
    inverted here, and would let a rejected fix masquerade as proof of a break."""
    if not isinstance(spt, dict):
        return [_g32(f"{ctx}.break_evidence.spt must be an object")]
    issues: list[Issue] = []
    if spt.get("result") != "passed":
        issues.append(
            _g32(f"{ctx}.break_evidence.spt.result={spt.get('result')!r} must be 'passed'")
        )
    rationale = spt.get("rationale")
    if not isinstance(rationale, str) or not rationale.strip():
        issues.append(_g32(f"{ctx}.break_evidence.spt.rationale must be non-empty"))
    return issues


def _check_v5_aggregate_coupling(
    current_review: dict, challenge: dict, state, subtype, members: list[dict]
) -> list[Issue]:
    """Aggregate outcome <-> state/halt_subtype coupling, plus the panel-keyed
    half of the plan's rule #6 amendment: aggregate 'broke' needs findings[]
    count in {1, 2} matching the distinct stable_ids the panel's breaks resolve
    to (two members may dedup to one finding); aggregate 'pending' needs
    findings[] exactly empty. The prose amendment to rule #6 itself is a
    documentation change, out of scope here.
    """
    issues: list[Issue] = []
    aggregate = challenge.get("outcome")
    outcomes = [m.get("outcome") for m in members]
    any_broke = "broke" in outcomes

    if aggregate == "held":
        if state != "HALT_SUCCESS":
            issues.append(_g32(f"aggregate 'held' requires state=HALT_SUCCESS, got {state!r}"))
        if not (len(members) == 3 and all(o == "held" for o in outcomes)):
            issues.append(_g32("aggregate 'held' requires all 3 panel members outcome='held'"))
    elif aggregate == "broke":
        ok_state = state == "CONTINUE" or (
            state == "HALT_STAGNATION" and subtype == "user_decision"
        )
        if not ok_state:
            issues.append(
                _g32(
                    f"aggregate 'broke' needs CONTINUE or HALT_STAGNATION/user_decision, "
                    f"got state={state!r} subtype={subtype!r}"
                )
            )
        if not any_broke:
            issues.append(_g32("aggregate 'broke' requires >=1 member with outcome='broke'"))
        findings_count = len(current_review.get("findings") or [])
        if findings_count not in (1, 2):
            issues.append(
                _g32(
                    f"aggregate 'broke' requires findings[] count in {{1, 2}}, got {findings_count}"
                )
            )
        stable_ids = {
            m["break_evidence"]["finding_stable_id"]
            for m in members
            if m.get("outcome") == "broke"
            and isinstance(m.get("break_evidence"), dict)
            and isinstance(m["break_evidence"].get("finding_stable_id"), str)
            and m["break_evidence"]["finding_stable_id"].strip()
        }
        if stable_ids and findings_count in (1, 2) and len(stable_ids) != findings_count:
            issues.append(
                _g32(
                    f"aggregate 'broke' findings[] count ({findings_count}) != distinct "
                    f"stable_ids resolved ({len(stable_ids)})"
                )
            )
    elif aggregate == "blocked":
        if not (state == "HALT_STAGNATION" and subtype == "verification_blocked"):
            issues.append(
                _g32(
                    f"aggregate 'blocked' needs HALT_STAGNATION/verification_blocked, "
                    f"got state={state!r} subtype={subtype!r}"
                )
            )
        if any_broke:
            issues.append(_g32("aggregate 'blocked' requires no member with outcome='broke'"))
        if outcomes.count("held") >= 3:
            issues.append(
                _g32("aggregate 'blocked' requires fewer than 3 members with outcome='held'")
            )
    elif aggregate == "pending":
        if not (state == "HALT_STAGNATION" and subtype == "user_decision"):
            issues.append(
                _g32(
                    f"aggregate 'pending' needs HALT_STAGNATION/user_decision, "
                    f"got state={state!r} subtype={subtype!r}"
                )
            )
        normalizations = [m.get("normalization") for m in members]
        if "pending_user_decision" not in normalizations:
            issues.append(
                _g32("aggregate 'pending' requires a member normalization='pending_user_decision'")
            )
        for m in members:
            if (
                m.get("outcome") == "broke"
                and m.get("normalization") not in _V5_NORMALIZATION_MARKERS
            ):
                issues.append(
                    _g32("aggregate 'pending' requires every 'broke' member to carry a raw marker")
                )
        findings_count = len(current_review.get("findings") or [])
        if findings_count != 0:
            issues.append(
                _g32(f"aggregate 'pending' requires findings[] exactly empty, got {findings_count}")
            )
        # The plan's G32 acceptance condition for raw evidence names all four:
        # aggregate pending, user_decision state, raw markers, AND a non-null
        # open_question_for_user -- a pending panel that asks the user nothing
        # is a halt with no question, which no one can answer.
        if current_review.get("open_question_for_user") in (None, ""):
            issues.append(_g32("aggregate 'pending' requires open_question_for_user non-null"))
    return issues
