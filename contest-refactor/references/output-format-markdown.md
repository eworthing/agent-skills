# Output Format — Markdown structure

Section schema for `CURRENT_REVIEW.md` (per-loop human-readable review file) and the compression rules applied when archiving completed loops to `REVIEW_HISTORY.md`.

JSON mirror schemas (`CURRENT_REVIEW.json`, `REVIEW_HISTORY.json`, `findings_registry.json`, `LOOP_STATE.json`, `halt_handoff`, `re_validation_context`, Per-Loop Progress Line Format, Deepening Keywords, Fuzzy-match rules, Schema version 3 changelog) live in [output-format-json.md](output-format-json.md). The artifact index is [output-format.md](output-format.md).

## Contents

- [CURRENT_REVIEW.md Structure](#current_reviewmd-structure) — full template: Discovery, Loop Counter, System Flag, Contest Verdict, Scorecard, Authority Map, Strengths, Findings, Simplification Check, Improvement Backlog, Deepening Candidates, Builder Notes, Final Judge Narrative, Loop N Result.
- [Per-loop archive format (PR 5, schema_version >= 2)](#per-loop-archive-format-pr-5-schema_version--2)

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
When emitting `HALT_STAGNATION/no_backlog` or a converged `HALT_LOOP_CAP` (empty backlog), every score below 9.5 must also name
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

Findings produced here must follow The Evidence Chain from `method.md`: Claim → Source → Consequence → Remedy. Claim = `Title` + `Why it matters` + `What is wrong`. Source = `Evidence`. Consequence = `Why this weakens submission`. Remedy = `Minimal correction path`.

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

## Retired Findings (this loop)
Emit one line per finding whose `status` transitioned to `unresolvable` per [method.md § Step 1.6](method.md). Format:

**Retired finding:** F-007 marked `unresolvable` after rejected attempts in loops 3 and 5. Continuing with 4 eligible backlog items.

If no retirement transitions this loop, omit the section. The same template is rendered in the user-facing handoff per [halt-handoff.md § Retirement precedence](halt-handoff.md).
```

## Per-loop archive format (PR 5, schema_version >= 2)

Moved to [output-format-markdown-archive.md](output-format-markdown-archive.md#per-loop-archive-format-pr-5-schema_version--2) — Step 3 step 9 (archive write) only; kept off the investigation path.
