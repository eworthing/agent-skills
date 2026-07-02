# Output Format — JSON schemas (per-loop)

JSON mirror schema for the per-loop artifact `CURRENT_REVIEW.json`, plus its embedded `halt_handoff` and `re_validation_context` objects, the Per-Loop Progress Line Format, the canonical Deepening Keywords list, and the 27 schema validation rules enforced by the validation hard gates. (Schema-version migration notes — the v2→v3 default-fill table — moved to [output-format-migrations.md](output-format-migrations.md), loaded only on the resume path.)

Persistent cross-loop state schemas (`LOOP_STATE.json`, `findings_registry.json`, `REVIEW_HISTORY.json`, plus the Fuzzy-match rules) live in [output-format-state-schemas.md](output-format-state-schemas.md). The human-readable markdown spec is in [output-format-markdown.md](output-format-markdown.md). Artifact index is [output-format.md](output-format.md).

## Contents

- [Schema version 4 changelog](#schema-version-4-changelog)
- [Schema version 3 changelog](output-format-migrations.md#schema-version-3-changelog) (moved — resume path)
- [CURRENT_REVIEW.json Schema](#current_reviewjson-schema)
- [Per-Loop Progress Line Format (schema_version >= 3)](#per-loop-progress-line-format-schema_version--3)
- [halt_handoff object (PR 4, schema_version >= 2)](#halt_handoff-object-pr-4-schema_version--2)
- [re_validation_context object (PR 4, schema_version >= 2)](#re_validation_context-object-pr-4-schema_version--2)
- [Deepening Keywords (canonical)](#deepening-keywords-canonical)
- [Schema validation rules (enforced by the validation hard gates)](#schema-validation-rules-enforced-by-the-validation-hard-gates)

Persistent state file schemas (`LOOP_STATE.json`, `findings_registry.json`, `REVIEW_HISTORY.json`, Fuzzy-match rules) → see [output-format-state-schemas.md](output-format-state-schemas.md).

## Schema version 4 changelog

`CURRENT_REVIEW.json` and `REVIEW_HISTORY.json` move to `schema_version: 4`, which adds the candidate/challenge fields below. G32 in [validation.md](validation.md) enforces the terminal-challenge invariant at `schema_version >= 4`; a loop running at v4 simply writes v4. (Solo beta — no prior-version artifacts are in play, so no migration path or default-fill is defined.)

### v4 changes

- New state `HALT_SUCCESS_candidate` (non-terminal): the loop emits this instead of terminal `HALT_SUCCESS`; the main agent promotes it to `HALT_SUCCESS` after an independent challenge passes.
- New halt_subtype value `verification_blocked` (applies when `state == "HALT_STAGNATION"` and challenge infrastructure is unavailable).
- New top-level field `run_id` (string, v4+): required non-null when `state ∈ {HALT_SUCCESS_candidate, HALT_SUCCESS}`. Identifies the loop run that produced the candidate.
- New top-level field `source_rev` (string sha, v4+): required non-null when `state ∈ {HALT_SUCCESS_candidate, HALT_SUCCESS}`. HEAD sha of the analyzed source tree at emit time.
- New top-level field `candidate_fingerprint` (string, v4+): required non-null when `state ∈ {HALT_SUCCESS_candidate, HALT_SUCCESS}`. Canonical hash of the architecture-relevant payload (scorecard scores + dispositions, findings evidence, residual rationales, lens, source-tree identity), EXCLUDING volatile metadata (commit sha, run_id, loop counter, timestamps, schema_version, state). This is the oscillation equivalence key — two candidates with identical architecture-relevant payload share a fingerprint even when commit/run/loop/timestamp metadata differs.
- New top-level field `halt_success_challenge` (object|null, v4+): required non-null **only** when `state == "HALT_SUCCESS"` (terminal); must be `null` for `HALT_SUCCESS_candidate` and all other states. See schema below.
- New gate G32 (HALT_SUCCESS independent challenge); new quality-pass behaviour on candidate state.

### halt_success_challenge object schema (v4+, required when state == "HALT_SUCCESS")

```jsonc
"halt_success_challenge": {
  "challenger_model": "claude-opus-4-8",  // non-empty string; model that ran the challenge
  "outcome": "held",                       // enum: "held" | "broke". "broke" with state=="HALT_SUCCESS" is ILLEGAL — downgrade first.
  "binding": {
    "candidate_commit_sha": "abc1234",    // non-empty string; commit sha of the candidate artifact being challenged
    "run_id": "run-2026-06-21-001",       // must equal top-level run_id
    "source_rev": "def5678"               // must equal top-level source_rev
  },
  "attempts": [                            // non-empty list; each attempt the challenger made
    {
      "arm": "new_finding",                // enum: "new_finding" | "residual_refutation"
      "target": "architecture_quality",   // finding title or scorecard dimension targeted
      "what_tried": "...",                 // what the challenger attempted
      "why_failed": "..."                  // why the challenge arm failed to break the candidate
    }
  ],
  "reason": "..."                          // one-sentence summary of why the candidate held
}
```

`outcome == "broke"` with `state == "HALT_SUCCESS"` is illegal: the main agent must downgrade to `HALT_SUCCESS_candidate` or `CONTINUE` before re-emitting. The challenger's job is to attempt to break the claim; if it succeeds, the candidate is demoted, not promoted.

## Schema version 3 changelog

Moved to [output-format-migrations.md § Schema version 3 changelog](output-format-migrations.md#schema-version-3-changelog) — the v2→v3 default-fill table is a resume / old-artifact concern (Step -1), not part of the per-loop investigation payload.

## CURRENT_REVIEW.json Schema

The JSON file is a faithful mirror of the Markdown contract in [output-format-markdown.md](output-format-markdown.md). Every Markdown field has a JSON field; enums match the Markdown allowed values; arrays match the OutputBudget caps; proofs are required where the Markdown spec requires them.

Findings produced here must follow The Evidence Chain from `method.md`: Claim → Source → Consequence → Remedy. The JSON-field mapping is documented inline in the findings schema below.

### Required-field schema (machine-readable)

```jsonc
{
  // Schema-version notation: (v2+) = required at schema_version >= 2; (v3+) = required at schema_version >= 3.
  // (PR 4, v2+) = first introduced in PR 4 at schema_version >= 2.

  // Loop bookkeeping (required)
  "schema_version": 4,                          // int, required. Pre-2026-05-09 = 1; PR 1-5 = 2; v3 revision = 3; v4 revision = 4.
  "loop": 3,                                    // int, 1-based
  "loop_cap": 10,                               // int
  "state": "CONTINUE",                          // enum: CONTINUE | HALT_SUCCESS | HALT_SUCCESS_candidate | HALT_STAGNATION | HALT_LOOP_CAP | HALT_DRY_RUN (HALT_DRY_RUN v3+; HALT_SUCCESS_candidate v4+ only)
  "halt_subtype": null,                         // enum (required when state == HALT_STAGNATION; null otherwise): no_progress | oscillation | user_decision | no_backlog | verification_blocked. Presence enforced by G34.
  "halt_handoff_text": null,                    // legacy v1 field. v2+ uses `halt_handoff` object below instead.
  "halt_handoff": null,                         // (PR 4, v2+) required when state ∈ {HALT_SUCCESS, HALT_STAGNATION, HALT_LOOP_CAP, HALT_DRY_RUN(v3+)}; null on CONTINUE and HALT_SUCCESS_candidate. Presence enforced by G34. Object schema below.
  "re_validated_at_sha": null,                  // string sha; populated by Resume Detection when drift was checked and same halt persists.
  "re_validation_context": null,                // (PR 4, v2+) required when re_validated_at_sha non-null. Object schema below.
  "dry_run": false,                             // (v3+) boolean. Audit trail of last invocation flag. NOT read on re-invocation (CLI flag is authoritative). true ⇒ state == "HALT_DRY_RUN".
  "strictness": "standard",                     // optional enum: standard | aggressive (default standard, absent ⇒ standard). Records the --strictness flag. ADVISORY ONLY — never consulted by any score/threshold gate (G5/G21/HALT_SUCCESS read score + residual_disposition only; _strictness_isolation_selftest.py proves preset-independence). Under "aggressive" the Critic requires an accepted inline residual to cite source-backed evidence (file:line / framework constraint / ADR ref) rather than bare prose, else queues it — raising the evidence bar, not the 9.5 threshold, and not forcing a residual_expires date. See architecture-rubric.md § 9.5+ Threshold "Strictness presets".
  "loop_metrics": null,                         // optional object | null (absent ⇒ no metric trend this loop). Hard metrics captured in Step 0 when the tools exist: { "coverage_pct"?: number, "lint_count"?: number, "complexity"?: number }, all optional. ADVISORY ONLY — never consulted by any score/threshold gate (_metric_isolation_selftest.py proves gate-independence). Persisted so scripts/audit_metric_trend.py can flag a metric that moved the wrong way between loops as *evidence* for the Critic (Meta-Rule 1: metrics support judgment, never decide it). Never a score or gate.

  // v4+ challenge fields (required non-null when state ∈ {HALT_SUCCESS_candidate, HALT_SUCCESS})
  "run_id": null,                               // (v4+) string | null. Required non-null when state ∈ {HALT_SUCCESS_candidate, HALT_SUCCESS}. Identifies the loop run that produced the candidate.
  "source_rev": null,                           // (v4+) string sha | null. Required non-null when state ∈ {HALT_SUCCESS_candidate, HALT_SUCCESS}. HEAD sha of analyzed source tree at emit time.
  "candidate_fingerprint": null,                // (v4+) string | null. Required non-null when state ∈ {HALT_SUCCESS_candidate, HALT_SUCCESS}. Canonical hash of architecture-relevant payload excluding volatile metadata. Oscillation equivalence key.
  "halt_success_challenge": null,               // (v4+) object | null. Required non-null ONLY when state == "HALT_SUCCESS" (terminal). Null for HALT_SUCCESS_candidate and all other states. Schema: see § Schema version 4 changelog.

  // Provider/model state (v2+; required on every loop, not first-loop-only)
  "provider": "claude_code",                    // enum: claude_code | codex | opencode | unknown. Detected per references/provider-adapters.md § Detection.
  "loop_model": "claude-sonnet-4-6",            // string, full canonical model ID. Default per provider-adapters.md loop-spawn table.
  "loop_model_source": "default",               // enum: default | env_override | user_flag
  "reviewer_model": "claude-sonnet-4-6",        // string, full canonical model ID. Default per provider-adapters.md reviewer-spawn table.
  "reviewer_model_source": "default",           // enum: default | env_override | user_flag
  "spawn_isolation": "subagent",                // enum: subagent | inline. "inline" only when provider == "unknown".
  "premium_dry_run": null,                      // optional null|object. Non-null only when --premium-dry-run-model or CONTEST_REFACTOR_PREMIUM_DRY_RUN_MODEL forced dry_run. Shape: {"model": "...", "model_source": "user_flag|env_override", "activated_dry_run": true}.
  "premium_loop_override": false,               // optional bool, absent => false. True only when --allow-premium-loop authorized non-dry-run execution of a premium loop model; false on every dry-run invocation.

  // Findings registry (v2+)
  "findings_registry_path": "./findings_registry.json", // string. Path to external registry. Never embedded in CURRENT_REVIEW.json.

  // Discovery (required first loop only; null on later loops)
  "discovery": {
    "source_roots": ["BenchHypeKit/Sources/"],
    "test_command": "cd BenchHypeKit && swift test",
    "build_command": "./build_install_launch.sh ios --skip-preflight",
    "lens": "Apple",                            // enum: Apple | Generic
    "adrs": ["ADR-0001: reject transport parity tests"],
    "domain_terms": ["AppState", "InstanceID", "TileCueResolver"],
    "test_scope": "full",                       // (v3+) enum: full | incremental. "incremental" iff --test-filter <pattern> set.
    "test_filter": null,                        // (v3+) null | string. non-null iff test_scope == "incremental".
    "working_tree_dirty_paths": []              // (v3+) array of paths dirty at Step 0 (`git status --porcelain`). Empty = clean. Overlap with Step 2 plan's touch list → loop aborts pre-Step-3.
  },

  // Verdict (required)
  "verdict": "Promising, but architecturally immature",
  // enum, exact strings:
  //   "Strong contender"
  //   "Good app, but not top-tier yet"
  //   "Promising, but architecturally immature"
  //   "Functionally solid, but structurally compromised"
  //   "Not contest ready"
  "verdict_explanation": "2-3 sentences",

  // Scorecard (required) — all 9 dimensions present every loop
  "scorecard": {
    "architecture_quality":      {"score": 8.5, "delta": "UP",   "proof": "BoardsScreen.swift:142", "residual_blocking_10": null, "residual_disposition": null, "residual_rationale_or_backlog_ref": null, "unverifiable_due_to_build_failure": false},
    "state_management":          {"score": 9.5, "delta": "SAME", "proof": "AppState.swift",         "residual_blocking_10": "EditingState.cueSaveWorkflow parallel field", "residual_disposition": "queued", "residual_rationale_or_backlog_ref": "F2", "unverifiable_due_to_build_failure": false},
    "domain_modeling":           {"score": 8.0, "delta": "UP",   "proof": "Cue.swift:55",           "residual_blocking_10": null, "residual_disposition": null, "residual_rationale_or_backlog_ref": null, "unverifiable_due_to_build_failure": false},
    "data_flow":                 {"score": 8.5, "delta": "SAME", "proof": "Effects/EffectPump.swift:42", "residual_blocking_10": null, "residual_disposition": null, "residual_rationale_or_backlog_ref": null, "unverifiable_due_to_build_failure": false},
    "framework_idioms":          {"score": 9.0, "delta": "UP",   "proof": "BoardsScreen.swift:33",  "residual_blocking_10": null, "residual_disposition": null, "residual_rationale_or_backlog_ref": null, "unverifiable_due_to_build_failure": false},
    "concurrency":               {"score": 9.5, "delta": "UP",   "proof": "SpotifyAdapter.swift:88", "residual_blocking_10": "AudioSessionConfigurator.Lease.deinit unbound Task carve-out", "residual_disposition": "accepted", "residual_rationale_or_backlog_ref": "Documented carve-out: Swift deinit cannot await; idempotent main-actor hop, microsecond-bounded; covered by AudioSessionConfiguratorLeaseDeinitTests.", "unverifiable_due_to_build_failure": false},
    "simplicity":                {"score": 8.5, "delta": "DOWN", "proof": "Reducer/AppReducer+Workflow.swift:771", "residual_blocking_10": null, "residual_disposition": null, "residual_rationale_or_backlog_ref": null, "unverifiable_due_to_build_failure": false},
    "test_strategy":             {"score": 8.0, "delta": "SAME", "proof": "BulkAddSoundReducerTests.swift", "residual_blocking_10": null, "residual_disposition": null, "residual_rationale_or_backlog_ref": null, "unverifiable_due_to_build_failure": false},
    "credibility":               {"score": 8.5, "delta": "UP",   "proof": "AppEngine.swift:46",     "residual_blocking_10": null, "residual_disposition": null, "residual_rationale_or_backlog_ref": null, "unverifiable_due_to_build_failure": false}
  },
  // Per-dimension rules:
  //   score: number, 1-10 (1 is the schema floor signaling broken/unverifiable; decimals allowed at 0.5 granularity above 1)
  //   delta: enum: UP | DOWN | SAME (vs. previous loop; "SAME" on loop 1)
  //   proof: required non-empty string when score > 7 OR when unverifiable_due_to_build_failure is true (proof = the carry-forward note)
  //   residual_blocking_10: required non-empty string when score >= 9.5 AND score < 10; null when score == 10 OR score < 9.5
  //   residual_disposition: required when residual_blocking_10 non-null. Enum: "accepted" | "queued"
  //                         "accepted" = documented inline; compatible with HALT_SUCCESS
  //                         "queued"   = added to Improvement Backlog; blocks HALT_SUCCESS (state stays CONTINUE)
  //   residual_rationale_or_backlog_ref: required when residual_blocking_10 non-null. Either a rationale string ("accepted") or a backlog Finding ID like "F2" ("queued").
  //   residual_blocker_kind: OPTIONAL enum (canon/residual-blocker-kinds.toml): structural_anchor_unmet | ceremony | framework_constrained | cosmetic | adr_carved_out. Names WHY a dimension stays below 9.5. At a converged empty-backlog terminal (HALT_STAGNATION/no_backlog or HALT_LOOP_CAP with empty backlog) G37 requires every sub-9.5 dimension to carry "structural_anchor_unmet"; the promotion-trigger kinds (ceremony/framework_constrained/cosmetic/adr_carved_out) mean the 9-anchor is met, so the dimension MUST be promoted to 9.5 with residual_disposition "accepted" (Residual Accounting Pass). Null/absent outside those terminals.
  //   residual_expires: OPTIONAL ISO-8601 date on an inline "accepted" residual. Absent = the residual stands on residual_rationale_or_backlog_ref alone (the correct shape for a permanent framework carve-out that will never change — e.g. "Swift deinit cannot await"; HALT_SUCCESS does not require a date). When present and its date has passed, it blocks HALT_SUCCESS (the Critic must reconsider the residual as active). This inline field is independent of the `.contest-refactor.toml` [[accepted_residuals]] tier, where `expires` is MANDATORY (broad path-pattern suppressions that should lapse) — see project-config.md + architecture-rubric.md § 9.5+ Threshold.
  //   unverifiable_due_to_build_failure: bool. True only on Step 1 step 2 build-failure path; bypasses G4 and G8.
  //   Hard rule: scores cannot increase loop-over-loop without proof citing structural change (G8). Suspended when unverifiable_due_to_build_failure is true.

  // Authority Map (required first loop AND when an authority finding is Priority 1; else empty array)
  "authority_map": [
    {
      "concern": "Tab selection",                                          // required
      "owner": "NavigationStore",                                          // required
      "allowed_writers": ["RootView (TabView binding)", "LoginViewModel.handleSuccess"],  // required, >=1
      "readers": ["RootView", "TabBarBadge"],                              // required, may be empty
      "persistence_seam": null,                                            // required field; null = not persisted
      "async_mutation_entry_points": ["LoginViewModel.handleSuccess"],     // required, may be empty
      "verdict": "Split and ambiguous"                                     // enum: Single and clear | Split and ambiguous
    }
  ],

  // Strengths (required, may be empty)
  "strengths": ["Reducer pure, effect pump deterministic — AppEngine.swift:46-58"],

  // Findings (required; 3-5 default, 6-7 max; empty allowed when state == HALT_SUCCESS or HALT_STAGNATION/no_backlog)
  // Findings produced here must follow The Evidence Chain from `method.md`: Claim → Source → Consequence → Remedy.
  // JSON-field-to-Evidence-Chain mapping:
  //   Claim       = `title` + `why_it_matters` + `what_is_wrong` (all three non-empty)
  //   Source      = `evidence[]` (non-empty)
  //   Consequence = `why_weakens_submission`
  //   Remedy      = `minimal_correction_path`
  "findings": [
    {
      "loop_local_id": "F1",                                               // required, "F<n>", fresh per loop, ordered by Priority. Replaces legacy "id" at v2+.
      "stable_id": "F-007",                                                // (v2+) required on every emitted finding. Format "F-NNN", looked up from findings_registry.json per Method Step 1.5.
      "id": "F1",                                                          // legacy alias of loop_local_id; emitted for v1 backward-compat. New writes can omit.
      "title": "Navigation has two writers",                               // required (Claim)
      "why_it_matters": "...",                                             // required (Claim)
      "what_is_wrong": "...",                                               // required (Claim)
      "evidence": ["App/RootView.swift:18", "Core/NavigationStore.swift:12"],  // required, >=1 entry (Source)
      "test_failed": "Deletion test",                                      // enum: Deletion test | Two-adapter rule | Shallow module | Interface-as-test-surface | Replace-don't-layer | n/a
      "dependency_category": "in-process",                                 // required when finding is Coupling & Leakage; else null. enum: in-process | local-substitutable | remote-owned | true-external
      "leverage_impact": "...",                                            // required (one sentence)
      "locality_impact": "...",                                            // required (one sentence)
      "metric_signal": "none",                                             // required string; "none" allowed
      "why_weakens_submission": "...",                                     // required (Consequence)
      "severity": "Serious deduction",                                     // enum: Cosmetic for contest | Noticeable weakness | Serious deduction | Likely disqualifier
      "adr_conflicts": [],                                                 // required array; empty allowed; entries are ADR IDs
      "adr_reopen_justification": null,                                    // required when adr_conflicts non-empty; else null
      "minimal_correction_path": "...",                                    // required (Remedy)
      "blast_radius": {                                                    // required
        "change": ["Core/NavigationStore.swift", "App/RootView.swift", "Tests/NavigationStoreTests.swift"],
        "avoid": ["Features/Auth/LoginViewModel.swift"]
      }
    }
  ],

  // Simplification Check (required)
  "simplification_check": {
    "structurally_necessary": "Collapsing navigation writers — passes Deletion test",  // required string
    "new_seam_justified": false,                                                       // required bool
    "new_seam_adapters": [],                                                           // required when new_seam_justified true; lists the >=2 Adapters
    "helpful_simplification": "...",                                                    // optional
    "should_not_be_done": "Adding Coordinator protocol — costume layer",               // required string ("none" allowed)
    "tests_after_fix": "Delete RootView selectedTab tests; assert via NavigationStore" // required string
  },

  // Improvement Backlog (presence rules per system_flag — see SKILL.md table)
  // CONTINUE: non-empty (1-3 items)
  // HALT_SUCCESS: empty
  // HALT_STAGNATION: optional; if present, unresolved_reason must be set
  // HALT_LOOP_CAP: optional; if present, unresolved_reason must be set
  "backlog": [
    {
      "priority": 1,                                                                   // required int, 1-based
      "title": "Collapse navigation duplicate authority",                              // required
      "kind": "structural",                                                            // enum: structural | simplification | polish
      "rank": "needed for winning",                                                    // enum: needed for winning | helpful | minor
      "why_it_matters": "...",                                                         // required
      "score_impact": "Architecture quality + State management each +1.0"              // required
    }
  ],
  // Required when system_flag in {HALT_STAGNATION, HALT_LOOP_CAP}; null otherwise.
  // For HALT_STAGNATION/no_backlog AND a converged HALT_LOOP_CAP (empty backlog), include residual accounting for each score < 9.5:
  // blocker, why it keeps the 9-anchor unmet, and why it is not backlog-worthy or accepted.
  "unresolved_reason": null,

  // Deepening Candidates (required array; 0-3 items; never invents new concerns)
  "deepening_candidates": [
    {
      "candidate_module": "NavigationStore",                                           // required
      "source_friction_proven": "RootView and LoginViewModel both write — see Finding F1",  // required, references a Finding ID
      "why_shallow_or_misplaced": "...",                                               // required
      "behavior_to_move_behind_interface": "...",                                      // required
      "dependency_category": "in-process",                                             // enum, same as findings
      "test_surface_after_change": "NavigationStoreTests asserts selectedTab transitions",  // required
      "smallest_first_step": "...",                                                    // required
      "what_not_to_do": "Do not introduce Coordinator protocol"                        // required
    }
  ],

  // Builder Notes (required; exactly 3 items unless verdict is HALT_SUCCESS or scope-limited)
  "builder_notes": [
    {
      "pattern": "Two writers to one mutable runtime concern",       // required
      "how_to_recognize": "...",                                     // required
      "smallest_coding_rule": "Find owner; bind everything else to its projection.",  // required
      "stack_example": "SwiftUI: TabView's selection binding is a read of NavigationStore, not an independent @State." // optional
    }
  ],

  // Final Judge Narrative (required, 1 paragraph)
  "narrative": "Place — promising but not yet contest-grade. Navigation duplicate authority is the biggest single deduction; concurrency is trustworthy; tests cover reducer paths but miss the navigation surface; future work risks adding Coordinator ceremony."

  // Loop N Result (required after Step 3 finishes; absent during HALT loops and before refactor)
  ,"loop_result": {
    "what_changed": "Consolidated save*Draft helpers into saveLibraryEntityDraft<Element>.",
    "evidence_change_is_honest": "swift test 1439 passed; lint clean",
    "risk_boundary_evidence": null,                                   // (v3+) object | null. null/absent ⇒ no Meta-Rule-4 risk boundary crossed this loop. When a COMMITTED change crosses one, REQUIRED: { "boundary_kind": <canon risk_boundary_kinds: isolation|sendable|conditional_compilation|cross_file_visibility|lock_ordering>, "verification": <canon risk_evidence_verifications: compile_matrix|focused_test|thread_sanitizer|sendable_conformance|reasoning_only|carried_forward>, "detail": "<non-empty: what was actually built/run>", "mechanically_testable": <bool> }. A green SINGLE-config compile is NOT evidence — there is deliberately no single-config verification value. `reasoning_only` is legal ONLY when mechanically_testable=false (invariant genuinely not mechanically testable; record why in detail). `carried_forward` = the crossing was not committed. Shape-gated by G33; the Layer-5 grader (exec_replay_grade.py) fails a committed boundary diff whose verification is not real.
    "targeted_finding_status": "resolved",                            // enum: resolved | carried_forward
    "unintended_regression": null,                                    // null or string describing the regression
    "changed_paths": ["BenchHypeKit/Sources/BenchHypeApplication/Reducer/AppReducer+Workflow.swift"],  // (v3+) source paths touched (from `git diff --name-only HEAD` after step 1). Combined with LOOP_STATE.pre_step3_blob_shas for narrow-revert on reviewer rejection.

    // Indirect coverage citation (PR 3, v2+). Required when what_changed contains a Deepening Keyword AND no test files in diff. Otherwise null.
    "interface_test_coverage_path": [
      {
        "file": "BenchHypeKitTests/Reducer/AppReducerSavedTests.swift",
        "assertion_lines": [142, 144],                                // inclusive range; encloses the assertion exercising the new code path
        "target_symbol": "saveLibraryEntityDraft",                    // newly-introduced OR existing-deepened identifier
        "target_symbol_kind": "new",                                  // string. Canonical enum: `new` | `existing_deepened`. Free-form `existing_<role>_interface` (e.g. `existing_bootstrap_interface`, `existing_fixture_interface`) accepted when the deepened symbol is a stable role-bearing interface (not new, not first-time-deepened) — name the role explicitly. `new` and `existing_deepened` remain the preferred values when they fit.
        "distinguishes_no_op": true                                   // true iff the cited assertion would fail if target_symbol's body were `fatalError()`
      }
    ]
  },

  // Implementation Review (required after Step 3 step 6 finishes; absent during HALT loops and before refactor)
  // Populated by the reviewer subagent per references/implementation-reviewer.md.
  // Verdict gates the commit: approved → commit code + artifacts; rejected → revert code, commit artifacts only.
  "implementation_review": {
    "verdict": "approved",                                            // enum: approved | rejected | conditional (final value never conditional in committed artifact — conditional is only mid-loop)
    "reason": "All three checks passed; targeted finding F1 no longer present in current source.",
    "checks": {
      "reality":    "passed",                                         // enum: passed | failed | skipped
      "honesty":    "passed",                                         // enum: passed | failed | skipped
      "regression": "passed"                                          // enum: passed | failed | skipped
    },
    "regressions": [],                                                // array of strings; empty when verdict approved
    "conditions": [],                                                 // array of strings; empty when verdict approved (populated only mid-loop on conditional)
    "rounds": 1,                                                      // int; number of reviewer invocations this loop (1 normally; 2 when conditional → re-spawn)
    "retry_count": 1,                                                 // (v3+) int 1..2. 1 = first-attempt success/clean fail; 2 = retried after transient infra failure.
    "retry_cause": null,                                              // (v3+) null | "timeout" | "spawn_error" | "malformed_json". non-null iff retry_count == 2. Substantive verdict reasons stay in `reason`.
    "retry_attempts": [                                               // (v3+) array, length == retry_count. Audit detail. Each entry: {attempt, outcome ∈ {ok, timeout, spawn_error, malformed_json}, error, duration_ms}.
      {"attempt": 1, "outcome": "ok", "error": null, "duration_ms": 7250}
    ]
  }
}
```

## Per-Loop Progress Line Format (schema_version >= 3)

Moved to [output-format-json-rules.md § Per-Loop Progress Line Format](output-format-json-rules.md#per-loop-progress-line-format-schema_version--3) — emit-time (Step 1 emit / Step 3), not investigation-time.

## halt_handoff object (PR 4, schema_version >= 2)

Moved to [output-format-json-rules.md § halt_handoff object](output-format-json-rules.md#halt_handoff-object-pr-4-schema_version--2) — emit-time.

## re_validation_context object (PR 4, schema_version >= 2)

Moved to [output-format-json-rules.md § re_validation_context object](output-format-json-rules.md#re_validation_context-object-pr-4-schema_version--2) — emit-time.

## Deepening Keywords (canonical)

The canonical list of keywords that mark a `loop_result.what_changed` as a deepening refactor. Both the `interface_test_coverage_path` required-when rule AND validation gate G17 reference this list verbatim. No keyword drift between schema and gate text.

```
collapsed | consolidated | merged | deepened | inlined | extracted | flattened
```

When `loop_result.what_changed` contains any of these keywords (case-insensitive substring match) AND no test files appear in the diff, the indirect-coverage carve-out applies and `loop_result.interface_test_coverage_path` is required.

## Schema validation rules (enforced by the validation hard gates)

Moved to [output-format-json-rules.md § Schema validation rules](output-format-json-rules.md#schema-validation-rules-enforced-by-the-validation-hard-gates) — emit-time coherence gates; the Critic collects fields against the Required-field schema above, these rules verify the artifact at emit.
