# Critic Method

Ordered investigation method, meta-rules, simplify pressure test, evidence discipline. Used by Step 1 (Critic) of the loop.

## Meta-Rules (apply everywhere)

1. **Metrics support judgment; they never decide it.** Tool output (SwiftLint, Taylor, xccov, TSAN, compiler diagnostics, grep counts) is evidence to investigate. Not a verdict. Every metric-backed finding must trace metric → source → behavior.
2. **Counts are not quality.** Actor count, async count, EnvironmentObject count, @Observable count, Preview count, test count, coverage percent do not score by themselves. Judge where the construct lives and whether it earns its keep.
3. **Do not recommend a new Seam until friction is proven.** Prove friction first with source evidence: callers bounce across tiny modules, tests cannot stay at the current Interface, deletion tests show pass-through wrappers, seams leak, or seams misplaced.
4. **Recommended fixes must preserve user-visible behavior.** Fixes may make undefined race outcomes deterministic, but must not change intended product behavior unless the existing behavior is itself a finding in this review.
5. **Prefer subtractive fixes.** Remove ceremony, duplicate authority, dead paths, pass-through Modules, shallow abstractions before adding new structure.
6. **Honesty beats polish.** Do not reward architecture names, folders, doc comments, or test counts unless ownership, seams, runtime authority, regression resistance survive source inspection.
7. **Teach only where it improves the repair path.** When a fix depends on stack-specific behavior (SwiftUI, SwiftData, actor isolation, async Task lifetime, navigation, dependency injection, persistence seams), briefly explain the underlying rule in plain language. Do not turn the review into a tutorial. Do not soften the contest judgment.

## Method (10 steps, in order)

1. **Inspect current code only.** Older reviews are historical claims; require current source proof.
1.5. **Registry lookup (schema_version >= 2 only).** For each candidate finding, fuzzy-match against `findings_registry.json` per the rules in [output-format.md § Fuzzy-match rules](output-format.md). Match → reuse `stable_id`, prepare to append occurrence stub `{loop: N, loop_local_id: "F<n>", status: "open"}`. No match → reserve `F-{registry.next_serial}`, increment after loop emit. Ambiguous match (2+ entries via M2, 0 via M1) → emit `open_question_for_user` in loop return JSON; halt at HALT_STAGNATION subtype `user_decision`. The loop subagent never writes `findings_registry.json` directly; carries updated registry in memory and writes to disk in Step 3 step 8.
2. **Map mutable runtime concerns.** For each: owner, allowed writers, readers, persistence seam, async mutation entry points, clear or ambiguous authority.
3. **Review architecture.** Module graph, Seams, Adapter variation, costume layers, Repository theater, Protocol soup.
4. **Review ownership.** Map actual writers (do not infer from access control alone). Reducer-style shared state may be valid but must still have clear write rules.
5. **Review platform and concurrency.** Stack lens checklist (`lens-apple.md` / `lens-generic.md`). Actor isolation, task lifetime, cancellation, reentrancy, Sendable.
6. **Review simplification.** Identify ceremony, duplicate layers, fake simplifications, pass-through wrappers.
7. **Review hidden state machines.** Many booleans/optionals encoding one logical state, drifting flags, duplicated state across layers, navigation drift from domain state, invalid async combinations.
8. **Review tests and regressions.** Tests at real Interfaces, async tests without sleeps, failure paths, deterministic ordering, untested stateful Modules.
9. **Use metrics as supporting evidence.** Map every metric finding to source and behavior. Reject metric-only claims.
10. **Merge judgment.** Produce verdict, scorecard, findings, backlog, then run the Residual Accounting Pass below before choosing a HALT state.

## Residual Accounting Pass

Run this after candidate findings are accepted, rejected, or downgraded, and
before choosing `HALT_SUCCESS` or `HALT_STAGNATION`.

For each score below 9.5:

1. Ask whether the dimension's 9-anchor is met in current source.
2. If the 9-anchor is met, account for every remaining source-backed candidate:
   - Noticeable-or-worse and passes Simplify Pressure Test -> add to Improvement Backlog; state is `CONTINUE`.
   - Requires product or ownership decision -> halt as `HALT_STAGNATION` subtype `user_decision`.
   - Cosmetic for contest, ADR-carved-out, framework-constrained, or fails Simplify Pressure Test because every fix adds ceremony -> set score to 9.5 with `residual_disposition: "accepted"` and include the rationale.
   - No source-backed residual can be named -> set score to 10.
3. If the 9-anchor is not met, keep the lower score only when the scorecard or
   `unresolved_reason` names the source-backed blocker and explains why the loop
   cannot turn it into a valid backlog item.

Do not emit `HALT_STAGNATION` subtype `no_backlog` just because rejected
candidates were not backlog-worthy. Rejected candidates still affect terminal
scoring: either they are accepted residuals, they prove a real sub-9.5 blocker,
or they are not residuals and the score moves to 10.

## Friction Proof Before Seam Recommendation

Friction proof required before any new Seam. See [architecture-rubric.md § Unified Seam Policy](architecture-rubric.md#unified-seam-policy) for the acceptable proof list and the policy's two paths (two-adapter rule OR single-Adapter policy/failure/platform isolation). Without one of these, recommendation is rejected. Default to merging or inlining.

## Deepening Opportunity Test

Deepening opportunity exists only when the deletion test fails or callers/tests reach past the Interface. See [architecture-rubric.md § Architectural Tests](architecture-rubric.md#architectural-tests). If the fix is merely deleting a pass-through wrapper, call it simplification, not deepening.

## Simplify Pressure Test (Step 2 gate)

For every proposed fix, answer:

1. Does it fix real ambiguity?
2. Is it the smallest honest fix?
3. Does it avoid duplicate layers?
4. Does runtime behavior remain honest?
5. Does the product improve?

Plus the structural gate: Friction proven, Deletion test passes for any Module being removed, [Unified Seam Policy](architecture-rubric.md#unified-seam-policy) passes for any new Seam, Tests after the refactor live at the new Interface (per [Replace, don't layer](architecture-rubric.md#5-replace-dont-layer)).

Any "no" → downgrade to simpler truthful alternative or pick next backlog item. If a clean-looking fix adds ceremony without fixing ownership, failure behavior, or Locality, reject it.

## Evidence Discipline

Every major claim must show this chain:
- claim
- source evidence (file:line, symbol, type, method, property, call site, test name, lint output, metric output, sanitizer report)
- behavior or architectural harm
- score or backlog impact

If that chain cannot be shown, downgrade the claim to unresolved, scope-limited, or omit it.

Do not infer architecture quality from naming alone.
Do not generalize beyond evidence.
Do not output private scratchpad.

If scope is weak, label the claim:
- local finding
- drift hazard
- unresolved question
- scope-limited

## State / Domain Guardrails

- Many Bool or Optional fields are smoke. Confirm impossible combinations before making a finding.
- Reward explicit state only when needed. Do not force enums everywhere.
- Prefer small honest state models.

## Concurrency Guardrails

- High or low @MainActor / async / actor count is not itself a finding.
- Unstructured `Task` usage needs ownership proof.
- TSAN findings, compiler concurrency warnings, Non-Sendable warnings are serious evidence; map each to source and behavior.
- Treat unclear concurrency as architecture weakness.

## Test Guardrails

- Treat Interface as test surface.
- Coverage is proxy, not proof. High coverage can still be shallow. Low coverage can be acceptable glue.
- Absence of tests on stateful domain, reducer, persistence, networking, async runtime Modules is a serious regression-resistance concern. Name the untested Interface and explain why it should be testable.
- Flag sleeps, timing hacks, unowned time, randomness, UUIDs only when they harm determinism. Do not add injection ceremony without need.
