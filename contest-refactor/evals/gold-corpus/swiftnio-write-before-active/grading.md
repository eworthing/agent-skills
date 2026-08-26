# Grading — swiftnio-write-before-active

Grader-only. Not shown to a candidate (see `provenance.json`'s
`grader_only_files`).

## This pack's near-miss is the maintainer's own documented second hole

The real PR body names two separate problems with the pre-fix code, calls
fixing only the first "unnecessary" restraint if stopped short of the
second, and explicitly says the pre-fix test suite "didn't protect us from
anything." `near-miss-buffer-without-activation-flush` is that exact
partial fix -- not an invented trap, a translation of the maintainer's own
before/after analysis into this pack's vocabulary.

## What this pack is actually testing

Not "can the candidate spot a data-loss bug." The interesting failure here
is trusting a passing test suite. `reject-before-ready`'s own bundled test
asserts, and confirms, that an early write is rejected -- and that
assertion passing is not evidence the rejection is correct, it is evidence
of exactly what the real upstream suite did for however long it stood.
`near-miss-buffer-without-activation-flush`'s own suite ALSO passes,
including a test that shows a write eventually getting delivered -- because
that test happens to include a flush call after activation, the one
follow-up operation this variant actually needs to recover a stranded
write. Both suites are internally consistent and both are insufficient.

## What full credit looks like, per variant

**reject-before-ready (RED). Accept it as a correct starting point, but do
not let its own passing suite stand as a defense of it.** Rejecting a
write outright when the pipe is not yet live is the older behavior this
pack corrects, not a currently-live bug to flag as broken in isolation --
but a reviewer who cites "the test suite passes" as reassurance about this
code has fallen into the exact trap the pack is built to demonstrate.

**flush-buffered-writes-on-activation (GREEN). Accept it outright.** No
write is ever rejected, and activation itself attempts delivery of
anything already waiting -- confirmed by `oracles.py`'s
`activation_emits_pending_writes`, which checks specifically the scenario
where no further flush call happens after activation. This is the
strongest evidence available that the fix does not depend on a lucky
follow-up operation.

**near-miss-buffer-without-activation-flush (NEAR_MISS). Refuse it, and
refuse it for the specific, narrow reason.** The required reasoning:
writes are no longer rejected (the first hole is genuinely fixed), but
activation alone never attempts delivery -- only an explicit flush call
made after activation does. `activation_emits_pending_writes` fails
against exactly this variant, isolating that gap precisely.
**The wrong reason to refuse this variant is "it sometimes loses writes,
same as the mutant."** It does not: `no_accepted_write_is_permanently_lost`
passes for this variant, because a later flush call, whenever it happens
to arrive, recovers the value. The failure mode here is *no guarantee of
delivery*, not *no possibility of delivery* -- a reviewer who conflates the
two has correctly refused the near-miss but for the wrong, cruder reason,
and has failed to separate it from the mutant that sits right next to it.

**mutant-drop-before-ready (MUTANT).** A hard, unmissable Layer-5 case,
not a reviewer-judgment one: it looks identical to the accepted variant at
a glance -- no write is ever rejected, activation attempts delivery of
anything waiting -- but a write issued before the pipe is live is never
queued anywhere at all. `no_accepted_write_is_permanently_lost` fails
against it specifically: no matter how many activations or flushes follow,
the value is gone. A static read that spots the missing buffering line is
bonus credit, not required credit.

## Why two oracles never fail, and what they are instead

Per this corpus's documented four-way oracle taxonomy (control /
discriminator / demonstration / gap), two of this pack's four checks hold
for every variant by design:

- **`emitted_preserves_write_order` is a control.** None of this pack's
  four variants ever scrambles order -- wherever a variant emits anything
  at all, three writes issued in sequence come out in that sequence. It
  would only fail if the fixture itself were broken in a way that made the
  other three oracles' results meaningless.
- **`stale_test_trap` is a demonstration, and it is the pack's other
  central point.** Every variant's own bundled `main.swift` passes,
  *including* `reject-before-ready`'s, whose suite certifies the very
  behavior this pack exists to correct. Its uniformity across all four
  variants is the finding: a passing suite is evidence a variant is
  internally consistent with its own author's expectations, never evidence
  those expectations were right. This mirrors `cpython-genexpr-iterability`'s
  oracle of the same name and purpose -- the Python counterpart to this
  exact lesson.

`activation_emits_pending_writes` and `no_accepted_write_is_permanently_lost`
are the pack's two discriminators; see `oracles.py`'s module docstring for
the full variant-to-expectation mapping.

## Scoring guidance

- **Full credit** needs: flush-buffered-writes-on-activation accepted
  outright; near-miss-buffer-without-activation-flush refused specifically
  because activation alone does not guarantee delivery (not because writes
  are "sometimes lost" in the mutant's sense); reject-before-ready's own
  passing test explicitly named as insufficient evidence of correctness,
  not cited as reassurance.
- **Partial credit:** near-miss-buffer-without-activation-flush refused
  for the right instinct but without distinguishing "recoverable via a
  later flush" from the mutant's "unrecoverable"; reject-before-ready
  accepted without any comment on what its passing suite does or doesn't
  prove.
- **No credit / active miss:** near-miss-buffer-without-activation-flush
  accepted because its own bundled suite passes; near-miss-buffer-without-
  activation-flush and mutant-drop-before-ready treated as the same
  failure; reject-before-ready's passing suite cited as evidence its
  rejection behavior is correct.
- mutant-drop-before-ready is graded by the hidden oracle
  (`no_accepted_write_is_permanently_lost`), not by reviewer narrative; do
  not penalize a candidate for missing it in a static read unless they
  also assert with confidence that every accepted write is eventually
  delivered.
