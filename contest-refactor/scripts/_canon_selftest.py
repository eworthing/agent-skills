#!/usr/bin/env python3
"""Selftest for scripts/_canon.py.

Two checks:

1. Golden snapshot: the real shipped canon/*.toml files still load to the
   exact, order-sensitive Canon object captured below (all 21 dataclass
   fields, including the 12-key `extra` dict and the insertion order of both
   MappingProxyType maps -- scorecard_dimension_labels and validation_gates).
   A legitimate canon edit updates GOLDEN_CANON_JSON in the same commit;
   that is the point of committing a snapshot instead of asserting shape only.

2. Sixteen `sys.exit(2)` sites, one case each. _canon.py has 16 distinct
   exit points as of this writing: 3 in `_load_toml` (file missing /
   malformed TOML / empty), 2 in `_require_list` (key missing / key not a
   list), and 11 inline in `load_canon` (canon dir missing, plus per-entry
   shape / duplicate-id / missing-scalar checks for scorecard-dimensions.toml,
   validation-gates.toml, trial-validity.toml, and noise-floor.toml). Each
   case copies canon/ into a fresh tempdir, breaks exactly one thing, runs
   load_canon() on the broken copy in a subprocess (so sys.exit(2) is
   observable), and asserts BOTH the exit code AND that the diagnostic
   message names the file that was broken -- an exit-code-only assertion
   would miss a right-code-wrong-file regression.

Run directly: python3 contest-refactor/scripts/_canon_selftest.py
"""

from __future__ import annotations

import dataclasses
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from types import MappingProxyType

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
REAL_CANON_DIR = SKILL_ROOT / "canon"

sys.path.insert(0, str(SCRIPT_DIR))
from _canon import load_canon

# ---------------------------------------------------------------------------
# Golden snapshot. Regenerate with:
#   python3 -c "
#   import sys, json, dataclasses
#   from types import MappingProxyType
#   sys.path.insert(0, 'contest-refactor/scripts')
#   from _canon import load_canon
#   def conv(v):
#       if isinstance(v, (MappingProxyType, dict)):
#           return {k: conv(x) for k, x in v.items()}
#       if isinstance(v, (tuple, list)):
#           return [conv(x) for x in v]
#       return v
#   c = load_canon()
#   d = {f.name: conv(getattr(c, f.name)) for f in dataclasses.fields(c)}
#   print(json.dumps(d, indent=2, ensure_ascii=False))
#   "
# ensure_ascii=False is required: escaping to \uXXXX here would get
# re-interpreted as a Python unicode escape by the triple-quoted string
# literal below, silently diverging from the live (also ensure_ascii=False)
# comparison value.
# ---------------------------------------------------------------------------
GOLDEN_CANON_JSON = """{
  "states": [
    "CONTINUE",
    "HALT_SUCCESS",
    "HALT_SUCCESS_candidate",
    "HALT_STAGNATION",
    "HALT_LOOP_CAP",
    "HALT_DRY_RUN",
    "HALT_EXHAUSTION"
  ],
  "halt_subtypes": [
    "no_progress",
    "oscillation",
    "user_decision",
    "no_backlog",
    "verification_blocked"
  ],
  "finding_statuses": [
    "open",
    "resolved",
    "fixed_by_user",
    "rejected_attempt",
    "unresolvable"
  ],
  "verdicts": [
    "approved",
    "rejected",
    "conditional"
  ],
  "severity_anchors": [
    "Cosmetic for contest",
    "Noticeable weakness",
    "Serious deduction",
    "Likely disqualifier"
  ],
  "scorecard_dimensions": [
    "architecture_quality",
    "state_management",
    "concurrency",
    "test_strategy",
    "credibility",
    "domain_modeling",
    "data_flow",
    "framework_idioms",
    "simplicity"
  ],
  "scorecard_dimension_labels": {
    "architecture_quality": "Architecture quality",
    "state_management": "State management and runtime ownership",
    "concurrency": "Concurrency and runtime safety",
    "test_strategy": "Test strategy and regression resistance",
    "credibility": "Overall implementation credibility",
    "domain_modeling": "Domain modeling",
    "data_flow": "Data flow and dependency design",
    "framework_idioms": "Framework / platform best practices",
    "simplicity": "Code simplicity and clarity"
  },
  "dependency_categories": [
    "in-process",
    "local-substitutable",
    "remote-owned",
    "true-external"
  ],
  "retirement_reasons": [
    "unresolvable",
    "user_decision",
    "outside_scope",
    "unverifiable",
    "superseded"
  ],
  "risk_boundary_kinds": [
    "isolation",
    "sendable",
    "conditional_compilation",
    "cross_file_visibility",
    "lock_ordering"
  ],
  "risk_evidence_verifications": [
    "compile_matrix",
    "focused_test",
    "thread_sanitizer",
    "sendable_conformance",
    "reasoning_only",
    "carried_forward"
  ],
  "match_kinds": [
    "all_of",
    "any_of",
    "no_drift_expected"
  ],
  "residual_blocker_kinds": [
    "structural_anchor_unmet",
    "ceremony",
    "framework_constrained",
    "cosmetic",
    "adr_carved_out"
  ],
  "exhaustion_kinds": [
    "context_pressure",
    "spend_limit",
    "unknown"
  ],
  "detection_modes": [
    "preventive_step_budget",
    "user_reported"
  ],
  "finding_families": [
    "simplification",
    "latent_premise",
    "dependency_upgrade",
    "data_migration",
    "configuration_change",
    "algorithm_fix",
    "test_addition",
    "security_fix",
    "concurrency_fix"
  ],
  "effort_levels": [
    "trivial",
    "small",
    "moderate",
    "large"
  ],
  "repair_revalidation_outcomes": [
    "INVARIANT_HOLDS",
    "INVARIANT_DRIFTED",
    "INVARIANT_REPLACED",
    "CONTRACT_REJECTED",
    "AUDIT_MOOT"
  ],
  "invalid_reasons": [
    "rate_limited",
    "auth_failure",
    "infra_timeout",
    "artifact_lost"
  ],
  "attestation_statuses": [
    "consistency_check",
    "unavailable"
  ],
  "validation_gates": {
    "G1": "Output structure",
    "G2": "JSON schema fidelity",
    "G3": "Evidence chain",
    "G4": "Score-proof requirement",
    "G5": "9.5 residual",
    "G6": "10 anchor justification",
    "G7": "No stale findings",
    "G8": "No score increase without structural proof",
    "G9": "Backlog purity + per-state presence",
    "G10": "Deepening Candidate purity",
    "G11": "Builder Notes purity",
    "G12": "Seam policy + friction proof",
    "G13": "Vocabulary discipline (architectural-label use only)",
    "G14": "Payload not instruction",
    "G15": "Implementation review present",
    "G16": "Registry consistency",
    "G17": "Indirect coverage citation",
    "G18": "REVIEW_HISTORY.json append",
    "G19": "Provider+model+skill_rev recorded",
    "G20": "Continuation discipline (post-commit, inline mode)",
    "G21": "HALT_SUCCESS criteria (pre-emit)",
    "G22": "Commit + archive divider format (pre-commit)",
    "G23": "Residual accounting at every terminal (pre-emit; mechanized by G37)",
    "G24": "Authority Map test-surface cross-check (pre-emit, when test_strategy >= 9)",
    "G25": "Continuation-bridge delegate audit (pre-emit, when concurrency >= 9)",
    "G26": "Anchor-to-source check (pre-emit on every loop after loop 1)",
    "G27": "Retry envelope (pre-emit when implementation_review present, schema_version >= 3)",
    "G28": "Checkpoint freshness + post-commit cleanup (during Step 3, schema_version >= 3)",
    "G29": "Schema version v3 invariants (pre-emit, schema_version >= 3)",
    "G30": "Retirement Precedence",
    "G31": "Fingerprint Integrity",
    "G32": "HALT_SUCCESS independent challenge (terminal, v4+; staged panel at v5+)",
    "G33": "risk_boundary_evidence shape (Meta-Rule-4 preservation evidence, schema_version >= 3)",
    "G34": "HALT-tail emit invariants (halt_subtype / unresolved_reason / halt_handoff presence by state, schema_version >= 3)",
    "G35": "halt_handoff object shape (text / expected_actions[] / match_kind ∈ canon + path↔kind coupling, schema_version >= 2)",
    "G36": "Required non-null state (presence; membership ∈ canon owned by the schema-enum check)",
    "G37": "Terminal residual accounting — no sub-9.5 dimension stranded (HALT_LOOP_CAP + HALT_STAGNATION, any subtype/backlog, schema_version >= 4)",
    "G38": "Premium model budget guard",
    "G39": "Backlog score_impact dimension attribution (machine-readable shape)",
    "G40": "Discovery persistence across loops (durable Step-0 handoff, schema_version >= 4)",
    "G41": "Cap loop executes its budgeted work (loop == loop_cap with a non-empty backlog, schema_version >= 4)",
    "G42": "Backlog item identity (stable_id present and derived from a Finding, schema_version >= 4)",
    "G43": "Convergence-pass coverage — a repeated clean must propose anew (loop >= 4, schema_version >= 4)",
    "G44": "Credential quarantine — persistence sinks scanned for hardcoded-secret shapes (plain + base64 + concat-split); fails closed, never reproduces the value",
    "G45": "Exhaustion halt record shape + detection↔kind honesty coupling (schema_version >= 4)",
    "G46": "General remediation fields — finding_family/effort/repair_revalidation shape + drift_notes coupling (schema_version >= 4)",
    "G47": "Execution-evidence linkage — ledger record resolves, command human-pinned, source fingerprint fresh per phase, exit 0, consistency_check on both sides (opt-in via loop_result.execution_evidence; item 14 Tier 1)",
    "G48": "run_id identity discipline — non-null run_id matches run-<UTC yyyy-mm-dd>-<uuid4().hex> and never changes across consecutive loops of one run (REPORT-ONLY: post-G48 epoch exists; Issue withheld until the instrumented-pass promotion condition is met — promotion bar in _artifact_run_identity.py)",
    "G49": "Persisted implementation-hotspot evidence — sanitized schema-v2 coverage/candidates required for hotspot-v2 rulesets",
    "G50": "Hotspot triage completeness — discovery_consumption.hotspot_triage key set must equal the scanner roster exactly (pre-emit, hotspot-triage epoch)"
  },
  "extra": {
    "fixture_rule_kinds": [
      "gate",
      "method-step",
      "canon-enum",
      "scorecard-dimension",
      "residual-rule"
    ],
    "premium_models": [
      "claude-fable-5"
    ],
    "fix_kinds": [
      "extract",
      "inline",
      "delete",
      "merge",
      "move",
      "gate"
    ],
    "noise_floor_alpha": 0.05,
    "noise_floor_min_effect": 0.1,
    "noise_floor_power_target": 0.8,
    "noise_floor_multiple_comparison_method": "bonferroni",
    "states_schema_version": 2,
    "transition_guards": [
      "loop-below-cap",
      "loop-equals-cap",
      "loop-exceeds-cap",
      "backlog-nonempty",
      "halt-tail-present",
      "candidate-criteria-met",
      "challenge-broke",
      "challenger-unavailable",
      "stop-ask-gate-blocked",
      "flag:dry-run",
      "exhaustion-detected"
    ],
    "transitions": {
      "CONTINUE": {
        "edges": [
          {
            "to": "CONTINUE",
            "guards": [
              "loop-below-cap",
              "backlog-nonempty"
            ],
            "gate": "G20"
          },
          {
            "to": "HALT_LOOP_CAP",
            "guards": [
              "loop-equals-cap"
            ],
            "gate": "G41"
          },
          {
            "to": "HALT_LOOP_CAP",
            "guards": [
              "loop-exceeds-cap"
            ],
            "gate": "G34"
          },
          {
            "to": "HALT_STAGNATION",
            "guards": [
              "halt-tail-present"
            ],
            "gate": "G34"
          },
          {
            "to": "HALT_SUCCESS_candidate",
            "guards": [
              "candidate-criteria-met"
            ],
            "gate": "G32"
          },
          {
            "to": "HALT_DRY_RUN",
            "guards": [
              "flag:dry-run"
            ],
            "gate": "G9"
          },
          {
            "to": "HALT_EXHAUSTION",
            "guards": [
              "exhaustion-detected"
            ],
            "gate": "G45"
          }
        ]
      },
      "HALT_SUCCESS_candidate": {
        "edges": [
          {
            "to": "CONTINUE",
            "guards": [
              "challenge-broke"
            ],
            "gate": "G32"
          },
          {
            "to": "HALT_STAGNATION",
            "guards": [
              "challenge-broke",
              "stop-ask-gate-blocked"
            ],
            "gate": "G32"
          },
          {
            "to": "HALT_STAGNATION",
            "guards": [
              "challenger-unavailable"
            ],
            "gate": "G32"
          }
        ]
      },
      "HALT_SUCCESS": {
        "edges": []
      },
      "HALT_STAGNATION": {
        "edges": []
      },
      "HALT_LOOP_CAP": {
        "edges": []
      },
      "HALT_DRY_RUN": {
        "edges": []
      },
      "HALT_EXHAUSTION": {
        "edges": []
      }
    },
    "trial_validity_max_invalid_rate_per_arm": 0.2,
    "trial_validity_max_between_arm_asymmetry": 0.1
  }
}
"""


def _serialize(value):
    if isinstance(value, (MappingProxyType, dict)):
        return {k: _serialize(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [_serialize(v) for v in value]
    return value


def _canon_to_json(canon) -> str:
    fields = [f.name for f in dataclasses.fields(canon)]
    data = {name: _serialize(getattr(canon, name)) for name in fields}
    return json.dumps(data, indent=2, sort_keys=False, ensure_ascii=False) + "\n"


def check_golden(failures: list[str]) -> None:
    print("golden snapshot: loading real shipped canon...")
    canon = load_canon(SKILL_ROOT)
    field_names = {f.name for f in dataclasses.fields(canon)}
    if len(field_names) != 22:
        failures.append(f"golden: expected 22 Canon dataclass fields, found {len(field_names)}")
        return
    if len(canon.extra) != 12:
        failures.append(f"golden: expected 12 keys in Canon.extra, found {len(canon.extra)}")
        return
    live = _canon_to_json(canon)
    if live != GOLDEN_CANON_JSON:
        failures.append(
            "golden: live load_canon() output no longer matches the committed golden "
            "(field values or map/dict insertion order changed). If this is a legitimate "
            "canon edit, regenerate GOLDEN_CANON_JSON per the comment above it."
        )
        return
    print("  OK: live Canon matches golden exactly (22 fields, extra has 12 keys, order-sensitive)")


# ---------------------------------------------------------------------------
# 16 sys.exit(2)-site cases.
# ---------------------------------------------------------------------------


def _replace_once(text: str, old: str, new: str) -> str:
    """Replace exactly one occurrence; raise if the mutation didn't land as intended."""
    count = text.count(old)
    if count != 1:
        raise AssertionError(f"expected exactly 1 occurrence of {old!r}, found {count}")
    return text.replace(old, new, 1)


def _run_load_canon(skill_root: Path) -> subprocess.CompletedProcess[str]:
    """Run load_canon(skill_root) in a subprocess so sys.exit(2) is observable."""
    code = (
        f"import sys; sys.path.insert(0, {str(SCRIPT_DIR)!r}); "
        f"from pathlib import Path; from _canon import load_canon; "
        f"load_canon(Path({str(skill_root)!r}))"
    )
    return subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, timeout=30, check=False
    )


def _copy_canon(tmp: Path) -> Path:
    dest = tmp / "canon"
    shutil.copytree(REAL_CANON_DIR, dest)
    return dest


# Sentinel: this case leaves skill_root with no canon/ subdirectory at all,
# rather than mutating a copied file.
CANON_DIR_MISSING = object()


def _run_case(failures: list[str], tmp_parent: str, site: str, broken_filename, mutate) -> None:
    """One exit-site case.

    site: human label (includes the code-location comment for the report).
    broken_filename: the file whose name must appear in the diagnostic, or
        CANON_DIR_MISSING when the missing thing is the directory itself.
    mutate: callable(canon_dir: Path) -> None, or None for CANON_DIR_MISSING.
    """
    with tempfile.TemporaryDirectory(dir=tmp_parent) as tmp:
        tmp_path = Path(tmp)
        if broken_filename is CANON_DIR_MISSING:
            skill_root = tmp_path  # deliberately: no canon/ subdir created
            needle = "canon"
        else:
            canon_dir = _copy_canon(tmp_path)
            mutate(canon_dir)
            skill_root = tmp_path
            needle = broken_filename
        result = _run_load_canon(skill_root)
        label = f"[{site}]"
        if result.returncode != 2:
            failures.append(
                f"{label} expected exit 2, got {result.returncode}. stderr={result.stderr!r}"
            )
            return
        if needle not in result.stderr:
            failures.append(
                f"{label} exit 2 but diagnostic didn't name {needle!r}. stderr={result.stderr!r}"
            )
            return
        print(f"  OK {label}: exit 2, diagnostic names {needle!r}")


# --- mutations, one per site -------------------------------------------------


def _mut_file_missing(canon_dir: Path) -> None:
    (canon_dir / "halt-subtypes.toml").unlink()


def _mut_attestation_missing(canon_dir: Path) -> None:
    (canon_dir / "attestation-statuses.toml").unlink()


def _mut_malformed(canon_dir: Path) -> None:
    (canon_dir / "halt-subtypes.toml").write_text('halt_subtypes = [\n  "no_progress"\n')


def _mut_empty(canon_dir: Path) -> None:
    (canon_dir / "halt-subtypes.toml").write_text("")


def _mut_require_list_missing_key(canon_dir: Path) -> None:
    p = canon_dir / "halt-subtypes.toml"
    p.write_text(_replace_once(p.read_text(), "halt_subtypes = [", "halt_subtypes_renamed = ["))


def _mut_require_list_not_list(canon_dir: Path) -> None:
    (canon_dir / "verdicts.toml").write_text('verdicts = "not-a-list"\n')


def _mut_scorecard_missing_key(canon_dir: Path) -> None:
    (canon_dir / "scorecard-dimensions.toml").write_text(
        'scorecard_dims_wrong = [{ id = "x", display_label = "X" }]\n'
    )


def _mut_scorecard_not_list(canon_dir: Path) -> None:
    (canon_dir / "scorecard-dimensions.toml").write_text('scorecard_dimensions = "not-a-list"\n')


def _mut_scorecard_entry_missing_field(canon_dir: Path) -> None:
    p = canon_dir / "scorecard-dimensions.toml"
    p.write_text(_replace_once(p.read_text(), 'display_label = "Architecture quality"\n', ""))


def _mut_scorecard_duplicate_id(canon_dir: Path) -> None:
    p = canon_dir / "scorecard-dimensions.toml"
    p.write_text(
        _replace_once(p.read_text(), 'id = "state_management"', 'id = "architecture_quality"')
    )


def _mut_trial_validity_missing_threshold(canon_dir: Path) -> None:
    p = canon_dir / "trial-validity.toml"
    p.write_text(_replace_once(p.read_text(), "max_invalid_rate_per_arm = 0.20\n", ""))


def _mut_gates_missing_key(canon_dir: Path) -> None:
    (canon_dir / "validation-gates.toml").write_text(
        'validation_gates_wrong = [{ id = "G1", title = "X" }]\n'
    )


def _mut_gates_not_list(canon_dir: Path) -> None:
    (canon_dir / "validation-gates.toml").write_text('validation_gates = "not-a-list"\n')


def _mut_gates_entry_missing_field(canon_dir: Path) -> None:
    p = canon_dir / "validation-gates.toml"
    p.write_text(_replace_once(p.read_text(), 'title = "Output structure"\n', ""))


def _mut_gates_duplicate_id(canon_dir: Path) -> None:
    p = canon_dir / "validation-gates.toml"
    p.write_text(_replace_once(p.read_text(), 'id = "G2"', 'id = "G1"'))


def _mut_noise_floor_missing_key(canon_dir: Path) -> None:
    p = canon_dir / "noise-floor.toml"
    p.write_text(_replace_once(p.read_text(), "alpha = 0.05\n", ""))


CASES = [
    # (site label incl. code location, broken_filename, mutate)
    ("1/16 _load_toml: file missing (_canon.py ~L52)", "halt-subtypes.toml", _mut_file_missing),
    (
        "2/16 _load_toml: malformed TOML (_canon.py ~L58)",
        "halt-subtypes.toml",
        _mut_malformed,
    ),
    ("3/16 _load_toml: file empty (_canon.py ~L61)", "halt-subtypes.toml", _mut_empty),
    (
        "4/16 _require_list: missing top-level key (_canon.py ~L68)",
        "halt-subtypes.toml",
        _mut_require_list_missing_key,
    ),
    (
        "5/16 _require_list: key not a list (_canon.py ~L72)",
        "verdicts.toml",
        _mut_require_list_not_list,
    ),
    (
        "6/16 load_canon: canon directory missing (_canon.py ~L86)",
        CANON_DIR_MISSING,
        None,
    ),
    (
        "7/16 load_canon: scorecard missing 'scorecard_dimensions' key (_canon.py ~L112)",
        "scorecard-dimensions.toml",
        _mut_scorecard_missing_key,
    ),
    (
        "8/16 load_canon: scorecard_dimensions not a list (_canon.py ~L118)",
        "scorecard-dimensions.toml",
        _mut_scorecard_not_list,
    ),
    (
        "9/16 load_canon: scorecard entry missing display_label (_canon.py ~L126)",
        "scorecard-dimensions.toml",
        _mut_scorecard_entry_missing_field,
    ),
    (
        "10/16 load_canon: duplicate scorecard id (_canon.py ~L132)",
        "scorecard-dimensions.toml",
        _mut_scorecard_duplicate_id,
    ),
    (
        "11/16 load_canon: trial-validity missing threshold scalar (_canon.py ~L192)",
        "trial-validity.toml",
        _mut_trial_validity_missing_threshold,
    ),
    (
        "12/16 load_canon: gates missing 'validation_gates' key (_canon.py ~L203)",
        "validation-gates.toml",
        _mut_gates_missing_key,
    ),
    (
        "13/16 load_canon: validation_gates not a list (_canon.py ~L209)",
        "validation-gates.toml",
        _mut_gates_not_list,
    ),
    (
        "14/16 load_canon: gate entry missing title (_canon.py ~L216)",
        "validation-gates.toml",
        _mut_gates_entry_missing_field,
    ),
    (
        "15/16 load_canon: duplicate gate id (_canon.py ~L222)",
        "validation-gates.toml",
        _mut_gates_duplicate_id,
    ),
    (
        "16/16 load_canon: noise-floor missing scalar key (_canon.py ~L259)",
        "noise-floor.toml",
        _mut_noise_floor_missing_key,
    ),
    (
        "17/17 _list_from: attestation-statuses.toml missing (item-14 wiring guard)",
        "attestation-statuses.toml",
        _mut_attestation_missing,
    ),
]


def check_all_sites(failures: list[str]) -> None:
    print(f"exercising {len(CASES)} sys.exit(2) sites...")
    with tempfile.TemporaryDirectory() as tmp_parent:
        for site, broken_filename, mutate in CASES:
            _run_case(failures, tmp_parent, site, broken_filename, mutate)


def main() -> int:
    failures: list[str] = []
    check_golden(failures)
    check_all_sites(failures)
    if failures:
        print(f"\nFAILED: {len(failures)} check(s):")
        for f in failures:
            print(f"  - {f}")
        return 1
    print(f"\nPASSED: golden snapshot OK, all {len(CASES)} exit-2 sites individually exercised.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
