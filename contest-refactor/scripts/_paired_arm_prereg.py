"""Prereg half of the paired-arm validator: the frozen-record structural and provenance checks.

Split out of `_paired_arm_validate.py` when that module reached 795 lines against the repo's
800-line hard cap (`common/scripts/check_module_size.py`) -- the same
`validate-artifact.py`/`_artifact_core.py` precedent, one level further down. The dependency runs
ONE way: `_paired_arm_validate` imports from here, never the reverse, so the shared constants and
hash helpers live here with the checks that own them.

This module implements: the shared constants (`STUDY_SCENARIOS`, `K`, `VALID_*`), `PlumbingError`,
`load_record()`, every `check_*` prereg helper, `validate_prereg()`, and `check_prereg_self_hash()`.
The attempt-level nullability table, the subset invariant, and the four per-`record_state` entry
points stay in `_paired_arm_validate.py`.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from _noise_floor import required_n_for_power  # type: ignore[import-not-found]  # noqa: E402

SKILL_ROOT = SCRIPT_DIR.parent

VALID_ARMS = ("with_skill", "without_skill")
VALID_RECORD_STATES = ("preregistered", "in_progress", "graded", "complete")
VALID_CANDIDATE_OUTPUT_STATUSES = ("ok", "malformed", "runaway")
VALID_TRIAL_STATUSES = ("valid", "invalid")
VALID_GRADE_STATUSES = ("graded", "not_applicable")
VALID_GRADE_STATUS_NA_REASONS = ("superseded", "partial", "exogenous_invalid")
VALID_CRITERION_CLASSES = ("outcome", "skill_contract", "unclassified")
VALID_ASSERTION_SOURCES = ("general_check", "evals_assertion")
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


def _git_show_bytes(sha: str, rel_path: str) -> bytes | None:
    """`git show <sha>:./<rel_path>`, resolved relative to SKILL_ROOT as cwd (the leading `./`
    is what makes a bare relative path work as a git pathspec). None on any failure -- unknown
    commit, path didn't exist at that commit, not a git repo -- callers treat that as fail-closed,
    not as "no drift"."""
    try:
        proc = subprocess.run(
            ["git", "-C", str(SKILL_ROOT), "show", f"{sha}:./{rel_path}"],
            capture_output=True,
            check=True,
        )
    except (subprocess.CalledProcessError, OSError):
        return None
    return proc.stdout


def _check_hash_map(
    hashes: Any, tag: str, required_paths: set[str], *, exact: bool, frozen_at: str | None = None
) -> list[str]:
    """Shared sha256-hex-map checker for `material_hashes` and `historical_file_hashes`: every
    value is a 64-hex digest, every path resolves, and the recorded hash matches the file's
    content -- a live re-verification, not a one-time assertion, so drift in a supposedly-frozen
    file is caught on every run (D3, for the historical pair).

    `frozen_at`, when set, is the record's `material_hashes_frozen_at` commit: the content check
    runs against `git show <frozen_at>:./<rel_path>` instead of the live working tree. This is
    for a `record_state=="complete"` record whose materials legitimately changed on disk AFTER
    the study finished -- the record is checked against what it was frozen against, not against
    disk drift the record never claimed to track. An unresolvable commit or missing blob is a
    provenance failure, not weaker than drift, so it is reported the same way (fail-closed).
    """
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
        if frozen_at is not None:
            blob = _git_show_bytes(frozen_at, rel_path)
            if blob is None:
                issues.append(
                    f"[{tag}] {rel_path}: cannot resolve git show "
                    f"material_hashes_frozen_at={frozen_at!r}:./{rel_path}"
                )
            elif hashlib.sha256(blob).hexdigest() != want:
                issues.append(
                    f"[{tag}] {rel_path}: recorded hash does not match "
                    f"git show {frozen_at}:./{rel_path}"
                )
            continue
        full = SKILL_ROOT / rel_path
        if not full.is_file():
            issues.append(f"[{tag}] {rel_path}: file does not exist at {full}")
        elif _sha256_file(full) != want:
            issues.append(
                f"[{tag}] {rel_path}: recorded hash does not match file on disk (drifted since freeze)"
            )
    return issues


def check_material_hashes(prereg: dict, *, frozen_at: str | None = None) -> list[str]:
    required = {
        "references/architecture-rubric.md",
        "references/method.md",
        "evals/paired_arm_task_with_skill.md",
        "evals/paired_arm_task_without_skill.md",
    } | {f"evals/scenarios/{sid}/scenario.md" for sid in STUDY_SCENARIOS}
    return _check_hash_map(
        prereg.get("material_hashes"), "material_hashes", required, exact=False, frozen_at=frozen_at
    )


def check_historical_file_hashes(prereg: dict, *, frozen_at: str | None = None) -> list[str]:
    """D3: the two historical baseline files must stay byte-identical to their preregistered
    hashes for the life of this study."""
    required = {"evals/principal_baseline.json", "evals/principal_baseline_replication.json"}
    return _check_hash_map(
        prereg.get("historical_file_hashes"),
        "historical_file_hashes",
        required,
        exact=True,
        frozen_at=frozen_at,
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
    required_ids = {
        "subset_invariant_with_skill_only",
        "readme_746_outcome_only",
        "symmetric_vocabulary_instructions",
        "grading_protocol_frozen_at_phase_2",
        "dispatch_envelope_frozen_at_phase_2",
        "ladder_and_spec_first_grading",
    }
    missing = required_ids - ids
    if missing:
        issues.append(
            f"[declared_divergences] missing required divergence id(s): {sorted(missing)}"
        )
    return issues


def check_grading(prereg: dict) -> list[str]:
    """The grading protocol must be frozen in the prereg, not decided at Phase 4 when outputs
    already exist. Phase 1 shipped only the subsample seed/fraction/size; the grader model,
    prompt hash, ambiguity triggers, adjudication rule, and masking protocol were added in the
    Phase-2 amendment recorded as declared divergence `grading_protocol_frozen_at_phase_2`.

    The substantive checks here mirror the house style of `check_candidate_output_rule`: pin the
    load-bearing semantics (the three mechanically-checkable triggers, no-batching ABORTS rather
    than adjusts, a THIRD adjudicator decides) rather than only asserting keys exist."""
    g = prereg.get("grading")
    if not isinstance(g, dict):
        return ["[grading] missing or not an object"]
    issues: list[str] = []
    if not isinstance(g.get("grader_model"), str) or not g["grader_model"]:
        issues.append("[grading] grader_model missing or empty")

    prompt_file = g.get("grader_prompt_file")
    prompt_hash = g.get("grader_prompt_sha256")
    if not isinstance(prompt_file, str) or not (SKILL_ROOT / prompt_file).is_file():
        issues.append("[grading] grader_prompt_file missing or does not resolve to a file")
    elif prereg.get("material_hashes", {}).get(prompt_file) != prompt_hash:
        # material_hashes is live-verified against disk by _check_hash_map, so agreeing with it
        # is what makes grader_prompt_sha256 a real freeze rather than a second copy that can rot.
        issues.append(
            "[grading] grader_prompt_sha256 does not agree with material_hashes entry for "
            f"{prompt_file} -- the prompt's freeze hash is recorded twice and they have drifted"
        )
    elif not _is_hex64(prompt_hash):
        issues.append("[grading] grader_prompt_sha256 is not a sha256 hex digest")

    triggers = g.get("ambiguity_triggers")
    want_ids = {"grader_uncertain", "no_cited_span", "opined_outside_residue"}
    if not isinstance(triggers, list):
        issues.append("[grading] ambiguity_triggers missing or not a list")
    else:
        got_ids = {t.get("id") for t in triggers if isinstance(t, dict)}
        missing = want_ids - got_ids
        if missing:
            issues.append(f"[grading] ambiguity_triggers missing required id(s): {sorted(missing)}")
        for i, t in enumerate(triggers):
            if not isinstance(t, dict) or not isinstance(t.get("trigger"), str) or not t["trigger"]:
                issues.append(f"[grading] ambiguity_triggers[{i}] missing a non-empty trigger")

    batching = g.get("one_output_per_call")
    if not isinstance(batching, str) or not batching:
        issues.append("[grading] one_output_per_call missing or empty")
    elif "abort" not in batching.lower():
        issues.append(
            "[grading] one_output_per_call must state that prohibitive grading cost ABORTS the "
            "run in favour of a fresh preregistration -- batching is never a mid-run lever"
        )

    adj = g.get("adjudication")
    if not isinstance(adj, dict):
        issues.append("[grading] adjudication missing or not an object")
    else:
        for field in ("on_trigger", "on_disagreement"):
            if not isinstance(adj.get(field), str) or not adj[field]:
                issues.append(f"[grading] adjudication.{field} missing or empty")
        if "third" not in str(adj.get("on_disagreement", "")).lower():
            issues.append(
                "[grading] adjudication.on_disagreement must route to a THIRD blinded "
                "adjudicator whose verdict is final -- no averaging, no host tie-breaking"
            )

    mask = g.get("label_masking")
    if not isinstance(mask, dict):
        issues.append("[grading] label_masking missing or not an object")
    else:
        for field in ("protocol", "limitation"):
            if not isinstance(mask.get(field), str) or not mask[field]:
                issues.append(f"[grading] label_masking.{field} missing or empty")

    est = g.get("disagreement_estimate")
    if not isinstance(est, dict):
        issues.append("[grading] disagreement_estimate missing or not an object")
    else:
        if not isinstance(est.get("unit"), str) or not est["unit"]:
            issues.append("[grading] disagreement_estimate.unit missing or empty")
        for field, top in (
            ("seed", "grading_subsample_seed"),
            ("fraction", "grading_subsample_fraction"),
            ("size_pairs", "grading_subsample_size_pairs"),
        ):
            if est.get(field) != prereg.get(top):
                issues.append(
                    f"[grading] disagreement_estimate.{field} disagrees with prereg.{top} "
                    "-- the subsample design is recorded twice and they have drifted"
                )
    return issues


def check_dispatch_envelope(prereg: dict) -> list[str]:
    """The text a slot actually receives is template + envelope. Freezing only the template would
    leave the delivered prompt underspecified, so the envelope is cross-pinned the same way the
    grader prompt is: its own recorded sha256 must agree with the live-verified material_hashes
    entry, and the block cannot simply be dropped."""
    env = prereg.get("dispatch_envelope")
    if not isinstance(env, dict):
        return ["[dispatch_envelope] missing or not an object"]
    issues: list[str] = []
    path, want = env.get("file"), env.get("sha256")
    if not isinstance(path, str) or not (SKILL_ROOT / path).is_file():
        issues.append("[dispatch_envelope] file missing or does not resolve to a file")
    elif prereg.get("material_hashes", {}).get(path) != want:
        issues.append(
            "[dispatch_envelope] sha256 does not agree with the material_hashes entry for "
            f"{path} -- the envelope's freeze hash is recorded twice and they have drifted"
        )
    elif not _is_hex64(want):
        issues.append("[dispatch_envelope] sha256 is not a sha256 hex digest")
    for field in ("purpose", "symmetry", "materials_are_copies"):
        if not isinstance(env.get(field), str) or not env[field]:
            issues.append(f"[dispatch_envelope] {field} missing or empty")
    return issues


def check_execution_ladder(prereg: dict) -> list[str]:
    """The ladder may re-ORDER work; it may not quietly drop any of it.

    The load-bearing check is the partition: every one of the 11 study scenarios appears in
    exactly one rung, and the rung pair-counts sum to N_PAIRS. A ladder that silently omitted a
    scenario would read as "we ran the study" while having skipped a case -- the same
    no-silent-exclusion property `_reviewer_baseline_selftest.py` already enforces for its corpus.
    """
    ladder = prereg.get("execution_ladder")
    if not isinstance(ladder, dict):
        return ["[execution_ladder] missing or not an object"]
    issues: list[str] = []
    seen: list[str] = []
    total = 0
    for key, rung in sorted(ladder.items()):
        if not key.startswith("rung_") or not isinstance(rung, dict):
            continue
        scenarios = rung.get("scenarios") or ([rung["scenario"]] if rung.get("scenario") else [])
        if not scenarios:
            issues.append(f"[execution_ladder] {key} declares no scenario(s)")
            continue
        seen += scenarios
        pairs = rung.get("pairs")
        if not isinstance(pairs, int) or pairs != len(scenarios) * K:
            issues.append(
                f"[execution_ladder] {key}: pairs={pairs!r} does not equal "
                f"{len(scenarios)} scenario(s) x K={K}"
            )
        else:
            total += pairs
    dupes = sorted({s for s in seen if seen.count(s) > 1})
    if dupes:
        issues.append(f"[execution_ladder] scenario(s) appear in more than one rung: {dupes}")
    missing = sorted(set(STUDY_SCENARIOS) - set(seen))
    if missing:
        issues.append(
            f"[execution_ladder] scenario(s) in no rung at all -- silently excluded: {missing}"
        )
    unknown = sorted(set(seen) - set(STUDY_SCENARIOS))
    if unknown:
        issues.append(f"[execution_ladder] rung names a non-study scenario: {unknown}")
    if not missing and not dupes and total != N_PAIRS:
        issues.append(f"[execution_ladder] rung pairs sum to {total}, expected {N_PAIRS}")
    for field in ("continuation_rule", "order_within_rungs", "against_motivated_stopping"):
        if not isinstance(ladder.get(field), str) or not ladder[field]:
            issues.append(f"[execution_ladder] {field} missing or empty")
    return issues


def check_grading_tiering(prereg: dict) -> list[str]:
    """Spec-first tiering is only sound while its asymmetry and its exit are both on the record."""
    t = (prereg.get("grading") or {}).get("tiering")
    if not isinstance(t, dict):
        return []  # tiering is optional; a sonnet-only run is still a valid configuration
    issues: list[str] = []
    spec = t.get("spec_first")
    if not isinstance(spec, dict):
        issues.append("[grading.tiering] spec_first missing or not an object")
    else:
        path, want = spec.get("authoring_prompt_file"), spec.get("authoring_prompt_sha256")
        if not isinstance(path, str) or not (SKILL_ROOT / path).is_file():
            issues.append("[grading.tiering] spec_first.authoring_prompt_file does not resolve")
        elif prereg.get("material_hashes", {}).get(path) != want:
            issues.append(
                "[grading.tiering] spec_first.authoring_prompt_sha256 disagrees with its "
                "material_hashes entry -- recorded twice and drifted"
            )
        if not isinstance(spec.get("written_before_outputs_exist"), str):
            issues.append("[grading.tiering] spec_first.written_before_outputs_exist missing")
        if not isinstance(spec.get("absence_is_explicit"), str):
            issues.append("[grading.tiering] spec_first.absence_is_explicit missing")

    esc = t.get("escalate_to_sonnet_iff")
    if not isinstance(esc, list) or not esc:
        issues.append("[grading.tiering] escalate_to_sonnet_iff missing or empty")
    else:
        blob = " ".join(str(e).lower() for e in esc)
        if "adverse" not in blob:
            issues.append(
                "[grading.tiering] escalate_to_sonnet_iff must escalate the ADVERSE grade "
                "(missed for a flag, over_flagged for a restraint) -- that is the direction the "
                "cheaper tier is measured to err in, and Decision 4 is a veto"
            )
        if "subsample" not in blob:
            issues.append(
                "[grading.tiering] escalate_to_sonnet_iff must include the preregistered "
                "double-graded subsample -- it is the check that the cascade is still valid"
            )
    if "re-grad" not in str(t.get("invalidation_rule", "")).lower():
        issues.append(
            "[grading.tiering] invalidation_rule must specify RE-GRADING on sonnet when the "
            "cascade fails its check, so adopting it stays reversible at a bounded, known cost"
        )
    if not isinstance(t.get("arms_are_not_tiered"), str) or not t["arms_are_not_tiered"]:
        issues.append(
            "[grading.tiering] arms_are_not_tiered missing -- the commitment that the ARM model "
            "is not a cost lever has to be on the record next to the lever that is"
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


def validate_prereg(prereg: Any, *, frozen_at: str | None = None) -> list[str]:
    if not isinstance(prereg, dict):
        return ["[prereg] missing or not an object"]
    issues: list[str] = []
    issues += check_rule_provenance(prereg)
    issues += check_candidate_output_rule(prereg)
    issues += check_decision_rules(prereg)
    issues += check_arms(prereg)
    issues += check_grading(prereg)
    issues += check_dispatch_envelope(prereg)
    issues += check_execution_ladder(prereg)
    issues += check_grading_tiering(prereg)
    issues += check_material_hashes(prereg, frozen_at=frozen_at)
    issues += check_historical_file_hashes(prereg, frozen_at=frozen_at)
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
