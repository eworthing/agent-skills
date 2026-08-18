from __future__ import annotations

from datetime import date

from _artifact_core import SERIOUS_OR_WORSE, Issue, _parse_iso_date


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


# G32 moved to _artifact_panel.py (check_g32_halt_success_challenge) when the v5 panel
# extension (Recommendation 1, plans/rec1-panel-certification.md) needed room this
# module's 800-line cap did not have. Same idiom as G37's move to _artifact_residual.py.


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
# HALT_EXHAUSTION (backlog item 17) requires both a reason and a handoff, same as its
# sibling HALT_LOOP_CAP -- see canon/states.toml's header comment for why it is a
# sibling terminal and not a halt_subtype (halt_subtype stays null for it, already
# covered by check_g34_halt_tail_invariants's default "non-null iff HALT_STAGNATION").
_G34_REASON_STATES = {"HALT_STAGNATION", "HALT_LOOP_CAP", "HALT_EXHAUSTION"}
_G34_HANDOFF_STATES = {
    "HALT_SUCCESS",
    "HALT_STAGNATION",
    "HALT_LOOP_CAP",
    "HALT_DRY_RUN",
    "HALT_EXHAUSTION",
}


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


# G37 moved to _artifact_residual.py (check_g37_terminal_residual_accounting) when its trigger
# widened past this module's LoC headroom. It lives beside G5's converse and G43, which answer the
# same question: is this scorecard coherent about what it is NOT claiming.


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


_G45_REQUIRED_KEYS = ("kind", "detection_mode", "evidence")


def check_g45_exhaustion_record(current_review: dict, canon) -> list[Issue]:
    """G45: exhaustion halt record SHAPE + detection<->kind honesty coupling (backlog item 17).

    Presence (bidirectional, mirroring G34's idiom): `exhaustion` non-null iff
    state == HALT_EXHAUSTION. When present it must be an object carrying exactly the
    three required non-empty-string keys (kind, detection_mode, evidence), each a
    member of canon/exhaustion-kinds.toml where applicable. Runs only for canon-valid
    states -- an invalid or missing `state` is the schema-enum check's concern, not
    G45's (mirrors G34's early return).

    The honesty coupling is the point of the gate: detection_mode ==
    "preventive_step_budget" implies kind == "unknown". A preventive step-budget
    checkpoint cannot tell context pressure from a spend limit from any other cause,
    so it is forbidden from claiming one -- only detection_mode == "user_reported" may
    name "context_pressure" or "spend_limit" (it may also say "unknown"). See
    references/halt-handoff.md for the three-deaths note this vocabulary models.
    Schema_version >= 4.
    """
    issues: list[Issue] = []
    if (current_review.get("schema_version") or 1) < 4:
        return issues
    state = current_review.get("state")
    if state not in set(canon.states):
        return issues  # invalid/missing state owned by check_schema_enums
    exhaustion = current_review.get("exhaustion")
    if state != "HALT_EXHAUSTION":
        if exhaustion is not None:
            issues.append(
                Issue(
                    "G45",
                    f"state={state} requires exhaustion=null; the record is scoped to "
                    f"HALT_EXHAUSTION",
                )
            )
        return issues
    if exhaustion is None:
        issues.append(Issue("G45", "state=HALT_EXHAUSTION requires a non-null exhaustion record"))
        return issues
    if not isinstance(exhaustion, dict):
        issues.append(
            Issue("G45", f"exhaustion must be an object; got {type(exhaustion).__name__}")
        )
        return issues

    extra_keys = set(exhaustion) - set(_G45_REQUIRED_KEYS)
    if extra_keys:
        issues.append(
            Issue(
                "G45",
                f"exhaustion has unexpected key(s) {sorted(extra_keys)}; only "
                f"{_G45_REQUIRED_KEYS} are legal",
            )
        )
    for key in _G45_REQUIRED_KEYS:
        value = exhaustion.get(key)
        if not (isinstance(value, str) and value.strip()):
            issues.append(Issue("G45", f"exhaustion.{key} must be a non-empty string"))

    kind = exhaustion.get("kind")
    if isinstance(kind, str) and kind.strip() and kind not in set(canon.exhaustion_kinds):
        issues.append(
            Issue(
                "G45",
                f"exhaustion.kind {kind!r} not in canon {sorted(canon.exhaustion_kinds)}",
            )
        )
    detection_mode = exhaustion.get("detection_mode")
    if (
        isinstance(detection_mode, str)
        and detection_mode.strip()
        and detection_mode not in set(canon.detection_modes)
    ):
        issues.append(
            Issue(
                "G45",
                f"exhaustion.detection_mode {detection_mode!r} not in canon "
                f"{sorted(canon.detection_modes)}",
            )
        )
    if detection_mode == "preventive_step_budget" and kind is not None and kind != "unknown":
        issues.append(
            Issue(
                "G45",
                f"exhaustion.detection_mode='preventive_step_budget' cannot claim "
                f"kind={kind!r}; a preventive step-budget checkpoint cannot tell context "
                f"pressure from a spend limit from any other cause, so kind must be "
                f"'unknown'",
            )
        )
    return issues
