"""Attempt + lifecycle half of the paired-arm validator for `scripts/validate-paired-arm.py`.

See `validate-paired-arm.py`'s own docstring for exit codes, the four `record_state`s, and usage.
This module implements the per-attempt nullability table (`validate_attempt()`), the
arm-conditional subset invariant (`check_subset_invariant()`), and the four per-state entry points
(`validate_preregistered()` / `_in_progress()` / `_graded()` / `_complete()`) the CLI dispatches on.

The prereg-side checks -- shared constants, `PlumbingError`, `load_record()`, every `check_*`
prereg helper, `validate_prereg()`, `check_prereg_self_hash()` -- live in `_paired_arm_prereg.py`
and are re-exported here so the CLI and the selftests keep importing from one place.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import _canon  # type: ignore[import-not-found]  # noqa: E402
from _paired_arm_prereg import (  # noqa: E402
    HEADLINE_EXCLUDED,
    N_PAIRS,
    SKILL_ROOT,
    STUDY_SCENARIOS,
    VALID_ARMS,
    VALID_ASSERTION_SOURCES,
    VALID_CANDIDATE_OUTPUT_STATUSES,
    VALID_CRITERION_CLASSES,
    VALID_GRADE_OUTCOMES,
    VALID_GRADE_STATUS_NA_REASONS,
    VALID_GRADE_STATUSES,
    VALID_RECORD_STATES,
    VALID_TRIAL_STATUSES,
    K,
    PlumbingError,
    _is_hex64,
    check_prereg_self_hash,
    load_record,
    validate_prereg,
)

# ---- attempts ---------------------------------------------------------------------------------


def _attempt_cap(pair_id: Any) -> int:
    """2 by default; execution.json may grant a NAMED pair extra attempts.

    Read from the OPERATIONAL record, never the prereg: the prereg freezes at first dispatch, and a
    grant is a fact measured afterwards. A missing or unreadable execution.json falls back to the
    preregistered 2 -- an absent operational file must never WIDEN a bound, only fail to widen it.
    Mirrors `attempt_cap()` in paired_arm_run.py, which gates dispatch; this gates the record, and
    the two must agree or a dispatched attempt cannot be stored.
    """
    if not isinstance(pair_id, str):
        return 2
    try:
        grants = json.loads(
            (SKILL_ROOT / "evals" / "paired-arm-outputs" / "execution.json").read_text()
        ).get("attempt_grants", [])
    except (OSError, ValueError):
        return 2
    return 2 + sum(
        int(g.get("extra_attempts", 0))
        for g in grants
        if isinstance(g, dict) and g.get("pair_id") == pair_id
    )


def validate_attempt(
    attempt: Any,
    idx: int,
    canon: _canon.Canon,
    *,
    require_grade_status: bool,
    scenarios: dict[str, str] | None = None,
) -> list[str]:
    """`scenarios` defaults to the 11 study scenarios. The Phase-2 cost pilot runs on EXCLUDED
    scenarios and passes its own set, so the pilot exercises this exact attempt validation rather
    than a parallel implementation of it -- which is the point of a pilot."""
    scenarios = STUDY_SCENARIOS if scenarios is None else scenarios
    p = f"attempts[{idx}]"
    if not isinstance(attempt, dict):
        return [f"[{p}] not an object"]
    issues: list[str] = []
    add = issues.append

    if attempt.get("scenario_id") not in scenarios:
        add(f"[{p}] scenario_id {attempt.get('scenario_id')!r} not one of {sorted(scenarios)}")
    if attempt.get("arm") not in VALID_ARMS:
        add(f"[{p}] arm {attempt.get('arm')!r} not one of {VALID_ARMS}")
    slot_index, attempt_index = attempt.get("slot_index"), attempt.get("attempt_index")
    if not isinstance(slot_index, int) or not (1 <= slot_index <= K):
        add(f"[{p}] slot_index must be an int in 1..{K}, got {slot_index!r}")
    cap = _attempt_cap(attempt.get("pair_id"))
    if not isinstance(attempt_index, int) or not (1 <= attempt_index <= cap):
        add(f"[{p}] attempt_index must be an int in 1..{cap}, got {attempt_index!r}")

    tv = attempt.get("trial_validity")
    if not isinstance(tv, dict) or tv.get("status") not in VALID_TRIAL_STATUSES:
        add(f"[{p}] trial_validity.status must be one of {VALID_TRIAL_STATUSES}")
        return issues  # the nullability branches below all key off status; bail rather than cascade
    status, reason = tv["status"], tv.get("reason")
    if status == "invalid" and reason not in canon.invalid_reasons:
        add(
            f"[{p}] trial_validity.reason {reason!r} must be one of the closed exogenous reasons {canon.invalid_reasons}"
        )
    elif status == "valid" and reason is not None:
        add(f"[{p}] trial_validity.reason must be null when status=='valid'")

    cos = attempt.get("candidate_output_status")
    verdict_json, structural_report = attempt.get("verdict_json"), attempt.get("structural_report")
    assertion_results, raw_output_path = (
        attempt.get("assertion_results"),
        attempt.get("raw_output_path"),
    )

    if status == "invalid":
        # exogenous: every downstream field is null -- including assertion_results, which is
        # null here (NOT []): null means "no candidate judgment exists", [] would read as
        # "judged, nothing passed".
        for field, value in (
            ("candidate_output_status", cos),
            ("verdict_json", verdict_json),
            ("structural_report", structural_report),
            ("raw_output_path", raw_output_path),
            ("assertion_results", assertion_results),
        ):
            if value is not None:
                add(f"[{p}] {field} must be null for an exogenous-invalid trial")
    elif cos not in VALID_CANDIDATE_OUTPUT_STATUSES:
        add(f"[{p}] candidate_output_status {cos!r} not one of {VALID_CANDIDATE_OUTPUT_STATUSES}")
    elif cos == "ok":
        if not isinstance(verdict_json, dict):
            add(f"[{p}] verdict_json required (non-null) when candidate_output_status=='ok'")
        if not isinstance(structural_report, dict):
            add(f"[{p}] structural_report required (non-null) when candidate_output_status=='ok'")
        if not isinstance(raw_output_path, str) or not raw_output_path:
            add(f"[{p}] raw_output_path required when candidate_output_status=='ok'")
        if not isinstance(assertion_results, list) or not assertion_results:
            add(f"[{p}] assertion_results required (non-empty) when candidate_output_status=='ok'")
    else:  # malformed | runaway
        if verdict_json is not None:
            add(f"[{p}] verdict_json must be null when candidate_output_status=={cos!r}")
        if structural_report is not None:
            add(f"[{p}] structural_report must be null when candidate_output_status=={cos!r}")
        if not isinstance(assertion_results, list) or not assertion_results:
            add(f"[{p}] assertion_results required when candidate_output_status=={cos!r}")
        elif any(a.get("passed") is not False for a in assertion_results if isinstance(a, dict)):
            add(
                f"[{p}] every assertion_results[].passed must be false when candidate_output_status=={cos!r}"
            )

    if isinstance(assertion_results, list):
        for j, a in enumerate(assertion_results):
            if not isinstance(a, dict):
                add(f"[{p}.assertion_results[{j}]] not an object")
                continue
            if not isinstance(a.get("assertion_index"), int):
                add(f"[{p}.assertion_results[{j}]] assertion_index missing/not int")
            if not isinstance(a.get("assertion_text"), str) or not a["assertion_text"]:
                add(f"[{p}.assertion_results[{j}]] assertion_text missing/empty")
            if a.get("criterion_class") not in VALID_CRITERION_CLASSES:
                add(f"[{p}.assertion_results[{j}]] criterion_class invalid")
            if a.get("source") not in VALID_ASSERTION_SOURCES:
                add(
                    f"[{p}.assertion_results[{j}]] source must be one of "
                    f"{VALID_ASSERTION_SOURCES} -- 5 of the 11 study scenarios have zero "
                    "deterministic assertions, so grade_structural.py's general_checks are the "
                    "only per-output results that exist before semantic grading; without a "
                    "source tag a general check and an evals.json assertion share an "
                    "assertion_index namespace they do not share"
                )
            if not isinstance(a.get("passed"), bool):
                add(f"[{p}.assertion_results[{j}]] passed missing/not bool")

    grade_status = attempt.get("grade_status")
    if require_grade_status or grade_status is not None:
        if grade_status not in VALID_GRADE_STATUSES:
            add(f"[{p}] grade_status {grade_status!r} not one of {VALID_GRADE_STATUSES}")
        elif grade_status == "not_applicable":
            if attempt.get("grade_status_reason") not in VALID_GRADE_STATUS_NA_REASONS:
                add(
                    f"[{p}] grade_status_reason must be one of {VALID_GRADE_STATUS_NA_REASONS} when grade_status=='not_applicable'"
                )
        else:  # "graded"
            if attempt.get("mechanical_grade") not in VALID_GRADE_OUTCOMES:
                add(f"[{p}] mechanical_grade required from {VALID_GRADE_OUTCOMES} when graded")
            if attempt.get("semantic_grade") not in VALID_GRADE_OUTCOMES:
                add(f"[{p}] semantic_grade required from {VALID_GRADE_OUTCOMES} when graded")
            for field in ("grader_id", "grader_model"):
                if not isinstance(attempt.get(field), str) or not attempt[field]:
                    add(f"[{p}] {field} required (non-empty) when graded")
            if not _is_hex64(attempt.get("grader_prompt_sha256")):
                add(f"[{p}] grader_prompt_sha256 required (sha256 hex) when graded")
    return issues


def _terminal(attempt: dict) -> bool:
    return not (
        attempt.get("grade_status") == "not_applicable"
        and attempt.get("grade_status_reason") == "superseded"
    )


def check_subset_invariant(per_scenario: dict) -> list[str]:
    """The arm-conditional subset invariant (a declared divergence in the prereg): applies to
    with_skill ONLY. flag: semantic.count <= mechanical.count. restraint: mechanical.count <=
    semantic.count. Silently skips scenarios/arms whose summary block isn't shaped this way --
    that shape is only expected once grading has actually populated per_scenario."""
    issues: list[str] = []
    for sid, kind in STUDY_SCENARIOS.items():
        block = per_scenario.get(sid, {})
        if not isinstance(block, dict):
            continue
        with_skill = block.get("with_skill")
        if not isinstance(with_skill, dict):
            continue
        mech = with_skill.get("mechanical")
        sem = with_skill.get("semantic")
        if not isinstance(mech, dict) or not isinstance(sem, dict):
            continue
        m, s = mech.get("count"), sem.get("count")
        if not isinstance(m, int) or not isinstance(s, int):
            continue
        if kind == "flag" and s > m:
            issues.append(
                f"[subset_invariant] {sid} (with_skill): semantic.count({s}) > mechanical.count({m})"
            )
        if kind == "restraint" and m > s:
            issues.append(
                f"[subset_invariant] {sid} (with_skill): mechanical.count({m}) > semantic.count({s})"
            )
    return issues


# ---- per-record_state dispatch -----------------------------------------------------------------


def validate_preregistered(record: dict) -> list[str]:
    issues = validate_prereg(
        record.get("prereg"), frozen_at=record.get("material_hashes_frozen_at")
    )
    issues += check_prereg_self_hash(record)
    if record.get("attempts") != []:
        issues.append("[record_state=preregistered] attempts must be empty ([])")
    if record.get("per_scenario") != {}:
        issues.append("[record_state=preregistered] per_scenario must be empty ({})")
    return issues


def validate_in_progress(record: dict, canon: _canon.Canon) -> list[str]:
    issues = validate_prereg(
        record.get("prereg"), frozen_at=record.get("material_hashes_frozen_at")
    )
    issues += check_prereg_self_hash(record)
    attempts = record.get("attempts")
    if not isinstance(attempts, list):
        return [*issues, "[record_state=in_progress] attempts must be a list"]
    for i, a in enumerate(attempts):
        issues += validate_attempt(a, i, canon, require_grade_status=False)
    return issues


def validate_graded(record: dict, canon: _canon.Canon) -> list[str]:
    issues = validate_prereg(
        record.get("prereg"), frozen_at=record.get("material_hashes_frozen_at")
    )
    issues += check_prereg_self_hash(record)
    attempts = record.get("attempts")
    if not isinstance(attempts, list) or not attempts:
        return [*issues, "[record_state=graded] attempts must be a non-empty list"]
    for i, a in enumerate(attempts):
        issues += validate_attempt(a, i, canon, require_grade_status=True)
    return issues


def validate_complete(record: dict, canon: _canon.Canon) -> list[str]:
    issues = validate_graded(record, canon)
    attempts = record.get("attempts")
    if not isinstance(attempts, list):
        return issues
    terminal_counts: dict[tuple[str, str], int] = {}
    for a in attempts:
        if not isinstance(a, dict):
            continue
        if not _terminal(a):
            continue
        key = (a.get("scenario_id"), a.get("arm"))
        terminal_counts[key] = terminal_counts.get(key, 0) + 1
    for sid in STUDY_SCENARIOS:
        for arm in VALID_ARMS:
            n = terminal_counts.get((sid, arm), 0)
            if n != K:
                issues.append(
                    f"[record_state=complete] {sid}/{arm}: expected exactly {K} terminal slots, got {n}"
                )
    per_scenario = record.get("per_scenario")
    if not isinstance(per_scenario, dict):
        issues.append("[record_state=complete] per_scenario must be an object")
    else:
        missing = set(STUDY_SCENARIOS) - per_scenario.keys()
        if missing:
            issues.append(
                f"[record_state=complete] per_scenario missing scenario(s): {sorted(missing)}"
            )
        issues += check_subset_invariant(per_scenario)
    return issues


__all__ = [
    "HEADLINE_EXCLUDED",
    "N_PAIRS",
    "SKILL_ROOT",
    "STUDY_SCENARIOS",
    "VALID_ARMS",
    "VALID_RECORD_STATES",
    "K",
    "PlumbingError",
    "load_record",
    "validate_complete",
    "validate_graded",
    "validate_in_progress",
    "validate_preregistered",
]
