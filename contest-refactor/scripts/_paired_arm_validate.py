"""Library for `scripts/validate-paired-arm.py` (the CLI stays a thin wrapper -- this module
holds the record-shape/lifecycle checks, mirroring the `_artifact_core.py` / `validate-artifact.py`
split already used in this repo for a validator too big for one file).

See `validate-paired-arm.py`'s own docstring for exit codes, the four `record_state`s, and usage.
This module implements: `PlumbingError`, `load_record()`, the prereg structural/provenance checks
(`validate_prereg()` and its `check_*` helpers), the per-attempt nullability table
(`validate_attempt()`), the arm-conditional subset invariant (`check_subset_invariant()`), and the
four per-state entry points (`validate_preregistered()` / `_in_progress()` / `_graded()` /
`_complete()`) the CLI dispatches on.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import _canon  # type: ignore[import-not-found]  # noqa: E402
from _noise_floor import required_n_for_power  # type: ignore[import-not-found]  # noqa: E402

SKILL_ROOT = SCRIPT_DIR.parent

VALID_ARMS = ("with_skill", "without_skill")
VALID_RECORD_STATES = ("preregistered", "in_progress", "graded", "complete")
VALID_CANDIDATE_OUTPUT_STATUSES = ("ok", "malformed", "runaway")
VALID_TRIAL_STATUSES = ("valid", "invalid")
VALID_GRADE_STATUSES = ("graded", "not_applicable")
VALID_GRADE_STATUS_NA_REASONS = ("superseded", "partial", "exogenous_invalid")
VALID_CRITERION_CLASSES = ("outcome", "skill_contract", "unclassified")
VALID_GRADE_OUTCOMES = ("caught", "held", "missed", "over_flagged", "uncertain")
VALID_EXPECTED_BASELINES = ("miss", "hold")

# The 11 study scenarios and their kind, fixed by the delegation brief (5 principal flags, 2
# usable principal restraint twins, both core flag/restraint pairs). `flag` kind's own
# expected_baseline is a PREDICTION, not a derived property, so this module validates enum
# membership and demands a recorded rationale -- it does not dictate which value a flag may take.
# An earlier draft hard-coded flag -> "miss"; that would have forced the two core flags to be
# preregistered against evidence already in hand (evals/advisory_baseline.json measured bare
# models catching every component-grain defect unaided, three rounds, two models). A validator
# that constrains a hypothesis to a default cannot express a differentiated prediction, which is
# precisely what makes this run informative. `restraint` stays pinned to "hold" for a different
# reason: it is definitional, not predictive (see check_expected_baseline).
STUDY_SCENARIOS: dict[str, str] = {
    "suppression-flag": "flag",
    "crossplat-flag": "flag",
    "suppression-restraint": "restraint",
    "crossplat-restraint": "restraint",
    "principal-invariant-owner-flag": "flag",
    "principal-invariant-owner-restraint": "restraint",
    "principal-duplicated-rule-flag": "flag",
    "principal-process-owner-flag": "flag",
    "principal-consistency-boundary-flag": "flag",
    "principal-consistency-boundary-restraint": "restraint",
    "principal-abstraction-seam-flag": "flag",
}
HEADLINE_EXCLUDED = {"principal-abstraction-seam-flag"}
K = 5
N_PAIRS = len(STUDY_SCENARIOS) * K  # 55


class PlumbingError(Exception):
    """Raised for anything that means "cannot even attempt validation" -- exit 2."""


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _is_hex64(value: Any) -> bool:
    return (
        isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)
    )


def load_record(path: Path) -> dict:
    if not path.is_file():
        raise PlumbingError(f"not a file: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise PlumbingError(f"{path}: invalid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise PlumbingError(f"{path}: top-level JSON must be an object, got {type(data).__name__}")
    return data


# ---- prereg: structural + provenance checks (record_state == "preregistered", but also run
# for every later state since the prereg must never change once frozen) -----------------------


def check_rule_provenance(prereg: dict) -> list[str]:
    """mechanical_rule/semantic_rule/contamination_rule must be copied VERBATIM from
    evals/principal_baseline_replication.json's own prereg -- that provenance, machine-checked
    against the historical file rather than merely asserted, is what makes "frozen" checkable."""
    issues: list[str] = []
    source_path = SKILL_ROOT / "evals" / "principal_baseline_replication.json"
    try:
        source = json.loads(source_path.read_text(encoding="utf-8"))
        source_prereg = source.get("prereg", {})
    except (OSError, json.JSONDecodeError) as exc:
        issues.append(f"[rule_provenance] cannot read {source_path} to verify verbatim copy: {exc}")
        return issues
    for key in ("mechanical_rule", "semantic_rule", "contamination_rule"):
        want = source_prereg.get(key)
        got = prereg.get(key)
        if not isinstance(got, str) or not got:
            issues.append(f"[rule_provenance] prereg.{key} missing or not a non-empty string")
        elif got != want:
            issues.append(
                f"[rule_provenance] prereg.{key} does not match "
                f"principal_baseline_replication.json's prereg.{key} verbatim"
            )
    return issues


def check_candidate_output_rule(prereg: dict) -> list[str]:
    issues: list[str] = []
    rule = prereg.get("candidate_output_rule")
    if not isinstance(rule, dict):
        return ["[candidate_output_rule] missing or not an object"]
    rows = rule.get("rows")
    if not isinstance(rows, list) or len(rows) != 3:
        issues.append("[candidate_output_rule] rows must be a list of exactly 3 entries")
        rows = []
    classifications = []
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            issues.append(f"[candidate_output_rule] rows[{i}] must be an object")
            continue
        for field in ("event", "classification", "effect"):
            if not isinstance(row.get(field), str) or not row[field]:
                issues.append(f"[candidate_output_rule] rows[{i}].{field} missing or empty")
        cls = row.get("classification")
        if cls not in ("adherence", "exogenous"):
            issues.append(
                f"[candidate_output_rule] rows[{i}].classification={cls!r} "
                "must be 'adherence' or 'exogenous'"
            )
        classifications.append(cls)
    if classifications and classifications.count("adherence") != 2:
        issues.append(
            "[candidate_output_rule] exactly 2 rows must classify as 'adherence' "
            "(malformed/empty output, candidate-induced runaway) and 1 as 'exogenous' "
            "(infrastructure timeout / rate limit / auth failure / lost artifact)"
        )
    if not isinstance(rule.get("tie_break"), str) or not rule["tie_break"]:
        issues.append("[candidate_output_rule] tie_break missing or empty")
    elif "runaway" not in rule["tie_break"].lower():
        issues.append(
            "[candidate_output_rule] tie_break must resolve ambiguity toward 'runaway' "
            "(the counted-failure/adherence side), per item 21"
        )
    return issues


def check_decision_rules(prereg: dict) -> list[str]:
    issues: list[str] = []
    dr = prereg.get("decision_rules")
    if not isinstance(dr, dict):
        return ["[decision_rules] missing or not an object"]
    required = (
        "decision_1_principal_corpus_growth",
        "decision_2_core_suite_acceptance",
        "decision_3_global_recall",
        "decision_4_negative_regression",
    )
    for key in required:
        if key not in dr or not isinstance(dr[key], dict):
            issues.append(f"[decision_rules] missing decision block: {key}")
    d2 = dr.get("decision_2_core_suite_acceptance", {})
    if isinstance(d2, dict):
        restriction = d2.get("criterion_class_restriction", "")
        if "outcome" not in str(restriction):
            issues.append(
                "[decision_rules] decision_2's criterion_class_restriction must scope to "
                'criterion_class=="outcome" assertions only'
            )
    d4 = dr.get("decision_4_negative_regression", {})
    if isinstance(d4, dict) and not isinstance(d4.get("rows"), list):
        issues.append("[decision_rules] decision_4_negative_regression.rows missing")
    if (
        "language_rule" not in dr
        or not isinstance(dr["language_rule"], str)
        or not dr["language_rule"]
    ):
        issues.append("[decision_rules] language_rule missing or empty")
    return issues


def _check_hash_map(hashes: Any, tag: str, required_paths: set[str], *, exact: bool) -> list[str]:
    """Shared sha256-hex-map checker for `material_hashes` and `historical_file_hashes`: every
    value is a 64-hex digest, every path resolves under SKILL_ROOT, and the recorded hash
    matches the file's content RIGHT NOW -- a live re-verification, not a one-time assertion, so
    drift in a supposedly-frozen file is caught on every run (D3, for the historical pair)."""
    if not isinstance(hashes, dict) or (not exact and not hashes):
        return [f"[{tag}] missing or empty"]
    issues: list[str] = []
    if exact and set(hashes.keys()) != required_paths:
        issues.append(f"[{tag}] keys must be exactly {sorted(required_paths)}")
    elif not exact:
        missing = required_paths - hashes.keys()
        if missing:
            issues.append(f"[{tag}] missing entries for: {sorted(missing)}")
    for rel_path, want in hashes.items():
        if not _is_hex64(want):
            issues.append(f"[{tag}] {rel_path}: value is not a sha256 hex digest")
            continue
        full = SKILL_ROOT / rel_path
        if not full.is_file():
            issues.append(f"[{tag}] {rel_path}: file does not exist at {full}")
        elif _sha256_file(full) != want:
            issues.append(
                f"[{tag}] {rel_path}: recorded hash does not match file on disk (drifted since freeze)"
            )
    return issues


def check_material_hashes(prereg: dict) -> list[str]:
    required = {
        "references/architecture-rubric.md",
        "references/method.md",
        "evals/paired_arm_task_with_skill.md",
        "evals/paired_arm_task_without_skill.md",
    } | {f"evals/scenarios/{sid}/scenario.md" for sid in STUDY_SCENARIOS}
    return _check_hash_map(prereg.get("material_hashes"), "material_hashes", required, exact=False)


def check_historical_file_hashes(prereg: dict) -> list[str]:
    """D3: the two historical baseline files must stay byte-identical to their preregistered
    hashes for the life of this study."""
    required = {"evals/principal_baseline.json", "evals/principal_baseline_replication.json"}
    return _check_hash_map(
        prereg.get("historical_file_hashes"), "historical_file_hashes", required, exact=True
    )


def check_frozen_order(prereg: dict) -> list[str]:
    issues: list[str] = []
    order = prereg.get("frozen_order")
    if not isinstance(order, list):
        return ["[frozen_order] missing or not a list"]
    if len(order) != N_PAIRS:
        issues.append(f"[frozen_order] must have exactly {N_PAIRS} entries, got {len(order)}")
    seen_ids: set[str] = set()
    reps_by_scenario: dict[str, list[int]] = {}
    for i, entry in enumerate(order):
        if not isinstance(entry, dict):
            issues.append(f"[frozen_order] entry {i} is not an object")
            continue
        pair_id = entry.get("pair_id")
        scenario_id = entry.get("scenario_id")
        rep = entry.get("rep")
        arm_order = entry.get("arm_order")
        if not isinstance(pair_id, str) or not pair_id:
            issues.append(f"[frozen_order] entry {i}: pair_id missing")
        elif pair_id in seen_ids:
            issues.append(f"[frozen_order] duplicate pair_id: {pair_id}")
        else:
            seen_ids.add(pair_id)
        if scenario_id not in STUDY_SCENARIOS:
            issues.append(
                f"[frozen_order] entry {i}: scenario_id {scenario_id!r} not one of the 11 study scenarios"
            )
        else:
            reps_by_scenario.setdefault(scenario_id, []).append(rep)
        if not isinstance(rep, int) or not (1 <= rep <= K):
            issues.append(f"[frozen_order] entry {i}: rep must be an int in 1..{K}, got {rep!r}")
        if not isinstance(arm_order, list) or sorted(arm_order) != sorted(VALID_ARMS):
            issues.append(
                f"[frozen_order] entry {i}: arm_order must be a permutation of {VALID_ARMS}, got {arm_order!r}"
            )
    for sid in STUDY_SCENARIOS:
        reps = sorted(reps_by_scenario.get(sid, []))
        if reps != list(range(1, K + 1)):
            issues.append(
                f"[frozen_order] scenario {sid!r} must appear with reps 1..{K} exactly once each, got {reps}"
            )
    for seed_key in ("dispatch_order_seed", "grading_subsample_seed"):
        if not isinstance(prereg.get(seed_key), int):
            issues.append(f"[frozen_order] prereg.{seed_key} missing or not an int")
    return issues


def check_terminal_selection_predicate(prereg: dict) -> list[str]:
    predicate = prereg.get("terminal_selection_predicate")
    if not isinstance(predicate, dict):
        return ["[terminal_selection_predicate] missing or not an object"]
    issues = []
    for field in ("attempt_2_is_terminal_iff", "otherwise", "basis"):
        if not isinstance(predicate.get(field), str) or not predicate[field]:
            issues.append(f"[terminal_selection_predicate] {field} missing or empty")
    basis = str(predicate.get("basis", ""))
    if "ordering" not in basis.lower():
        issues.append(
            "[terminal_selection_predicate] basis must state the predicate is never ordering-based"
        )
    return issues


def check_expected_baseline(prereg: dict) -> list[str]:
    issues: list[str] = []
    eb = prereg.get("expected_baseline")
    if not isinstance(eb, dict):
        return ["[expected_baseline] missing or not an object"]
    missing = set(STUDY_SCENARIOS) - eb.keys()
    if missing:
        issues.append(f"[expected_baseline] missing scenario(s): {sorted(missing)}")
    for sid, kind in STUDY_SCENARIOS.items():
        value = eb.get(sid)
        if value not in VALID_EXPECTED_BASELINES:
            issues.append(
                f"[expected_baseline] {sid}: {value!r} not one of {VALID_EXPECTED_BASELINES}"
            )
            continue
        if kind == "restraint" and value != "hold":
            # A restraint twin predicted to be over-flagged by the bare arm would mean the twin
            # is not a legitimate carve-out at all -- a corpus defect, not a hypothesis.
            issues.append(
                f"[expected_baseline] {sid} (kind=restraint): {value!r} -- a restraint twin must "
                f"be predicted 'hold'; predicting 'miss' asserts the twin is not a valid carve-out"
            )
    if not isinstance(prereg.get("expected_baseline_rationale"), dict):
        issues.append(
            "[expected_baseline] expected_baseline_rationale missing -- each prediction must "
            "record why it was made, so a hypothesis contradicting held evidence is visible"
        )
    return issues


def check_non_claim(prereg: dict) -> list[str]:
    issues: list[str] = []
    nc = prereg.get("non_claim")
    if not isinstance(nc, dict):
        return ["[non_claim] missing or not an object"]
    for field in ("claim_type", "evaluate_lift_status", "readout_language_rule"):
        if not isinstance(nc.get(field), str) or not nc[field]:
            issues.append(f"[non_claim] {field} missing or empty")
    if nc.get("evaluate_lift_status") != "unreportable":
        issues.append(
            "[non_claim] evaluate_lift_status must be 'unreportable' (floors: [] in noise_floor.json)"
        )
    params = nc.get("power_params")
    if not isinstance(params, dict) or {"min_effect", "alpha", "power"} - params.keys():
        issues.append("[non_claim] power_params must have min_effect/alpha/power")
    else:
        try:
            want_n = required_n_for_power(params["min_effect"], params["alpha"], params["power"])
        except (ValueError, TypeError) as exc:
            issues.append(f"[non_claim] power_params invalid: {exc}")
        else:
            if nc.get("required_n_for_power") != want_n:
                issues.append(
                    f"[non_claim] required_n_for_power={nc.get('required_n_for_power')!r} does not match "
                    f"_noise_floor.required_n_for_power(**power_params)={want_n} -- recompute, don't hand-type"
                )
    if nc.get("observed_n_cases") != len(STUDY_SCENARIOS):
        issues.append(
            f"[non_claim] observed_n_cases must equal {len(STUDY_SCENARIOS)} (the study corpus size)"
        )
    return issues


def check_declared_divergences(prereg: dict) -> list[str]:
    issues: list[str] = []
    divs = prereg.get("declared_divergences")
    if not isinstance(divs, list):
        return ["[declared_divergences] missing or not a list"]
    ids = set()
    for i, d in enumerate(divs):
        if not isinstance(d, dict):
            issues.append(f"[declared_divergences] entry {i} is not an object")
            continue
        for field in ("id", "statement", "reason"):
            if not isinstance(d.get(field), str) or not d[field]:
                issues.append(f"[declared_divergences] entry {i}: {field} missing or empty")
        ids.add(d.get("id"))
    required_ids = {"subset_invariant_with_skill_only", "readme_746_outcome_only"}
    missing = required_ids - ids
    if missing:
        issues.append(
            f"[declared_divergences] missing required divergence id(s): {sorted(missing)}"
        )
    return issues


def check_arms(prereg: dict) -> list[str]:
    issues: list[str] = []
    if not isinstance(prereg.get("arm_model"), str) or not prereg["arm_model"]:
        issues.append("[arms] arm_model missing or empty")
    arms = prereg.get("arms")
    if not isinstance(arms, dict) or set(arms.keys()) != set(VALID_ARMS):
        return [*issues, f"[arms] arms must have exactly keys {VALID_ARMS}"]
    with_skill = arms.get("with_skill", {})
    without_skill = arms.get("without_skill", {})
    want_materials = {"references/architecture-rubric.md", "references/method.md"}
    if set(with_skill.get("materials", [])) != want_materials:
        issues.append(f"[arms] with_skill.materials must be exactly {sorted(want_materials)}")
    if without_skill.get("materials", None) not in ([], None):
        issues.append(
            "[arms] without_skill.materials must be empty (scenario + neutral prompt only)"
        )
    for arm_name, arm in (("with_skill", with_skill), ("without_skill", without_skill)):
        template = arm.get("task_template")
        if not isinstance(template, str) or not (SKILL_ROOT / template).is_file():
            issues.append(f"[arms] {arm_name}.task_template missing or does not resolve to a file")
    return issues


def validate_prereg(prereg: Any) -> list[str]:
    if not isinstance(prereg, dict):
        return ["[prereg] missing or not an object"]
    issues: list[str] = []
    issues += check_rule_provenance(prereg)
    issues += check_candidate_output_rule(prereg)
    issues += check_decision_rules(prereg)
    issues += check_arms(prereg)
    issues += check_material_hashes(prereg)
    issues += check_historical_file_hashes(prereg)
    issues += check_frozen_order(prereg)
    issues += check_terminal_selection_predicate(prereg)
    issues += check_expected_baseline(prereg)
    issues += check_non_claim(prereg)
    issues += check_declared_divergences(prereg)
    for key in ("K", "decision_threshold", "headline_excluded", "study_scenarios"):
        if key not in prereg:
            issues.append(f"[prereg] missing top-level field: {key}")
    if prereg.get("K") != K:
        issues.append(f"[prereg] K must be {K}, got {prereg.get('K')!r}")
    if prereg.get("headline_excluded") != sorted(HEADLINE_EXCLUDED):
        issues.append(f"[prereg] headline_excluded must be {sorted(HEADLINE_EXCLUDED)}")
    return issues


def check_prereg_self_hash(record: dict) -> list[str]:
    """`prereg_sha256` is this record's own self-referential freeze hash -- sha256 of the
    canonical-JSON `prereg` object. Every state re-checks it against the live `prereg` object,
    which is how "prereg byte-identical to its preregistered hash" (the in_progress+ row of the
    lifecycle table) is actually checkable without an external baseline file."""
    prereg = record.get("prereg")
    want = record.get("prereg_sha256")
    if not _is_hex64(want):
        return ["[prereg_sha256] missing or not a sha256 hex digest"]
    got = _sha256_text(_canonical_json(prereg))
    if got != want:
        return [
            "[prereg_sha256] does not match sha256(canonical_json(prereg)) -- prereg has drifted since freeze"
        ]
    return []


# ---- attempts ---------------------------------------------------------------------------------


def validate_attempt(
    attempt: Any, idx: int, canon: _canon.Canon, *, require_grade_status: bool
) -> list[str]:
    p = f"attempts[{idx}]"
    if not isinstance(attempt, dict):
        return [f"[{p}] not an object"]
    issues: list[str] = []
    add = issues.append

    if attempt.get("scenario_id") not in STUDY_SCENARIOS:
        add(f"[{p}] scenario_id {attempt.get('scenario_id')!r} not one of the 11 study scenarios")
    if attempt.get("arm") not in VALID_ARMS:
        add(f"[{p}] arm {attempt.get('arm')!r} not one of {VALID_ARMS}")
    slot_index, attempt_index = attempt.get("slot_index"), attempt.get("attempt_index")
    if not isinstance(slot_index, int) or not (1 <= slot_index <= K):
        add(f"[{p}] slot_index must be an int in 1..{K}, got {slot_index!r}")
    if not isinstance(attempt_index, int) or attempt_index not in (1, 2):
        add(f"[{p}] attempt_index must be 1 or 2, got {attempt_index!r}")

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
    issues = validate_prereg(record.get("prereg"))
    issues += check_prereg_self_hash(record)
    if record.get("attempts") != []:
        issues.append("[record_state=preregistered] attempts must be empty ([])")
    if record.get("per_scenario") != {}:
        issues.append("[record_state=preregistered] per_scenario must be empty ({})")
    return issues


def validate_in_progress(record: dict, canon: _canon.Canon) -> list[str]:
    issues = validate_prereg(record.get("prereg"))
    issues += check_prereg_self_hash(record)
    attempts = record.get("attempts")
    if not isinstance(attempts, list):
        return [*issues, "[record_state=in_progress] attempts must be a list"]
    for i, a in enumerate(attempts):
        issues += validate_attempt(a, i, canon, require_grade_status=False)
    return issues


def validate_graded(record: dict, canon: _canon.Canon) -> list[str]:
    issues = validate_prereg(record.get("prereg"))
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
