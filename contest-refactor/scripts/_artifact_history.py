from __future__ import annotations

from pathlib import Path

import _canon
import _fingerprint
from _artifact_core import (
    _G22_COMMIT_SUBJECT_RE,
    _G22_COMMIT_SUBJECT_V1_RE,
    _G22_DIVIDER_RE,
    _G27_CANONICAL_FAILED_PHRASE,
    _G27_FORBIDDEN_REASON_VOCAB,
    _G27_RETRY_CAUSES,
    _PROVIDER_DEFAULTS,
    DISPOSITION_SIDECARS,
    ELIGIBLE_BACKLOG_STATUSES,
    SERIOUS_OR_WORSE,
    SKILL_ROOT,
    Issue,
    _find_git_root,
    _git_command,
)

# G28 lives in _artifact_snapshots.py (module-size split, register D6 note) —
# re-exported here so existing imports (validate-artifact.py) are unaffected.
from _artifact_snapshots import check_g28_loop_state_freshness  # noqa: F401


def _occurrences_for(registry: dict | None, stable_id: str) -> list[dict]:
    if registry is None:
        return []
    for entry in registry.get("entries") or []:
        if entry.get("stable_id") == stable_id:
            return list(entry.get("occurrences") or [])
    return []


def _occurrence_fingerprint(occ: dict) -> tuple[str | None, str | None, str | None]:
    fp = occ.get("fingerprint") or {}
    return (
        fp.get("claim_consequence_hash"),
        fp.get("evidence_paths_hash"),
        occ.get("attempted_remedy_hash"),
    )


def _branch_a_satisfied(prior_rejected: list[dict], retiring_hashes: tuple[str, str, str]) -> bool:
    """≥2 prior rejected_attempts share all three hashes with each other AND the retiring occurrence."""
    if any(h is None for h in retiring_hashes):
        return False
    matching = [occ for occ in prior_rejected if _occurrence_fingerprint(occ) == retiring_hashes]
    return len(matching) >= 2


def _branch_b_satisfied(
    occurrences_before_retiring: list[dict], retiring_hashes_2: tuple[str, str]
) -> bool:
    """≥2 prior occurrences share 2-way hashes with each other AND retiring; ≥1 intervening resolved."""
    if any(h is None for h in retiring_hashes_2):
        return False
    # collect indices of occurrences whose 2-way hashes match the retiring basis,
    # AND whose status is NOT `resolved` (the resolved occurrence serves only as
    # the "intervening" pivot — it cannot count as one of the matching pair).
    matching_non_resolved: list[int] = []
    resolved_indices: list[int] = []
    for idx, occ in enumerate(occurrences_before_retiring):
        cch, eph, _ = _occurrence_fingerprint(occ)
        if cch == retiring_hashes_2[0] and eph == retiring_hashes_2[1]:
            if occ.get("status") == "resolved":
                resolved_indices.append(idx)
            else:
                matching_non_resolved.append(idx)
        elif occ.get("status") == "resolved":
            # A resolved occurrence with DIFFERENT hashes can still serve as the pivot,
            # but the rule's spirit is "the finding reappeared after a correction";
            # we accept any resolved between two matching occurrences as the pivot.
            resolved_indices.append(idx)
    if len(matching_non_resolved) < 2:
        return False
    # Need at least one resolved index strictly between the earliest and latest
    # matching-non-resolved indices.
    first = matching_non_resolved[0]
    last = matching_non_resolved[-1]
    return any(first < r < last for r in resolved_indices)


def check_retirement_rule(current_review: dict, registry: dict | None) -> list[Issue]:
    """Validate mechanical retirement: status==unresolvable requires Branch A or Branch B + retirement metadata."""
    issues: list[Issue] = []
    if registry is None:
        return issues
    for entry in registry.get("entries") or []:
        stable_id = entry.get("stable_id", "<unknown>")
        occurrences = list(entry.get("occurrences") or [])
        for idx, occ in enumerate(occurrences):
            if occ.get("status") != "unresolvable":
                continue
            # Required metadata
            retirement = occ.get("retirement") or {}
            reason = retirement.get("reason")
            rationale = retirement.get("rationale")
            ctx = f"registry {stable_id} occurrence[{idx}]"
            if reason is None:
                issues.append(
                    Issue(
                        "retirement",
                        "missing retirement.reason",
                        context=ctx,
                    )
                )
            if not (isinstance(rationale, str) and rationale.strip()):
                issues.append(
                    Issue(
                        "retirement",
                        "missing or empty retirement.rationale",
                        context=ctx,
                    )
                )
            cch, eph, arh = _occurrence_fingerprint(occ)
            prior = occurrences[:idx]
            prior_rejected = [p for p in prior if p.get("status") == "rejected_attempt"]
            branch_a_ok = _branch_a_satisfied(prior_rejected, (cch, eph, arh))
            branch_b_ok = _branch_b_satisfied(prior, (cch, eph))
            if not (branch_a_ok or branch_b_ok):
                issues.append(
                    Issue(
                        "retirement",
                        "mechanical retirement rule failed: "
                        "neither Branch A (≥2 prior rejected_attempts with identical 3-way hashes "
                        "matching the retiring occurrence) nor Branch B (≥2 prior occurrences with "
                        "identical 2-way hashes separated by ≥1 resolved occurrence, matching the "
                        "retiring occurrence) is satisfied",
                        context=ctx,
                    )
                )
    return issues


def check_g30_disposition_coverage(current_review: dict, registry: dict | None) -> list[Issue]:
    """G30: HALT_STAGNATION/oscillation must disposition every eligible Serious-or-worse finding."""
    issues: list[Issue] = []
    if current_review.get("state") != "HALT_STAGNATION":
        return issues
    if current_review.get("halt_subtype") != "oscillation":
        return issues
    if registry is None:
        issues.append(
            Issue(
                "G30",
                "HALT_STAGNATION/oscillation requires findings_registry.json for disposition coverage",
            )
        )
        return issues
    halt_handoff = current_review.get("halt_handoff")
    if halt_handoff is not None and not isinstance(halt_handoff, dict):
        # A present-but-non-dict halt_handoff is a root-type defect owned by G35.
        # Bail so G30 does not (a) AttributeError on `.get()` below, nor (b) treat the
        # handoff as empty and double-fire spurious missing-disposition issues alongside
        # G35 on the same malformed field. Once the type is fixed, the re-run checks coverage.
        return issues
    halt_handoff = halt_handoff or {}
    dispositions = {
        entry.get("stable_id"): entry
        for entry in (halt_handoff.get("remaining_serious_findings_disposition") or [])
    }
    canon = _canon.load_canon(SKILL_ROOT)
    for entry in registry.get("entries") or []:
        stable_id = entry.get("stable_id")
        severity = entry.get("severity")
        if severity not in SERIOUS_OR_WORSE:
            continue
        occurrences = entry.get("occurrences") or []
        if not occurrences:
            continue
        latest = occurrences[-1]
        if latest.get("status") not in ELIGIBLE_BACKLOG_STATUSES:
            continue
        if stable_id not in dispositions:
            issues.append(
                Issue(
                    "G30",
                    f"Serious-or-worse finding {stable_id} (status={latest.get('status')!r}) "
                    f"missing from halt_handoff.remaining_serious_findings_disposition[]",
                )
            )
            continue
        disp_entry = dispositions[stable_id]
        disposition = disp_entry.get("disposition")
        if disposition not in canon.retirement_reasons:
            issues.append(
                Issue(
                    "G30",
                    f"finding {stable_id} disposition {disposition!r} not in canon/retirement-reasons.toml",
                )
            )
            continue
        sidecar = DISPOSITION_SIDECARS.get(disposition)
        if sidecar is not None:
            sidecar_value = disp_entry.get(sidecar)
            if not (
                (isinstance(sidecar_value, str) and sidecar_value.strip())
                or (isinstance(sidecar_value, (list, dict)) and sidecar_value)
            ):
                issues.append(
                    Issue(
                        "G30",
                        f"finding {stable_id} disposition={disposition!r} missing required sidecar {sidecar!r}",
                    )
                )
    return issues


def check_g31_fingerprint_integrity(registry: dict | None) -> list[Issue]:
    """G31: stored fingerprints recompute equal to current field values."""
    issues: list[Issue] = []
    if registry is None:
        return issues
    for entry in registry.get("entries") or []:
        stable_id = entry.get("stable_id", "<unknown>")
        # Validate the occurrence-level fingerprints against any inline finding
        # snapshot fields. The validator depends on the occurrences carrying the
        # hashes; mismatch between two occurrences with otherwise identical-looking
        # Claim/Source flags drift.
        for idx, occ in enumerate(entry.get("occurrences") or []):
            ctx = f"registry {stable_id} occurrence[{idx}]"
            snapshot = occ.get("finding_snapshot") or {}
            if not snapshot:
                # Without a snapshot we cannot independently recompute. The Critic
                # is expected to embed `finding_snapshot` for retiring occurrences
                # (Branch A / Branch B) so the validator can re-derive. Absence
                # is treated as advisory only — the registry entry's top-level
                # `title` is the best we can do.
                continue
            recomputed = _fingerprint.compute_all(snapshot)
            stored_cch = (occ.get("fingerprint") or {}).get("claim_consequence_hash")
            stored_eph = (occ.get("fingerprint") or {}).get("evidence_paths_hash")
            stored_arh = occ.get("attempted_remedy_hash")
            if stored_cch and recomputed["fingerprint"]["claim_consequence_hash"] != stored_cch:
                issues.append(
                    Issue(
                        "G31",
                        f"claim_consequence_hash drift "
                        f"(stored={stored_cch}, recomputed={recomputed['fingerprint']['claim_consequence_hash']})",
                        context=ctx,
                    )
                )
            if stored_eph and recomputed["fingerprint"]["evidence_paths_hash"] != stored_eph:
                issues.append(
                    Issue(
                        "G31",
                        f"evidence_paths_hash drift "
                        f"(stored={stored_eph}, recomputed={recomputed['fingerprint']['evidence_paths_hash']})",
                        context=ctx,
                    )
                )
            if stored_arh and recomputed["attempted_remedy_hash"] != stored_arh:
                issues.append(
                    Issue(
                        "G31",
                        f"attempted_remedy_hash drift "
                        f"(stored={stored_arh}, recomputed={recomputed['attempted_remedy_hash']})",
                        context=ctx,
                    )
                )
    return issues


def check_g18_review_history_append(current_review: dict, history: dict | None) -> list[Issue]:
    """G18: REVIEW_HISTORY.json must contain exactly N entries (N = current loop),
    and the most recent entry must equal CURRENT_REVIEW.json (parsed-dict equality).
    Per validation.md:82-83. Schema_version >= 2.
    """
    issues: list[Issue] = []
    if (current_review.get("schema_version") or 1) < 2:
        return issues
    if history is None:
        return issues
    loops = history.get("loops")
    if not isinstance(loops, list):
        issues.append(
            Issue(
                "G18",
                "REVIEW_HISTORY.json.loops must be a list",
            )
        )
        return issues
    expected_n = current_review.get("loop")
    if isinstance(expected_n, int) and len(loops) != expected_n:
        issues.append(
            Issue(
                "G18",
                f"REVIEW_HISTORY.json has {len(loops)} loops[] entries; "
                f"current_review.loop == {expected_n} requires exactly {expected_n} entries",
            )
        )
    if loops and loops[-1] != current_review:
        issues.append(
            Issue(
                "G18",
                "REVIEW_HISTORY.json.loops[-1] must equal CURRENT_REVIEW.json verbatim "
                "(parsed-dict equality)",
            )
        )
    return issues


def check_g19_provider_model(current_review: dict) -> list[Issue]:
    """G19: provider/model attribution per validation.md:84-85 + provider-adapters.md.
    Schema_version >= 2.

    Invariants:
    - Required keys non-empty: provider, *_model_source, spawn_isolation.
    - *_model_source ∈ {"default", "env_override", "user_flag"}.
    - When *_model_source == "default", model value must equal _PROVIDER_DEFAULTS[provider].
    - provider == "unknown" ⇒ spawn_isolation == "inline" AND both models null AND
      both sources == "default" (per provider-adapters.md § unknown explicit text).
    - Known providers (claude_code, codex, opencode) ⇒ both models are non-null strings.
    - Reject placeholder literal "inline-current-model".
    - schema_version >= 4: skill_rev is `string | null` when present (names the ruleset).
      TYPE-only, not presence: a reader cannot tell "this version omitted it" from "this run
      predates the field", so presence is a Step -1 emit obligation (startup.md).
    """
    issues: list[Issue] = []
    schema_version = current_review.get("schema_version") or 1
    if schema_version < 2:
        return issues

    if schema_version >= 4 and "skill_rev" in current_review:
        skill_rev = current_review["skill_rev"]
        if skill_rev is not None and (not isinstance(skill_rev, str) or not skill_rev):
            issues.append(
                Issue(
                    "G19",
                    f"skill_rev={skill_rev!r} must be a non-empty string or null "
                    f"(short SHA of $SKILL_DIR HEAD, captured in Step -1)",
                )
            )

    provider = current_review.get("provider")
    loop_model = current_review.get("loop_model")
    loop_source = current_review.get("loop_model_source")
    reviewer_model = current_review.get("reviewer_model")
    reviewer_source = current_review.get("reviewer_model_source")
    spawn = current_review.get("spawn_isolation")

    if not provider:
        issues.append(Issue("G19", "provider field required (non-empty)"))
        return issues
    if not spawn:
        issues.append(Issue("G19", "spawn_isolation field required (non-empty)"))
    if not loop_source:
        issues.append(Issue("G19", "loop_model_source field required (non-empty)"))
    if not reviewer_source:
        issues.append(Issue("G19", "reviewer_model_source field required (non-empty)"))

    # `inherited` (row 32): without it this gate compelled the lie it validated.
    valid_sources = {"default", "env_override", "user_flag", "inherited"}
    if loop_source is not None and loop_source not in valid_sources:
        issues.append(
            Issue(
                "G19",
                f"loop_model_source={loop_source!r} not in {sorted(valid_sources)}",
            )
        )
    if reviewer_source is not None and reviewer_source not in valid_sources:
        issues.append(
            Issue(
                "G19",
                f"reviewer_model_source={reviewer_source!r} not in {sorted(valid_sources)}",
            )
        )

    if provider == "unknown":
        if spawn != "inline":
            issues.append(
                Issue(
                    "G19",
                    f"provider='unknown' requires spawn_isolation='inline', got {spawn!r}",
                )
            )
        if loop_model is not None:
            issues.append(
                Issue(
                    "G19",
                    f"provider='unknown' requires loop_model=null, got {loop_model!r}",
                )
            )
        if reviewer_model is not None:
            issues.append(
                Issue(
                    "G19",
                    f"provider='unknown' requires reviewer_model=null, got {reviewer_model!r}",
                )
            )
        if loop_source not in (None, "default"):
            issues.append(
                Issue(
                    "G19",
                    f"provider='unknown' requires loop_model_source='default', "
                    f"got {loop_source!r} (per provider-adapters.md § unknown)",
                )
            )
        if reviewer_source not in (None, "default"):
            issues.append(
                Issue(
                    "G19",
                    f"provider='unknown' requires reviewer_model_source='default', "
                    f"got {reviewer_source!r} (per provider-adapters.md § unknown)",
                )
            )
    elif provider in _PROVIDER_DEFAULTS:
        for field, value, src in (
            ("loop_model", loop_model, loop_source),
            ("reviewer_model", reviewer_model, reviewer_source),
        ):
            if value is None and src == "inherited":
                continue  # null is honest here: the spawn chose no model
            if value is None or not isinstance(value, str) or not value:
                issues.append(
                    Issue(
                        "G19",
                        f"known provider {provider!r} requires {field} non-empty string, "
                        f"got {value!r}",
                    )
                )
            elif value == "inline-current-model":
                issues.append(
                    Issue(
                        "G19",
                        f"{field}={value!r} is a placeholder; record the real model identity",
                    )
                )
        # Default-source ⇒ value matches provider default.
        provider_default = _PROVIDER_DEFAULTS[provider]
        if (
            loop_source == "default"
            and isinstance(loop_model, str)
            and loop_model != provider_default
        ):
            issues.append(
                Issue(
                    "G19",
                    f"loop_model={loop_model!r} marked source='default' but provider "
                    f"{provider!r} default is {provider_default!r}",
                )
            )
        if (
            reviewer_source == "default"
            and isinstance(reviewer_model, str)
            and reviewer_model != provider_default
        ):
            issues.append(
                Issue(
                    "G19",
                    f"reviewer_model={reviewer_model!r} marked source='default' but provider "
                    f"{provider!r} default is {provider_default!r}",
                )
            )
    else:
        # Provider not in known table and not "unknown" — invalid value.
        issues.append(
            Issue(
                "G19",
                f"provider={provider!r} not in {sorted(_PROVIDER_DEFAULTS)} "
                "(per provider-adapters.md)",
            )
        )
    return issues


def check_g22_archive_divider(
    artifact_dir: Path, current_review: dict, project_config: dict | None = None
) -> list[Issue]:
    """G22 (both halves): REVIEW_HISTORY.md `--- Loop ` dividers must match
    output-format-markdown.md format; recent commit subjects must match the
    pattern from validation.md:92. Schema_version >= 2.

    The commit-subject sub-check runs only when project_config is non-None
    (i.e., a .contest-refactor.toml is findable in the artifact ancestor
    chain — signal that we're in a loop-managed repo). Fixture dirs nested
    inside the skills repo skip the git shell-out silently.
    """
    issues: list[Issue] = []
    if (current_review.get("schema_version") or 1) < 2:
        return issues
    md_path = artifact_dir / "REVIEW_HISTORY.md"
    if md_path.exists():
        try:
            text = md_path.read_text(encoding="utf-8")
        except OSError as exc:
            issues.append(Issue("G22", f"REVIEW_HISTORY.md unreadable: {exc}"))
            text = ""
        for lineno, line in enumerate(text.splitlines(), start=1):
            if line.startswith("--- Loop ") and not _G22_DIVIDER_RE.match(line):
                issues.append(
                    Issue(
                        "G22",
                        f"REVIEW_HISTORY.md line {lineno}: archive divider does not match "
                        f"`--- Loop <N> (UTC <ISO-8601 timestamp>) ---`",
                        context=line[:120],
                    )
                )
    # Commit-subject sub-check (requires git + loop-managed repo).
    if project_config is None:
        return issues
    git_root = _find_git_root(artifact_dir)
    if git_root is None:
        return issues
    loop_n = current_review.get("loop")
    if not isinstance(loop_n, int) or loop_n < 1:
        return issues
    rc, out = _git_command(git_root, "log", f"-n{loop_n}", "--format=%s")
    if rc != 0 or not out:
        return issues
    subjects = [s for s in out.splitlines() if s.strip()]
    for subject in subjects:
        if _G22_COMMIT_SUBJECT_RE.match(subject):
            continue
        if _G22_COMMIT_SUBJECT_V1_RE.match(subject):
            issues.append(
                Issue(
                    "G22",
                    "commit subject missing required `[registry: ...]` suffix "
                    "(schema_version >= 2 requires it)",
                    context=subject[:120],
                )
            )
        else:
            issues.append(
                Issue(
                    "G22",
                    "commit subject does not match loop-N pattern "
                    "`loop <N>: <verb-phrase>; finding F<n> (stable_id F-<NNN>) "
                    "<status> [registry: +<n> findings(, ~<n> occurrences)?]`",
                    context=subject[:120],
                )
            )
    return issues


def check_g27_retry_envelope(current_review: dict) -> list[Issue]:
    """G27: implementation_review retry envelope shape per validation.md:104-110.
    Schema_version >= 3.

    - retry_count ∈ {1, 2}.
    - retry_count == 1 ⇒ retry_cause is None AND len(retry_attempts) == 1.
    - retry_count == 2 ⇒ retry_cause ∈ {timeout, spawn_error, malformed_json}
      AND len(retry_attempts) == 2 AND retry_attempts[0]["outcome"] == retry_cause.
    - reason MUST NOT match forbidden infra-cause vocabulary.
    - When all attempts non-ok AND verdict == "rejected", reason must equal the
      exact canonical phrase.
    """
    issues: list[Issue] = []
    if (current_review.get("schema_version") or 1) < 3:
        return issues
    impl = current_review.get("implementation_review")
    if not isinstance(impl, dict):
        return issues
    retry_count = impl.get("retry_count")
    retry_cause = impl.get("retry_cause")
    retry_attempts = impl.get("retry_attempts") or []
    reason = impl.get("reason") or ""
    verdict = impl.get("verdict")

    if retry_count not in (1, 2):
        issues.append(
            Issue(
                "G27",
                f"implementation_review.retry_count={retry_count!r} not in {{1, 2}}",
            )
        )
        return issues  # downstream checks depend on retry_count being valid

    if not isinstance(retry_attempts, list):
        issues.append(
            Issue(
                "G27",
                "implementation_review.retry_attempts must be a list",
            )
        )
        return issues

    if retry_count == 1:
        if retry_cause is not None:
            issues.append(
                Issue(
                    "G27",
                    f"retry_count=1 requires retry_cause=null, got {retry_cause!r}",
                )
            )
        if len(retry_attempts) != 1:
            issues.append(
                Issue(
                    "G27",
                    f"retry_count=1 requires retry_attempts length 1, got {len(retry_attempts)}",
                )
            )
    else:  # retry_count == 2
        if retry_cause not in _G27_RETRY_CAUSES:
            issues.append(
                Issue(
                    "G27",
                    f"retry_count=2 requires retry_cause ∈ {sorted(_G27_RETRY_CAUSES)}, "
                    f"got {retry_cause!r}",
                )
            )
        if len(retry_attempts) != 2:
            issues.append(
                Issue(
                    "G27",
                    f"retry_count=2 requires retry_attempts length 2, got {len(retry_attempts)}",
                )
            )
        elif isinstance(retry_attempts[0], dict):
            first_outcome = retry_attempts[0].get("outcome")
            if first_outcome != retry_cause:
                issues.append(
                    Issue(
                        "G27",
                        f"retry_attempts[0].outcome={first_outcome!r} must match "
                        f"retry_cause={retry_cause!r}",
                    )
                )

    if isinstance(reason, str) and _G27_FORBIDDEN_REASON_VOCAB.search(reason):
        match = _G27_FORBIDDEN_REASON_VOCAB.search(reason)
        issues.append(
            Issue(
                "G27",
                f"implementation_review.reason contains forbidden infra-cause vocab "
                f"{match.group(0)!r}; transient causes belong in retry_cause/retry_attempts, "
                f"not reason",
            )
        )

    # Canonical-phrase enforcement: retry_count == 2 AND all attempts non-ok AND verdict rejected.
    if retry_count == 2 and verdict == "rejected" and isinstance(retry_attempts, list):
        all_failed = retry_attempts and all(
            isinstance(a, dict) and a.get("outcome") != "ok" for a in retry_attempts
        )
        if all_failed and reason != _G27_CANONICAL_FAILED_PHRASE:
            issues.append(
                Issue(
                    "G27",
                    f"when retry_count=2 with all attempts non-ok and verdict=rejected, "
                    f"implementation_review.reason must equal exactly "
                    f"{_G27_CANONICAL_FAILED_PHRASE!r}; got {reason!r}",
                )
            )
    return issues
