# State Machine Composition Appendix — sequencing 4 new intercept points

**Trigger**: Gemini Pro peer review round 1 (B1, HIGH): "bundle proposes Parallel Critics + Synthesis, Validator Subagent per finding, Cross-Model Critic (Phase 1.5), Clean-Environment Revalidation (Phase 1.9). None of the docs define how these phases compose. Race conditions and catastrophic token bloat without a unified target state machine."

This appendix resolves B1. It sequences all proposed-in-this-bundle intercept points into a single end-to-end loop pipeline, names the orchestrator (main agent vs subagent), defines composition rules + race-condition mitigations, and documents the token-budget envelope per phase.

## Baseline state machine (today, contest-refactor SKILL.md)

```
Step -1: Resume Detection (main agent)
Step 0:  Context Discovery (main agent, first loop only)
Step 1:  Critic Phase   ┐
Step 2:  Architect Phase│ (one loop subagent runs all three)
Step 3:  Execution Phase┘
```

Per loop, ONE subagent runs Step 1 → Step 2 → Step 3 contiguously. Main agent handles Step -1 / Step 0 / dispatch / halt routing.

## Target state machine (with all bundle adoptions)

```
Main agent owns orchestration. Each numbered phase is one tool call boundary.
Multiple subagents dispatched across phases; per-phase context is sealed.

Step -1: Resume Detection                                            [main]
Step  0: Context Discovery                                           [main]
         (sub-steps 1-7 = existing contest-refactor Step 0; new additions post-lens-detection are 7a-7g, all running AFTER sub-step 7 records discovery)
         7a: lint config ingestion (GOVERNANCE Gap A) — post-lens, lens-specific configs known
         7b: CI workflow ingestion (GOVERNANCE Gap B) — post-lens, mandatory flags extracted
         7c: import graph build  (GOVERNANCE Gap D, P1 PROMOTED) — post-lens, parser registry per lens
         7d: repo-map build      (TRACEABILITY Gap E, P1 PROMOTED) — reuses 7c AST infrastructure
         7e: boundary-rule load  (GOVERNANCE Gap C) — checks against graph from 7c
         7f: hotspot compute     (ROI-PRIORITIZATION Phase 1-2) — independent of lens
         7g: specialty-lens availability scan (SPECIALTY-LENS-DISPATCH Phase 1)

Step  1: Critic Pipeline                                             [main orchestrates]
         1.0 — Critic subagent dispatch                              [Critic subagent]
               (CRITIC-INDEPENDENCE Gap A: Critic split from Actor)
               Within Critic subagent:
                 - Method step 5a: specialty-lens trigger eval
                   (SPECIALTY-LENS-DISPATCH Phase 2)
                 - If lens-registry triggers ≥2 specialty lenses AND
                   --parallel-critics enabled:
                     Dispatch N parallel critic sub-subagents
                     (CRITIC-INDEPENDENCE Gap B + PARALLEL-CRITIC-ARTIFACT-CONTRACT)
                     Each writes critics/{critic_source}--{summary.json,evidence.md}
                     Synthesis step (within Critic subagent) reads summaries first,
                     dedupes per SCHEMA-GAP Gap 4 fields, lazy-loads MD evidence
                 - Else (single-critic mode):
                     Critic writes CURRENT_REVIEW.json directly
               Returns: provisional CURRENT_REVIEW.json + routing JSON

         1.1 — Validator subagent gate (SCHEMA-GAP Gap 5)            [main]
               Pre-condition: provisional CURRENT_REVIEW.json has findings
               Main dispatches N validator subagents in parallel
               (one per finding; each sees only finding desc + evidence-cited files)
               Each returns: confirmed | downgrade_severity:<level> | reject:<reason>
               Main applies verdicts → updates CURRENT_REVIEW.json findings array
               Findings dropped post-validation: append to excluded_candidates[]
               (TWO-LAYER-DETECTION-GAP optional field)

         1.2 — Cross-Model Critic gate (CROSS-MODEL-CRITIC-GAP)      [main]
               Pre-condition: --cross-model-critic <provider> flag set
               Main dispatches external-provider CLI subprocess
               Provider sees: validated findings (post-1.1) + source code
               Returns: per-finding cross_model_verdict ∈ {agreed,disputed,added}
               Main applies to CURRENT_REVIEW.json
               Skipped when flag absent (default off)

         1.25 — State recompute (per Codex round 1 B1)               [main]
               Re-derive provisional state from post-1.2 findings + scorecard.
               Required because 1.1 may have rejected findings that empty the backlog,
               and 1.2 may have added/disputed findings that change severity.
               1.3 must NOT run on a stale pre-routing state.
               Writes `provisional_state` field to LOOP_PHASE_STATE.json (new artifact, see below).

         1.3 — Clean-Env Revalidation gate (CLEAN-ENVIRONMENT-VALIDATION-GAP)  [main]
               Pre-condition: --clean-validate-before-halt flag set
                              AND post-1.25 provisional state == HALT_SUCCESS
               Main creates worktree, cd, runs test_command, re-runs G21 + G24 + G25
               On any failure: state → HALT_STAGNATION/clean_revalidation_failed
               On pass: state stays HALT_SUCCESS
               Skipped when flag absent OR provisional state != HALT_SUCCESS

         1.4 — Step 1 routing (existing per SKILL.md Step 1 Routing) [main]
               Branches on final state:
                 HALT_* → archive, commit artifacts only, terminate
                 CONTINUE + non-empty backlog → dispatch Step 2 (Actor subagent)
                 CONTINUE + empty backlog → Residual Accounting per G23

Step  2: Architect Phase                                             [Actor subagent — FRESH]
         (CRITIC-INDEPENDENCE Gap A: Actor subagent reads CURRENT_REVIEW.json only;
          no Critic reasoning trace bleed-through)

Step  3: Execution Phase                                             [Actor subagent continues]
         (within same Actor subagent as Step 2; runs LOOP_STATE checkpoint discipline)

Step 12: Loop dispatch (continuation OR halt handoff per existing rules)
```

## Composition rules (race-condition + token-budget mitigation)

### Rule 1: Sequential gates, not parallel

1.0 → 1.1 → 1.2 → 1.3 → 1.4 run **strictly sequentially**. Each gate consumes the output of the previous. Parallelizing 1.1/1.2/1.3 against each other = race condition: cross-model might validate a finding that validator was about to reject; clean-env might revalidate a HALT_SUCCESS that cross-model was about to dispute.

Within 1.0, parallel critics ARE permitted (each sees sealed input; synthesis happens after all return).

### Rule 2: Each gate is opt-in EXCEPT 1.0 + 1.4

- **1.0** (Critic subagent dispatch) — always runs; this is contest-refactor's existing Step 1
- **1.4** (Step 1 routing) — always runs; this is contest-refactor's existing routing

- **1.1** (Validator) — opt-in via `--validator-subagent` flag (default off initially; ramp to default-on after fixtures prove stability)
- **1.2** (Cross-Model) — opt-in via `--cross-model-critic <provider>` flag (default off; high latency cost)
- **1.3** (Clean-Env) — opt-in via `--clean-validate-before-halt` flag (default off; high latency cost)

ALL FOUR can be enabled simultaneously. ZERO enabled = baseline contest-refactor behavior (back-compat).

### Rule 3: Validator MUST precede Cross-Model

If both 1.1 and 1.2 enabled, validator runs first. Rationale: cross-model is the most expensive gate (external CLI subprocess, 30-90s). Don't pay external cost on findings the local validator is about to filter. Order keeps token budget bounded.

### Rule 4: Clean-Env runs LAST and only for HALT_SUCCESS candidates

1.3 is the only gate that can revert a state from HALT_SUCCESS back to HALT_STAGNATION. It MUST run after 1.0/1.1/1.2 because:
- If validator rejected findings such that backlog empties, state may transition to HALT_SUCCESS only at 1.4 routing
- If cross-model added findings that bump severity, state may transition AWAY from HALT_SUCCESS
- 1.3 needs the final post-1.2 state to know whether to fire

Pre-condition check: `provisional state == "HALT_SUCCESS"` AND `--clean-validate-before-halt`. Else skip.

### Rule 5: Parallel critics use sealed input within 1.0 ONLY

Per CRITIC-INDEPENDENCE Gap B + PARALLEL-CRITIC-ARTIFACT-CONTRACT-GAP: when 1.0 fans out, each parallel critic subagent gets sealed input (only its lens + standards + diff). Synthesis happens WITHIN the parent Critic subagent context after all parallel critics return.

Subsequent gates (1.1 / 1.2 / 1.3) see the synthesized CURRENT_REVIEW.json, NOT individual critic outputs. The split-artifact pattern (JSON summaries + lazy MD load) is internal to 1.0; gates 1.1+ consume only the consolidated artifact.

### Rule 6: Subagent context boundaries AND artifact writer ownership

| Phase | Context | Writes to (artifact ownership) |
|---|---|---|
| Step -1, Step 0 | main agent | CURRENT_REVIEW.json (initial), governance_context (Step 0 sub-step 7a-7g) |
| 1.0 Critic subagent (+ parallel critic sub-subagents within) | fresh subagent per loop | provisional CURRENT_REVIEW.json; critics/*--summary.json + evidence.md (when parallel); LOOP_PHASE_STATE.current_phase = "1.0" written by main BEFORE dispatch, "1.0_done" written by main on return |
| 1.1 Validator subagents | N fresh subagents, parallel | each subagent RETURNS verdict JSON to main (subagents do NOT write LOOP_PHASE_STATE — that's main-agent-only per ownership rule, fix per Codex round 3 B1); main agent aggregates returned verdicts → writes LOOP_PHASE_STATE.validator_verdicts[] → updates CURRENT_REVIEW.json findings |
| 1.2 Cross-Model Critic | external CLI subprocess | main writes cross-model result to CURRENT_REVIEW.cross_model_critic; LOOP_PHASE_STATE.cross_model_status |
| 1.25 State recompute | main agent | LOOP_PHASE_STATE.provisional_state |
| 1.3 Clean-Env Revalidation | main agent; runs in temp worktree | CURRENT_REVIEW.clean_revalidation; LOOP_PHASE_STATE.clean_env_status |
| 1.4 Routing | main agent | CURRENT_REVIEW.state (final); LOOP_PHASE_STATE.current_phase = "1.4_done" |
| Step 2-3 Actor subagent | fresh subagent per loop | LOOP_STATE.json (existing Step-3-only checkpoint); CURRENT_REVIEW.loop_result (Step 3); commit + REVIEW_HISTORY append |
| Step 12 dispatch | main agent | LOOP_PHASE_STATE.json deleted after successful commit + state ∈ {HALT_*, CONTINUE-next-loop} |

**LOOP_PHASE_STATE.json (NEW artifact, per Codex round 1 B1)**:

Separate from existing `LOOP_STATE.json` (which is mid-Step-3 checkpoint owned by Actor subagent — DO NOT extend it; that breaks the Step-3-only ownership contract per `output-format-state-schemas.md:16`).

```jsonc
// .contest-refactor/loops/{loop}/LOOP_PHASE_STATE.json
// Written by MAIN AGENT only during Step 1 phases 1.0-1.4. Step 2-3 don't touch it.
// Atomic write-fsync per phase transition.
{
  "schema_version": 1,
  "loop": 3,
  "current_phase": "1.25_state_recompute",        // canon/loop-phases.toml
  "phases_completed": ["1.0", "1.1", "1.2"],
  "started_at": "...",
  "last_updated_at": "...",
  "provisional_state": "HALT_SUCCESS",            // populated post-1.25; consumed by 1.3
  "validator_verdicts": [
    {"finding_id": "F1", "verdict": "confirmed"},
    {"finding_id": "F2", "verdict": "downgrade_severity:Noticeable weakness"},
    {"finding_id": "F3", "verdict": "reject:Layer 2 disagrees"}
  ],
  "cross_model_status": {
    "invocation_status": "completed",
    "added_findings": ["F8"],
    "disputed_findings": ["F2"],
    "agreed_findings": ["F1"]
  },
  "clean_env_status": null                        // populated post-1.3
}
```

**Lifecycle**:
1. Main agent writes initial `LOOP_PHASE_STATE.json` at Step 0 sub-step 7g (after specialty-lens scan; before Step 1 dispatch). Fields: `loop`, `current_phase: "1.0"`, empty arrays.
2. Each phase 1.0-1.4 transition: main writes update + fsync.
3. After Step 12 successful commit AND state ∈ {HALT_*, CONTINUE-next-loop ready}: delete `LOOP_PHASE_STATE.json` (atomic rename + unlink).
4. Resume: if `LOOP_PHASE_STATE.json` exists at Step -1, resume from `current_phase`; if `LOOP_STATE.json` ALSO exists, Actor subagent's Step-3 checkpoint takes precedence (Step 2-3 is later in pipeline).

**Cross-doc validity**: existing `LOOP_STATE.json` schema in `output-format-state-schemas.md` unchanged. G28 (LOOP_STATE.json invariants) unaffected.

Critic context never sees Validator/Cross-Model/Clean-Env output; those gates UPDATE the artifact main reads. Actor context never sees Critic reasoning trace, only the final artifact. This is the entire point of subagent isolation.

## Token-budget envelope per phase

For a typical loop with --parallel-critics + --validator-subagent enabled (1.0 + 1.1 active), cross-model + clean-env disabled:

| Phase | Tokens | Note |
|---|---|---|
| 1.0 Critic (single) | ~30k | source reads + Method execution + emit |
| 1.0 Critic (parallel, 6 lenses) | ~30k × 6 = 180k | fan-out budget |
| 1.0 Synthesis | ~5k | reads summaries + lazy-loads ~3 evidence MDs |
| 1.1 Validator (5 findings) | ~3k × 5 = 15k | each validator sees only narrow finding + 1-2 cited files |
| 1.2 Cross-Model | ~40-60k | external provider full review |
| 1.3 Clean-Env | ~0 contest-refactor tokens (subprocess; not LLM in this gate) | filesystem + test runtime |
| Total worst case (all enabled, parallel critics) | ~245k | within Opus 4.7 1M-context budget |

Most users will run with 1.1 (validator) enabled and 1.2/1.3 disabled by default. That's ~50k per loop, comfortable in 200k-context models.

## Failure-mode composition

| If this fails | Effect on subsequent gates |
|---|---|
| 1.0 Critic crashes | Whole loop aborts; LOOP_PHASE_STATE.json (NOT LOOP_STATE.json — Step 1 ownership band, fix per Codex round 3 B1) preserves resume point at `current_phase = "step_1_critic_dispatch"` |
| 1.0 parallel critic timeout | Failed critic's lens contributes empty summary with `status: "error"`; synthesis continues with N-1 critics; new halt subtype `partial_critic_synthesis` if ≥50% failed |
| 1.1 Validator timeout per finding | Fall back to `confirmed` (don't block on infra failure; SCHEMA-GAP Gap 5 + GATES-GAP Gap D 30s timeout) |
| 1.1 Validator rejects all findings | State → HALT_STAGNATION/critic_unfounded (HALT-STATE-GAP Gap B) |
| 1.2 Cross-Model unavailable | Fail-open per CROSS-MODEL-CRITIC-GAP Gap A; `cross_model_critic.invocation_status: "unavailable"`; proceed to 1.3/1.4 |
| 1.2 Cross-Model disputes all findings | Record disputes; do NOT auto-drop. Main agent presents to user as `open_question_for_user`; halt subtype `cross_model_dispute_unresolved` (new — add to canon/halt-subtypes.toml) |
| 1.3 Clean-Env worktree creation fails | Fail-open per CLEAN-ENVIRONMENT-VALIDATION-GAP risk #1; warn user; proceed to 1.4 without revalidation |
| 1.3 Test re-run fails in clean env | State → HALT_STAGNATION/clean_revalidation_failed; CURRENT_REVIEW.clean_revalidation captures failure diff for user diagnosis (NOT LOOP_STATE.json — Step 1 ownership band, fix per Codex round 3 B1); LOOP_PHASE_STATE.clean_env_status records failure for resume routing |

## New canonical entries required

`canon/halt-subtypes.toml` final consolidated enum after this appendix (per Codex round 1 N3 — single source of truth; all docs that propose new subtypes MUST add here, not in their own canon-update sections):

```toml
halt_subtypes = [
    # Existing
    "no_progress",
    "oscillation",
    "user_decision",
    "no_backlog",
    # Added by gap docs (consolidated here, source doc cited)
    "critic_unfounded",                  # HALT-STATE-GAP Gap B + SCHEMA Gap 5 validator
    "clean_revalidation_failed",         # CLEAN-ENVIRONMENT-VALIDATION-GAP Phase 1.3 failure
    "cross_model_dispute_unresolved",    # CROSS-MODEL-CRITIC-GAP / this appendix 1.2 failure
    "partial_critic_synthesis",          # PARALLEL-CRITIC-ARTIFACT-CONTRACT / this appendix 1.0 failure
    "synthesis_conflict",                # PARALLEL-CRITIC-ARTIFACT-CONTRACT scorecard merge
    "no_economic_case",                  # ROI-PRIORITIZATION (all backlog at "low" tier)
    "cross_domain_inconsistency",        # DOMAIN-AWARE-SCANNING (if Gap A ever ships)
]
```

**Single ownership rule**: any gap doc proposing a new halt subtype MUST (a) add a row to this table, (b) NOT include `halt_subtypes = [...]` blocks elsewhere in its own doc. Subtypes listed in this appendix's table are authoritative; conflicting per-doc canon snippets are out-of-date.

`canon/loop-phases.toml` (NEW canonical file):

```toml
# Canonical loop-phase enum. Used by LOOP_PHASE_STATE.json.current_phase (main-agent Step 1 phases)
# AND LOOP_STATE.json.current_phase (Actor-subagent Step 2-3 phases). DO NOT mix ownership:
# LOOP_PHASE_STATE owns step_1_* phases; LOOP_STATE owns step_2_* and step_3_*.
loop_phases = [
    "step_minus_1_resume_detection",
    "step_0_context_discovery",
    "step_1_critic_dispatch",                  # 1.0  [LOOP_PHASE_STATE]
    "step_1_validator_gate",                   # 1.1  [LOOP_PHASE_STATE]
    "step_1_cross_model_gate",                 # 1.2  [LOOP_PHASE_STATE]
    "step_1_state_recompute",                  # 1.25 [LOOP_PHASE_STATE] NEW per Codex round 1 B1
    "step_1_clean_env_gate",                   # 1.3  [LOOP_PHASE_STATE]
    "step_1_routing",                          # 1.4  [LOOP_PHASE_STATE]
    "step_2_architect",                        #      [LOOP_STATE]
    "step_3_execution",                        #      [LOOP_STATE]
    "step_12_loop_dispatch",                   #      main agent; no checkpoint artifact
]
```

`LOOP_PHASE_STATE.json` (NEW, defined above) carries `current_phase` for step_1_* phases. `LOOP_STATE.json` (existing) continues to carry `current_phase` for step_2_/step_3_ phases ONLY. G45 (new): every state-file write must include `current_phase` matching its artifact's ownership band; phase transitions monotonic; cross-artifact phase write = G45 failure.

## Validation gates added by this appendix

**G45 (new) — ownership-band-scoped (per Codex round 2 B1)**: Phase ownership enforced across BOTH state-file artifacts.

- `LOOP_PHASE_STATE.json.current_phase` MUST be one of `{step_1_critic_dispatch, step_1_validator_gate, step_1_cross_model_gate, step_1_state_recompute, step_1_clean_env_gate, step_1_routing}` (the step_1_* band).
- `LOOP_STATE.json.current_phase` MUST be one of `{step_2_architect, step_3_execution}` (the step_2_/step_3_ band).
- Step_1_* phase written to LOOP_STATE.json = G45 failure (cross-artifact-band violation).
- Step_2_/step_3_* phase written to LOOP_PHASE_STATE.json = G45 failure.
- Both artifacts: transitions monotonic forward within a loop (no jumping back).
- step_minus_1_*, step_0_*, step_12_* are main-agent phases with no state-file artifact (audit-only via CURRENT_REVIEW.phase_order_audit[]).

**G46 (new)**: When `--validator-subagent` AND `--cross-model-critic` both active, validator MUST run before cross-model. Cross-model phase invoked before validator phase = G46 failure. Enforced at main agent orchestration layer; recorded in CURRENT_REVIEW.json.phase_order_audit[] (new audit field).

**G47 (new)**: When `--clean-validate-before-halt` active AND provisional state == HALT_SUCCESS, clean-env phase MUST run before final state lands. Skipping 1.3 in this case = G47 failure.

## Schema additions (additive, `schema_version: 4`)

Top-level CURRENT_REVIEW.json:

```jsonc
{
  "phase_order_audit": [                    // NEW — records which gates ran this loop
    {"phase": "step_1_critic_dispatch", "started_at": "...", "completed_at": "...", "status": "completed"},
    {"phase": "step_1_validator_gate", "started_at": "...", "completed_at": "...", "status": "completed"},
    {"phase": "step_1_cross_model_gate", "status": "skipped", "skip_reason": "flag_not_set"},
    {"phase": "step_1_clean_env_gate", "status": "skipped", "skip_reason": "state_not_halt_success"},
    {"phase": "step_1_routing", "started_at": "...", "completed_at": "..."}
  ]
}
```

`LOOP_PHASE_STATE.json` (Step 1 ownership band — fix per Codex round 2 B1; LOOP_STATE.json schema example previously here was WRONG, LOOP_STATE only carries step_2_/step_3_):

```jsonc
{
  "current_phase": "step_1_validator_gate",    // step_1_* phase belongs here, NOT in LOOP_STATE.json
  // ... existing LOOP_PHASE_STATE fields ...
}
```

`LOOP_STATE.json` (Step 2-3 ownership band — unchanged from existing schema in output-format-state-schemas.md):

```jsonc
{
  "current_phase": "step_3_execution",         // step_2_/step_3_* only; cross-band = G45 failure
  // ... existing LOOP_STATE fields ...
}
```

## What this appendix does NOT do

- Doesn't change Step -1 / Step 0 / Step 2 / Step 3 mechanics — those are existing
- Doesn't make any of 1.1/1.2/1.3 default-on — all opt-in
- Doesn't allow gate reordering — sequence is fixed by Rules 1, 3, 4
- Doesn't add new failure-mode behavior beyond what individual gap docs already specified — just composes the failure modes consistently

## Test fixture for this appendix

Add to SKILL-TDD-FIXTURES-GAP fixture #6 (NEW, after the original 5):

```
loop-fixtures/all-gates-enabled/
├── fixture.toml                            # invocation_flags: --parallel-critics --validator-subagent --cross-model-critic codex --clean-validate-before-halt
├── codebase/                               # small Swift module
├── baseline/                               # without contest-refactor
└── expected/
    ├── phase_order_audit-expected.json     # verifies G45 + G46 + G47 enforcement
    └── ...
```

This fixture is the ONLY way to verify the composition rules in this appendix actually hold at runtime. Without it, the appendix is documentation theater.

## Cross-doc revisions implied by this appendix

| Doc | Change needed |
|---|---|
| CRITIC-INDEPENDENCE-GAP Gap B | Reference this appendix for sub-subagent dispatch boundaries within 1.0 |
| PARALLEL-CRITIC-ARTIFACT-CONTRACT-GAP | Clarify synthesis is internal to 1.0 (Critic subagent), not a separate main-agent phase |
| SCHEMA-GAP Gap 5 (validator subagent) | Reference 1.1 placement; note pre-condition (Critic emit) + post-condition (cross-model gate consumes its output) |
| CROSS-MODEL-CRITIC-GAP | ✅ APPLIED round 2: Phase 1.5 → Phase 1.2 (all references renamed) |
| CLEAN-ENVIRONMENT-VALIDATION-GAP | ✅ APPLIED round 2: Phase 1.9 → Phase 1.3 (all references renamed); pre-condition clarified to "post-validator-and-cross-model state == HALT_SUCCESS" |
| SPECIALTY-LENS-DISPATCH-GAP | Reference 1.0 Method step 5a placement; clarify lens triggers fire BEFORE parallel-critic fan-out (else fan-out has no lens-list to fan over) |
| HALT-STATE-GAP | Add new halt subtypes `cross_model_dispute_unresolved` + `partial_critic_synthesis` |

## Adoption order for this appendix

This appendix is meta-documentation. It ships when ANY of 1.1/1.2/1.3 ships. Concrete ordering:

1. **Pre-requisite**: CRITIC-INDEPENDENCE Gap A (Critic+Actor subagent split) MUST land first. Without that, "main agent orchestrates 4 gates" has no main agent — Critic and Actor share context.
2. **First gate**: 1.1 (Validator subagent) — adopt with SCHEMA-GAP Gap 5; smallest cost, biggest signal-to-noise win
3. **Second gate**: 1.0 fan-out (parallel critics) — adopt with CRITIC-INDEPENDENCE Gap B + PARALLEL-CRITIC-ARTIFACT-CONTRACT-GAP; needs specialty-lens registry from SPECIALTY-LENS-DISPATCH-GAP
4. **Third gate**: 1.3 (Clean-Env) — adopt with CLEAN-ENVIRONMENT-VALIDATION-GAP; opt-in only
5. **Fourth gate**: 1.2 (Cross-Model) — adopt with CROSS-MODEL-CRITIC-GAP; opt-in only; depends on second provider install
6. **Throughout**: G45 + G46 + G47 ship alongside the gate they enforce

Once 2+ gates are adopted, this appendix becomes the authoritative reference. Until then, individual gap docs are sufficient.

## Why this appendix exists

Gemini Pro caught what Claude Opus missed: each gap doc optimized its own intercept point in isolation. None considered how 4 new intercepts would race for the same loop budget OR contend for state transitions. Without this sequencing, implementing 1.1 + 1.2 in any order produces a non-deterministic loop.

Cross-model adversarial review delivered its promised value at the meta-level: composition was the blindspot.
