# Output Format

Each loop produces two files at repo root:

- `CURRENT_REVIEW.md` — human-readable, structured below
- `CURRENT_REVIEW.json` — machine-readable mirror

Previous `CURRENT_REVIEW.md` is appended to `REVIEW_HISTORY.md` (preceded by `--- Loop N (UTC timestamp) ---`) before being overwritten. This preserves cross-loop deltas without keeping multiple live files.

## CURRENT_REVIEW.md Structure

```
### Discovery (first loop only)
- Source roots:
- Test command:
- Build command:
- ADRs found: [list of titles or "none"]
- Domain terms (CONTEXT.md): [list or "none"]
- Selected lens: [Apple | Generic]

### Loop Counter
Loop N of M (cap)

### System Flag
[STATE: CONTINUE] | [STATE: HALT_SUCCESS] | [STATE: HALT_STAGNATION] | [STATE: HALT_LOOP_CAP]

---

## Contest Verdict
Choose one:
- Strong contender
- Good app, but not top-tier yet
- Promising, but architecturally immature
- Functionally solid, but structurally compromised
- Not contest ready

Short explanation (2–3 sentences).

## Scorecard (1-10)
Format: `[Score] | [Delta: UP/DOWN/SAME vs prev loop] | [Concrete proof: file:line or symbol]`.
Scores CANNOT increase without structural proof. Code simplicity drops → over-engineered the last refactor; revert.
Award 10 only when the dimension matches its 10-anchor and no source-backed behavior-preserving improvement is identifiable.
Every score above 7 must have at least one source-backed reason in this text.
When emitting `HALT_STAGNATION/no_backlog`, every score below 9.5 must also name
the source-backed blocker that keeps the dimension below the 9.5 threshold and
why it is not a valid backlog item or accepted residual.

- Architecture quality:
- State management and runtime ownership:
- Domain modeling:
- Data flow and dependency design:
- Framework / platform best practices:
- Concurrency and runtime safety:
- Code simplicity and clarity:
- Test strategy and regression resistance:
- Overall implementation credibility:

## Authority Map
For each major mutable runtime concern:
- Owner:
- Allowed writers:
- Observers / readers:
- Persistence seam:
- Async mutation entry points:
- Verdict: [Single and clear | Split and ambiguous]

(First loop only; re-emit if an authority finding is Priority 1.)

## Strengths That Matter
List only contest-relevant strengths backed by source. No mediocre praise. Do not praise counts.

## Findings
3–5 findings default. 6–7 only when each additional finding changes verdict, scorecard, or backlog. Fewer is better than padded.

For each finding:

### Finding #N: [Title]

**Why it matters** — contest-level harm in one sentence.

**What is wrong** — exact problem.

**Evidence** — file paths + line numbers; specific symbols if lines unavailable.

**Architectural test failed** — [Deletion test | Two-adapter rule | Shallow module | Interface-as-test-surface | Replace-don't-layer | n/a — different category]

**Dependency category** (if Coupling & Leakage finding) — exact enum: `in-process` | `local-substitutable` | `remote-owned` | `true-external` (these are the canonical machine strings; do not vary)

**Leverage impact** — do callers learn too much?

**Locality impact** — does change spread too widely?

**Metric signal, if any** — useful metrics only; "none" when none.

**Why this weakens submission** — architecture harm clearly stated.

**Severity** — [Cosmetic for contest | Noticeable weakness | Serious deduction | Likely disqualifier]

**ADR conflicts** — list of ADR IDs this finding contradicts, or "none". If contradicting, justify reopening.

**Minimal correction path** — smallest honest fix. When stack-specific behavior matters, briefly explain the rule in plain language. Reject ceremony-heavy fixes.

**Blast radius** — files to change vs. files to strictly avoid.

## Simplification Check
- Structurally necessary: [what this fix resolves — cite the architectural test passed]
- New seam justified: [if a port/adapter is added, name the ≥2 Adapters that will exist]
- Helpful simplification: [if applicable]
- Should NOT be done: [anything that would add ceremony, duplicate state, or broaden Interfaces without reducing ambiguity]
- Tests after fix: [which old tests are deleted (Replace, don't layer); where new interface-level tests live]

## Improvement Backlog
1–3 fixes in strict priority order. Priority 1 is focus of next loop. Derived only from Findings + Simplification Check; introduces no new concerns.

For each item:
- why it matters
- score impact
- structural / simplification / polish
- needed for winning / helpful / minor

Prioritize:
1. biggest contest gain
2. honesty plus simplicity
3. runtime safety
4. regression resistance
5. anti-overengineering
6. Leverage and Locality gains

## Deepening Candidates
0–3 candidates derived only from Findings or Simplification Check. For refactors where a Module could gain Depth, Leverage, or Locality. Do not invent new concerns. Do not propose a new Seam unless friction was already proven.

For each candidate:
- candidate Module or cluster
- source friction proven in this review
- why the current Interface is shallow or misplaced
- what behavior should move behind the deeper Interface
- dependency category: `in-process` | `local-substitutable` | `remote-owned` | `true-external` (canonical machine strings — same as Findings)
- test surface after the change
- smallest first step
- what not to do

If no real deepening candidates, say so. Do not pad.

## Builder Notes
Top 3 structural lessons in plain language for a technically inclined developer not deeply fluent in the stack. For each:
- what pattern appeared in this code
- how to recognize the same pattern next time
- the smallest coding rule to prevent it
- one stack-specific example if useful

Practical. Do not repeat every finding. Do not introduce new findings. Do not turn into tutorial.

## Final Judge Narrative
Short blunt summary. State clearly:
- win, place, or miss
- whether simplification helped or hurt this loop
- whether runtime ownership is trustworthy
- whether concurrency is trustworthy
- whether tests reduce regressions
- whether future work risks overengineering

## Loop N Result (appended at Step 3 step 4 after refactor; absent in HALT loops)
One paragraph:
- what changed (file paths, brief)
- what test/lint output proves the change is honest
- whether the targeted Priority 1 finding is **resolved** (gone from current source) or **carried forward** (next-loop Priority 1 again)
- any unintended scorecard regression observed
```

## CURRENT_REVIEW.json Schema

The JSON file is a faithful mirror of the Markdown contract. Every Markdown field has a JSON field; enums match the Markdown allowed values; arrays match the OutputBudget caps; proofs are required where the Markdown spec requires them.

### Required-field schema (machine-readable)

```jsonc
{
  // Loop bookkeeping (required)
  "schema_version": 2,                          // int, required. Existing pre-2026-05-09 artifacts default to 1; new gates G16-G20 + new fields apply only when >= 2.
  "loop": 3,                                    // int, 1-based
  "loop_cap": 10,                               // int
  "state": "CONTINUE",                          // enum: CONTINUE | HALT_SUCCESS | HALT_STAGNATION | HALT_LOOP_CAP
  "halt_subtype": null,                         // enum (required when state == HALT_STAGNATION; null otherwise): no_progress | oscillation | user_decision | no_backlog
  "halt_handoff_text": null,                    // legacy schema_version=1 field. At schema_version >= 2 use `halt_handoff` object below instead.
  "halt_handoff": null,                         // (PR 4, schema_version >= 2) required when state ∈ {HALT_*}; null on CONTINUE. Replaces flat halt_handoff_text. Object schema below.
  "re_validated_at_sha": null,                  // string sha; populated by Resume Detection when drift was checked and same halt persists.
  "re_validation_context": null,                // (PR 4, schema_version >= 2) required when re_validated_at_sha non-null. Object schema below.

  // Provider/model state (required when schema_version >= 2; on every loop, not first-loop-only)
  "provider": "claude_code",                    // enum: claude_code | codex | opencode | unknown. Detected per references/provider-adapters.md § Detection.
  "loop_model": "claude-sonnet-4-6",            // string, full canonical model ID. Default per provider-adapters.md loop-spawn table.
  "loop_model_source": "default",               // enum: default | env_override | user_flag
  "reviewer_model": "claude-sonnet-4-6",        // string, full canonical model ID. Default per provider-adapters.md reviewer-spawn table.
  "reviewer_model_source": "default",           // enum: default | env_override | user_flag
  "spawn_isolation": "subagent",                // enum: subagent | inline. "inline" only when provider == "unknown".

  // Findings registry (required when schema_version >= 2)
  "findings_registry_path": "./findings_registry.json", // string. Path to the external registry file. CURRENT_REVIEW.json never embeds registry content.

  // Discovery (required first loop only; null on later loops)
  "discovery": {
    "source_roots": ["BenchHypeKit/Sources/"],
    "test_command": "cd BenchHypeKit && swift test",
    "build_command": "./build_install_launch.sh ios --skip-preflight",
    "lens": "Apple",                            // enum: Apple | Generic
    "adrs": ["ADR-0001: reject transport parity tests"],
    "domain_terms": ["AppState", "InstanceID", "TileCueResolver"]
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
  "findings": [
    {
      "loop_local_id": "F1",                                               // required, "F<n>", fresh per loop, ordered by Priority. Replaces legacy "id" field at schema_version >= 2.
      "stable_id": "F-007",                                                // required when schema_version >= 2 on every emitted finding (CONTINUE and HALT loops alike). Format "F-NNN", looked up from findings_registry.json per Method Step 1.5.
      "id": "F1",                                                          // legacy alias of loop_local_id; emitted for schema_version < 2 backward-compat. New writes can omit.
      "title": "Navigation has two writers",                               // required
      "why_it_matters": "...",                                             // required
      "what_is_wrong": "...",                                              // required
      "evidence": ["App/RootView.swift:18", "Core/NavigationStore.swift:12"],  // required, >=1 entry
      "test_failed": "Deletion test",                                      // enum: Deletion test | Two-adapter rule | Shallow module | Interface-as-test-surface | Replace-don't-layer | n/a
      "dependency_category": "in-process",                                 // required when finding is Coupling & Leakage; else null. enum: in-process | local-substitutable | remote-owned | true-external
      "leverage_impact": "...",                                            // required (one sentence)
      "locality_impact": "...",                                            // required (one sentence)
      "metric_signal": "none",                                             // required string; "none" allowed
      "why_weakens_submission": "...",                                     // required
      "severity": "Serious deduction",                                     // enum: Cosmetic for contest | Noticeable weakness | Serious deduction | Likely disqualifier
      "adr_conflicts": [],                                                 // required array; empty allowed; entries are ADR IDs
      "adr_reopen_justification": null,                                    // required when adr_conflicts non-empty; else null
      "minimal_correction_path": "...",                                    // required
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

    // Indirect coverage citation (PR 3, schema_version >= 2). Required when what_changed contains a Deepening Keyword AND no test files appear in the diff. Otherwise null.
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
    "rounds": 1                                                       // int; number of reviewer invocations this loop (1 normally; 2 when conditional → re-spawn)
  }
}
```

## halt_handoff object (PR 4, schema_version >= 2)

Replaces the flat `halt_handoff_text` field at schema_version >= 2. Required when `state` ∈ {`HALT_SUCCESS`, `HALT_STAGNATION`, `HALT_LOOP_CAP`}; null on `CONTINUE`.

```jsonc
"halt_handoff": {
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
  ]
}
```

`match_kind` semantics:
- `all_of` — match if at least one match_keyword AND at least one match_path hit. **Default when match_paths is non-empty** (rule #18 enforces).
- `any_of` — match if any match_keyword OR any match_path hit. Permitted only when match_paths is empty (keyword-only fallback).
- `no_drift_expected` — match if `git log <halt_sha>..HEAD` returns empty.

The loop subagent emits `halt_handoff.expected_actions[]` from the menu options in halt-handoff.md. Each menu option becomes a HandoffAction with `action_id` derived from the option's verb/object and `match_keywords` / `match_paths` populated from the option's referenced symbols.

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

## Per-loop archive format (PR 5, schema_version >= 2)

When a completed `CURRENT_REVIEW.md` is archived to `REVIEW_HISTORY.md` in Step 3 step 9, apply these compressions to the .md archive only (`REVIEW_HISTORY.json` keeps full per-loop fidelity in `loops[]`):

1. **Discovery section**: omit on loops 2+ (only loop 1's archive carries Discovery; subsequent loops include the line "see Loop 1 Discovery").
2. **Builder Notes**: render only `pattern` per item with link "→ REVIEW_HISTORY.json `loops[N].builder_notes` for full notes".
3. **Simplification Check**: render as a 5-row table (one row per field: structurally_necessary, new_seam_justified, helpful_simplification, should_not_be_done, tests_after_fix) instead of bulleted prose.
4. **Loop N Result + Loop N Implementation Review**: keep verbatim (load-bearing audit chain).
5. **Findings**: keep verbatim (load-bearing structural record).
6. **Scorecard**: keep verbatim (delta basis for next loop's Critic).
7. **Authority Map / Strengths / Final Judge Narrative**: keep verbatim.

Compression applies prospectively from `schema_version >= 2` archives. Pre-version-2 archives in REVIEW_HISTORY.md remain in full prose form (no rewrite). Estimated savings on .md archive size: 15-20% per loop.

The live `CURRENT_REVIEW.md` is never compressed — only the archived copy in REVIEW_HISTORY.md. Downstream tools needing structured access read `REVIEW_HISTORY.json` directly.

## Deepening Keywords (canonical)

The canonical list of keywords that mark a `loop_result.what_changed` as a deepening refactor. Both the `interface_test_coverage_path` required-when rule AND validation gate G17 reference this list verbatim. No keyword drift between schema and gate text.

```
collapsed | consolidated | merged | deepened | inlined | extracted | flattened
```

When `loop_result.what_changed` contains any of these keywords (case-insensitive substring match) AND no test files appear in the diff, the indirect-coverage carve-out applies and `loop_result.interface_test_coverage_path` is required.

## findings_registry.json schema

External file at repo root. Created on first loop or via Step -1 step 0.6 bootstrap; persisted across loops; committed alongside CURRENT_REVIEW.{md,json} + REVIEW_HISTORY.{md,json}. Never embedded in CURRENT_REVIEW.json — referenced by `findings_registry_path`.

```jsonc
{
  "registry_schema_version": 2,        // int. Independent of CURRENT_REVIEW.json schema_version. Both default to 2 going forward.
  "next_serial": 8,                    // int. Monotonically incremented as new stable_ids are assigned.
  "entries": [
    {
      "stable_id": "F-007",            // string, regex ^F-\d{3,}$
      "title": "Oversized workflow file (>800 LOC)",
      "category_hint": "file-length",  // string, free-form taxonomy hint
      "primary_file": "BenchHypeKit/Sources/BenchHypeApplication/Reducer/AppReducer+Workflow.swift",
      "primary_evidence_lines": [1, 661],  // [start, end]
      "test_failed": "Shallow module",     // enum, same as findings[].test_failed
      "severity": "Cosmetic for contest",  // enum, same as findings[].severity
      "first_seen_loop": 1,
      "first_seen_sha": "<sha>",
      "last_seen_loop": 7,
      "occurrences": [
        {"loop": 1, "loop_local_id": "F3", "status": "open", "sha": "<observation_sha>"},
        {"loop": 3, "loop_local_id": "F3", "status": "fixed_by_user", "sha": "c066b0b"},
        {"loop": 5, "loop_local_id": "F2", "status": "rejected_attempt", "sha": "<resolution_sha>", "reviewer_reason": "<one sentence>"}
      ]
    }
  ]
}
```

Occurrence `status` enum: `open` (still in backlog) | `resolved` (loop's reviewer approved a fix) | `fixed_by_user` (user resolved between loops) | `rejected_attempt` (reviewer rejected the loop's attempted fix; do not drop, the audit chain needs it).

Occurrence `sha` semantics:
- `status == "resolved"` → resolution commit sha (the loop's commit that landed the fix; matches `Step 3 step 11` commit_sha for that loop).
- `status == "fixed_by_user"` → the user's commit sha that resolved the finding between loops (typically detected via Step -1 step 4a drift matching).
- `status == "rejected_attempt"` → the loop's commit sha (committing review artifacts only, no code change; the attempted-fix code was reverted in Step 3 step 6).
- `status == "open"` → the head sha at observation time (i.e., the parent of the loop's commit; equivalent to `git rev-parse HEAD~1` from the loop's commit perspective). For loop 1 with no prior commit, this is the sha of the most recent commit before `/contest-refactor` was invoked.

`first_seen_sha` always uses the observation-time sha (per the `open` rule), so it answers "what was the codebase state when this finding was first noticed."

## Fuzzy-match rules (Method Step 1.5 + bootstrap)

A candidate finding matches a registry entry iff `entry.last_seen_loop >= N - 3` AND **either**:

- **(M1) Title proximity**: case-insensitive cosine similarity of word-bag(title) >= 0.6.
- **(M2) Strong tuple**: same `primary_file` AND same `test_failed` AND same `severity` AND `|candidate.primary_evidence_lines.start - entry.primary_evidence_lines.start| <= 50`.

If 2+ entries match the candidate via M2 and 0 via M1 → emit `open_question_for_user` in loop return JSON; halt at HALT_STAGNATION subtype `user_decision`. Do not silently pick one.

## REVIEW_HISTORY.json schema

Mirrors REVIEW_HISTORY.md as a structured archive. Each loop's complete CURRENT_REVIEW.json is appended to the top-level `loops[]` array on Step 3 step 8.

```jsonc
{
  "schema_version": 2,
  "loops": [
    { /* full CURRENT_REVIEW.json snapshot for loop 1, schema_version: 1 if pre-migration */ },
    { /* full CURRENT_REVIEW.json snapshot for loop 2 */ }
  ]
}
```

Compression rules in `## Per-loop archive format` apply only to REVIEW_HISTORY.md. REVIEW_HISTORY.json keeps full per-loop fidelity for downstream tooling.

If REVIEW_HISTORY.md exists at first invocation but REVIEW_HISTORY.json does not, Step -1 step 0.6 reverse-parses to a best-effort .json with each entry marked `schema_version: 1`. Lossy; some fields may be null.

### Schema validation rules (enforced by the validation hard gates)

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
18. **Halt handoff required**: when `state` ∈ {`HALT_SUCCESS`, `HALT_STAGNATION`, `HALT_LOOP_CAP`}:
    - schema_version 1: `halt_handoff_text` non-empty string built from the matching template in `references/halt-handoff.md` with all placeholders resolved.
    - **schema_version >= 2 (PR 4)**: `halt_handoff` object non-null with `text` non-empty AND `expected_actions[]` array (may be empty). Each HandoffAction must satisfy: if `match_paths` is non-empty, `match_kind` must be `all_of`; if `match_paths` is empty, `match_kind` ∈ {`any_of`, `no_drift_expected`}. Null on `CONTINUE`.
19. **no_backlog residual accounting**: when `state == "HALT_STAGNATION"` AND `halt_subtype == "no_backlog"`, `unresolved_reason` must account for every score `< 9.5`: the source-backed blocker, why it keeps the 9-anchor unmet, and why it cannot be a backlog item or accepted residual. Rejected Cosmetic/ADR/SPT-failing candidates alone do not satisfy this rule when the dimension's 9-anchor is met; those become accepted residuals at 9.5 or disappear into a score of 10.
20. **user_decision coherence**: when `halt_subtype == "user_decision"`, `open_question_for_user` (in subagent return JSON) and `unresolved_reason` must both be non-null and consistent.
21. **Stable ID presence (PR 1)**: *Applies when schema_version >= 2.* Every emitted finding (in CONTINUE and HALT loops alike) has both `loop_local_id` (regex `^F\d+$`) and `stable_id` (regex `^F-\d{3,}$`) non-empty. `stable_id` either matches an entry in `findings_registry.json` (lookup via Method Step 1.5 fuzzy-match rules above) or is a new ID equal to `findings_registry.next_serial - 1` after that loop's increment. Reviewer-rejected loops still emit findings with stable_id; the registry occurrence carries `status: "rejected_attempt"`.
22. **Interface test coverage citation (PR 3)**: *Applies when schema_version >= 2.* When `loop_result.what_changed` contains any keyword from § Deepening Keywords AND the diff contains no test file changes, `loop_result.interface_test_coverage_path` must be non-null with at least one entry. Each entry must have `target_symbol` non-empty, `target_symbol_kind` matching the regex `^(new|existing_deepened|existing_[a-z_]+_interface)$` (canonical: `new` or `existing_deepened`; role-bearing variants like `existing_bootstrap_interface` accepted when the symbol is a stable named-role interface), AND `distinguishes_no_op == true`. Otherwise `interface_test_coverage_path` is null.
23. **re_validation_context coherence (PR 4)**: *Applies when schema_version >= 2.* When `re_validated_at_sha` is non-null, `re_validation_context` is required with all fields non-null (`drift_commit_count`, `prior_handoff_actions_taken`, `expected_actions_unmatched`, `why_halt_persists`, `re_validation_run_by`). Each `prior_handoff_actions_taken` entry's `match_kind` must equal the corresponding action's `match_kind` from the prior loop's `halt_handoff.expected_actions[]`. `re_validation_run_by == "main_agent_step_neg_one"` (canonical for current protocol).

Both CURRENT_REVIEW.md / .json AND `findings_registry.json` AND `REVIEW_HISTORY.json` (when schema_version >= 2) are committed at end of each loop alongside the code change.
