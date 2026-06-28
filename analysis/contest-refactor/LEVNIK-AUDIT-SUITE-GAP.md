# Levnik Audit-Suite Gap — contest-refactor vs ln-620 + 9 L3 workers

> **CURRENT-STATE (2026-06-28):** COVERED — orchestrator / two-layer / phase-machine / scoring equivalents already present. See [`GAP-AUDIT-AND-IMPROVEMENT-PLAN-2026-06-28.md`](GAP-AUDIT-AND-IMPROVEMENT-PLAN-2026-06-28.md) for the source-verified audit.

Source: `refs/competitors/levnik-skills/plugins/codebase-audit-suite/` (35+ specialized auditor skills across audit/test/architecture/persistence sub-suites). Inspected after research flagged it as "newest serious entrant on persisted-state orchestration." Source confirms; research understated scope (suite is 35+ workers, not just one).

## What it actually is

**L2 Coordinator + 9 L3 Workers** (ln-620 plus ln-621 through ln-629 hardcoded). Coordinator dispatches via `Skill()` tool (not Task, not MCP). Two-mode operation: managed (parent passes `runId` + `summaryArtifactPath`) vs standalone.

Three sibling audit-sub-suites under the same plugin: tests (ln-630-638, 9 workers), patterns/architecture (ln-640-647, 8 workers), persistence/runtime (ln-650-654, 5 workers). Total: 35 specialized workers.

**Phase machine** (ln-620 SKILL.md verbatim):

```
1. PHASE_0_CONFIG
2. PHASE_1_DISCOVERY
3. PHASE_2_RESEARCH
4. PHASE_3_DELEGATE
5. PHASE_4_AGGREGATE
6. PHASE_5_REPORT
7. PHASE_6_SELF_CHECK
```

**File-based handoff at `.hex-skills/runtime-artifacts/runs/{run_id}/`:**

| Path | Lifecycle |
|---|---|
| `audit-report/{worker}--{identifier}.md` | Temporary; deleted post-consolidation |
| `evaluation-worker/{worker}--{identifier}.json` | Durable transport (severity counts, score, report_path) |
| `evaluation-coordinator/{coordinator}--summary.json` | Durable coordinator envelope |
| `audit-report/ln-620--final-report.md` | **Only artifact kept after cleanup** |

**No cross-loop registry.** Each run isolated. Final consolidated MD is the only durable artifact between runs. (Contest-refactor wins here: `findings_registry.json` + cross-loop stable_id beats per-run-isolation.)

## Verbatim scoring (audit_scoring.md, complete file)

```
penalty = (critical x 2.0) + (high x 1.0) + (medium x 0.5) + (low x 0.2)
score = max(0, 10 - penalty)

| Score | Action |
|-------|--------|
| 10 | No action |
| 8-9 | Low-priority fixes |
| 6-7 | Next-sprint fixes |
| 4-5 | Prioritized fixes |
| 1-3 | Immediate action |
```

Optional diagnostic sub-scores (`compliance`, `completeness`, `quality`, `implementation`) are informational only; primary `score` always uses penalty formula.

## Verbatim summary envelope (audit_summary_contract.md)

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
    "status": "completed",          // enum: completed | skipped | error  (NOTE: "complete" invalid)
    "operation": "auditing",
    "warnings": [],
    "audit": {
      "category": "Security",
      "report_path": ".hex-skills/.../ln-621--global.md",
      "score": 8.5,
      "issues_total": 3,
      "severity_counts": {"critical": 0, "high": 1, "medium": 2, "low": 0}
    }
  }
}
```

## Comparison to contest-refactor

| Mechanism | contest-refactor | levnik audit-suite |
|---|:--:|:--:|
| Critic role decomposition | 1 monolithic Critic + lens system | 35+ specialty workers across 4 sub-suites |
| Worker dispatch | Subagent via Task tool (Schema-Gap proposed split) | `Skill()` tool dispatch with hardcoded worker list per coordinator |
| Phase enum | Step -1/0/1/2/3 implicit | 7 explicit phases (`PHASE_0_CONFIG`..`PHASE_6_SELF_CHECK`) |
| Worker plan / applicability filter | n/a (single Critic) | DISCOVERY phase detects stack, skips inapplicable workers |
| Per-worker scoring | n/a | ✓ per-worker 0-10 penalty score (distributed rubric) |
| Cross-worker dedup with source tracking | partial (registry fingerprint) | ✓ "this finding appears in worker X and Y, prefer source Z" |
| Two-layer detection discipline | implicit | ✓ MANDATORY: Layer 1 grep candidate → Layer 2 context verify |
| Stage advancement via artifacts | ✓ (LOOP_STATE.json) | ✓ (worker JSONs + coordinator checkpoints) |
| Worker artifact contract (JSON transport + MD evidence) | partial (findings in single CURRENT_REVIEW.json) | ✓ split: JSON for coordination, MD for evidence |
| Severity enum | 4-tier contest-themed | 4-tier industry (critical/high/medium/low) |
| Penalty-based composite scoring | — (G21 threshold) | ✓ explicit formula |
| Score-band action labels | — | ✓ 5 bands (no-action / low / next-sprint / prioritized / immediate) |
| Domain-aware scanning (multi-domain repo) | — | ✓ `domain_mode + current_domain + scan_path` |
| Cleanup discipline post-final-report | ✓ LOOP_STATE.json atomic delete | ✓ delete temp worker MDs, keep JSON + checkpoints + manifests |
| Cross-loop persistence | ✓ findings_registry.json + fingerprint | — (each run isolated) |
| Halt taxonomy + subtypes | ✓ 5 states + 4 subtypes | partial (phase barriers block; no explicit halt enum) |
| Per-finding retirement enum | ✓ 5 reasons | — |
| Halt handoff with structured actions | ✓ expected_actions[] | — |

## Specialty coverage gaps (contest-refactor's single Critic misses)

Verified from source — 5 areas where levnik's specialty decomposition exceeds contest-refactor's lens system:

1. **Concurrency (ln-628)** — 7 checks: async races, thread safety, TOCTOU, deadlocks, blocking I/O in async, resource contention, cross-process races. Beyond lens-apple's `Continuation-bridge delegate audit` (G25); contest-refactor has no thread-safety/TOCTOU/deadlock detection rules.

2. **Architecture boundary (ln-642)** — Transaction boundary ownership (commit/rollback distribution across layers), session DI vs local consistency, flat orchestration depth chains. Contest-refactor's Authority Map covers ownership-of-mutable-concern but not transaction-boundary-ownership or session-DI-pattern-consistency.

3. **Security (ln-621)** — Hardcoded secrets with prod-vs-test fixture distinction, SQL injection with ORM context verification, XSS with framework auto-escape awareness, sensitive env defaults, per-endpoint input validation. Contest-refactor's lens-generic doesn't differentiate ORM-mediated SQL from raw concatenation; lens-apple has no XSS coverage.

4. **Test isolation + oracle quality (ln-635, ln-638)** — Two-layer test isolation detection (Layer 1 grep shared state, Layer 2 read test fixtures), oracle effectiveness (assertion specificity, flakiness markers). Contest-refactor's `test_strategy` dimension (G24) checks for test-surface presence but not isolation or oracle quality.

5. **Persistence + query (ln-650, ln-651)** — N+1 detection via graph traversal + ORM call patterns, query plan analysis (cartesian products, missing indexes), transaction correctness (saga vs ACID decision validation). Contest-refactor has no data-access-layer audit; would only catch via prose Implementation Review.

## P0/P1 GAPS — what to import

### Gap A (P0): Two-layer detection discipline as canonical rule

Verbatim from `audit_worker_core_contract.md`: *"Verify Layer 1 candidates before reporting. Use precise `file:line` locations when available. Apply worker-specific false-positive filters."*

Contest-refactor's Critic implicitly does this (Method step 1 evidence-gathering before scoring) but doesn't formalize. **Adopt:** add to `references/method.md` as explicit rule: *"Two-layer detection: Layer 1 grep/glob candidate scan; Layer 2 context verification (read surrounding code/fixtures). No finding emitted from Layer 1 alone."*

Pairs with SCHEMA-GAP's `confidence` field per its 2-value canon (`high|medium`, see [SCHEMA-GAP § Confidence enum canon](SCHEMA-GAP-CONTEST-REFACTOR.md#confidence-enum-canon-sc1-resolution)): Layer 2 strong verification → `confidence: high`; Layer 2 weak verification → `confidence: medium`; Layer 2 failure or Layer 1 alone → dropped into `excluded_candidates[]`, never emitted as a finding. (Earlier draft of this line said "`confidence: medium` or dropped" for Layer-2-failure — that was inconsistent with the canon, which reserves `medium` for weak-passing Layer 2 only; `low` is intentionally absent because emitted findings carry actionable signal, not speculation.)

### Gap B (P0): Per-finding category + score band

Levnik's score-band action labels (`no-action / low-priority / next-sprint / prioritized / immediate`) give actionable per-finding triage that contest-refactor's 4-tier severity (`Cosmetic for contest | Noticeable weakness | Serious deduction | Likely disqualifier`) lacks.

Note: contest-refactor's severity IS action-oriented (it tells the Actor what to fix first) but contest-themed. Levnik's industry-vocabulary labels are more portable.

**Recommendation:** keep contest-themed severity (it's part of the brand), but document the mapping in `canon/severity-anchors.toml`:

```toml
severity_anchors = [
    "Cosmetic for contest",        # ≈ low-priority
    "Noticeable weakness",         # ≈ next-sprint
    "Serious deduction",           # ≈ prioritized
    "Likely disqualifier",         # ≈ immediate
]
```

Lets external consumers map. No schema change.

### Gap C (P1): Specialty worker decomposition for high-value lenses

Contest-refactor's monolithic Critic + lens system can't carry 35 specialty rule sets. But the doc § 6 P1 ("Risk-triggered external lenses") explicitly calls for trigger-based specialty lens dispatch.

**Adopt** the audit-suite pattern selectively. Don't ship 35 workers; ship 4-6 as dispatchable specialty lenses triggered by Critic's Method step 1 risk detection:

| Specialty | Trigger condition | Adapted from |
|---|---|---|
| Concurrency hazards | scoring `concurrency >= 9` OR async code touched | ln-628 |
| Security boundaries | auth / parsing / crypto / secrets / file IO touched | ln-621 |
| Persistence efficiency | ORM call patterns OR query construction touched | ln-650 / ln-651 |
| Test isolation + oracle | scoring `test_strategy >= 9` OR test files touched | ln-635 / ln-638 |
| Architecture boundary | layer crossing detected OR transaction code touched | ln-642 |
| Dead code | refactor candidate appears to be removal | ln-626 |

Each specialty lens follows the existing `lens-apple.md` / `lens-generic.md` shape (markdown rule pack), NOT the full L3-Worker subagent pattern. Loads on trigger only; not always-on (preserves token budget).

### Gap D (P1): Worker artifact contract for parallel critics

When CRITIC-INDEPENDENCE Gap B (parallel critic mode) ships, levnik's split-artifact pattern is the cleanest schema:

- Per-critic JSON summary (transport, durable, fast to consume) → main agent reads first
- Per-critic MD evidence (verbose, temporary, deleted post-synthesis) → main agent reads only when JSON flags a finding worth deep-diving

Contest-refactor currently bundles everything in `CURRENT_REVIEW.json` + `CURRENT_REVIEW.md`. The split keeps coordination cheap when 4-6 parallel critics each emit MD reports of significant size.

**Schema sketch** (additive, when parallel critics ship):

```jsonc
{
  "critic_results": [
    {
      "critic_source": "concurrency_critic",
      "summary_path": ".contest-refactor/loops/{loop}/critics/concurrency_critic--summary.json",
      "evidence_path": ".contest-refactor/loops/{loop}/critics/concurrency_critic--evidence.md",
      "status": "completed",      // enum: completed | skipped | error
      "severity_counts": {"likely_disqualifier": 0, "serious": 1, "noticeable": 2, "cosmetic": 0}
    }
  ]
}
```

Pairs with SCHEMA-GAP Gap 3 (`critic_source` field) and CRITIC-INDEPENDENCE Gap B.

### Gap E (P2): Domain-aware scanning for multi-domain repos

Levnik's `domain_mode + current_domain + scan_path` lets one repo with multiple sub-domains (e.g., `services/order-intake/`, `services/billing/`) be audited per-domain with findings tagged. Contest-refactor scans whole repo or via `--scope <dir>` flag but doesn't tag findings with domain.

**Defer.** Only useful for multi-domain monorepos. Add to discovery if user demand appears.

### Gap F (defer): Penalty-based composite scoring as alternative to 9.5+

Levnik's `score = max(0, 10 - penalty)` with `penalty = critical*2.0 + high*1.0 + medium*0.5 + low*0.2` is deterministic and falsifiable per-dimension. Contest-refactor's 9.5+ threshold is composite + qualitative.

This intersects the metric-worship critique from earlier research. NOT a recommended adoption — contest-refactor's qualitative anchors (per `architecture-rubric.md`) are intentionally not formulaic. Document as a path NOT taken with rationale.

## What contest-refactor wins (do not regress)

| Mechanism | contest-refactor | levnik |
|---|---|---|
| Cross-loop persistent finding identity | ✓ `findings_registry.json` + fingerprint + stable_id | — each run isolated |
| Per-finding retirement reasons | ✓ 5 reasons | — |
| Halt subtype taxonomy | ✓ 4 subtypes | — phase-barriers only |
| Halt handoff with structured actions | ✓ `expected_actions[]` + drift matcher | — |
| Atomic LOOP_STATE checkpoint with `(step_started, step_completed)` recovery key | ✓ | partial (checkpoint exists, recovery key unclear) |
| ICA-grounded `test_failed` enum | ✓ 5 architectural tests | — generic categories |
| `leverage_impact` + `locality_impact` per finding | ✓ | — |
| Authority Map | ✓ first-loop + Priority-1 authority findings | — |
| Anchor-to-source drift detection (G26) | ✓ | — |
| Pre-edit blast_radius prediction | ✓ | — |
| Pre-step3 blob_shas narrow revert | ✓ | — |

Levnik's architecture is broader (35 specialty workers) but shallower per-finding (no cross-loop identity, no retirement, no narrow revert, no causal trace).

## Per-doc revisions needed

### SCHEMA-GAP-CONTEST-REFACTOR.md
- Add to canon documentation: levnik's penalty formula as **path NOT taken** + rationale (qualitative anchors preserved)
- Note levnik's industry-severity mapping in `severity_anchors.toml` comment

### CRITIC-INDEPENDENCE-GAP.md
- **Gap B (parallel critic mode) gets reference implementation**: levnik's L2 Coordinator + L3 Worker pattern via `Skill()` dispatch with hardcoded worker list. Strong proof point that parallel critic mode works in production.
- Note levnik's per-worker JSON+MD split (foreshadowing Gap D below)

### HALT-STATE-GAP.md
- Add levnik's 7-phase enum + phase-barrier model as comparator
- Note contest-refactor wins on halt subtype + handoff + cross-loop identity (levnik has phase-barriers but no halt taxonomy)
- Cleanup-discipline cross-check: levnik deletes worker MDs post-consolidation; contest-refactor deletes LOOP_STATE.json post-commit. Both correct; document the parallel.

### GOVERNANCE-GAP.md
- **NEW comparator**: levnik audit-suite, especially `audit_final_report_contract.md`'s mandatory source-order research (official docs > MCP Ref > Context7 > web). Aligns with contest-refactor's lens system but adds explicit research-source-order rule.
- Add Gap G (defer): mandatory research-source-order discipline before validating actionable issues. Cross-link to user's existing global Context7 routing rule in `~/.claude/CLAUDE.md`.

### TRACEABILITY-GAP.md
- Add levnik's split-artifact contract as forward-compat reference for parallel-critic mode (Gap D in this doc)
- Note levnik's `evidence_basis_counts` optional field in summary payload as analog to contest-refactor's evidence chain — minor field-naming inspiration

### GATES-GAP.md
- Add levnik's coordinator self-check phase (PHASE_6_SELF_CHECK) as analog to validation gates. Levnik does it at runtime; contest-refactor does it via `validate-artifact.py`. Document the parallel.

## New gap docs needed (priority-ranked)

| # | Doc | Scope | Sources |
|---|---|---|---|
| P0 | **SPECIALTY-LENS-DISPATCH-GAP.md** | Gap C above — 4-6 trigger-dispatched specialty lenses (Concurrency / Security / Persistence / Test-Isolation / Architecture-Boundary / Dead-Code) | levnik ln-621/628/635/638/642/650/651 + doc § 6 P1 "Risk-triggered external lenses" |
| P0 | **TWO-LAYER-DETECTION-GAP.md** | Gap A above — formalize Layer 1 grep + Layer 2 context verify as Method rule. Small standalone doc OR fold into existing Method updates. | levnik audit_worker_core_contract.md |
| P1 | **PARALLEL-CRITIC-ARTIFACT-CONTRACT-GAP.md** | Gap D above — split JSON summary + MD evidence per critic. Schema sketch + lifecycle. Pairs with CRITIC-INDEPENDENCE Gap B + SCHEMA Gap 3. | levnik audit_summary_contract.md + audit_final_report_contract.md |
| P2 | **DOMAIN-AWARE-SCANNING-GAP.md** | Gap E above — `domain_mode + current_domain + scan_path` for multi-domain monorepos. Defer until user demand. | levnik audit_worker_core_contract.md |

## Adoption order (across this delta)

1. **Gap A (two-layer detection rule)** — single Method.md edit + one canon entry; immediate noise-reduction win
2. **Gap B (severity-anchor mapping comment)** — one-line canon comment for external-consumer mapping
3. **Gap C (specialty-lens dispatch via triggers)** — biggest architectural win; closes doc § 6 P1 mechanism via levnik's pattern adapted to lens-style markdown packs
4. **Gap D (split-artifact contract)** — defer until CRITIC-INDEPENDENCE Gap B (parallel critic mode) lands; ships together
5. **Gap E (domain-aware)** — defer indefinitely
6. **Gap F (penalty scoring)** — document as path NOT taken; informs future thinking on metric-worship critique

## What this means for the metric-worship critique

Earlier research (`RESEARCH-DELTA.md`) flagged contest-refactor's 9.5+ scoring as metric-worship vulnerable. Levnik's penalty formula is a working counter-example: deterministic, falsifiable per-finding, no anchor drift. Contest-refactor stays with qualitative anchors for good reasons (per-dimension rubric judgments resist gaming better than aggregable counts), but:

- Two-layer detection (Gap A) directly mitigates anchor drift at finding-emit time
- Specialty-lens dispatch (Gap C) decomposes scoring noise into discrete domain-specific verdicts (concurrency, security, persistence, etc.), each with its own anchors
- Per-worker scoring would conflict with contest-refactor's single composite scorecard

Result: adopt Gap A + Gap C to harden against metric-worship without surrendering qualitative anchors. Document Gap F (penalty formula) as deliberately-not-adopted with reasoning.
