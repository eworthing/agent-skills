from __future__ import annotations

from datetime import date

from _artifact_core import SERIOUS_OR_WORSE, Issue, _parse_iso_date
from candidate_fingerprint import candidate_fingerprint


def check_halt_success_gating(current_review: dict, project_config: dict | None) -> list[Issue]:
    """HALT_SUCCESS: no unresolved Serious-or-worse, no expired accepted residuals."""
    issues: list[Issue] = []
    if current_review.get("state") not in ("HALT_SUCCESS", "HALT_SUCCESS_candidate"):
        return issues
    findings = current_review.get("findings") or []
    for finding in findings:
        if finding.get("severity") in SERIOUS_OR_WORSE:
            issues.append(
                Issue(
                    "HALT_SUCCESS",
                    f"HALT_SUCCESS with unresolved Serious-or-worse finding "
                    f"{finding.get('loop_local_id') or '<unknown>'}",
                )
            )
    # Reject if any accepted residual is expired
    today = date.today()
    if project_config:
        for residual in project_config.get("accepted_residuals") or []:
            expires = _parse_iso_date(residual.get("expires"))
            if expires is not None and expires < today:
                issues.append(
                    Issue(
                        "HALT_SUCCESS",
                        f"HALT_SUCCESS cited expired accepted_residual {residual.get('id')!r} "
                        f"(expires={residual.get('expires')!r}, today={today.isoformat()})",
                    )
                )
    # Also reject inline accepted residuals in scorecard with `expires` date in the past
    scorecard = current_review.get("scorecard") or {}
    for dim, entry in scorecard.items():
        if not isinstance(entry, dict):
            continue
        if entry.get("residual_disposition") != "accepted":
            continue
        expires_raw = entry.get("residual_expires")
        expires = _parse_iso_date(expires_raw)
        if expires is not None and expires < today:
            issues.append(
                Issue(
                    "HALT_SUCCESS",
                    f"scorecard {dim} accepted residual expired (expires={expires_raw!r})",
                )
            )
    return issues


def check_g21_scorecard(current_review: dict) -> list[Issue]:
    """G21-scorecard: HALT_SUCCESS requires every dimension to satisfy
    score == 10 OR (score >= 9.5 AND residual_disposition == "accepted").

    Promotes [validation.md G21] + [output-format-json.md rule #13] to a
    structural check. Mirrors the rule text from references/validation.md:
        - score == 10                                            → pass
        - score >= 9.5 AND score < 10 AND disp == "accepted"     → pass
        - anything else (including queued at any score)          → fail
    """
    issues: list[Issue] = []
    if current_review.get("state") not in ("HALT_SUCCESS", "HALT_SUCCESS_candidate"):
        return issues
    scorecard = current_review.get("scorecard") or {}
    if not isinstance(scorecard, dict):
        issues.append(
            Issue(
                "G21-scorecard",
                "scorecard must be a mapping of dimension → entry",
            )
        )
        return issues
    for dim, entry in scorecard.items():
        if not isinstance(entry, dict):
            issues.append(
                Issue(
                    "G21-scorecard",
                    f"scorecard {dim!r} entry must be a mapping",
                )
            )
            continue
        score_raw = entry.get("score")
        # Convert score to float for comparison; accept int and float
        try:
            score = float(score_raw)
        except (TypeError, ValueError):
            issues.append(
                Issue(
                    "G21-scorecard",
                    f"scorecard {dim!r} score={score_raw!r} is not a number",
                )
            )
            continue
        disposition = entry.get("residual_disposition")
        if score == 10:
            continue  # explicit pass
        if 9.5 <= score < 10 and disposition == "accepted":
            continue  # accepted residual pass
        # Anything else fails. Build a precise diagnostic.
        if score < 9.5:
            issues.append(
                Issue(
                    "G21-scorecard",
                    f"HALT_SUCCESS dimension {dim!r} score={score} < 9.5 "
                    f"(every scorecard dimension must satisfy score == 10 OR "
                    f"(score >= 9.5 AND residual_disposition == 'accepted'))",
                )
            )
        elif 9.5 <= score < 10 and disposition == "queued":
            issues.append(
                Issue(
                    "G21-scorecard",
                    f"HALT_SUCCESS dimension {dim!r} score={score} has "
                    f"residual_disposition='queued' "
                    f"(queued residuals block HALT_SUCCESS; promote to "
                    f"'accepted' with a rationale or keep state CONTINUE "
                    f"until the backlog item is resolved)",
                )
            )
        else:
            issues.append(
                Issue(
                    "G21-scorecard",
                    f"HALT_SUCCESS dimension {dim!r} score={score} "
                    f"residual_disposition={disposition!r} "
                    f"(every scorecard dimension must satisfy score == 10 OR "
                    f"(score >= 9.5 AND residual_disposition == 'accepted'))",
                )
            )
    return issues


def check_g32_halt_success_challenge(current_review: dict) -> list[Issue]:
    """G32: HALT_SUCCESS terminal state (v4+) requires an independent challenge.

    When state == "HALT_SUCCESS" and schema_version >= 4:
    - halt_success_challenge must be non-null.
    - .outcome must be "held" (outcome "broke" with terminal HALT_SUCCESS is illegal).
    - .challenger_model must be non-empty.
    - .attempts must be a non-empty list of shaped attempts.
    - .attempts must include a new_finding arm targeting simplicity or domain_modeling.
    - .binding.run_id must equal top-level run_id.
    - .binding.source_rev must equal top-level source_rev.
    - .binding.candidate_commit_sha must be non-empty.

    When state == "HALT_SUCCESS_candidate" and schema_version >= 4:
    - halt_success_challenge must be null.
    - run_id, source_rev, candidate_fingerprint must all be non-null.

    For either v4+ success state, candidate_fingerprint must equal the canonical digest.

    When schema_version < 4: G32 does not fire.
    """
    issues: list[Issue] = []
    schema_version = current_review.get("schema_version") or 1
    if schema_version < 4:
        return issues  # legacy v3 HALT_SUCCESS without a challenge stays valid

    state = current_review.get("state")
    if state not in ("HALT_SUCCESS", "HALT_SUCCESS_candidate"):
        return issues

    top_run_id = current_review.get("run_id")
    top_source_rev = current_review.get("source_rev")
    top_fingerprint = current_review.get("candidate_fingerprint")
    challenge = current_review.get("halt_success_challenge")

    expected_fingerprint = candidate_fingerprint(current_review)
    if top_fingerprint != expected_fingerprint:
        issues.append(
            Issue(
                "G32",
                f"candidate_fingerprint={top_fingerprint!r} must equal canonical digest "
                f"{expected_fingerprint!r}",
            )
        )

    if state == "HALT_SUCCESS_candidate":
        # Candidate is exempt from challenge but must carry identity fields.
        if challenge is not None:
            issues.append(
                Issue(
                    "G32",
                    "state=HALT_SUCCESS_candidate must have halt_success_challenge=null "
                    "(candidate is not yet promoted to terminal; challenge belongs on HALT_SUCCESS)",
                )
            )
        if not top_run_id:
            issues.append(
                Issue(
                    "G32",
                    "state=HALT_SUCCESS_candidate requires run_id non-null (v4+)",
                )
            )
        if not top_source_rev:
            issues.append(
                Issue(
                    "G32",
                    "state=HALT_SUCCESS_candidate requires source_rev non-null (v4+)",
                )
            )
        if not top_fingerprint:
            issues.append(
                Issue(
                    "G32",
                    "state=HALT_SUCCESS_candidate requires candidate_fingerprint non-null (v4+)",
                )
            )
        return issues

    # state == "HALT_SUCCESS" (terminal)
    if challenge is None:
        issues.append(
            Issue(
                "G32",
                "state=HALT_SUCCESS at schema_version >= 4 requires halt_success_challenge "
                "non-null (independent challenge must be run before terminal success)",
            )
        )
        return issues

    if not isinstance(challenge, dict):
        issues.append(
            Issue(
                "G32",
                f"halt_success_challenge must be an object, got {type(challenge).__name__}",
            )
        )
        return issues

    outcome = challenge.get("outcome")
    if outcome == "broke":
        issues.append(
            Issue(
                "G32",
                "halt_success_challenge.outcome='broke' with state=HALT_SUCCESS is illegal; "
                "main agent must demote candidate before emitting terminal HALT_SUCCESS",
            )
        )
    elif outcome != "held":
        issues.append(
            Issue(
                "G32",
                f"halt_success_challenge.outcome={outcome!r} must be 'held' "
                "(terminal HALT_SUCCESS requires a passing challenge)",
            )
        )

    challenger_model = challenge.get("challenger_model")
    if not isinstance(challenger_model, str) or not challenger_model.strip():
        issues.append(
            Issue(
                "G32",
                "halt_success_challenge.challenger_model must be a non-empty string",
            )
        )

    attempts = challenge.get("attempts")
    if not isinstance(attempts, list) or len(attempts) == 0:
        issues.append(
            Issue(
                "G32",
                "halt_success_challenge.attempts must be a non-empty list "
                "(challenger must make at least one arm attempt)",
            )
        )
    else:
        has_diversity_arm = False
        for index, attempt in enumerate(attempts):
            if not isinstance(attempt, dict):
                issues.append(
                    Issue(
                        "G32",
                        f"halt_success_challenge.attempts[{index}] must be an object",
                    )
                )
                continue
            for field in ("arm", "target", "what_tried", "why_failed"):
                value = attempt.get(field)
                if not isinstance(value, str) or not value.strip():
                    issues.append(
                        Issue(
                            "G32",
                            f"halt_success_challenge.attempts[{index}].{field} "
                            "must be a non-empty string",
                        )
                    )
            arm = attempt.get("arm")
            if isinstance(arm, str) and arm not in {"new_finding", "residual_refutation"}:
                issues.append(
                    Issue(
                        "G32",
                        f"halt_success_challenge.attempts[{index}].arm={arm!r} must be "
                        "'new_finding' or 'residual_refutation'",
                    )
                )
            if attempt.get("arm") == "new_finding" and attempt.get("target") in {
                "simplicity",
                "domain_modeling",
            }:
                has_diversity_arm = True
        if not has_diversity_arm:
            issues.append(
                Issue(
                    "G32",
                    "halt_success_challenge.attempts must include a new_finding arm "
                    "targeting simplicity or domain_modeling",
                )
            )

    reason = challenge.get("reason")
    if not isinstance(reason, str) or not reason.strip():
        issues.append(
            Issue(
                "G32",
                "halt_success_challenge.reason must be a non-empty string",
            )
        )

    binding = challenge.get("binding")
    if not isinstance(binding, dict):
        issues.append(
            Issue(
                "G32",
                "halt_success_challenge.binding must be an object with "
                "candidate_commit_sha, run_id, source_rev",
            )
        )
    else:
        candidate_commit_sha = binding.get("candidate_commit_sha")
        if not isinstance(candidate_commit_sha, str) or not candidate_commit_sha.strip():
            issues.append(
                Issue(
                    "G32",
                    "halt_success_challenge.binding.candidate_commit_sha must be a non-empty string",
                )
            )
        binding_run_id = binding.get("run_id")
        if binding_run_id != top_run_id:
            issues.append(
                Issue(
                    "G32",
                    f"halt_success_challenge.binding.run_id={binding_run_id!r} must equal "
                    f"top-level run_id={top_run_id!r}",
                )
            )
        binding_source_rev = binding.get("source_rev")
        if binding_source_rev != top_source_rev:
            issues.append(
                Issue(
                    "G32",
                    f"halt_success_challenge.binding.source_rev={binding_source_rev!r} must equal "
                    f"top-level source_rev={top_source_rev!r}",
                )
            )

    return issues


def check_g33_risk_boundary_evidence(current_review: dict, canon) -> list[Issue]:
    """G33: loop_result.risk_boundary_evidence SHAPE (Meta-Rule-4 preservation evidence), schema_version >= 3.

    The field is OPTIONAL (null/absent ⇒ no risk boundary crossed this loop). When present it must be a
    well-formed object: boundary_kind ∈ canon, verification ∈ canon, non-empty detail, and the reasoning_only
    escape is legal only when mechanically_testable is false. The validator checks SHAPE only (it has no git
    diff); the git-grounded safety semantics live in the Layer-5 grader (exec_replay_grade.py).
    """
    issues: list[Issue] = []
    if (current_review.get("schema_version") or 1) < 3:
        return issues
    lr = current_review.get("loop_result")
    if not isinstance(lr, dict):
        return issues
    if "risk_boundary_evidence" not in lr:
        return issues
    ev = lr.get("risk_boundary_evidence")
    if ev is None:
        return issues
    if not isinstance(ev, dict):
        issues.append(Issue("G33", "risk_boundary_evidence must be an object or null"))
        return issues
    bk = ev.get("boundary_kind")
    if bk not in set(canon.risk_boundary_kinds):
        issues.append(
            Issue(
                "G33",
                f"risk_boundary_evidence.boundary_kind {bk!r} not in {sorted(canon.risk_boundary_kinds)}",
            )
        )
    verification = ev.get("verification")
    if verification not in set(canon.risk_evidence_verifications):
        issues.append(
            Issue(
                "G33",
                f"risk_boundary_evidence.verification {verification!r} not in "
                f"{sorted(canon.risk_evidence_verifications)}",
            )
        )
    detail = ev.get("detail")
    if not (isinstance(detail, str) and detail.strip()):
        issues.append(Issue("G33", "risk_boundary_evidence.detail required (non-empty string)"))
    if verification == "reasoning_only" and ev.get("mechanically_testable") is not False:
        issues.append(
            Issue(
                "G33",
                "risk_boundary_evidence.verification=reasoning_only requires mechanically_testable=false",
            )
        )
    return issues


# G34 state predicates (rule predicates, not new enum domains; canon owns membership).
_G34_REASON_STATES = {"HALT_STAGNATION", "HALT_LOOP_CAP"}
_G34_HANDOFF_STATES = {"HALT_SUCCESS", "HALT_STAGNATION", "HALT_LOOP_CAP", "HALT_DRY_RUN"}


def check_g34_halt_tail_invariants(current_review: dict, canon) -> list[Issue]:
    """G34: HALT-tail emit invariants — PRESENCE of halt_subtype / unresolved_reason / halt_handoff by state.

    Bidirectional (required-when AND null-otherwise), schema_version >= 3. Enforces the presence halves of
    [output-format-json-rules.md] rules #11/#17/#18:
      - halt_subtype      non-null iff state == HALT_STAGNATION  (membership stays with check_schema_enums)
      - unresolved_reason non-null iff state in {HALT_STAGNATION, HALT_LOOP_CAP}
      - halt_handoff      non-null iff state in {HALT_SUCCESS, HALT_STAGNATION, HALT_LOOP_CAP, HALT_DRY_RUN};
                          null for CONTINUE and HALT_SUCCESS_candidate (a non-terminal pause for the
                          main-agent challenge, not a user-facing halt).
    G34 checks handoff PRESENCE only; the rule #18 handoff SHAPE (text / expected_actions[] / match_kind) is a
    separate, currently-unenforced rule. Runs only for canon-valid states — an invalid or missing `state` is
    the schema-enum check's concern, not G34's (so G34 does not double-report it).
    """
    issues: list[Issue] = []
    if (current_review.get("schema_version") or 1) < 3:
        return issues
    state = current_review.get("state")
    if state not in set(canon.states):
        return issues  # invalid/missing state owned by check_schema_enums
    # rule #17 — halt_subtype presence by state (domain ∈ canon stays with check_schema_enums)
    subtype = current_review.get("halt_subtype")
    if state == "HALT_STAGNATION":
        if subtype is None:
            issues.append(
                Issue("G34", "state=HALT_STAGNATION requires a non-null halt_subtype (rule #17)")
            )
    elif subtype is not None:
        issues.append(
            Issue("G34", f"state={state} requires halt_subtype=null (rule #17); got {subtype!r}")
        )
    # rule #11 — unresolved_reason presence by state
    reason = current_review.get("unresolved_reason")
    if state in _G34_REASON_STATES:
        if reason is None:
            issues.append(
                Issue("G34", f"state={state} requires a non-null unresolved_reason (rule #11)")
            )
    elif reason is not None:
        issues.append(Issue("G34", f"state={state} requires unresolved_reason=null (rule #11)"))
    # rule #18 — halt_handoff PRESENCE by state (shape is out of scope)
    handoff = current_review.get("halt_handoff")
    if state in _G34_HANDOFF_STATES:
        if handoff is None:
            issues.append(
                Issue("G34", f"state={state} requires a non-null halt_handoff (rule #18 presence)")
            )
    elif handoff is not None:
        issues.append(
            Issue(
                "G34",
                f"state={state} requires halt_handoff=null (rule #18); CONTINUE and the non-terminal "
                f"HALT_SUCCESS_candidate carry no user-facing handoff",
            )
        )
    return issues


def check_g35_halt_handoff_shape(current_review: dict, canon) -> list[Issue]:
    """G35: shape of the halt_handoff OBJECT (rule #18 shape half; presence is G34's job).

    Scoped to the handoff-required states (_G34_HANDOFF_STATES) — the states where G34 has confirmed the
    handoff is non-null but checked neither its type nor shape. For every other state (CONTINUE,
    HALT_SUCCESS_candidate) G34 owns the null-required contract, so G35 staying out keeps the predicates
    disjoint. Enforces exactly rule #18's documented shape — no more (action_id / match_keywords *content*
    is a deliberate non-goal):
      - halt_handoff must be an object (a non-dict here — "string", [..] — is the root-type defect that
        satisfies G34's not-null presence check but has no other owner; check_g30 bails on it so G35 is sole).
      - text: a non-empty string.
      - expected_actions: a list.
      - each action (a dict): match_kind ∈ canon.match_kinds, with the path↔kind coupling —
        non-empty match_paths ⟹ all_of; empty/absent match_paths ⟹ {any_of, no_drift_expected}.
    """
    issues: list[Issue] = []
    if current_review.get("state") not in _G34_HANDOFF_STATES:
        return issues  # null-required / non-handoff states are G34's concern, not G35's
    handoff = current_review.get("halt_handoff")
    if handoff is None:
        return issues  # absence is G34's presence concern, not shape
    if not isinstance(handoff, dict):
        issues.append(
            Issue(
                "G35",
                f"halt_handoff must be an object when present (rule #18 shape); got {type(handoff).__name__}",
            )
        )
        return issues
    text = handoff.get("text")
    if not (isinstance(text, str) and text.strip()):
        issues.append(Issue("G35", "halt_handoff.text must be a non-empty string (rule #18 shape)"))
    actions = handoff.get("expected_actions")
    if not isinstance(actions, list):
        issues.append(
            Issue("G35", "halt_handoff.expected_actions must be an array (rule #18 shape)")
        )
        return issues
    valid_kinds = set(canon.match_kinds)
    for i, action in enumerate(actions):
        if not isinstance(action, dict):
            issues.append(Issue("G35", f"halt_handoff.expected_actions[{i}] must be an object"))
            continue
        aid = action.get("action_id") or i
        match_paths = action.get("match_paths")
        if match_paths is not None and not isinstance(match_paths, list):
            issues.append(
                Issue("G35", f"expected_actions[{aid!r}].match_paths must be an array when present")
            )
            continue
        paths_nonempty = bool(match_paths)
        match_kind = action.get("match_kind")
        if match_kind not in valid_kinds:
            issues.append(
                Issue(
                    "G35",
                    f"expected_actions[{aid!r}] match_kind {match_kind!r} not in canon match-kinds "
                    f"{sorted(valid_kinds)}",
                )
            )
        elif paths_nonempty and match_kind != "all_of":
            issues.append(
                Issue(
                    "G35",
                    f"expected_actions[{aid!r}] has non-empty match_paths so match_kind must be 'all_of' "
                    f"(rule #18 coupling); got {match_kind!r}",
                )
            )
        elif not paths_nonempty and match_kind not in ("any_of", "no_drift_expected"):
            issues.append(
                Issue(
                    "G35",
                    f"expected_actions[{aid!r}] has empty match_paths so match_kind must be 'any_of' or "
                    f"'no_drift_expected' (rule #18 coupling); got {match_kind!r}",
                )
            )
    return issues


def check_g36_required_state(current_review: dict, canon) -> list[Issue]:
    """G36: `state` is a required, non-null field (covers both `state: null` and an absent key).

    Presence only — membership (`state ∈ canon.states`) for a non-null foreign state stays with
    check_schema_enums, so the two never overlap. Closes a hole owned by no gate today: check_schema_enums
    fires only when `state is not None`, and G34 returns early when `state ∉ canon.states`.
    """
    if current_review.get("state") is None:
        return [
            Issue(
                "G36",
                "state is a required field and must be non-null (rule #30); "
                "membership ∈ canon is the schema-enum check's concern",
            )
        ]
    return []


# G37: residual-blocker-kind coherence at converged empty-backlog terminals.
# Mechanizes the Residual Accounting Pass (method-critic.md) / G23 at the terminals where the
# Critic decides HALT: the ONLY residual_blocker_kind that licenses keeping a dimension below
# 9.5 is "structural_anchor_unmet". The promotion-trigger kinds mean the 9-anchor is met and the
# dimension MUST be promoted to 9.5 with residual_disposition: "accepted". Field is additive on v4.
_G37_STRUCTURAL_KIND = "structural_anchor_unmet"
_G37_PROMOTION_TRIGGER_KINDS = {"ceremony", "framework_constrained", "cosmetic", "adr_carved_out"}


def check_g37_residual_blocker_coherence(current_review: dict) -> list[Issue]:
    """G37: at a converged empty-backlog terminal, every sub-9.5 dimension must carry
    residual_blocker_kind == "structural_anchor_unmet". A promotion-trigger kind (or a missing
    kind) is the scoring incoherence the Residual Accounting Pass forbids.

    Trigger (closed set — mirrors references/validation.md G23 + references/method-critic.md):
      - state == HALT_STAGNATION AND halt_subtype == "no_backlog", OR
      - state == HALT_LOOP_CAP AND backlog == [] AND some dimension scores < 9.5.
    Every other terminal bypasses: HALT_STAGNATION/{user_decision,oscillation,no_progress,
    verification_blocked}, HALT_SUCCESS(_candidate), HALT_DRY_RUN, HALT_LOOP_CAP with a NON-empty
    backlog (those sub-9.5 scores have legitimate queued items), and CONTINUE. Schema_version >= 4.
    """
    issues: list[Issue] = []
    if (current_review.get("schema_version") or 1) < 4:
        return issues
    state = current_review.get("state")
    subtype = current_review.get("halt_subtype")
    backlog = current_review.get("backlog") or []
    scorecard = current_review.get("scorecard") or {}
    if not isinstance(scorecard, dict):
        return issues  # scorecard shape is check_schema_enums / G21's concern

    sub95: list[tuple[str, float]] = []
    for dim, entry in scorecard.items():
        if not isinstance(entry, dict):
            continue
        try:
            score = float(entry.get("score"))
        except (TypeError, ValueError):
            continue
        if score < 9.5:
            sub95.append((dim, score))

    no_backlog = state == "HALT_STAGNATION" and subtype == "no_backlog"
    cap_converged = state == "HALT_LOOP_CAP" and not backlog and bool(sub95)
    if not (no_backlog or cap_converged):
        return issues

    terminal = "HALT_STAGNATION/no_backlog" if no_backlog else "HALT_LOOP_CAP"
    for dim, score in sub95:
        kind = scorecard[dim].get("residual_blocker_kind")
        if kind == _G37_STRUCTURAL_KIND:
            continue
        if kind in _G37_PROMOTION_TRIGGER_KINDS:
            issues.append(
                Issue(
                    "G37",
                    f"{terminal} dimension {dim!r} score={score} < 9.5 cites promotion-trigger "
                    f"residual_blocker_kind={kind!r}; the Residual Accounting Pass requires promoting it to "
                    f"9.5 with residual_disposition='accepted' (only 'structural_anchor_unmet' licenses keeping "
                    f"a dimension below 9.5 at a converged terminal)",
                )
            )
        elif kind is None:
            issues.append(
                Issue(
                    "G37",
                    f"{terminal} dimension {dim!r} score={score} < 9.5 must declare residual_blocker_kind "
                    f"(only 'structural_anchor_unmet' licenses a sub-9.5 score at a converged terminal); got null",
                )
            )
        # any other non-null value is an unknown enum token — owned by check_schema_enums, not G37
    return issues


def check_g38_premium_model_budget_guard(current_review: dict, canon) -> list[Issue]:
    """G38: premium loop models require an invocation-level budget guard.

    Safety rule: if `loop_model` is in canon.extra["premium_models"], the artifact must
    either be a dry run (`dry_run: true`) or record an explicit full-loop override
    (`premium_loop_override: true`). Coherence rule: `premium_dry_run`, when present,
    must describe the dedicated premium dry-run flag/env path that forced dry_run.
    """
    issues: list[Issue] = []
    if (current_review.get("schema_version") or 1) < 2:
        return issues

    premium_models = set((getattr(canon, "extra", {}) or {}).get("premium_models", ()))
    if not premium_models:
        return issues

    loop_model = current_review.get("loop_model")
    loop_source = current_review.get("loop_model_source")
    dry_run = current_review.get("dry_run") is True
    premium_loop_override = current_review.get("premium_loop_override", False)
    premium_dry_run = current_review.get("premium_dry_run")

    if "premium_loop_override" in current_review and not isinstance(premium_loop_override, bool):
        issues.append(
            Issue(
                "G38",
                f"premium_loop_override must be a boolean when present, got "
                f"{type(premium_loop_override).__name__}",
            )
        )
    if premium_loop_override is True and dry_run:
        issues.append(
            Issue(
                "G38",
                "premium_loop_override must be false on any dry-run invocation; "
                "--allow-premium-loop only authorizes non-dry-run premium execution",
            )
        )

    if premium_dry_run is not None:
        if not isinstance(premium_dry_run, dict):
            issues.append(
                Issue(
                    "G38",
                    f"premium_dry_run must be null or an object, got {type(premium_dry_run).__name__}",
                )
            )
        else:
            pd_model = premium_dry_run.get("model")
            pd_source = premium_dry_run.get("model_source")
            activated = premium_dry_run.get("activated_dry_run")
            if not dry_run:
                issues.append(
                    Issue(
                        "G38",
                        "premium_dry_run is present but dry_run is not true; dedicated premium "
                        "dry-run controls must force invocation-scoped dry_run",
                    )
                )
            if pd_model != loop_model:
                issues.append(
                    Issue(
                        "G38",
                        f"premium_dry_run.model={pd_model!r} must equal loop_model={loop_model!r}",
                    )
                )
            if pd_model not in premium_models:
                issues.append(
                    Issue(
                        "G38",
                        f"premium_dry_run.model={pd_model!r} is not in canonical premium models "
                        f"{sorted(premium_models)}",
                    )
                )
            if pd_source not in {"user_flag", "env_override"}:
                issues.append(
                    Issue(
                        "G38",
                        f"premium_dry_run.model_source={pd_source!r} must be 'user_flag' or "
                        "'env_override'",
                    )
                )
            elif pd_source != loop_source:
                issues.append(
                    Issue(
                        "G38",
                        f"premium_dry_run.model_source={pd_source!r} must equal "
                        f"loop_model_source={loop_source!r}",
                    )
                )
            if activated is not True:
                issues.append(
                    Issue(
                        "G38",
                        f"premium_dry_run.activated_dry_run must be true, got {activated!r}",
                    )
                )

    if (
        isinstance(loop_model, str)
        and loop_model in premium_models
        and not dry_run
        and premium_loop_override is not True
    ):
        issues.append(
            Issue(
                "G38",
                f"loop_model={loop_model!r} is a premium model; non-dry-run execution requires "
                "premium_loop_override=true from --allow-premium-loop",
            )
        )
    return issues
