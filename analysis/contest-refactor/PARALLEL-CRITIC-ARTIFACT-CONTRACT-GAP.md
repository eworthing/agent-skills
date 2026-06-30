# Parallel Critic Artifact Contract Gap — contest-refactor vs levnik audit-suite

> **CURRENT-STATE (2026-06-28):** DEFERRED — self-gated — no consumers until CRITIC-INDEPENDENCE Gap B (parallel critics) ships. See [`GAP-AUDIT-AND-IMPROVEMENT-PLAN-2026-06-28.md`](GAP-AUDIT-AND-IMPROVEMENT-PLAN-2026-06-28.md) for the source-verified audit.
> Gate numbers **G37+** cited below are UNBUILT proposals — G33–G36 have since SHIPPED (2026-06-29); the live catalog (`contest-refactor/canon/validation-gates.toml`) now stops at **G36**. *(Re-verified 2026-06-30.)*

Source: `refs/competitors/levnik-skills/shared/references/audit_summary_contract.md` + `audit_final_report_contract.md` + `audit_output_schema.md`. Verified verbatim in LEVNIK-AUDIT-SUITE-GAP.

Pre-requisite gap doc. **Defer adoption until CRITIC-INDEPENDENCE Gap B (parallel critic mode) ships.** This doc designs the artifact contract that parallel critics will produce; without parallel critics, the contract has no consumers.

## Baseline: contest-refactor today (monolithic Critic)

- One Critic per loop produces one `CURRENT_REVIEW.json` (full artifact: findings + scorecard + verdict + backlog)
- Same artifact carries everything Implementation Reviewer + Actor need
- No multi-source merge problem because there's one source

When parallel critics ship (CRITIC-INDEPENDENCE Gap B), N critics produce N partial artifacts. Two failure modes appear:

1. **Token bloat**: N×CURRENT_REVIEW.json loaded simultaneously by synthesis step
2. **Merge ambiguity**: which critic's verdict wins on overlapping findings? whose scorecard counts?

Levnik audit-suite solves both by splitting per-critic output into transport (JSON, durable, fast-load) + evidence (MD, temporary, lazy-load). Contest-refactor should adopt the pattern WHEN it needs to.

## What levnik does (verbatim, key contracts)

### audit_worker_core_contract.md (Execution Rules section)

> - Report only unless fixes are explicitly allowed.
> - Verify Layer 1 candidates before reporting.
> - Use precise `file:line` locations when available.
> - Apply worker-specific false-positive filters.
> - Score with the shared formula.
> - **Write the markdown report once under `output_dir`.**
> - **Write JSON summary to `summaryArtifactPath` or the standalone runtime path.**

### audit_summary_contract.md (Envelope)

```jsonc
{
  "schema_version": "1.0.0",
  "summary_kind": "evaluation-worker",
  "run_id": "ln-620-global-...",
  "identifier": "global",
  "producer_skill": "ln-621",
  "produced_at": "2026-03-27T10:00:00Z",
  "payload": {
    "worker": "ln-621",
    "status": "completed",      // enum: completed | skipped | error  ("complete" invalid)
    "operation": "auditing",
    "warnings": [],
    "audit": {
      "category": "Security",
      "report_path": ".hex-skills/runtime-artifacts/runs/<run_id>/audit-report/ln-621--global.md",
      "score": 8.5,
      "issues_total": 3,
      "severity_counts": {"critical": 0, "high": 1, "medium": 2, "low": 0}
    }
  }
}
```

Strict enum: `"complete"` is invalid; only `"completed"` permitted.

### audit_final_report_contract.md (consumer protocol)

> Before writing the final report, the coordinator must:
>
> 1. read every completed worker JSON summary
> 2. read every worker `report_path` markdown file referenced by those summaries
> 3. normalize findings into a shared issue shape
> 4. deduplicate repeated findings across workers, domains, and report files
> 5. validate each actionable issue against current best-practice evidence

> ## Cleanup Rules
>
> After the final report is written:
>
> - delete every temporary worker markdown report under the run's `audit-report/` directory
> - keep the final coordinator report
> - keep JSON summaries, checkpoints, manifests, and logs
> - checkpoint cleanup evidence with `cleanup_verified=true`

## Strategic insight

The KEY insight is **lazy loading**: coordinator reads ALL JSON summaries first (fast, structured), reads MD evidence ONLY for findings that need deep review. With N=6 parallel critics emitting 50KB each of evidence, the synthesis step would otherwise consume 300KB before deciding what to focus on.

## Proposed contest-refactor parallel-critic artifact contract

When CRITIC-INDEPENDENCE Gap B ships parallel critics, each critic writes to:

```
.contest-refactor/loops/{loop_number}/critics/
├── {critic_source}--summary.json        # JSON transport, durable, fast-load
└── {critic_source}--evidence.md         # MD evidence, temporary, lazy-load
```

After synthesis:

```
.contest-refactor/loops/{loop_number}/
├── CURRENT_REVIEW.json                  # consolidated, durable
├── CURRENT_REVIEW.md                    # consolidated, durable
└── critics/
    └── {critic_source}--summary.json    # KEEP (audit trail)
                                          # {critic_source}--evidence.md DELETED post-synthesis
```

### Per-critic summary JSON schema

```jsonc
{
  "schema_version": 4,
  "summary_kind": "contest-refactor-critic",
  "loop": 3,
  "critic_source": "concurrency_critic",     // matches lens-registry.toml id
  "critic_model": "claude-sonnet-4-6",
  "produced_at": "2026-04-15T14:31:05Z",
  "evidence_path": ".contest-refactor/loops/3/critics/concurrency_critic--evidence.md",

  "status": "completed",                     // enum: completed | skipped | error  ("complete" invalid)
  "skip_reason": null,                       // required when status == "skipped"
  "error": null,                             // {type, message} when status == "error"

  "findings_summary": {
    "total": 3,
    "severity_counts": {
      "likely_disqualifier": 0,
      "serious_deduction": 1,
      "noticeable_weakness": 2,
      "cosmetic_for_contest": 0
    },
    "evidence_basis_counts": {
      "code_evidence": 3,
      "metric_evidence": 0,
      "test_evidence": 0
    }
  },

  "scorecard_input": {                       // critic's per-dimension input (synthesis combines)
    "concurrency": {"score": 8.5, "proof": "SpotifyAdapter.swift:88"},
    "state_management": {"score": 9.0, "proof": "AppState.swift"}
    // critic only scores dimensions in its specialty; others null
  },

  "warnings": [],
  "lens_trigger_evidence": "concurrency_critic fired: working_tree_dirty_paths overlap **/concurrent/**, code patterns matched [withCheckedContinuation, Task.detached]"
}
```

### Per-critic evidence MD schema

Free-form markdown with required sections:

```markdown
# {critic_source} — Loop {loop_number} Evidence

## Findings

### F1: Navigation has two writers
- **Severity**: Serious deduction
- **Evidence**:
  - App/RootView.swift:18 (Layer 1)
  - App/RootView.swift:15-30 (Layer 2 context)
- **Layer 2 verdict**: true_positive
- **Layer 2 rationale**: ...
- **why_weakens_submission**: ...
- **minimal_correction_path**: ...
- **blast_radius**: {change: [...], avoid: [...]}

### F2: ...

## Layer Trigger Evidence
{prose explaining which lens triggers fired and why}

## Excluded Candidates
{Layer 1 candidates that failed Layer 2; bounded ≤20 entries per TWO-LAYER-DETECTION-GAP optional addition}
```

### Synthesis step (`Step 1 synthesis`)

After all parallel critics return.

**Authorship rule (per Gemini Pro round 3 N2 — LLM map-reduce anti-pattern)**: the **Python orchestrator** (`scripts/synthesize-critics.py`, new) physically constructs the final consolidated `CURRENT_REVIEW.json`. The LLM is invoked ONLY as a "pure function" for specific ambiguous cases. Asking an LLM to carry a 6-critic merged JSON structure through its context window is token-expensive + invites hallucination at field boundaries (the same patch-offset-arithmetic class of bug N1 round 2 flagged for `changed_line_count`).

The split:

| Action | Authored by |
|---|---|
| Read all `critics/*--summary.json` | Python (deterministic JSON parse) |
| Build merged findings table from summaries | Python (in-memory list of dicts) |
| Coarse-bucket findings by `(primary_file, test_failed)` tuple | Python (cheap candidate bucket only — NOT the merge key per Codex round 1 B3) |
| **Fine-cluster within each bucket** by `(claim_consequence_hash, location_span_hash)` where location_span_hash = sha256(sorted evidence[] file:line ranges) | Python (per SCHEMA-GAP fingerprint scheme + new location-span hash); also cluster ACROSS files when claim_consequence_hash matches (e.g., "same auth-token-singleton finding in 3 files") | Python (deterministic) |
| Pick highest-severity per cluster as primary | Python (deterministic enum order: Likely disqualifier > Serious > Noticeable > Cosmetic) |
| Set `merged_into` / `also_known_as` / `locations` fields | Python (writes SCHEMA-GAP Gap 4 fields) |
| Lazy-load `critics/*--evidence.md` per non-merged finding | Python (filesystem read; one MD per finding) |
| Extract `evidence[]` / `why_weakens_submission` / `minimal_correction_path` / `blast_radius` from MD | Python (regex-extracts named sections per template) |
| Compose final `CURRENT_REVIEW.json` shape | Python (writes valid JSON, validate-artifact.py-checkable before LLM ever sees it) |
| **Ambiguous overlap resolution (LLM-as-pure-function)** | LLM via narrow subagent dispatch, sees only: the ambiguous pair, both critics' evidence excerpts, the rubric criterion |
| Write `CURRENT_REVIEW.md` (human-readable narrative) | LLM (this is genuinely generative work) |

Sequence:

1. **Python**: Read all `critics/*--summary.json`. Build in-memory findings list. (No LLM context.)
2. **Python**: Cross-critic dedup (per Codex round 1 B3 — `(file, test_failed)` alone is lossy: collapses distinct findings in same file + misses semantically-identical findings across files).
   - **Step 2a**: Coarse bucket by `(primary_file, test_failed)` — cheap candidate filter only.
   - **Step 2b**: Within each bucket, fine-cluster by `(claim_consequence_hash, location_span_hash)`. Findings with matching claim+location fingerprint are duplicates; findings with same `(file, test_failed)` but different claim are distinct (don't collapse).
   - **Step 2c**: Cross-file pass — re-cluster ACROSS buckets when `claim_consequence_hash` matches alone (catches "same auth-token-singleton pattern in 3 files"). Cross-file clusters get `also_known_as: [...]` + `locations: [...]` (per-file occurrence list).
   - **Step 2d**: Within each cluster: highest-severity wins as primary; lower-severity findings get `merged_into: "<primary_loop_local_id>"`.
3. **Python**: For each non-merged finding, lazy-load its critic's evidence.md and extract required fields by section name (h3-marker grep). If section missing → record `extraction_failure` in synthesis_log; finding gets `confidence: medium` downgrade.
4. **Python ambiguous-overlap detection**: when a fine-cluster (after Step 2b/2c) has 2+ findings at the SAME severity (no clear primary), flag as `ambiguous_overlap`. Bounded: typically <5% of findings.
5. **LLM ambiguous-overlap resolution**: for each `ambiguous_overlap`, dispatch a tiny resolver subagent. Input: 2-3 candidate findings + their evidence excerpts + the rubric criterion. Output: `{primary_id: "<id>", merged_into: ["<id>"], rationale: "..."}`. Subagent never sees the rest of the artifact; pure function.
6. **Python**: Apply ambiguous-overlap resolutions. Write `CURRENT_REVIEW.json` to disk. Validate against schema BEFORE writing.
7. **Python**: Scorecard merge. Each scorecard dimension authored by the critic whose specialty owns it (per `lens-registry.toml § dimension_ownership`). When multiple critics scored the same dimension AND scores differ by ≤0.5, Python takes the maximum (conservative). When differ by >0.5, escalate to user_decision halt subtype (no LLM averaging — that's hallucination-prone interpolation).
8. **LLM**: Generate `CURRENT_REVIEW.md` narrative sections (Builder Notes, Final Judge Narrative). Reads the just-written `CURRENT_REVIEW.json` for ground truth.
9. **Python**: Cleanup. Delete all `critics/*--evidence.md`; KEEP all `critics/*--summary.json` for audit trail.
10. **Python**: Validation. Run validate-artifact.py covering G16 (registry consistency) + new G38 (per-critic summary presence) + new G39 (cleanup verification) + new G40 (synthesis cardinality).

Token budget under this split:
- Python steps 1-4 + 6-7 + 9-10: ~0 LLM tokens (just disk I/O + dict manipulation)
- LLM step 5 (ambiguous overlaps, typical case 0-3 invocations × 2k tokens each): ≤6k
- LLM step 8 (narrative): ~10k
- Total LLM contribution to synthesis: ≤16k vs prior design's ~50k+ for LLM-authored JSON map-reduce

## New validation gates

**G38: Per-critic summary presence**. When `lenses_fired[].length > 0` (parallel-critic mode active), every entry in `lenses_fired[]` MUST have a corresponding `.contest-refactor/loops/{loop}/critics/{critic_source}--summary.json` file. Missing file = G38 failure.

**G39: Evidence cleanup**. After synthesis, no `.contest-refactor/loops/{loop}/critics/*--evidence.md` files may exist. Presence after synthesis = G39 failure. Failure routes via Resume Precedence Matrix as orphan-evidence case.

**G40: Synthesis verdict consistency**. Consolidated `CURRENT_REVIEW.json.findings[]` cardinality MUST equal sum of per-critic `findings_summary.total` minus dedup count (recorded in `synthesis_log`). Mismatch = G40 failure (lost or duplicated finding).

## Gap matrix

| Mechanism | contest-refactor (today) | levnik | proposed contest-refactor (this gap) |
|---|:--:|:--:|:--:|
| Per-source artifact split | n/a (one Critic) | ✓ JSON + MD per worker | ✓ JSON + MD per critic |
| Lazy MD load discipline | n/a | ✓ coordinator reads summaries first | ✓ synthesis step reads summaries first |
| Cleanup post-synthesis | n/a | ✓ delete worker MDs | ✓ delete critic evidence MDs |
| Audit trail (summaries kept) | n/a | ✓ JSON summaries durable | ✓ JSON summaries durable |
| Strict status enum (`completed` not `complete`) | n/a | ✓ documented | ✓ documented in schema |
| Per-source severity counts | n/a | ✓ in payload | ✓ in findings_summary |
| Per-source scorecard contribution | n/a | partial (per-worker score only) | ✓ per-critic scorecard_input |
| Dedup metadata fields | partial (SCHEMA-GAP Gap 4 reserved) | partial (markdown notes) | ✓ uses SCHEMA-GAP fields |
| Synthesis log | n/a | partial (cleanup_verified flag) | ✓ synthesis_log section in CURRENT_REVIEW.md |

## What NOT to import

| Tempting | Why skip |
|---|---|
| levnik's `summary_kind: "evaluation-worker"` schema verbatim | levnik is a generic evaluation framework. contest-refactor's `summary_kind: "contest-refactor-critic"` is more specific; don't mix vocabularies. |
| MD evidence as final artifact | Levnik keeps final MD. Contest-refactor's CURRENT_REVIEW.md serves that role; per-critic MDs are intermediate. Cleanup is correct. |
| Keeping all per-critic evidence indefinitely | Audit trail is JSON summaries + consolidated CURRENT_REVIEW.json/.md; per-critic MDs are scratchpads. Don't accumulate disk debt. |
| Letting synthesis happen in LLM context | When N critics each emit 50KB evidence, LLM-context synthesis is wasteful. Lazy-load via filesystem cuts cost. |
| Per-critic dedup before synthesis | Each critic dedups WITHIN its own findings; cross-critic dedup is the synthesizer's job. Don't ask each critic to know about siblings. |
| Coordinator-by-coordinator file path nesting | Levnik nests `runtime-artifacts/runs/{run_id}/{evaluation-worker,audit-report,evaluation-coordinator}/`. Contest-refactor's flatter `.contest-refactor/loops/{loop}/critics/` is sufficient — no separate coordinator dir. |

## Pairing with other gap docs

- **CRITIC-INDEPENDENCE-GAP Gap B (parallel critic mode)**: this doc is the artifact contract for that gap
- **SCHEMA-GAP Gap 3 + Gap 4 (`critic_source` + dedup metadata)**: per-critic summaries set `critic_source`; synthesis populates `merged_into` + `also_known_as`
- **SPECIALTY-LENS-DISPATCH-GAP**: each parallel critic is a triggered specialty lens
- **HALT-STATE-GAP**: new halt subtype `synthesis_conflict` (when critics disagree on a scorecard dimension and no resolution rule applies); pairs with `critic_unfounded`
- **LEVNIK-AUDIT-SUITE-GAP**: this is the direct adoption of levnik's split-artifact pattern; cross-link

## Adoption order

This entire doc is gated by **CRITIC-INDEPENDENCE Gap B (parallel critic mode) shipping first**. Order WITHIN this doc:

1. **Phase 1 (concurrent with CRITIC-INDEPENDENCE Gap B)**: Define per-critic summary JSON schema in `references/output-format-state-schemas.md`.
2. **Phase 2**: Implement synthesis step in `references/method.md` § Step 1 synthesis.
3. **Phase 3**: Add G38 + G39 + G40 validation gates.
4. **Phase 4**: Wire `.contest-refactor/loops/{loop}/critics/` lifecycle into `LOOP_PHASE_STATE.json` checkpoints (NOT LOOP_STATE.json — synthesis happens within Step 1 phase 1.0, owned by LOOP_PHASE_STATE per STATE-MACHINE-COMPOSITION-APPENDIX G45 ownership band; fix per Codex round 2 B1).

## Risk flags

1. **Disk pressure from per-critic evidence**: each critic could emit 100KB+ of evidence MD. 6 critics × 100KB × 10 loops = 6MB per run. Cleanup mitigates BUT only after synthesis completes. Mitigation: synthesis is a Phase 1.0 boundary; if interrupted mid-synthesis, LOOP_PHASE_STATE.json `current_phase = "step_1_critic_dispatch"` + phase-internal sub-step counter handles resume (NOT LOOP_STATE.json — synthesis is Step 1 owned, per STATE-MACHINE-COMPOSITION-APPENDIX G45 ownership band, fix per Codex round 2 B1); cleanup happens AFTER successful synthesis.
2. **Lazy-load latency**: synthesis reads summaries first, then loads MDs on demand. Filesystem I/O per finding could be slow. Mitigation: summaries carry enough metadata that >80% of dedup decisions don't need MD load.
3. **Strict status enum gotcha**: `"complete"` vs `"completed"` is the levnik trap (their docs explicitly call out `"complete" is invalid`). Contest-refactor must enforce same. Mitigation: `canon/critic-status.toml` enum + validate-artifact.py exact-match check.
4. **Synthesis prompt-template drift**: synthesis logic is partly LLM-driven (dedup judgment). Mitigation: deterministic dedup keys (`primary_file` + `test_failed`) handle 80% of cases; LLM only judges ambiguous overlap.
5. **Critic-without-trigger fired**: a critic whose lens trigger didn't fire still emits a summary (`status: "skipped"`). Synthesis must handle skipped critics (`skip_reason` populated). G38 doesn't require summary for un-triggered critics.
