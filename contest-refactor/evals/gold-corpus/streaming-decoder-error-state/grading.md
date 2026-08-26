# Grading — streaming-decoder-error-state

Grader-only. Not shown to a candidate (see `provenance.json`'s
`grader_only_files`).

## This pack is a restraint control, not a defect hunt

`protocol-decoder-with-error-state` (GREEN) is deliberately the most
state-dense file in the pack: four cases, a nested switch, several
branches. An automated complexity scanner is expected to nominate it as a
hotspot on sight. The reviewer's job is to inspect that nomination and
**dismiss** it -- every one of those states is a real, distinguishable
protocol condition, not incidental complexity. If a reviewer turns this
fixture into an automatic simplification finding, scanner/Critic
integration has failed, and that failure is what this pack exists to
catch. Accordingly this pack is graded primarily through `must_not_find`,
not through findings a reviewer must produce.

## Causality, precisely

The real-world case behind this pack is a chain, not a single fix: PR
**#837** (merged first) added the error-latch state that stops a decoder
from calling decode again after a user-thrown error. PR **#814** (this
pack's `source_pr`, merged ten days later) then moved the decoder onto a
shared incremental-decoder protocol, carrying #837's error state forward
as one of its cases, and raised allocation limits as a disclosed trade to
make that move. A downstream project's own six-month intermittent-failure
bug was closed as fixed through that **combined chain**. #814
**participates in** that resolution; it did not fix the bug alone, and
this is not a longitudinal defect story about #814 in isolation. Getting
this backwards is a real error a candidate can make and should not be
credited.

## What full credit looks like, per variant

**hand-rolled-buffer-loop (RED). Accept it as a correct, working starting
point.** Its buffering, re-entrancy guard, and leftover-bytes bookkeeping
are inlined into the same type as its parsing state -- a real
architectural weakness (nothing about its buffering could be reused by a
second parser without copying it), and, predating any error-latch, a
consumer's thrown error is swallowed silently and decoding continues.
Neither is a defect to flag as broken in isolation: they are the gaps the
later variants close. `oracles.py`'s
`no_delivery_after_consumer_error` records this variant's own behavior
(nonzero deliveries after a throw) without asserting it as a required
finding -- see that module's docstring for why RED is graded honestly
rather than forced to match GREEN.

**protocol-decoder-with-error-state (GREEN). Accept it outright, and
accept its complexity as load-bearing.** `awaitingHeader` /
`awaitingCountedContinuation` / `awaitingUnboundedContinuation` /
`errored` are four real, distinguishable protocol conditions sitting on a
small shared buffering-and-re-entrancy protocol. The pack's own near-miss
and mutant each demonstrate, on a concrete input, what breaks when one of
those distinctions is removed -- that is the strongest possible evidence
the state count is doing real work, not padding. The in-code comment
documenting this variant's higher per-message allocation (versus a
hand-tuned single-buffer loop) records a measured, accepted trade, not an
unexamined regression; a review that flags it as waste without weighing
what it buys has failed this pack's efficiency-lens restraint case.

**flattened-states-with-flags (NEAR_MISS). Refuse it, and refuse it for
the specific, narrow reason.** The required reasoning: this variant
keeps the same shared buffering protocol and the same correct
error-latch as GREEN -- its difference is purely the parsing-state
representation, collapsed from a four-case enum into `isErrored`,
`isUnbounded`, and a `remaining` counter. `remaining == 0` is used as a
proxy for "awaiting the start of a new message," and that proxy is wrong
exactly once: it also holds throughout the entire body of an
in-progress unbounded frame, since that mode never touches `remaining`.
Feed it an unbounded frame whose first body line happens to look like a
valid zero-length counted header (`oracles.py`'s
`distinct_states_not_collapsible`, sequence `#*`, `#0`, `.`) and it
reports **two** frames -- an invented empty counted frame, then an
emptied-out unbounded frame -- where the accepted variant reports **one**
(`unbounded:[#0]`). This is not visible from this variant's own bundled
suite, which never happens to construct that input; a reviewer citing
"it still passes its own tests and reads more simply" has matched the
near-miss's own pitch rather than testing it.
**The wrong reason to refuse this variant is a generic "flags are
fragile" instinct without naming the specific collapsed pair.** Full
credit requires naming which two states become indistinguishable
("awaiting the start of a new message" and "awaiting a continuation line
of the current one") and the concrete input that exposes it, not a
vague preference for enums over booleans.

**mutant-missing-error-state (MUTANT).** A hard, unmissable Layer-5
case, not a reviewer-judgment one: it keeps GREEN's exact state enum and
shared buffering protocol, minus the `errored` case and its `do`/`catch`
latch. Nothing distinguishes it from GREEN for any input that never
triggers a consumer error, and its own bundled suite -- which never
triggers one -- passes. `no_delivery_after_consumer_error` fails against
it specifically: after the consumer throws for a delivered frame, this
variant keeps calling it for every well-formed frame that follows,
silently, with no crash. A static read that spots the missing `errored`
case is bonus credit, not required credit; `must_find_if_present`'s
`missing-error-state-transition` entry is scoped to this variant only.

## Why one oracle never fails, and what it is instead

Per this corpus's documented four-way oracle taxonomy (control /
discriminator / demonstration / gap):

- **`distinct_states_not_collapsible` and `no_delivery_after_consumer_error`
  are this pack's two discriminators.** The first isolates the near-miss's
  gap precisely (fails only against `flattened-states-with-flags`); the
  second isolates the mutant's gap precisely (fails only against
  `mutant-missing-error-state`). See `oracles.py`'s module docstring for
  the exact expectation matrix, including why RED is deliberately
  unasserted on the second.
- **`ordinary_message_decodes_identically` is a control.** None of this
  pack's four variants mishandles an unremarkable, non-adversarial
  message -- wherever any variant decodes the same well-formed counted
  frame, all four produce the identical result. It would only fail if the
  fixture itself were broken in a way that made the other two oracles'
  results meaningless.

## Scoring guidance

- **Full credit** needs: GREEN's state machine and its allocation trade
  both accepted as-is, with the trade explicitly named as measured rather
  than passed over in silence; `flattened-states-with-flags` refused with
  the specific collapsed-state pair and the concrete misparsing input
  named, not a generic "prefer enums" comment; RED accepted as a correct
  but architecturally coupled starting point, not penalized for its
  (expected, undefended) lack of an error-latch.
- **Partial credit:** `flattened-states-with-flags` refused on a correct
  instinct ("this loses information the enum had") without identifying
  which two states collapse or constructing the input that proves it;
  GREEN's state count accepted without any comment on the allocation
  trade one way or the other.
- **No credit / active miss:** GREEN's state machine flagged as
  over-engineered, or its nested branches flagged as a smell with no
  identified semantic duplicate; `flattened-states-with-flags`'s
  flag-and-counter shape recommended as a cleanup of GREEN; the raised
  per-message allocation treated as unexamined waste; claiming PR #814
  fixed the downstream bug on its own rather than participating in the
  #837+#814 chain.
- `mutant-missing-error-state` is graded by the hidden oracle
  (`no_delivery_after_consumer_error`), not by reviewer narrative; do not
  penalize a candidate for missing it in a static read unless they also
  assert with confidence that every consumer error is contained.
