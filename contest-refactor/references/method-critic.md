# Critic Method — convergence passes + guardrails (Step 1, Critic only)

The Residual Accounting Pass, the Adversarial Pass on Accepted Residuals, and the State/Domain, Concurrency, and Test guardrails. Used by the **Critic** (Step 1, Method step 10) to decide HALT vs CONTINUE and to guard scoring. Carved out of [method.md](method.md) so the Step-3 implementation reviewer — which checks a diff against the Simplify Pressure Test + Evidence Chain + Meta-Rule 4 (all kept in [method.md](method.md)) and does **not** converge or score — does not carry it. The Critic reads both files per the `SKILL.md` Reference Load Matrix.

## Residual Accounting Pass

Run this after candidate findings are accepted, rejected, or downgraded, and
before choosing `HALT_SUCCESS`, `HALT_STAGNATION`, or `HALT_LOOP_CAP`. The cap is a
terminal too: when the loop ends with an empty backlog and any sub-9.5 dimension, run
this pass before emitting `HALT_LOOP_CAP`, exactly as for `no_backlog` (enforced by G37).

For each score below 9.5:

1. Ask whether the dimension's 9-anchor is met in current source.
2. If the 9-anchor is met, account for every remaining source-backed candidate:
   - Noticeable-or-worse and passes Simplify Pressure Test -> add to Improvement Backlog; state is `CONTINUE`.
   - Requires product or ownership decision -> halt as `HALT_STAGNATION` subtype `user_decision`.
   - **Context-sufficiency cap:** 9.5+ for the dimension genuinely turns on a business / regulatory / consistency rule that is absent from `CONTEXT.md` / ADRs and not derivable from source (e.g. may a compliance audit entry be written eventually vs transactionally; must two entities be strongly consistent) -> do **not** certify 9.5+ on the Actor's disclosure of the tradeoff alone. Cap below 9.5 with the missing rule named as the blocker and demanded as evidence; halt `user_decision` if it blocks the top structural finding. Source-determinable choices are exempt — a derived, rebuildable read model is correctly eventually consistent, an aggregate's internal writes are atomic by definition; capping those for missing context is over-reach. (Mirrors the _Context-sufficiency cap_ in [architecture-rubric.md](architecture-rubric.md).)
   - Cosmetic for contest, ADR-carved-out, framework-constrained, or fails Simplify Pressure Test because every fix adds ceremony -> set score to 9.5 with `residual_disposition: "accepted"` and include the rationale.
   - No source-backed residual can be named -> set score to 10.
3. If the 9-anchor is not met, keep the lower score only when the scorecard or
   `unresolved_reason` names the source-backed blocker and explains why the loop
   cannot turn it into a valid backlog item. At a converged empty-backlog terminal
   (`no_backlog` or `HALT_LOOP_CAP` with empty backlog) tag that dimension
   `residual_blocker_kind: "structural_anchor_unmet"` — the only kind that licenses a
   sub-9.5 score there. The step-2 promotion reasons (ceremony / framework-constrained /
   cosmetic / ADR-carved-out) are NOT legal sub-9.5 blockers: citing one keeps the
   dimension below 9.5 illegitimately and is rejected by **G37**; promote to 9.5-accepted instead.

Do not emit `HALT_STAGNATION` subtype `no_backlog` just because rejected
candidates were not backlog-worthy. Rejected candidates still affect terminal
scoring: either they are accepted residuals, they prove a real sub-9.5 blocker,
or they are not residuals and the score moves to 10.

## Adversarial Pass on Accepted Residuals

Run this pass after Residual Accounting Pass completes, before choosing a HALT state, on every loop where at least one dimension scored 9.5 with `residual_disposition: "accepted"`. Purpose: re-test whether an accepted residual still earns its acceptance against current source, or whether a cheap structural fix now exists that the original disposition missed.

For each `residual_disposition: "accepted"` entry:

1. Propose the **smallest possible structural fix** for the residual. Default to subtractive (per Meta-Rule 5). If no subtractive fix exists, propose the smallest additive fix. Cite the proposed fix in concrete terms (delete `X`, inline `Y`, replace `Z` with the existing `W`).
2. Run the proposed fix through the Simplify Pressure Test (5 questions + structural gate) below.
3. **If SPT passes** (all 5 questions answer "yes" AND structural gate passes): the residual was incorrectly accepted. Re-open as a Noticeable-or-worse finding. Use the proposed fix as the evidence chain's remedy. Either move the dimension score below 9.5 OR keep at 9.5 and route the finding to the Improvement Backlog (per the Residual Accounting Pass branches above).
4. **If SPT fails on any question**: the disposition still earned. Note the rejection in the residual rationale as `SPT-rejected on Qn: <one-line reason>`. Score holds.

**Bar discipline**: the target set is bounded — accepted residuals only, not the whole codebase. This is bar-raising against `9.5 + accepted residual` complacency, not finding-fishing. The SPT itself is unchanged; the fake-clean anti-examples in [Simplify Pressure Test (Step 2 gate)](#simplify-pressure-test-step-2-gate) still reject ceremony fixes. A residual that resists a subtractive fix because every alternative adds a costume layer is correctly accepted; the rationale must say so.

**Oscillation guard**: any finding re-opened by the Adversarial Pass still flows through Step 1.5 registry lookup AND Step 1.6 retirement rules. If the same `stable_id` was previously surfaced via Adversarial Pass and resolved/rejected, Branch A (3-way hash equality) or Branch B (2-way hash equality with intervening `resolved`) will retire it as `unresolvable`, blocking infinite re-open / re-accept cycles. The Adversarial Pass does not bypass G30 retirement precedence.

**Loop 1 exempt** when no prior `residual_disposition: "accepted"` exists in `findings_registry.json` or this loop's draft scorecard. Otherwise applies every loop.


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
