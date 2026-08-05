# Critic Method — convergence passes + guardrails (Step 1, Critic only)

The Backlog Prioritization Pass, the Stalled-Dimension Sweep, the Residual Accounting Pass, the Adversarial Pass on Accepted Residuals, and the Delta Derivation, State/Domain, Concurrency, and Test guardrails. Used by the **Critic** (Step 1, Method step 10) to decide HALT vs CONTINUE and to guard scoring. Carved out of [method.md](method.md) so the Step-3 implementation reviewer — which checks a diff against the Simplify Pressure Test + Evidence Chain + Meta-Rule 4 (all kept in [method.md](method.md)) and does **not** converge or score — does not carry it. The Critic reads both files per the `SKILL.md` Reference Load Matrix.

## Backlog Prioritization Pass

Run before the Residual Accounting Pass. It assigns `priority`, and nothing downstream
corrects it: the Step-2 tiebreak fires only on a *shared* priority, and the Actor takes
`priority: 1` verbatim.

Rank by **expected marginal contest gain**, not confidence of completion. The two
invert routinely — the cheapest, most certain item is usually the one on the dimension
already nearest target — and always taking it ratchets one dimension to 9.5 while the
rest stand still.

0. **Actionability.** An item blocked by a recorded user constraint or a product
   decision is not silently demoted: rank it on merit, and if it would be Priority 1,
   name the blocker in the accounting sentence and take the next actionable item.
   Escalate to `user_decision` only when it is the *sole* candidate — on a real
   15-loop run, halting at the first blocked top-rank fires at loop 4 and forfeits
   eleven loops of work. The failure to prevent is the opposite: carrying a blocked
   top-ranked item at Priority 2 for fifteen loops without ever naming it.
1. **Distance to target.** +0.5 at 5.5 buys progress toward an anchor; +0.5 at 9.0
   buys a residual. Not the same gain.
2. **Stall — at two granularities.**
   - *Dimension stall.* Consecutive prior loops with `delta != "UP"`, from
     `REVIEW_HISTORY.json`. A dimension unmoved for three or more loops is not being
     investigated, whatever its scorecard reason says. Break near-ties toward it.
   - *Item deferral.* Consecutive prior loops in which an item sat in the backlog and
     was not executed, from the registry's `occurrences[]` chain. An item deferred three
     or more times is telling you something, and it is one of exactly two things: either
     it is genuinely worth less than its position claims — in which case **drop it from
     the backlog and say why**, rather than carrying it as permanent furniture — or the
     ranking is being dominated by a renewable supply of higher-severity findings and the
     queue will never drain on its own. In the second case, break the tie toward the
     deferred item. Carry it or drop it; do not defer it indefinitely.

   Why this needs its own criterion: in a 10-loop run the same item was written as
   next-loop Priority 1 at loops 3-6 and overridden each time by a Serious finding that
   loop's own Step 1 had just turned up in one large file. Every override was defensible
   and every one was named in the accounting sentence — nothing was hidden. What was
   missing is escalation on repetition, so "correctly deferred" repeated until the file
   ran out of Serious findings. This is the cheap-win ratchet rotated: there one
   *dimension* always won, here one *severity tier* did. Neither is visible from inside
   a single loop, which is why it belongs in the pass that reads `REVIEW_HISTORY.json`.
3. **Severity** ([architecture-rubric.md § Severity Anchors](architecture-rubric.md#severity-anchors)).
4. **Honesty plus simplicity, then runtime safety** — at equal gain, subtractive beats
   additive (Meta-Rule 5).
5. **Anti-overengineering, then Leverage and Locality.**

Rank by distance, never by dimension identity: the same test-coverage item correctly
wins at 3.0 and correctly loses at 9.5.

**Priority-1 accounting** (one sentence, Builder Notes). Name the dimension Priority 1
moves and why no candidate further from target was available — the candidate you
rejected and the SPT question it failed, or that the sweep found none, or the blocker
under criterion 0. Accounting, not a quota: "the only `domain_modeling` candidate
fails SPT Q1" is complete. Priority 1 landing on the nearest-target dimension for
three consecutive loops without that sentence is the ratchet, and it is a defect in
this pass rather than in the individual choices, each of which was defensible.

## Stalled-Dimension Sweep

Run before the Residual Accounting Pass, from loop 4 on. Trigger: any dimension below
9.5 whose `delta` has been `SAME` for three or more loops. A dimension parked at 9.5
on an accepted residual is supposed to be still.

One Builder Notes line per triggered dimension — either **a named candidate**
(`file:line` plus the claim, emitted as a finding through the normal evidence chain,
so Builder Notes carries only the ID and G11 holds), or **an explicit clean** naming
the source surface you actually walked and why nothing on it passes the Simplify
Pressure Test. "Walked `Domain/` (7 types); every field that could carry a
construction-time invariant already does" is a clean; "nothing found" is fake-clean
reward.

Does NOT obligate net-new findings — coverage check, not finding-fishing; G3 evidence
chain still required. Same contract as [method.md Step 1.7](method.md#method-10-steps-in-order).
No quota, and a dimension whose ceiling is honest should collect the same clean every
loop. The output is a record of where the loop looked, so a `SAME` running ten loops
is either a decision someone made or a hole someone can see.

## Residual Accounting Pass

Run this after candidate findings are accepted, rejected, or downgraded, the
Backlog Prioritization Pass has assigned priority, the Stalled-Dimension Sweep has
run, and before choosing `HALT_SUCCESS`, `HALT_STAGNATION`, or `HALT_LOOP_CAP`. The cap is a
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


## Delta Derivation Guardrail

The anchor-to-source rule ([method.md](method.md) Step 1, G26) says re-derive each score
from current source rather than trusting the prior scorecard. Read it as binding on prior
loops' **reasoning patterns** too, not only their numbers.

A convention that emerges across loops — "we found a new instance of a known defect class,
so the dimension moves DOWN", or its mirror "we closed one, so it moves UP" — is a fact
about how recent loops argued, not a fact about current source, and it carries no authority
over your delta. Judge each dimension against its own anchor in
[architecture-rubric-scoring.md](architecture-rubric-scoring.md) as the code stands today
and let the delta fall out of that comparison. If your stated reason for a delta is
"consistent with what recent loops did", that is anchoring, not derivation.

This cuts both ways, and the correction is not to lean the other way. Do not over-correct
into UP to compensate for a run of DOWNs, or into DOWN because the scores look generous.
UP, SAME and DOWN each have to be reachable on their merits every loop.

Observed cost: one loop marked two dimensions DOWN on finding a deeper instance of a known
defect class — arguably right, and its own humility check conceded SAME was defensible. The
next two loops inherited that pattern instead of re-deriving, and the scorecard fell 2.0
points across three loops *while seven genuine race conditions were fixed and both gates
stayed green*. A scorecard that moves opposite to the source it is scoring has stopped
measuring the source.

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
