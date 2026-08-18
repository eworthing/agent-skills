#!/usr/bin/env python3
"""Self-test: validate-paired-arm.py mechanizes the paired-arm record_state lifecycle it claims
to, nothing more.

Backlog item 16 house rule, followed exactly as scripts/_grade_structural_selftest.py does: this
selftest EXECS the shipped artifact (subprocess against scripts/validate-paired-arm.py) against
synthetic fixture records -- it never reimplements the validator's checking logic. RED-first:
every failure class below is asserted to actually fail (the specific exit code, the specific
message substring) before this file is considered green, not merely assumed.

Covers, against a real base fixture (the committed evals/paired_arm_replication.json) plus
purpose-built in_progress/graded/complete fixtures:
  - the real committed record validates (record_state=="preregistered", exit 0)
  - plumbing (exit 2): missing file, malformed JSON
  - prereg RED cases (exit 1): missing/unknown record_state, non-empty attempts/per_scenario at
    preregistered, tampered rule provenance, drifted material hash, drifted historical hash (D3),
    truncated frozen_order, wrong expected_baseline, wrong required_n_for_power, stale
    prereg_sha256
  - the per-attempt nullability table (exit 0/1) across all three trial shapes: exogenous-
    invalid, valid+ok, valid+malformed
  - grade_status handling at record_state=="graded" (exit 0/1)
  - record_state=="complete": exact 5-terminal-slots-per-(scenario,arm) count and the
    arm-conditional subset invariant (exit 0/1)
  - --check-git-provenance (documented Phase-1 stub, exit 0)
  - --previous regression detection: no baseline given (silent), a clean baseline (exit 0), and
    a regressed baseline -- an attempt un-graded or rewritten (exit 1)

Run: python3 scripts/_paired_arm_selftest.py   (exit 0 = pass, 1 = fail)
"""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

SKILL_ROOT = Path(__file__).resolve().parent.parent
VALIDATOR = SKILL_ROOT / "scripts" / "validate-paired-arm.py"
REAL_RECORD_PATH = SKILL_ROOT / "evals" / "paired_arm_replication.json"

FAILURES: list[str] = []


def _prereg_sha256(prereg: dict) -> str:
    """Mirror of the record's own freeze hash so fixtures stay internally consistent."""
    return hashlib.sha256(
        json.dumps(prereg, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _check(label: str, condition: bool, detail: str = "") -> None:
    mark = "PASS" if condition else "FAIL"
    print(f"  [{mark}] {label}" + (f"  ({detail})" if detail else ""))
    if not condition:
        FAILURES.append(label)


def _run(
    tmpdir: Path, name: str, record: dict, extra_args: list[str] | None = None
) -> tuple[int, str, str]:
    p = tmpdir / name
    p.write_text(json.dumps(record))
    proc = subprocess.run(
        [sys.executable, str(VALIDATOR), str(p), *(extra_args or [])],
        capture_output=True,
        text=True,
    )
    return proc.returncode, proc.stdout, proc.stderr


def load_real_record() -> dict:
    return json.loads(REAL_RECORD_PATH.read_text())


# ---- attempt fixture factories (mirror the nullability table in the plan / validator) ---------


def exogenous_attempt(
    scenario_id: str, arm: str, slot: int, *, reason: str = "infra_timeout"
) -> dict:
    return {
        "scenario_id": scenario_id,
        "arm": arm,
        "slot_index": slot,
        "attempt_index": 1,
        "trial_validity": {"status": "invalid", "reason": reason},
        "candidate_output_status": None,
        "raw_output_path": None,
        "verdict_json": None,
        "structural_report": None,
        "assertion_results": None,
        "grade_status": "not_applicable",
        "grade_status_reason": "exogenous_invalid",
        "mechanical_grade": None,
        "semantic_grade": None,
        "grader_id": None,
        "grader_model": None,
        "grader_prompt_sha256": None,
    }


def ok_attempt(scenario_id: str, arm: str, slot: int, *, graded: bool = False) -> dict:
    a: dict[str, Any] = {
        "scenario_id": scenario_id,
        "arm": arm,
        "slot_index": slot,
        "attempt_index": 1,
        "trial_validity": {"status": "valid", "reason": None},
        "candidate_output_status": "ok",
        "raw_output_path": f"evals/paired-arm-outputs/{scenario_id}/{arm}-{slot}.md",
        "verdict_json": {"verdict": "rejected", "blocks_95": True},
        "structural_report": {"assertions": [], "residue": []},
        "assertion_results": [
            {
                "assertion_index": 0,
                "assertion_text": "names the defect",
                "criterion_class": "outcome",
                "passed": True,
            },
        ],
        "grade_status": None,
        "grade_status_reason": None,
        "mechanical_grade": None,
        "semantic_grade": None,
        "grader_id": None,
        "grader_model": None,
        "grader_prompt_sha256": None,
    }
    if graded:
        a.update(
            grade_status="graded",
            mechanical_grade="caught",
            semantic_grade="caught",
            grader_id="grader-1",
            grader_model="claude-sonnet-5",
            grader_prompt_sha256="a" * 64,
        )
    return a


def malformed_attempt(scenario_id: str, arm: str, slot: int) -> dict:
    return {
        "scenario_id": scenario_id,
        "arm": arm,
        "slot_index": slot,
        "attempt_index": 1,
        "trial_validity": {"status": "valid", "reason": None},
        "candidate_output_status": "malformed",
        "raw_output_path": None,
        "verdict_json": None,
        "structural_report": None,
        "assertion_results": [
            {
                "assertion_index": 0,
                "assertion_text": "names the defect",
                "criterion_class": "outcome",
                "passed": False,
            },
        ],
        "grade_status": "not_applicable",
        "grade_status_reason": "exogenous_invalid",
        "mechanical_grade": None,
        "semantic_grade": None,
        "grader_id": None,
        "grader_model": None,
        "grader_prompt_sha256": None,
    }


def wrap(
    record_state: str,
    prereg: dict,
    prereg_sha256: str,
    attempts: list[dict],
    per_scenario: dict | None = None,
) -> dict:
    return {
        "schema_version": 1,
        "record_state": record_state,
        "prereg_sha256": prereg_sha256,
        "prereg": prereg,
        "captured_at": None,
        "per_scenario": per_scenario or {},
        "attempts": attempts,
    }


def main() -> int:
    real = load_real_record()
    prereg, prereg_sha256 = real["prereg"], real["prereg_sha256"]
    scenarios = list(prereg["study_scenarios"])
    arms = ("with_skill", "without_skill")

    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)

        # ==== GREEN: the real committed record ======================================
        print("== GREEN: real committed record (record_state=preregistered) ==")
        rc, out, err = _run(tmpdir, "green.json", real)
        _check("exit code 0", rc == 0, f"got {rc}: {err[:300]}")
        _check("stdout reports OK", "OK" in out, out.strip())

        # ==== plumbing (exit 2) ========================================================
        print("== RED: plumbing ==")
        proc = subprocess.run(
            [sys.executable, str(VALIDATOR), str(tmpdir / "nope.json")],
            capture_output=True,
            text=True,
        )
        _check("missing file -> exit 2", proc.returncode == 2, f"got {proc.returncode}")
        bad_json_path = tmpdir / "bad.json"
        bad_json_path.write_text("{not valid json")
        proc = subprocess.run(
            [sys.executable, str(VALIDATOR), str(bad_json_path)], capture_output=True, text=True
        )
        _check("malformed JSON -> exit 2", proc.returncode == 2, f"got {proc.returncode}")

        # ==== prereg / record_state RED cases (exit 1) =================================
        print("== RED: record_state ==")
        bad = copy.deepcopy(real)
        del bad["record_state"]
        rc, _, err = _run(tmpdir, "no_state.json", bad)
        _check("missing record_state -> exit 1", rc == 1, f"got {rc}")

        bad = copy.deepcopy(real)
        bad["record_state"] = "bogus"
        rc, _, err = _run(tmpdir, "bad_state.json", bad)
        _check("unknown record_state -> exit 1", rc == 1, f"got {rc}")

        print("== RED: preregistered attempts/per_scenario must be empty ==")
        bad = copy.deepcopy(real)
        bad["attempts"] = [{"scenario_id": "x"}]
        rc, _, err = _run(tmpdir, "attempts_nonempty.json", bad)
        _check("non-empty attempts at preregistered -> exit 1", rc == 1, f"got {rc}")
        _check("names the violation", "attempts must be empty" in err, err[:200])

        bad = copy.deepcopy(real)
        bad["per_scenario"] = {"x": {}}
        rc, _, err = _run(tmpdir, "per_scenario_nonempty.json", bad)
        _check("non-empty per_scenario at preregistered -> exit 1", rc == 1, f"got {rc}")

        print(
            "== RED: rule provenance (copied verbatim from principal_baseline_replication.json) =="
        )
        bad = copy.deepcopy(real)
        bad["prereg"]["mechanical_rule"] = "a paraphrase, not the verbatim rule"
        rc, _, err = _run(tmpdir, "rule_tampered.json", bad)
        _check("tampered mechanical_rule -> exit 1", rc == 1, f"got {rc}")
        _check("names rule_provenance", "rule_provenance" in err, err[:200])

        print("== RED: material hash drift ==")
        bad = copy.deepcopy(real)
        bad["prereg"]["material_hashes"]["references/method.md"] = "0" * 64
        rc, _, err = _run(tmpdir, "material_drift.json", bad)
        _check("drifted material hash -> exit 1", rc == 1, f"got {rc}")
        _check("names material_hashes", "material_hashes" in err, err[:200])

        print("== RED: historical file hash drift (D3) ==")
        bad = copy.deepcopy(real)
        bad["prereg"]["historical_file_hashes"]["evals/principal_baseline.json"] = "1" * 64
        rc, _, err = _run(tmpdir, "historical_drift.json", bad)
        _check("tampered historical hash -> exit 1", rc == 1, f"got {rc}")
        _check("names historical_file_hashes", "historical_file_hashes" in err, err[:200])

        print("== RED: frozen_order malformed ==")
        bad = copy.deepcopy(real)
        bad["prereg"]["frozen_order"] = bad["prereg"]["frozen_order"][:-1]
        rc, _, err = _run(tmpdir, "order_short.json", bad)
        _check("truncated frozen_order (54 not 55) -> exit 1", rc == 1, f"got {rc}")

        bad = copy.deepcopy(real)
        bad["prereg"]["frozen_order"][0]["arm_order"] = ["with_skill", "with_skill"]
        rc, _, err = _run(tmpdir, "order_bad_arms.json", bad)
        _check("non-permutation arm_order -> exit 1", rc == 1, f"got {rc}")

        print("== RED: expected_baseline validity (enum + restraint pin + rationale) ==")
        # A flag may be predicted EITHER way -- that is a hypothesis, not a derived default, and
        # the two core flags are deliberately predicted 'hold' against the principal flags' 'miss'.
        # The validator must NOT reject a differentiated prediction.
        ok = copy.deepcopy(real)
        ok["prereg"]["expected_baseline"]["principal-invariant-owner-flag"] = "hold"
        ok["prereg_sha256"] = _prereg_sha256(ok["prereg"])
        rc, _, err = _run(tmpdir, "eb_flag_hold.json", ok)
        _check("flag predicted 'hold' is ALLOWED -> exit 0", rc == 0, f"got {rc}: {err}")

        bad = copy.deepcopy(real)
        bad["prereg"]["expected_baseline"]["suppression-flag"] = "sometimes"
        bad["prereg_sha256"] = _prereg_sha256(bad["prereg"])
        rc, _, err = _run(tmpdir, "eb_enum.json", bad)
        _check("expected_baseline off-enum -> exit 1", rc == 1, f"got {rc}")

        bad = copy.deepcopy(real)
        bad["prereg"]["expected_baseline"]["suppression-restraint"] = "miss"
        bad["prereg_sha256"] = _prereg_sha256(bad["prereg"])
        rc, _, err = _run(tmpdir, "eb_restraint.json", bad)
        _check("restraint predicted 'miss' -> exit 1", rc == 1, f"got {rc}")

        bad = copy.deepcopy(real)
        del bad["prereg"]["expected_baseline_rationale"]
        bad["prereg_sha256"] = _prereg_sha256(bad["prereg"])
        rc, _, err = _run(tmpdir, "eb_no_rationale.json", bad)
        _check("missing expected_baseline_rationale -> exit 1", rc == 1, f"got {rc}")

        print("== RED: non_claim.required_n_for_power must match _noise_floor's own function ==")
        bad = copy.deepcopy(real)
        bad["prereg"]["non_claim"]["required_n_for_power"] = 100
        rc, _, err = _run(tmpdir, "n_wrong.json", bad)
        _check("hand-typed required_n_for_power mismatch -> exit 1", rc == 1, f"got {rc}")
        _check("names non_claim", "non_claim" in err, err[:200])

        print("== RED: grading protocol must stay frozen and internally consistent ==")
        bad = copy.deepcopy(real)
        del bad["prereg"]["grading"]
        bad["prereg_sha256"] = _prereg_sha256(bad["prereg"])
        rc, _, err = _run(tmpdir, "gr_missing.json", bad)
        _check("grading block absent -> exit 1", rc == 1, f"got {rc}")
        _check("names grading", "[grading]" in err, err[:200])

        # The prompt's freeze hash is recorded twice (grading.grader_prompt_sha256 and
        # material_hashes); the point of recording it twice is that they must agree.
        bad = copy.deepcopy(real)
        bad["prereg"]["grading"]["grader_prompt_sha256"] = "0" * 64
        bad["prereg_sha256"] = _prereg_sha256(bad["prereg"])
        rc, _, err = _run(tmpdir, "gr_hash_split.json", bad)
        _check(
            "grader_prompt_sha256 disagrees with material_hashes -> exit 1", rc == 1, f"got {rc}"
        )

        for trig in ("grader_uncertain", "no_cited_span", "opined_outside_residue"):
            bad = copy.deepcopy(real)
            bad["prereg"]["grading"]["ambiguity_triggers"] = [
                t for t in bad["prereg"]["grading"]["ambiguity_triggers"] if t["id"] != trig
            ]
            bad["prereg_sha256"] = _prereg_sha256(bad["prereg"])
            rc, _, err = _run(tmpdir, f"gr_trig_{trig}.json", bad)
            _check(f"ambiguity trigger {trig!r} dropped -> exit 1", rc == 1, f"got {rc}")

        # Batching is the one grading lever that must never be pulled mid-run: prohibitive cost
        # aborts in favour of a fresh preregistration. Softening the wording is the failure mode.
        bad = copy.deepcopy(real)
        bad["prereg"]["grading"]["one_output_per_call"] = (
            "One output per call; batch same-scenario outputs if grading cost is too high."
        )
        bad["prereg_sha256"] = _prereg_sha256(bad["prereg"])
        rc, _, err = _run(tmpdir, "gr_batch.json", bad)
        _check("no-batching rule softened to a mid-run lever -> exit 1", rc == 1, f"got {rc}")

        bad = copy.deepcopy(real)
        bad["prereg"]["grading"]["adjudication"]["on_disagreement"] = (
            "The host averages the two grades and picks the majority reading."
        )
        bad["prereg_sha256"] = _prereg_sha256(bad["prereg"])
        rc, _, err = _run(tmpdir, "gr_adj.json", bad)
        _check("host tie-breaking instead of a third adjudicator -> exit 1", rc == 1, f"got {rc}")

        bad = copy.deepcopy(real)
        bad["prereg"]["grading"]["disagreement_estimate"]["size_pairs"] = 55
        bad["prereg_sha256"] = _prereg_sha256(bad["prereg"])
        rc, _, err = _run(tmpdir, "gr_subsample.json", bad)
        _check("subsample resized away from prereg top-level -> exit 1", rc == 1, f"got {rc}")

        print("== RED: prereg_sha256 must track a live prereg edit ==")
        bad = copy.deepcopy(real)
        bad["prereg"]["declared_divergences"].append(
            {"id": "extra", "statement": "unregistered edit", "reason": "selftest injection"}
        )
        rc, _, err = _run(tmpdir, "hash_stale.json", bad)
        _check("prereg edited without updating prereg_sha256 -> exit 1", rc == 1, f"got {rc}")
        _check("names prereg_sha256", "prereg_sha256" in err, err[:200])

        # ==== in_progress: the per-attempt nullability table ===========================
        print("== in_progress: exogenous-invalid attempt ==")
        rec = wrap(
            "in_progress", prereg, prereg_sha256, [exogenous_attempt(scenarios[0], "with_skill", 1)]
        )
        rc, _, err = _run(tmpdir, "ip_exogenous_ok.json", rec)
        _check("valid exogenous attempt -> exit 0", rc == 0, err[:300])

        bad = copy.deepcopy(rec)
        bad["attempts"][0]["assertion_results"] = []  # must be null (not []) when exogenous-invalid
        rc, _, err = _run(tmpdir, "ip_exogenous_empty_list.json", bad)
        _check(
            "exogenous attempt with [] assertion_results (not null) -> exit 1", rc == 1, f"got {rc}"
        )

        bad = copy.deepcopy(rec)
        bad["attempts"][0]["trial_validity"]["reason"] = "not_a_canon_reason"
        rc, _, err = _run(tmpdir, "ip_bad_reason.json", bad)
        _check("non-canon invalid_reason -> exit 1", rc == 1, f"got {rc}")

        print("== in_progress: valid+ok attempt ==")
        rec_ok = wrap(
            "in_progress", prereg, prereg_sha256, [ok_attempt(scenarios[0], "with_skill", 1)]
        )
        rc, _, err = _run(tmpdir, "ip_ok.json", rec_ok)
        _check("valid ok attempt -> exit 0", rc == 0, err[:300])

        bad = copy.deepcopy(rec_ok)
        bad["attempts"][0]["verdict_json"] = None
        rc, _, err = _run(tmpdir, "ip_ok_missing_verdict.json", bad)
        _check("ok attempt missing verdict_json -> exit 1", rc == 1, f"got {rc}")

        print("== in_progress: valid+malformed attempt ==")
        rec_malformed = wrap(
            "in_progress", prereg, prereg_sha256, [malformed_attempt(scenarios[0], "with_skill", 1)]
        )
        rc, _, err = _run(tmpdir, "ip_malformed_ok.json", rec_malformed)
        _check("valid malformed attempt (all assertions failed) -> exit 0", rc == 0, err[:300])

        bad = copy.deepcopy(rec_malformed)
        bad["attempts"][0]["assertion_results"][0]["passed"] = True
        rc, _, err = _run(tmpdir, "ip_malformed_bad_pass.json", bad)
        _check("malformed attempt with a passing assertion -> exit 1", rc == 1, f"got {rc}")

        bad = copy.deepcopy(rec_malformed)
        bad["attempts"][0]["verdict_json"] = {"verdict": "approved"}
        rc, _, err = _run(tmpdir, "ip_malformed_has_verdict.json", bad)
        _check("malformed attempt with a non-null verdict_json -> exit 1", rc == 1, f"got {rc}")

        # ==== graded: grade_status handling ============================================
        print("== graded: grade_status required + shaped ==")
        rec_graded_na = wrap(
            "graded", prereg, prereg_sha256, [exogenous_attempt(scenarios[0], "with_skill", 1)]
        )
        rc, _, err = _run(tmpdir, "graded_na_ok.json", rec_graded_na)
        _check("graded state, not_applicable attempt -> exit 0", rc == 0, err[:300])

        bad = copy.deepcopy(rec_graded_na)
        bad["attempts"][0]["grade_status"] = None
        rc, _, err = _run(tmpdir, "graded_missing_status.json", bad)
        _check("graded state missing grade_status -> exit 1", rc == 1, f"got {rc}")

        rec_graded_ok = wrap(
            "graded",
            prereg,
            prereg_sha256,
            [ok_attempt(scenarios[0], "with_skill", 1, graded=True)],
        )
        rc, _, err = _run(tmpdir, "graded_full.json", rec_graded_ok)
        _check("fully graded ok attempt -> exit 0", rc == 0, err[:300])

        bad = copy.deepcopy(rec_graded_ok)
        bad["attempts"][0]["grader_prompt_sha256"] = "not-a-hex-digest"
        rc, _, err = _run(tmpdir, "graded_bad_hash.json", bad)
        _check("graded attempt with non-hex grader_prompt_sha256 -> exit 1", rc == 1, f"got {rc}")

        bad = copy.deepcopy(rec_graded_ok)
        bad["attempts"][0]["grade_status_reason"] = None  # graded status carries no reason field
        bad["attempts"][0]["grade_status"] = "not_applicable"
        rc, _, err = _run(tmpdir, "graded_bad_na_reason.json", bad)
        _check("not_applicable attempt with no closed reason -> exit 1", rc == 1, f"got {rc}")

        # ==== complete: exact 5-terminal-slots + subset invariant ======================
        print("== complete: 5 terminal slots per (scenario, arm) + subset invariant ==")
        all_attempts = [
            exogenous_attempt(sid, arm, slot)
            for sid in scenarios
            for arm in arms
            for slot in range(1, 6)
        ]
        per_scenario = {
            sid: {
                "with_skill": {
                    "mechanical": {"count": 0, "n": 5, "decision": "inconclusive"},
                    "semantic": {"count": 0, "n": 5, "decision": "inconclusive"},
                },
                "without_skill": {
                    "mechanical": {"count": 0, "n": 5, "decision": "inconclusive"},
                    "semantic": {"count": 0, "n": 5, "decision": "inconclusive"},
                },
            }
            for sid in scenarios
        }
        rec_complete = wrap("complete", prereg, prereg_sha256, all_attempts, per_scenario)
        rc, _, err = _run(tmpdir, "complete_ok.json", rec_complete)
        _check("110 terminal attempts, consistent per_scenario -> exit 0", rc == 0, err[:400])

        bad = copy.deepcopy(rec_complete)
        bad["attempts"].pop()  # one scenario/arm group now has only 4 terminal slots
        rc, _, err = _run(tmpdir, "complete_short.json", bad)
        _check("109 attempts (one group short) -> exit 1", rc == 1, f"got {rc}")

        bad = copy.deepcopy(rec_complete)
        flag_sid = next(sid for sid in scenarios if sid.endswith("-flag"))
        bad["per_scenario"][flag_sid]["with_skill"]["mechanical"]["count"] = 1
        bad["per_scenario"][flag_sid]["with_skill"]["semantic"]["count"] = 3
        rc, _, err = _run(tmpdir, "complete_subset_violation.json", bad)
        _check("subset invariant violated on with_skill flag -> exit 1", rc == 1, f"got {rc}")
        _check("names subset_invariant", "subset_invariant" in err, err[:200])

        # ==== --check-git-provenance stub ==============================================
        print("== --check-git-provenance: documented Phase-1 stub ==")
        p = tmpdir / "for_stub.json"
        p.write_text(json.dumps(real))
        proc = subprocess.run(
            [sys.executable, str(VALIDATOR), str(p), "--check-git-provenance"],
            capture_output=True,
            text=True,
        )
        _check("stub exits 0", proc.returncode == 0, f"got {proc.returncode}")
        _check(
            "stub says so explicitly (not a silent no-op)",
            "stub" in proc.stdout.lower(),
            proc.stdout[:200],
        )

        # ==== --previous regression detection ==========================================
        print("== --previous: regression detection only fires when given a baseline ==")
        prev_path = tmpdir / "previous.json"
        prev_path.write_text(json.dumps(rec_graded_ok))
        curr_path = tmpdir / "current_clean.json"
        curr_path.write_text(json.dumps(rec_graded_ok))
        proc = subprocess.run(
            [sys.executable, str(VALIDATOR), str(curr_path), "--previous", str(prev_path)],
            capture_output=True,
            text=True,
        )
        _check(
            "unchanged record against --previous -> exit 0", proc.returncode == 0, proc.stderr[:300]
        )

        regressed = copy.deepcopy(rec_graded_ok)
        regressed["attempts"][0]["grade_status"] = "not_applicable"
        regressed["attempts"][0]["grade_status_reason"] = "partial"
        regressed["attempts"][0]["mechanical_grade"] = None
        regressed["attempts"][0]["semantic_grade"] = None
        regressed["attempts"][0]["grader_id"] = None
        regressed["attempts"][0]["grader_model"] = None
        regressed["attempts"][0]["grader_prompt_sha256"] = None
        regressed_path = tmpdir / "current_regressed.json"
        regressed_path.write_text(json.dumps(regressed))
        proc = subprocess.run(
            [sys.executable, str(VALIDATOR), str(regressed_path), "--previous", str(prev_path)],
            capture_output=True,
            text=True,
        )
        _check(
            "un-graded attempt against --previous -> exit 1",
            proc.returncode == 1,
            f"got {proc.returncode}",
        )
        _check("names regression", "regression" in proc.stderr, proc.stderr[:300])

        proc = subprocess.run(
            [sys.executable, str(VALIDATOR), str(curr_path)], capture_output=True, text=True
        )
        _check(
            "no --previous given -> exit 0, no temporal claim attempted",
            proc.returncode == 0,
            proc.stderr[:300],
        )

    print()
    if FAILURES:
        print(f"_paired_arm_selftest: FAIL ({len(FAILURES)} check(s) failed)")
        for f in FAILURES:
            print(f"  - {f}")
        return 1
    print("_paired_arm_selftest: OK (all checks passed)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
