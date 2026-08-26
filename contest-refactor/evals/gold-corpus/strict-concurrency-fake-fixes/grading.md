# Grading — strict-concurrency-fake-fixes

Grader-only. Not shown to a candidate (see `provenance.json`'s
`grader_only_files`).

## This pack's gold is contested, not pristine

The real PR this pack is drawn from is accepted and merged, but its own
author opened a large, unmerged draft revert of it three weeks later
(see `provenance.json`'s `related_history`). That does not disprove the
accepted state -- a closed, unmerged draft is not a finding of
wrongness -- but a reviewer who is handed this history should treat the
accepted approach as **contested**, not as settled fact. Noting the real
annotations carry an ongoing cost, or that the approach was contested
from inside the project, is a fair and accurate reading. **Do not treat
that observation as a defect in this pack's judgment; it is exactly
correct.**

## What this pack is actually testing

Not "can the candidate spot an unprotected shared counter." That is
`unsynchronized-shared-state` and `mutant-unchecked-marker`, and both are
unmissable once you look at the actual result of a lost update. **The
real test is telling apart three different reasons a fix can be wrong,
and one reason it can be right, across four archetypes that all touch
the same two-line hazard:**

| archetype | correct reviewer behavior |
| --- | --- |
| unchecked-Sendable marker over mutable state | Reject unless a stated invariant **and** a synchronization mechanism both exist |
| blanket global-actor isolation | Reject if it changes execution topology or cascades isolation through unrelated APIs |
| unsafe opt-out on the stored property | Reject as diagnostic silencing unless a clear external invariant genuinely holds |
| a real synchronization primitive | **Accept** — it actually protects the shared state |

## Why nothing in this pack races for real

Every check here is fully deterministic. There is no `Task`, no thread,
no timing, anywhere in this pack. `scripted_interleaving_preserves_update`
observes a lost update by driving a fixed, scripted call sequence --
never by racing anything. Whether that sequence *can even be
constructed* against a given variant depends on what that variant's real
API exposes: `unsynchronized-shared-state`, `mutant-unchecked-marker`,
and `near-miss-unsafe-optout-with-claimed-invariant` all leave `count` at
ordinary access -- `nonisolated(unsafe)` opts out of isolation checking,
it does not restrict who can touch the property -- so the grader can read
it twice before writing it back twice on all three, reproducing exactly
what unsynchronized concurrent access would do. `guarded-value-container`
and `near-miss-blanket-global-isolation` make `count` unreachable except
through `increment()` (private in the first, actor-isolated in the
second) -- there the same adversarial sequence, translated into calls
against that variant's real shape, is just two calls to `increment()`,
which is what a correct caller would do anyway.

**This has one sharp consequence that full credit requires understanding:
`near-miss-unsafe-optout-with-claimed-invariant` fails
`scripted_interleaving_preserves_update` for exactly the same reason
`mutant-unchecked-marker` does -- the update is genuinely lost, honestly.
That is not what makes them different fixture roles.** What separates the
near-miss from the mutant is that the near-miss *claims* an invariant
("only mutated during setup") that would, if true, make the unsafe
opt-out legitimate -- and `claimed_invariant_actually_holds` shows the
claim is false. The mutant makes no such claim at all; there is nothing
for that oracle to check against it, and it passes vacuously.

## What full credit looks like, per variant

**unsynchronized-shared-state (RED). Accept it as a correct, if unsafe,
starting point.** Every ordinary call works; the hazard is what happens
under real concurrent access, which nothing here has been checked to
survive. `scripted_interleaving_preserves_update` demonstrates a genuine
lost update.

**guarded-value-container (GREEN). Accept it outright.** `count` is
private, and `increment()` performs its whole read-modify-write under one
lock acquisition. There is no way to split its read from its write from
outside the file -- confirmed structurally, not just narratively, by the
same oracle that catches the red and the mutant being unable to express
the attack here at all.

**near-miss-blanket-global-isolation (NEAR_MISS #1). Refuse it, and
refuse it on the right grounds.** The race is genuinely gone --
`scripted_interleaving_preserves_update` passes, honestly, because the fix
is real. **A reviewer who checks only "is the race gone" accepts this
variant, and that is the trap.** The correct refusal names
`unrelated_call_site_stays_callable`'s finding specifically: `statusLine()`
has nothing to do with concurrent access to `count`, and isolating the
whole type to a global actor swept it into the same isolation domain
anyway, turning a previously synchronous call site into one that now
requires actor isolation. **The wrong reasons to refuse this variant:**
"it's slower," "actors are overkill," or any objection that doesn't name
the specific unrelated API dragged along by the isolation.

**near-miss-unsafe-optout-with-claimed-invariant (NEAR_MISS #2). Refuse
it, and refuse it for a third, different reason.** Its comment claims
`count` is "only mutated during setup, before either call site can reach
it." `claimed_invariant_actually_holds` drives the second path
(`increment()`, the same operation both call sites use) after `setup()`
and observes the state change -- the claim is false. This variant also
fails `scripted_interleaving_preserves_update`, for the same structural
reason `mutant-unchecked-marker` does: `count` is plain and directly
reachable. **The required reasoning is naming the false invariant
specifically, not just "it's also racy like the mutant."** Collapsing
this near-miss into the mutant misses what a stated-but-checkable
invariant claim is supposed to teach: the work is verifying the specific
claim, not treating every unsafe annotation as equally unexamined.

**mutant-unchecked-marker (MUTANT).** A hard, unmissable Layer-5 case: it
is `unsynchronized-shared-state` with `@unchecked Sendable` added and
nothing else -- no lock, no actor, no invariant claim of any kind.
`scripted_interleaving_preserves_update` fails against it exactly as it
does against the red. A static read that notices the bare, mechanism-free
`@unchecked Sendable` is bonus credit, not required credit -- the
`must_find_if_present` entry scoped to this variant names it directly.

## Why one oracle never fails, and what it is instead

`ordinary_sequential_calls_are_recorded` is a **control**: two ordinary,
non-adversarial calls land correctly in every variant, including the
mutant, whose defect only shows up under the adversarial interleaving.
It would only fail if this fixture itself were broken in a way that made
the other three oracles' results meaningless.

`scripted_interleaving_preserves_update`, `unrelated_call_site_stays_callable`,
and `claimed_invariant_actually_holds` are this pack's three
discriminators. `scripted_interleaving_preserves_update` alone does not
separate `near-miss-unsafe-optout-with-claimed-invariant` from
`mutant-unchecked-marker` -- both fail it, honestly -- see
`oracles.py`'s module docstring for the full variant-to-expectation
mapping and its note on why that overlap is not a fixture defect: the
near-miss's distinguishing failure lives entirely in
`claimed_invariant_actually_holds`.

## Scoring guidance

- **Full credit** needs: `unsynchronized-shared-state` accepted as a
  correct starting point; `guarded-value-container` accepted outright;
  `near-miss-blanket-global-isolation` refused **specifically for
  cascading isolation to an unrelated API**, not for the race (which is
  genuinely gone); `near-miss-unsafe-optout-with-claimed-invariant`
  refused **specifically because the stated invariant is checked and
  found false**, not merely because it uses an unsafe annotation.
- **Partial credit:** either near-miss refused for a generic "this feels
  unsafe" instinct without naming its specific, checkable defect; the two
  near-misses treated as interchangeable ("both near-misses, both bad for
  the same reason").
- **No credit / active miss:** `near-miss-blanket-global-isolation`
  accepted because the race is gone; `near-miss-unsafe-optout-with-claimed-invariant`
  accepted because it states an invariant, without checking it;
  `mutant-unchecked-marker` treated as acceptable because it compiles
  without diagnostics; a global actor recommended as the general remedy
  for shared mutable state rather than one option with a real,
  named cost.
- `mutant-unchecked-marker` is graded by the hidden oracle
  (`scripted_interleaving_preserves_update`), not by reviewer narrative;
  do not penalize a candidate for missing the bare `@unchecked Sendable`
  in a static read unless they also assert with confidence that the
  counter is safe under concurrent access.
