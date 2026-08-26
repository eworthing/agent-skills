# Grading — werkzeug-socket-lifecycle

Grader-only. Not shown to a candidate (see `provenance.json`'s
`grader_only_files`).

## What this pack is actually testing

Not "can the candidate confirm a consolidation works." Confirming that is
real work, and it's the easy half. **The real test is whether the candidate
checks a five-line-for-five-line equivalence when a helper is deleted and
its responsibilities move elsewhere.** The upstream PR this pack is modeled
on literally shipped a line-by-line before/after mapping in its own PR body
because that is exactly where this class of change goes wrong: not in the
lines that got rewritten, but in the one responsibility nobody wrote a line
for at all.

## What full credit looks like, per variant

**helper-and-eager-service (RED). Flag it, and flag it precisely.** The
specific, required reasoning: `start_service`'s `adopt` path constructs a
`Service(endpoint, bind=False)`, which -- because the pre-refactor `Service`
always provisions a `Listener()` in `__init__` regardless of `bind` --
creates a placeholder that is then silently overwritten by the caller's own
listener. Nothing closes the placeholder first. That is a real, silent
descriptor leak, one per call that supplies a pre-provisioned listener.
**The finding must be scoped correctly**: the plain, non-adopt
`start_service(endpoint)` path in this same variant does not leak -- the one
`Listener` it creates is the one it binds, activates, and later closes.
Generalizing the leak to "this module leaks resources" rather than "the
adopt path leaks a placeholder" is a correct instinct executed sloppily.

**consolidated-service-ownership (GREEN). Accept it outright, and verify
its own claim rather than repeating it.** The specific, required reasoning:
(1) confirm the consolidation is complete -- `clear_stale`, reuse
configuration, inheritance, bind-with-friendly-conflict-handling, and
activation all now live in `Service.__init__`, and the placeholder gets
closed immediately in the `bind=False` branch, closing the RED leak; (2)
independently trace what a bind conflict does through `start_service`,
rather than trusting `CHANGES.md`'s "no caller-visible behavior changes"
line. That trace turns up a real discrepancy: `start_service`'s non-adopt
path used to raise `EndpointInUseError` straight out of `Service`'s raw
`bind` call, which a caller could catch; now that the friendly-message-and-
`terminate` handling lives inside `Service.__init__` itself, *every*
`start_service` call shares that behavior, including the ones that never
went through the old helper. **A candidate who accepts the CHANGES.md claim
without checking this has done half the review.** Just as important: **a
candidate who treats this discrepancy as a blocking defect, or who proposes
'fixing' it by reverting to a bare `raise`, has failed the other half.**
This is a real, accepted, currently-shipping cost (verified against the
real PR's outcome: the equivalent code is still in `BaseWSGIServer`'s
constructor on werkzeug's `main`, never reverted) -- naming it is fair
comment; rejecting the refactor or rewriting the conflict handling over it
is over-flagging.

**near-miss-dropped-reuse (NEAR_MISS). Refuse it, and refuse it on the
right grounds.** This is the pack's centerpiece alongside
consolidated-service-ownership: a candidate who has just correctly accepted
the consolidated shape, verified its claim, and resisted the urge to
'fix' the conflict-handling residual, should not then wave through a
sibling that looks identical at a glance. The specific, required reasoning:
every other responsibility the deleted helper had gets a preserved
counterpart in `Service.__init__` *except* reuse configuration --
`set_reuse` is never called anywhere in this variant, so every listener it
provisions comes up with `reuse_enabled` `False`, where the pre-refactor
helper (and every other variant here) set it `True`. **The wrong reason to
refuse this variant is "it changed something, that's risky" found by a
vague instinct alone.** The right reason names the specific responsibility
that has no counterpart, and notes that the variant's own bundled tests
never assert on `reuse_enabled` at all -- which is exactly why its own
author never caught the gap.

**mutant-handoff-close-before-read (MUTANT).** This one is primarily a
Layer-5 execution/hidden-oracle case, not a reviewer-judgment one.
Structurally it is almost identical to consolidated-service-ownership --
same class attributes, same conflict handling, same leak fix -- with the
two statements in `start_with_handoff` swapped: it closes the listener
*before* reading `descriptor_id` instead of after, so the id handed to a
successor is always `-1`, dead on arrival, even on a clean, uncontended
provision. What the pack requires is that the hidden oracle
`handoff_yields_live_descriptor` fails against it -- see `oracles.py`. A
static read that catches the swapped order by inspection is bonus credit,
not required credit.

## The core lesson: a deleted helper's responsibilities need a checklist, not a skim

The upstream PR this pack is modeled on didn't get this right by accident --
its own body includes a line-by-line mapping of what the deleted helper did
and where each piece landed. `near-miss-dropped-reuse` is what happens when
that checklist is run with one line silently dropped: the code looks
complete, reads as complete, and passes its own tests, because the gap is
an absence, not a change anything can diff against. The pack's other axis --
consolidated-service-ownership's changelog overclaiming "no caller-visible
behavior changes" -- is the same lesson from the opposite direction: an
author's own confident summary is not a substitute for tracing the code,
even when the author is right about almost everything in it.

## Scoring guidance

- **Full credit** needs: consolidated-service-ownership accepted, with the
  conflict-handling discrepancy named as a real but non-blocking residual
  (not accepted uncritically, not rejected, not "fixed"); near-miss-
  dropped-reuse refused specifically for the missing `set_reuse` call (not
  vague risk-aversion); helper-and-eager-service flagged specifically for
  the adopt-path placeholder leak, correctly scoped away from the non-adopt
  path.
- **Partial credit:** consolidated-service-ownership accepted but the
  conflict-handling discrepancy is missed entirely (claim taken at face
  value); near-miss-dropped-reuse refused for the right instinct but
  without naming which specific responsibility (reuse) has no counterpart;
  helper-and-eager-service's leak found but over-generalized to the whole
  module.
- **No credit / active miss:** consolidated-service-ownership rejected, or
  its conflict handling "fixed" by reverting to a bare raise;
  near-miss-dropped-reuse accepted or preferred over
  consolidated-service-ownership for looking equally consolidated;
  helper-and-eager-service's leak dismissed because nothing raises.
- mutant-handoff-close-before-read is graded by the hidden oracle
  (`handoff_yields_live_descriptor`), not by reviewer narrative; do not
  penalize a candidate for missing it in a static read unless they also
  assert with confidence that the handoff always returns a usable
  descriptor.
