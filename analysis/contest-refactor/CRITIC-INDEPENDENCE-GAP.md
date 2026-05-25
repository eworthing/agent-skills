# Critic Independence Gap — contest-refactor vs P0 competitors

Compares `contest-refactor`'s Critic Phase (`SKILL.md` Step 1 + `references/trust-model.md` Loop Isolation) against:

- **Open Code Review** (`refs/competitors/open-code-review/`) — 28 sealed personas + Tech Lead synthesizer + Discourse phase
- **Anthropic code-review plugin** (`refs/competitors/anthropic-claude-code/plugins/code-review/`) — 4 parallel critics + per-issue validator subagent

## Baseline: contest-refactor today

- **Single Critic role.** Step 1 runs the 10-step Method, produces `CURRENT_REVIEW.json` findings + backlog.
- **Critic + Actor share one subagent context.** Step 1 (Critic) → Step 2 (Architect) → Step 3 (Execution) execute as one unit inside the same loop subagent.
- **Cross-loop isolation only.** Each loop spawns fresh subagent reading only persisted artifacts — loop N+1's Critic can't see loop N's Actor reasoning, but within loop N there's no boundary.
- **Trust Model isolates payload from instruction** (prompt-injection guard), not Critic from Actor.
- **Validation hard gates G1–G31** catch schema/evidence violations post-hoc; they don't enforce Critic blindness to Actor's plan.

This violates the doc's P0 ask verbatim: *"Critics produce findings before seeing the Actor plan."*

## Gap matrix

Legend: **✓** = present, **partial** = weaker form, **—** = absent, **n/a** = not applicable (e.g., advisory tool has no Actor).

| Mechanism | contest-refactor | Open Code Review | Anthropic code-review |
|---|:--:|:--:|:--:|
| Multiple parallel critics | — (1 Critic) | ✓ 28 personas, configurable subset | ✓ 4 critics (2× CLAUDE.md, 1× bug, 1× logic/security) |
| Sealed input (no peer findings pre-emit) | n/a | ✓ explicit — each persona's subagent gets only persona + standards + diff | ✓ via subagent isolation |
| Redundancy on same lens | — | ✓ `--redundancy` flag (e.g., `principal-1`, `principal-2`) | ✓ 2× Sonnet CLAUDE.md auditors run in parallel |
| Persona library | — (Critic is monolithic) | ✓ 28 named (Principal, Security, Mozart…Beck/Fowler/Hickey/Metz/Ousterhout) | partial (4 implicit roles, not named) |
| **Critic blind to Actor plan within a loop** | **—** | n/a (advisory only) | n/a (advisory only) |
| Discourse / debate phase | — | ✓ Phase 6: AGREE / CHALLENGE / CONNECT / SURFACE | — |
| Confidence adjusted by peer review | — | ✓ AGREE +1, CHALLENGE undefended −1 | partial (validator binary pass/fail at ≥80) |
| Validator with rejection authority | partial (`validate-artifact.py` schema gates, not logic) | partial (Tech Lead synthesis) | ✓ per-issue validator subagent, sees only issue desc + PR context |
| Dedup rule | — | ✓ Synthesis Phase 7 dedupes across reviewers | partial ("post ONE comment per unique issue" enforced in Step 9) |
| Synthesizer cannot override blockers | n/a | ✓ Tech Lead synthesizes but one reviewer-blocker stands | n/a |

## Strategic insight

Open Code Review and Anthropic are both **advisory** — they have no Actor, so "Critic blind to Actor" is trivially satisfied (Actor doesn't exist). They demonstrate critic-vs-critic independence (multiple parallel reviewers), not Critic-vs-Actor independence.

Contest-refactor's gap is the **Critic-vs-Actor** version, which neither competitor solves. The mechanisms are still importable, but the Actor-Critic boundary is contest-refactor's own to design and cannot be waved away as "Anthropic already proved it." A missed comparator worth folding into the final pass is `levnik-skills`, whose multi-model review / critical-verification workflow is closer to contest-refactor's host-vs-reviewer split than either of the two sampled P0 repos.

## P0 GAPS — what to fix

### Gap A (highest priority): Critic-Actor subagent split within a loop

Currently one subagent runs Critic → Architect → Execution. The Critic can preemptively soften findings knowing the same context window will have to fix them; the Actor can rationalize past inconvenient findings because both share the same reasoning trace.

**Fix:** split the loop subagent boundary. Loop N becomes two subagents:

1. **Critic subagent** — runs Step 1 only. Reads source + prior `CURRENT_REVIEW.json`. Writes new `CURRENT_REVIEW.json` + system flag. Returns terse routing JSON to main (no Actor context generated).
2. **Actor subagent** — runs Step 2 + Step 3. Reads only the just-written `CURRENT_REVIEW.json` (no Critic reasoning trace). Selects priority-1, plans, executes, commits.

Cost is higher than "one extra Agent call." This changes loop routing, restart semantics, and the trust boundary between emitted findings and later execution. To make the split real rather than cosmetic, the handoff must also be **immutable**:

- main agent records a `findings_hash` (or equivalent immutable digest) when the Critic phase emits
- Actor may append `loop_result` / review data but must not rewrite `findings[]`
- post-Actor validation compares the digest before accepting the loop

Benefit: Critic cannot anticipate Actor's plan; Actor cannot re-litigate Critic's findings because only the persisted artifact survives the boundary.

Schema implication: the existing prompt template in `references/trust-model.md` already serializes state via files, but the split is **not** just a docs tweak. It needs routing/orchestration changes plus an immutable handoff check.

### Gap B: Parallel critic mode (the doc's P1 elevated)

Doc § 6 P1 already calls for parallel-critic mode — Architecture / Bug-regression / Test / Security / Local-conventions / Anti-theater critics running in parallel. Both competitors prove the pattern works.

**Adopt sealed-input dispatch verbatim from Open Code Review:** each critic subagent receives only

- Its lens definition (`references/lens-<name>.md`)
- Project standards (`CONTEXT.md`, `docs/adr/`, prior `findings_registry.json`)
- Source on disk (it explores freely)
- **NOT** other critics' draft output

Plus dedup metadata fields already reserved in Schema Gap Analysis (`critic_source`, `merged_into`, `also_known_as`, `locations`).

### Gap C: Validator subagent that can reject Critic findings

Anthropic's validator subagent is the cleanest pattern: per-finding, sees only the finding description + minimal context, scores confidence, rejects below threshold. Contest-refactor's `validate-artifact.py` is structurally similar (catches G1–G31 violations) but operates on schema/evidence presence, not on whether the *finding itself* is well-founded.

**Adopt as second-stage validation on Critic emit:** after Critic writes `CURRENT_REVIEW.json`, spawn one validator subagent per finding (parallel). Each gets only:

- The single finding (title, evidence[], why_weakens_submission, severity)
- Source files cited in `evidence[]` (read-only, narrow)
- The rubric anchor for the claimed severity
- The single question: "Does the evidence support the claim at this severity?"

Validator returns one of: `confirmed` | `downgrade_severity:<level>` | `reject:<reason>`. Critic subagent re-emits with validator output applied. Pairs naturally with the Schema Gap doc's recommended `confidence` and `severity_rationale` fields.

This logic belongs in a **validator subagent**, not in `validate-artifact.py`. The Python validator can confirm that the validator output was recorded; it cannot prove the semantic judgment itself.

### Gap D (defer): Discourse phase

Open Code Review's Discourse phase (AGREE/CHALLENGE/CONNECT/SURFACE with confidence math) is over-engineered for single-loop runs. But it's a natural escalation for **high-stakes findings only**: any `Likely disqualifier` (highest severity) could require a second critic's AGREE before passing to Actor. Smaller surface, same independence benefit.

Defer until parallel-critic mode (Gap B) ships; until then there's only one critic to AGREE with.

### Gap E (adopt now, free): Synthesizer-cannot-override-blockers rule

Open Code Review's hard rule — "Tech Lead synthesizes but does NOT override blockers; one reviewer blocking = must change" — has a clean contest-refactor analog: the **Actor cannot drop a `Likely disqualifier` finding from the backlog or downgrade its severity**. Only the Critic (next loop) can mark it `rejected_attempt` after evidence diagnosis.

This is a Step 2 routing rule plus a handoff invariant. Do **not** assign it to `validate-artifact.py` unless the artifact first gains the structured data needed to prove who changed what.

## What NOT to import

| Tempting | Why skip |
|---|---|
| All 28 OCR personas | Persona explosion = token bonfire. Pick 4-6 lenses tied to the rubric: architecture, concurrency, state-ownership, tests, local-conventions, anti-theater. Skip name-personas (Beck/Fowler/etc.) — they encode taste; contest-refactor encodes rules. |
| OCR's Discourse phase as default | Two reviewer rounds + structured response types per loop. Too expensive for routine findings. Gate to `Likely disqualifier` only (Gap D). |
| Anthropic's redundant-critic pattern (2× same lens) | Diminishing returns when critic-lens definitions are well-bounded. Useful only when critic output is noisy; contest-refactor's `test_failed` taxonomy already constrains output. |
| Validator that sees full source context | Anthropic's validator deliberately gets only issue desc + PR context, not full code. This forces the validator to question the finding's self-sufficiency. Contest-refactor's validator should do the same: read only `evidence[]` cited files, not the whole repo. |
| Confidence math from peer agreement (OCR AGREE +1 / CHALLENGE -1) | Only meaningful when multiple critics overlap on the same finding. Adopt at Gap B (parallel critics), not before. |

## Recommended adoption order

1. **Gap A (Critic-Actor subagent split + immutable handoff)** — single biggest independence win.
2. **Gap C (Validator subagent per finding)** — semantic rejection belongs here; also unlocks HALT `critic_unfounded`.
3. **Gap E (Actor-cannot-drop-blocker rule)** — add after the split so the boundary is enforceable.
4. **Gap B (Parallel critic mode)** — biggest lift; requires lens splits + dedup metadata fields + sealed-input dispatch.
5. **Gap D (Discourse for `Likely disqualifier` only)** — defer until Gap B lands.

## Minimal SKILL.md changes for Gap A (the immediate win)

Today `references/trust-model.md § Loop Isolation` says each loop runs Step 1+2+3 as one subagent. Change to:

> Each loop after Step 0 runs as **two sequential subagent invocations**:
>
> 1. **Critic subagent** — runs Step 1 only. Subagent prompt template loads `SKILL.md`, `CURRENT_REVIEW.md` (prior loop), `REVIEW_HISTORY.md` tail, selected lens. Emits new `CURRENT_REVIEW.json` and returns routing JSON (system flag + priority_1 stable_id + scorecard deltas). No Architect/Execution context generated.
> 2. **Actor subagent** — runs Steps 2 + 3 only, dispatched by main if and only if Critic returned `system_flag == CONTINUE` and backlog non-empty. Subagent prompt template loads `SKILL.md`, the just-written `CURRENT_REVIEW.json`, `LOOP_STATE.json` (for checkpoint-resume). Plans, executes, commits, returns loop_result routing JSON.
>
> Main agent records a `findings_hash` (or equivalent immutable digest) immediately after Critic emit. The Actor may append `loop_result` / review metadata but may not rewrite `findings[]`; post-Actor validation compares the digest before accepting the loop.
>
> The boundary forces Actor to reason from the persisted artifact only — same way loop N+1's Critic already does. Critic cannot pre-soften findings knowing it will fix them; Actor cannot re-litigate findings in shared context.

Do **not** make this a plain artifact gate in `validate-artifact.py`; the validator cannot see dispatch history. If contest-refactor wants an audit trail, record dispatch metadata in `LOOP_STATE.json` (or equivalent routing state) and enforce it in the main-agent orchestration layer.
