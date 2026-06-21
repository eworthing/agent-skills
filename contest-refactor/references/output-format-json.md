# Output Format — JSON schemas (per-loop)

JSON mirror schema for the per-loop artifact `CURRENT_REVIEW.json`, plus its embedded `halt_handoff` and `re_validation_context` objects, the Per-Loop Progress Line Format, the canonical Deepening Keywords list, the Schema version 3 changelog, and the 27 schema validation rules enforced by the validation hard gates.

Persistent cross-loop state schemas (`LOOP_STATE.json`, `findings_registry.json`, `REVIEW_HISTORY.json`, plus the Fuzzy-match rules) live in [output-format-state-schemas.md](output-format-state-schemas.md). The human-readable markdown spec is in [output-format-markdown.md](output-format-markdown.md). Artifact index is [output-format.md](output-format.md).

## Contents

- [Schema version 4 changelog](#schema-version-4-changelog)
- [Schema version 3 changelog](#schema-version-3-changelog)
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

`CURRENT_REVIEW.json`, `REVIEW_HISTORY.json`, and `findings_registry.json` bump `schema_version: 2 → 3`. `LOOP_STATE.json` is a new file on its own track at `schema_version: 1`. Backward compatibility:

- v2 artifacts on disk at re-invocation are honored read-only by Step -1; missing v3 fields default per the table below.
- A loop running at v3 writes v3 artifacts; mixed-version `REVIEW_HISTORY.json.loops[]` entries are legal (each entry carries its own `schema_version`).
- G29 in [validation.md](validation.md) enforces these invariants.

### v2 → v3 default-fill table (when reading a v2 artifact)

| Missing v3 field | Default |
|---|---|
| `dry_run` (top-level CURRENT_REVIEW.json) | `false` |
| `discovery.test_scope` | `"full"` |
| `discovery.test_filter` | `null` |
| `discovery.working_tree_dirty_paths` | `[]` |
| `implementation_review.retry_count` | `1` |
| `implementation_review.retry_cause` | `null` |
| `implementation_review.retry_attempts` | `[{"attempt": 1, "outcome": "ok", "error": null, "duration_ms": null}]` |
| `loop_result.changed_paths` | `[]` |

### v3 changes (additive; no breaking changes)

- New halt state `HALT_DRY_RUN` (state enum extended); `halt_subtype: null`.
- New top-level field `dry_run` (boolean, audit only — re-invocation reads the user's CLI flag, not this field).
- New discovery fields `test_scope`, `test_filter`, `working_tree_dirty_paths`.
- New `implementation_review` fields `retry_count`, `retry_cause`, `retry_attempts[]` (transient retry metadata; substantive verdict stays in `reason`).
- New `loop_result.changed_paths[]` (paths the loop touched; restore source for narrow revert in conjunction with `LOOP_STATE.pre_step3_blob_shas`).
- New `LOOP_STATE.json` artifact for mid-Step-3 checkpointing.
- New gates G27 (retry envelope), G28 (checkpoint freshness), G29 (schema v3 invariants); new quality pass Q8 (per-loop progress line).

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
  "halt_subtype": null,                         // enum (required when state == HALT_STAGNATION; null otherwise): no_progress | oscillation | user_decision | no_backlog
  "halt_handoff_text": null,                    // legacy v1 field. v2+ uses `halt_handoff` object below instead.
  "halt_handoff": null,                         // (PR 4, v2+) required when state ∈ {HALT_*}; null on CONTINUE. Object schema below.
  "re_validated_at_sha": null,                  // string sha; populated by Resume Detection when drift was checked and same halt persists.
  "re_validation_context": null,                // (PR 4, v2+) required when re_validated_at_sha non-null. Object schema below.
  "dry_run": false,                             // (v3+) boolean. Audit trail of last invocation flag. NOT read on re-invocation (CLI flag is authoritative). true ⇒ state == "HALT_DRY_RUN".

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
  // For HALT_STAGNATION/no_backlog, include residual accounting for each score < 9.5:
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

Every loop dispatch (CONTINUE) and every HALT_* emit prints a single one-line progress summary to the terminal so callers (`/loop`, wrapper agents, log greppers) can track loop activity without parsing the full review. Q8 in [validation.md](validation.md) is the quality-pass check; the format is:

```
loop <N>/<cap> | F<n> <slug> | <dim> <a>→<b> <UP|DOWN|SAME> | tests <green|red|n/a> | reviewer: <approved|rejected|conditional|n/a> | <duration>s
```

Field rules:

- `<N>/<cap>` — `loop` and `loop_cap` from CURRENT_REVIEW.json.
- `F<n>` — `loop_local_id` of the targeted Priority-1 finding for the loop. `n/a` on HALT_SUCCESS / HALT_DRY_RUN.
- `<slug>` — kebab-case finding title, max 40 chars (e.g., "collapse-repository-theater"). Truncate at 40 chars without ellipsis. `none` on HALT_SUCCESS.
- `<dim>` — scorecard short code: `arch` | `tests` | `concur` | `error` | `code` | `ownership` | `coupling` | `depth` | `impl`. Pick the dimension with the largest absolute delta this loop; ties broken alphabetically.
- `<a>→<b>` — prior loop's score → current loop's score (e.g., `8.0→8.5`). `n/a→n/a` when no prior loop exists (loop 1).
- `<UP|DOWN|SAME>` — delta enum from the picked dimension's scorecard entry.
- `<green|red|n/a>` — test status: `green` if Step 1 build/tests passed, `red` if failed (build-failure path), `n/a` for HALT_DRY_RUN (Step 1 ran but no claim emitted).
- `<approved|rejected|conditional|n/a>` — `implementation_review.verdict` from the loop. `n/a` for HALT_DRY_RUN / HALT_SUCCESS / HALT_LOOP_CAP / HALT_STAGNATION (no refactor executed).
- `<duration>` — wall-clock seconds from Step 1 start to Step 3 step 11 commit (or to halt emit, when no commit). Integer.

### Variants

HALT_SUCCESS:
```
loop <N>/<cap> | HALT_SUCCESS | scorecard: <avg_score> | tests green | <duration>s
```

HALT_DRY_RUN:
```
loop <N>/<cap> | HALT_DRY_RUN | plan-only (Step 2) | tests <green|red|n/a> | <duration>s
```

HALT_STAGNATION:
```
loop <N>/<cap> | HALT_STAGNATION/<subtype> | F<n> <slug> | <dim> <a>→<b> SAME | tests <green|red> | <duration>s
```

HALT_LOOP_CAP:
```
loop <N>/<cap> | HALT_LOOP_CAP | F<n> <slug> (carried) | <dim> <a>→<b> <delta> | tests <green|red> | <duration>s
```

### Examples

```
loop 3/10 | F3 collapse-repository-theater | arch 8.0→8.5 UP | tests green | reviewer: approved | 47s
loop 7/10 | HALT_SUCCESS | scorecard: 9.6 | tests green | 38s
loop 1/10 | HALT_DRY_RUN | plan-only (Step 2) | tests green | 12s
loop 4/10 | HALT_STAGNATION/oscillation | F2 splice-workflow-file | arch 8.5→8.5 SAME | tests green | 51s
```

Q8 verifies presence and shape; format violations never block emit.

## halt_handoff object (PR 4, schema_version >= 2)

Replaces the flat `halt_handoff_text` field at schema_version >= 2. Required when `state` ∈ {`HALT_SUCCESS`, `HALT_STAGNATION`, `HALT_LOOP_CAP`}; null on `CONTINUE`.

```jsonc
"halt_handoff": {
  "state": "HALT_STAGNATION",                                        // optional mirror of top-level state for self-contained validation; default = top-level state when absent
  "halt_subtype": "oscillation",                                     // optional mirror of top-level halt_subtype; default = top-level halt_subtype when absent
  "text": "<full user-facing message per references/halt-handoff.md template, all placeholders resolved>",
  "expected_actions": [
    {
      "action_id": "split-workflow-file",                              // string, kebab-case identifier
      "description": "Split AppReducer+Workflow.swift to clear file_length warning",
      "match_keywords": ["split", "workflow", "AppReducer+Workflow"],  // array of strings; substring match against commit subjects
      "match_paths": ["BenchHypeKit/Sources/BenchHypeApplication/Reducer/AppReducer+Workflow.swift"],  // array of paths; match against commit's changed files
      "match_kind": "all_of"                                           // enum: all_of | any_of | no_drift_expected
    },
    {
      "action_id": "accept-halt",
      "description": "User accepts current halt; no commits expected",
      "match_keywords": [],
      "match_paths": [],
      "match_kind": "no_drift_expected"
    }
  ],
  "remaining_serious_findings_disposition": [
    // Required at schema_version >= 2 when state == HALT_STAGNATION AND halt_subtype == "oscillation".
    // Every Serious-or-worse finding with status ∈ {open, rejected_attempt} in the registry must appear here
    // with a canonical `disposition` (from canon/retirement-reasons.toml) plus the required sidecar.
    // G30 enforces coverage; the validator rejects HALT_STAGNATION/oscillation when any eligible
    // Serious-or-worse finding is missing or its sidecar is missing.
    { "stable_id": "F-007", "disposition": "unresolvable" },
    { "stable_id": "F-009", "disposition": "user_decision", "user_decision_ref": "ADR-0042" },
    { "stable_id": "F-011", "disposition": "outside_scope", "scope_label": "audio-engine" },
    { "stable_id": "F-013", "disposition": "unverifiable", "reason": "requires hardware test rig not available in scope" },
    { "stable_id": "F-015", "disposition": "superseded", "superseded_by": "F-020" }
  ]
}
```

`match_kind` semantics:
- `all_of` — match if at least one match_keyword AND at least one match_path hit. **Default when match_paths is non-empty** (rule #18 enforces).
- `any_of` — match if any match_keyword OR any match_path hit. Permitted only when match_paths is empty (keyword-only fallback).
- `no_drift_expected` — match if `git log <halt_sha>..HEAD` returns empty.

The loop subagent emits `halt_handoff.expected_actions[]` from the menu options in halt-handoff.md. Each menu option becomes a HandoffAction with `action_id` derived from the option's verb/object and `match_keywords` / `match_paths` populated from the option's referenced symbols.

### remaining_serious_findings_disposition[] sidecar rules (G30)

Each entry has `stable_id` plus `disposition` (one of the canonical values from `canon/retirement-reasons.toml`) plus a required sidecar field, depending on `disposition`:

- `disposition == "unresolvable"` — no extra sidecar; the registry already carries the `retirement` block (`reason` + `rationale`).
- `disposition == "user_decision"` — `user_decision_ref` non-empty (e.g., `"ADR-0042"`).
- `disposition == "outside_scope"` — `scope_label` non-empty (the scope label that does not cover the finding).
- `disposition == "unverifiable"` — `reason` non-empty (one-line explanation of why the available tools cannot validate the finding's claim).
- `disposition == "superseded"` — `superseded_by` non-empty (the stable_id of the replacement finding).

A missing sidecar where one is required is a G30 failure.

## re_validation_context object (PR 4, schema_version >= 2)

Required when `re_validated_at_sha` is non-null (Step -1 ran a fresh Step-1 critic pass on drift). Null otherwise.

```jsonc
"re_validation_context": {
  "drift_commit_count": 3,                                             // int. count of commits in <halt_sha>..HEAD
  "prior_handoff_actions_taken": [
    {
      "action_id": "split-workflow-file",
      "matched_commit_sha": "c066b0b",
      "commit_subject": "split AppReducer+Workflow.swift by feature",
      "match_kind": "all_of",
      "matched_keywords": ["split", "workflow"],
      "matched_paths": ["BenchHypeKit/Sources/BenchHypeApplication/Reducer/AppReducer+Workflow.swift"]
    }
  ],
  "expected_actions_unmatched": ["accept-halt"],                       // array of action_ids that did not match any commit (or "no_drift_expected" actions when drift exists)
  "why_halt_persists": "The workflow file split landed cleanly; remaining findings are cosmetic test-name polish, not contest-relevant.",  // one-sentence summary composed by main agent's re-validation pass
  "re_validation_run_by": "main_agent_step_neg_one"                    // enum: main_agent_step_neg_one (canonical) | other-future-routes
}
```

## Deepening Keywords (canonical)

The canonical list of keywords that mark a `loop_result.what_changed` as a deepening refactor. Both the `interface_test_coverage_path` required-when rule AND validation gate G17 reference this list verbatim. No keyword drift between schema and gate text.

```
collapsed | consolidated | merged | deepened | inlined | extracted | flattened
```

When `loop_result.what_changed` contains any of these keywords (case-insensitive substring match) AND no test files appear in the diff, the indirect-coverage carve-out applies and `loop_result.interface_test_coverage_path` is required.

## Schema validation rules (enforced by the validation hard gates)

1. Every Markdown section has a corresponding JSON field. Missing JSON field = hard gate failure.
2. Enum values exactly match the Markdown allowed strings (no synonyms, no abbreviations).
3. `proof` non-empty when `score > 7` OR when `unverifiable_due_to_build_failure == true` (in the build-failure case `proof` is the carry-forward note rather than a structural citation).
4. `residual_blocking_10` non-empty when `9.5 ≤ score < 10`; null when `score == 10`.
5. `dependency_category` non-null when finding is a Coupling & Leakage finding (title or `what_is_wrong` references domain↔framework or domain↔persistence leakage). Allowed values: `in-process` | `local-substitutable` | `remote-owned` | `true-external` (no synonyms; no `remote but owned` or `true external`).
6. `findings` count is 3-5 (or up to 7 if each addition changes verdict/scorecard/backlog). Three exceptions: (a) **empty** allowed when `state == "HALT_SUCCESS"`; (b) **empty** allowed when `state == "HALT_STAGNATION"` AND `halt_subtype == "no_backlog"`; (c) **exactly 1 finding** allowed when the build-failure path is active — detected as `state == "CONTINUE"` AND at least one scorecard entry has `unverifiable_due_to_build_failure == true`. The single finding must be the build-failure finding (`severity: "Likely disqualifier"`, `test_failed: "n/a"`). Rule #19 independently validates no-backlog residual accounting.
7. `backlog` presence by `state`:
   - `CONTINUE` → non-empty (1-3 items)
   - `HALT_SUCCESS` → empty
   - `HALT_STAGNATION` → optional; if non-empty, items carry forward as suggestions; `unresolved_reason` must be non-null
   - `HALT_LOOP_CAP` → optional; if non-empty, items name the best next move; `unresolved_reason` must be non-null
8. `loop_result` present iff a refactor was executed this loop (i.e., loop reached Step 3 step 4); absent during HALT loops AND during build-failure path (Step 1 step 2).
9. `adr_conflicts` non-empty implies `adr_reopen_justification` non-null.
10. Verdict string is one of the five exact enum values.
11. `unresolved_reason` non-null when `state` in {`HALT_STAGNATION`, `HALT_LOOP_CAP`}; null otherwise.
12. **9.5 residual disposition**: when `score >= 9.5 AND score < 10`, `residual_disposition` ∈ {`accepted`, `queued`} and `residual_rationale_or_backlog_ref` non-null. When `score == 10` OR `score < 9.5`, both fields are null.
13. **HALT_SUCCESS gating**: when `state == "HALT_SUCCESS"`, every scorecard dimension must satisfy: `score == 10` OR (`score >= 9.5` AND `residual_disposition == "accepted"`). Any `queued` residual blocks HALT_SUCCESS — downgrade to CONTINUE.
14. **Build-failure carry-forward**: when any scorecard entry has `unverifiable_due_to_build_failure: true`, gates G4 (score>7 source-backed) and G8 (no score increase without proof) are suspended for that entry. The flag is permitted only on Step 1 step 2 (build-failure path).
15. **Implementation review presence**: `implementation_review` is required when `loop_result` is present (i.e., a refactor was executed); absent when `loop_result` is absent. Final committed `verdict` ∈ {`approved`, `rejected`} — `conditional` is a mid-loop transient state that must be resolved (re-spawn → approved or rejected) before commit. `rounds` ≥ 1; `rounds == 2` only when first reviewer pass returned `conditional`.
16. **Reject ↔ loop_result coherence**: when `implementation_review.verdict == "rejected"`, `loop_result.targeted_finding_status` must equal `"carried_forward"` AND `loop_result.unintended_regression` must equal `implementation_review.reason`. Mismatch = G2 fails.
17. **Halt subtype required**: when `state == "HALT_STAGNATION"`, `halt_subtype` ∈ {`no_progress`, `oscillation`, `user_decision`, `no_backlog`}. Other halts must have `halt_subtype: null`.
18. **Halt handoff required**: when `state` ∈ {`HALT_SUCCESS`, `HALT_STAGNATION`, `HALT_LOOP_CAP`, `HALT_DRY_RUN`} (HALT_DRY_RUN at schema_version >= 3 only):
    - schema_version 1: `halt_handoff_text` non-empty string built from the matching template in `references/halt-handoff.md` with all placeholders resolved.
    - **schema_version >= 2 (PR 4)**: `halt_handoff` object non-null with `text` non-empty AND `expected_actions[]` array (may be empty). Each HandoffAction must satisfy: if `match_paths` is non-empty, `match_kind` must be `all_of`; if `match_paths` is empty, `match_kind` ∈ {`any_of`, `no_drift_expected`}. Null on `CONTINUE`.
19. **no_backlog residual accounting**: when `state == "HALT_STAGNATION"` AND `halt_subtype == "no_backlog"`, `unresolved_reason` must account for every score `< 9.5`: the source-backed blocker, why it keeps the 9-anchor unmet, and why it cannot be a backlog item or accepted residual. Rejected Cosmetic/ADR/SPT-failing candidates alone do not satisfy this rule when the dimension's 9-anchor is met; those become accepted residuals at 9.5 or disappear into a score of 10.
20. **user_decision coherence**: when `halt_subtype == "user_decision"`, `open_question_for_user` (in subagent return JSON) and `unresolved_reason` must both be non-null and consistent.
21. **Stable ID presence (PR 1, v2+)**: Every emitted finding (CONTINUE and HALT alike) has both `loop_local_id` (regex `^F\d+$`) and `stable_id` (regex `^F-\d{3,}$`) non-empty. `stable_id` matches an entry in `findings_registry.json` (Method Step 1.5 fuzzy-match) or is a new ID equal to `findings_registry.next_serial - 1` after the loop's increment. Reviewer-rejected loops still emit findings with stable_id; registry occurrence carries `status: "rejected_attempt"`.
22. **Interface test coverage citation (PR 3, v2+)**: When `loop_result.what_changed` contains any keyword from § Deepening Keywords AND diff contains no test file changes, `loop_result.interface_test_coverage_path` must be non-null with at least one entry. Each entry: `target_symbol` non-empty, `target_symbol_kind` matches `^(new|existing_deepened|existing_[a-z_]+_interface)$` (canonical: `new` or `existing_deepened`; role-bearing variants like `existing_bootstrap_interface` accepted when symbol is a stable named-role interface), AND `distinguishes_no_op == true`. Otherwise null.
23. **re_validation_context coherence (PR 4, v2+)**: When `re_validated_at_sha` non-null, `re_validation_context` required with all fields non-null (`drift_commit_count`, `prior_handoff_actions_taken`, `expected_actions_unmatched`, `why_halt_persists`, `re_validation_run_by`). Each `prior_handoff_actions_taken` entry's `match_kind` must equal prior loop's matching action's `match_kind`. `re_validation_run_by == "main_agent_step_neg_one"` (canonical).

24. **HALT_DRY_RUN coherence (v3+)**: when `state == "HALT_DRY_RUN"`, `dry_run == true` AND `halt_subtype == null` AND `halt_handoff` non-null with text from [halt-handoff.md § HALT_DRY_RUN](halt-handoff.md). CURRENT_REVIEW.md contains `## Loop N Plan (dry-run)` with the Step 2 plan. `loop_result` and `implementation_review` absent (no Step 3 work). `backlog` non-empty (plan derives from a Priority-1 finding). G9 backlog purity unaffected.

25. **Retry envelope shape (v3+)**: `implementation_review.retry_count ∈ {1, 2}`. When `retry_count == 1`: `retry_cause == null` AND `retry_attempts[]` has 1 entry. When `retry_count == 2`: `retry_cause ∈ {"timeout", "spawn_error", "malformed_json"}` AND `retry_attempts[]` has 2 entries AND first entry's `outcome` matches `retry_cause`. `reason` MUST NOT mention "after 2 attempts" or transient causes; those live in `retry_cause` / `retry_attempts[]` only. Both attempts fail → `verdict == "rejected"` AND `reason == "reviewer unavailable; manual verification required"` exactly.

26. **changed_paths populated (v3+)**: when `loop_result` present, `loop_result.changed_paths[]` non-empty (empty diff = nothing changed and `loop_result` should be absent per rule #8).

27. **test_scope coherence (v3+)**: `discovery.test_scope ∈ {"full", "incremental"}`. `"incremental"` → `discovery.test_filter` non-null non-empty. `"full"` → `discovery.test_filter` null. Per [validation.md G21 extension](validation.md), `state == "HALT_SUCCESS"` requires `discovery.test_scope == "full"` if any prior loop in REVIEW_HISTORY.json had incremental scope.

28. **HALT_SUCCESS challenge (v4+)**: enforced by G32 in [validation.md](validation.md). Rules differ by state and schema_version:
    - **`state == "HALT_SUCCESS"` at schema_version >= 4**: `halt_success_challenge` required non-null; `halt_success_challenge.outcome == "held"`; `halt_success_challenge.challenger_model` non-empty; `halt_success_challenge.attempts` a non-empty list; `halt_success_challenge.binding.run_id` equals top-level `run_id`; `halt_success_challenge.binding.source_rev` equals top-level `source_rev`; `halt_success_challenge.binding.candidate_commit_sha` non-empty. Any miss is a G32 failure.
    - **`state == "HALT_SUCCESS_candidate"` at schema_version >= 4**: `halt_success_challenge` must be `null`; `run_id`, `source_rev`, `candidate_fingerprint` must all be non-null. The candidate is EXEMPT from the challenge requirement — it awaits promotion by the main agent.
    - **schema_version < 4**: G32 does not fire. Legacy v3 `HALT_SUCCESS` without a challenge remains valid.
    - **`state == "HALT_SUCCESS_candidate"`**: obeys the same scorecard / backlog / findings rules as `HALT_SUCCESS` (every dim 10 or 9.5-accepted; empty backlog; empty findings). It is a success claim awaiting challenge, not a downgrade.
    - **`outcome == "broke"` + `state == "HALT_SUCCESS"`**: illegal. Main agent must demote the candidate before emitting terminal `HALT_SUCCESS` (the challenger breaks → demote, not promote).

Both CURRENT_REVIEW.md / .json AND `findings_registry.json` AND `REVIEW_HISTORY.json` (v2+) are committed at end of each loop alongside the code change.
