# Phase Context Isolation Gap — contest-refactor inter-phase context discipline

> **CURRENT-STATE (2026-06-28):** DEFERRED — subagent-per-loop already isolates each loop; `context:fork` per-phase is P2, measure-first. See [`GAP-AUDIT-AND-IMPROVEMENT-PLAN-2026-06-28.md`](GAP-AUDIT-AND-IMPROVEMENT-PLAN-2026-06-28.md) for the source-verified audit.

Source: `refs/competitors/alirezarezvani-claude-skills/` (16.1k★, MIT, added 2026-05-25 p.m.) — `context: fork` inter-skill contract. Parent skill invokes sub-skill with YAML frontmatter `context: fork` → fresh forked context → returns ≤200-word digest → parent never sees child's ingestion artifacts. Eliminates cross-skill context pollution.

Also referenced in: HALT-STATE-GAP Gap G (Validator-phase fork only; this doc treats the full phase-context-isolation question).

## Baseline: contest-refactor today

Per `references/method.md` + STATE-MACHINE-COMPOSITION-APPENDIX, contest-refactor's loop runs the following phases sequentially in the SAME main-agent context:

| Phase | Owner | Inputs | Outputs | Currently shares context? |
|---|---|---|---|---|
| Step 0 Context Discovery | main agent (first loop only) | CWD scan | `discovery{...}` | ✓ |
| Step 1 Critic Phase 1.0 | main agent (per CRITIC-INDEPENDENCE Gap A could become subagent) | source files, discovery, governance_context | `CURRENT_REVIEW.findings[]` | ✓ |
| Phase 1.1 Validator | NEW per SCHEMA-GAP Gap C — subagent | Critic emit | trim decisions | depends on adoption |
| Phase 1.2 Cross-Model Critic | NEW per CROSS-MODEL-CRITIC Gap A — external provider subprocess (Codex stdin) | Critic emit + source | adversarial findings | ✗ external subprocess (effectively forked) |
| Phase 1.25 State recompute | main agent | merged findings | recomputed score | ✓ |
| Phase 1.3 Clean-Env Revalidation | NEW per CLEAN-ENVIRONMENT-VALIDATION-GAP — worktree subprocess | candidate HALT_SUCCESS state | revalidation result | ✗ worktree subprocess (effectively forked) |
| Phase 1.4 Routing | main agent | final review state | next-step decision | ✓ |
| Phase 1.5 Cross-Model Scoring | NEW per CROSS-MODEL-CRITIC Gap E — external SDK subprocess (Gemini Flash) | candidate HALT_SUCCESS | score 1-10 | ✗ external subprocess (effectively forked) |
| Step 2 Architect Phase | main agent | findings → backlog | Architect plan | ✓ |
| Step 3 Implementation | main agent (per CRITIC-INDEPENDENCE Gap A could become Actor subagent) | Architect plan | code edits + commit | ✓ |
| Step 3.6 Implementation Review | subagent (per current method.md) | code edits + Architect plan | accept/reject verdict | ✗ subagent (already forked) |
| Step 12 Loop dispatch | main agent | LOOP_STATE | next-loop or HALT | ✓ |

**Current state**: 5 of 12 phases run in main-agent shared context. 4 of 12 run in subprocess / subagent (effectively forked). 3 of 12 are NEW per recent gap docs (Validator / Cross-Model Critic / Cross-Model Scoring) and their context-scope is design choice.

## alirezarezvani's mechanism

YAML frontmatter declaration:

```yaml
---
name: vendor-management
context: fork
skills: [process-mapper, vendor-management, capacity-planner, ...]
---
```

Effects when invoked:
1. Parent context window NOT extended with vendor-management's reasoning
2. Vendor-management gets FRESH context with the parent's invocation prompt only
3. Vendor-management runs ingestion (file reads, Python tool invocations, reference loads)
4. Returns ≤200-word digest (terse summary) to parent
5. Parent receives digest only; ingestion artifacts never enter parent's context

**Implementation underneath**: subagent dispatch (same as Claude Code's Task tool). The `context: fork` declaration is sugar over subagent semantics.

## Gap matrix

Legend: **✓** = present, **partial** = weaker form, **—** = absent.

| Phase | Current context-mode | Optimal context-mode | Reason | Adopt fork? |
|---|---|---|---|---|
| Step 0 Discovery | shared | shared | Discovery output feeds entire loop; forking loses transparency | NO |
| Step 1 Critic 1.0 | shared (proposed subagent split per CRITIC-INDEPENDENCE Gap A) | shared (Critic IS the analysis) | Forking Critic loses iterative reasoning context | NO |
| Phase 1.1 Validator | shared (proposed) | **forked** | Validator should ONLY see Critic emit (file paths + findings JSON), NOT Critic's chain-of-thought; eliminates Critic-bias contamination | **YES** |
| Phase 1.2 Cross-Model Critic | forked (subprocess) | forked | Already effective; external provider can't access main context | n/a (already forked) |
| Phase 1.25 State recompute | shared | shared | Mechanical merge; no judgment | NO |
| Phase 1.3 Clean-Env Revalidation | forked (worktree subprocess) | forked | Worktree IS isolated by definition | n/a |
| Phase 1.4 Routing | shared | shared | Needs cumulative state to route | NO |
| Phase 1.5 Cross-Model Scoring | forked (SDK subprocess) | forked | External provider | n/a |
| Step 2 Architect | shared | shared | Architect uses cumulative finding state | NO |
| Step 3 Implementation | shared (proposed Actor subagent per CRITIC-INDEPENDENCE Gap A) | shared via Actor subagent | Actor SHOULD share Architect's plan; subagent already isolates from Critic | NO (Actor subagent ≠ forked context) |
| Step 3.6 Implementation Review | subagent | subagent | Already isolated from main reasoning | n/a |
| Step 12 Loop dispatch | shared | shared | Loop-state cumulative | NO |

## Strategic insight

**Most phases are CORRECTLY shared-context already.** Forking everything would break the loop's coherent reasoning chain. The places forking PAYS are:

1. **Phase 1.1 Validator** — Validator's job is to scrutinize Critic's emit independently. If Validator sees Critic's chain-of-thought, it inherits Critic's biases. Forked context → Validator gets only the structured emit + source → checks independently.

2. **Phase 1.2 Cross-Model Critic** — already forked (subprocess).

3. **Phase 1.3 Clean-Env Revalidation** — already forked (worktree).

4. **Phase 1.5 Cross-Model Scoring** — already forked (SDK).

So the ONLY new fork-candidate is **Phase 1.1 Validator** (Gap G in HALT-STATE-GAP).

The other potential candidate, **Phase 1.0 Critic if split into subagent per CRITIC-INDEPENDENCE Gap A**, should NOT be forked. The Critic IS the loop's analysis engine; isolating it from Discovery + cumulative findings_registry context would lose loop-spanning awareness.

## P2 GAPS — what to potentially adopt

### Gap A: `context: fork` for Phase 1.1 Validator subagent (HALT-STATE Gap G)

Per HALT-STATE-GAP Gap G: Validator subagent receives ONLY the Critic emit (file paths + findings JSON) + source files — NOT the Critic's chain-of-thought. Validator emits trim decisions → parent receives JSON digest only.

**Implementation**: Validator dispatched via `Agent` tool with explicit context-cap directive in prompt:
```
You are the Validator subagent for contest-refactor Phase 1.1. You receive:
1. Critic emit (CURRENT_REVIEW.findings[]) — JSON only
2. Source files at evidence_paths[]

You do NOT receive:
- Critic's reasoning steps
- Discovery / governance context (request via Read if needed)
- Previous loop's findings_registry

Output: per-finding trim decision { finding_id, decision: "keep" | "trim", trim_reason? } + brief rationale (≤200 words total).
```

**Cost**: per-loop subagent spawn = +2-5s. Critic-Validator independence gain may justify; measure first.

### Gap B: `context: fork` for Implementation Reviewer (Step 3.6)

Today Implementation Reviewer subagent already runs forked (subagent dispatch). Verify the prompt explicitly excludes Critic's reasoning steps. If currently inherits cumulative loop context, add explicit context-cap directive. Low-effort hardening.

### Gap C: Don't fork the rest

Discovery, Critic 1.0, State recompute, Routing, Architect, Step 3 Actor, Step 12 dispatch — all NEED cumulative loop context. Forking would degrade quality.

**Hard rule**: only fork phases whose JOB is independent verification (Validator). Never fork phases whose job is cumulative-state reasoning (Critic, Architect, Actor).

## What NOT to import

| Tempting | Why skip |
|---|---|
| Fork every phase for "maximum isolation" | Loses iterative reasoning. Contest-refactor's strength is loop-spanning awareness; forking everything regresses to stateless analysis. |
| alirezarezvani's 200-word digest cap | Contest-refactor's CURRENT_REVIEW.json digest is structured JSON, not natural-language. The 200-word convention is for English summaries; JSON has different optimal verbosity. |
| `context: fork` declaration in SKILL.md frontmatter | contest-refactor is a single SKILL.md (not skill-of-skills); the YAML declaration mechanism doesn't apply. Subagent dispatch via Agent tool achieves equivalent. |
| Forking for Critic-Actor split per CRITIC-INDEPENDENCE Gap A | Already addressed by subagent dispatch (subagent != forked context). Critic subagent inherits relevant cumulative state; Actor subagent inherits Architect plan. Both NEED shared loop awareness within their role. |

## Adoption order

1. **Gap A (Validator fork)** — pairs with HALT-STATE Gap G + SCHEMA-GAP Gap C. Ships when Validator subagent ships.
2. **Gap B (Implementation Reviewer fork-hardening)** — verify Step 3.6 prompt explicitly excludes Critic reasoning. Low-effort.

## Pairing with other gap docs

- **HALT-STATE-GAP Gap G**: this doc's Gap A IS HALT-STATE Gap G — same recommendation, fuller context here.
- **SCHEMA-GAP Gap C** (Validator subagent): blocked-on dependency. Gap A in this doc requires Validator to exist first.
- **CRITIC-INDEPENDENCE-GAP Gap A** (Critic+Actor subagent split): related but distinct. Critic+Actor split = role separation (different prompts, different responsibilities). Context fork = context isolation (same subagent dispatch mechanism but explicit context-cap in prompt). Both can coexist; do not conflate.
- **STATE-MACHINE-COMPOSITION-APPENDIX**: documents the phase sequencing; this doc adds context-mode column.
