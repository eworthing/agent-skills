# Grading — demand-signalling-state-machine

Grader-only. Not shown to a candidate (see `provenance.json`'s
`grader_only_files`).

## This pack is a restraint control, not a defect hunt

Every other pack in this corpus is built around a reviewer catching
something wrong. This one is built around a reviewer *not* catching
something that is not wrong. `demand-signalled-state-machine` (GREEN) is
the single most state-dense file in the pack, and it is also the correct,
accepted answer. An automated hotspot scanner is expected to nominate it —
six enum cases, several carrying their own bookkeeping — and the point of
this pack is whether the reviewer inspects that nomination and dismisses
it, or rubber-stamps it into a simplification finding. If a reviewer turns
this pack's GREEN into an automatic "too many states" or "flatten this"
recommendation, the scanner/critic pipeline has failed the exact case it
exists to guard against, independent of anything the near-miss or mutant
do.

## Why the coordinator is modelled as a pure step function, not real tasks

The real PR replaced a per-demand-task implementation with one coordinator
task per iterator, one child task per upstream, and a state machine
synchronizing continuation resumption and cancellation across all of them.
None of that is reproducible deterministically on this machine without
introducing genuine concurrency, and a flaky oracle is worse than no
oracle. So this fixture models the coordinator as `Relay`, a class whose
entire public surface is `step(_ event: RelayEvent) -> [RelayAction]`:
events are demand arriving, a source producing a value, a source
finishing, or cancellation; actions are "resume this request with this
value," "resume this request with a finish signal," or "start this
source's work." A pending continuation is represented purely as an
integer request id inside the returned action list — never as a real
Swift continuation — which is what makes "every pending continuation
resumed exactly once" a plain, countable, deterministic fact instead of a
race to reproduce. A reader should understand this substitution going in:
nothing here recovers real Swift concurrency, only the judgment structure
the real coordinator's state machine produces.

## What full credit looks like, per variant

**task-per-demand (RED). Accept it as a correct, if wasteful, starting
state.** Every demand it serves eventually resolves with the right value,
in the right order, and cancellation resumes exactly what is outstanding.
Its actual cost is narrow and real: every single demand restarts a fresh
unit of work for every source still in play, rather than reusing work an
earlier demand already started, and because that per-demand work reaches
into the relay's own shared state, the type has to carry a broad
concurrency-safety marker (`ConcurrencySafe`) it would not otherwise need.
Neither of those costs makes it broken. `oracles.py`'s
`no_per_demand_task_creation` is the direct, countable version of the
first cost — this variant's "start a source's work" count grows with the
number of demands served, where every other variant's count stays flat at
one.

**demand-signalled-state-machine (GREEN). Accept it outright, and accept
its density as the point, not a cost to be justified away.** Its `Phase`
enum has six cases because it is tracking three genuinely independent
questions at once: is a value already available, is a consumer request
currently outstanding, and has every source finished. Collapsing any pair
of those questions together is precisely what the near-miss does, and
precisely what breaks. The density buys three checkable properties this
pack's oracles confirm directly: a source's work starts exactly once for
the relay's lifetime (`no_per_demand_task_creation` holds flat at 1),
more than one outstanding demand is tracked and resolved correctly and in
order (`distinct_states_not_collapsible` matches the hand-derived
expected sequence), and a demand arriving after every source has already
finished still gets an immediate answer instead of hanging forever (the
`.finished`/`.cancelled` phases' shared `demandArrived` handling, exercised
by `control_simple_demand_then_yield` and by every variant's own bundled
`main.swift`).

**collapsed-suspension-flag (NEAR_MISS). Refuse it, and refuse it for the
specific, checkable reason, not a generic instinct about flags.** This is
the pack's centerpiece, and it is built to be genuinely persuasive: one
`Bool` and one stored optional value really do replace a six-case enum,
the resulting file is shorter and reads as simpler, and on any sequence
where at most one demand is ever outstanding at a time — including every
cancellation scenario a reviewer is likely to reach for first — it is
completely indistinguishable from GREEN. A full-credit review names the
actual seam: the single storage slot cannot represent "more than one
demand outstanding" at all. When a second demand arrives while the relay
is already suspended awaiting the first, the flag-based design's
`pendingRequest` slot is silently overwritten by the second request's id,
and the first request is never resumed by anything — not rejected, not
erred, simply forgotten, forever. `oracles.py`'s
`distinct_states_not_collapsible` drives exactly that sequence (two
demands, then one produced value) and compares the two variants' full,
ordered action lists: they agree on every step except the last, where
GREEN correctly resumes the *first* request and the near-miss incorrectly
resumes the *second*, having already lost the first. A reviewer who
checks only the buffered-value happy path, or only a cancellation
scenario with one request outstanding, will see nothing wrong — those
paths are genuinely, provably identical between the two variants, which
is exactly what makes stopping there insufficient.

**mutant-dropped-cancellation (MUTANT).** This one is a hard, unmissable
Layer-5 case, not a reviewer-judgment one: it is GREEN's exact state
machine with exactly one transition changed — cancelling while a demand
is outstanding and unsatisfied now discards that request instead of
resuming it with a finish signal. Every sequence that never cancels at
that precise moment is completely identical to GREEN, including this
variant's own bundled `main.swift` (which deliberately does not exercise
that one path, the same way the other packs' mutants' own suites avoid
their one changed line) and this pack's own control sequence.
`oracles.py`'s `every_continuation_resumed_exactly_once_under_cancellation`
fails against it specifically, on both of its scripted cancellation
scenarios; every other variant passes both, honestly, because none of
their own defects live on this path.

## Oracle taxonomy

Per this corpus's own four-way oracle classification (control /
discriminator / demonstration / gap), this pack's four checks split as:

- **`control_simple_demand_then_yield` is a control.** Its null failure
  expectation is deliberate: none of this pack's three costs (redundant
  restarts, a lost second demand, a dropped cancellation resume) touch an
  ordinary single-demand-at-a-time path at all, so all four variants
  agreeing here is the baseline the other three checks are measured
  against, not an oversight.
- **`every_continuation_resumed_exactly_once_under_cancellation` and
  `distinct_states_not_collapsible` are discriminators.** Each fires
  against exactly one variant — the mutant and the near-miss,
  respectively — and each is scoped deliberately: the cancellation check
  reports RED and the near-miss as honestly *passing*, because their
  respective costs (wasted restarts, a lost second demand) do not
  overlap with cancellation-while-one-request-outstanding; the
  states-collapse check is scoped to GREEN and the near-miss only, since
  RED's unrelated restart behavior and the mutant's dormant-on-this-
  sequence cancellation defect would both produce a mismatch for reasons
  that have nothing to do with what this check is testing.
- **`no_per_demand_task_creation` is also a discriminator, aimed at
  RED.** Unlike the other two, it targets the RED variant itself rather
  than the near-miss or mutant — the same shape as this corpus's
  `worst_case_compared_units_bounded` oracle in `rope-chunk-stable-
  identity`, where a hidden oracle can legitimately measure a cost in the
  *starting* variant that the accepted redesign specifically eliminates.

## Scoring guidance

- **Full credit** needs: demand-signalled-state-machine accepted outright,
  with its state count read as three genuine distinctions rather than
  excess; collapsed-suspension-flag refused specifically for the lost-
  second-demand defect (not a generic "flags are fragile" objection); and
  task-per-demand recognized as correct-but-costlier, not broken.
- **Partial credit:** collapsed-suspension-flag refused only on a vague
  "this feels less safe" or "collapsing state to a flag is always risky"
  basis, without naming the concrete overwritten-slot mechanism or citing
  a sequence where it actually produces a wrong answer.
- **No credit / active miss:** any recommendation to reduce demand-
  signalled-state-machine's state count, flatten its phases, or treat its
  associated-value cases as duplication — with or without collapsed-
  suspension-flag's shape offered as the replacement. This is the pack's
  central failure mode and outweighs any other finding a review gets
  right.
- mutant-dropped-cancellation is graded by the hidden oracle
  (`every_continuation_resumed_exactly_once_under_cancellation`), not by
  reviewer narrative; do not penalize a candidate for missing it in a
  static read unless they also assert with confidence that every
  cancellation path resumes correctly.
