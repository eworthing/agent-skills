# Grading — swiftnio-registration-id-representation

Grader-only. Not shown to a candidate (see `provenance.json`'s
`grader_only_files`).

## This pack's near-miss is a real class of trap, not an invented one

The real PR replaced manual, per-use-site bit shifting and masking of a
packed registration-ID word with named Swift types and one boundary
conversion function, in the author's own words: "Instead of manual
shifting / masking we can write the whole registration ID code normally
in Swift ... Result: Nicer code." A sibling PR, mid-review, factored out a
generic integer bit-packing utility -- a legitimate tool in general. This
pack's near-miss asks what happens if that generic utility is offered as
*the whole fix* instead of the named types: it is a real deduplication,
and it is not the thing the real PR was actually for.

## What this pack is actually testing

Not "can the candidate spot a shift/mask bug." The interesting failure
here is rewarding a smaller diff for solving the wrong problem.
`near-miss-generic-bit-packing-helper` is shorter than both
`inline-shift-mask-per-site` (the starting point) and
`typed-fields-single-conversion` (the accepted answer) -- exactly the
property that makes "prefer the smallest diff" a bad heuristic on its
own. The domain concepts (a ticket, a lane, a tier) never become visible
or type-checked in the near-miss; only the packing *mechanism* got
deduplicated.

## What full credit looks like, per variant

**inline-shift-mask-per-site (RED). Accept it as a correct, if
duplicated, starting point.** Every round trip is correct; the defect is
duplication and the absence of any type-level protection against
confusing two fields, not incorrect arithmetic.

**typed-fields-single-conversion (GREEN). Accept it outright.**
`TicketID`, `BeltLane`, and `HandlingTier` are distinct types; a caller
cannot transpose a ticket and a lane and have it compile.
`distinct_field_types_not_interchangeable` confirms this directly by
compiling a snippet that does exactly that swap and observing it fail to
type-check. Bit shifting exists in exactly one place
(`ConveyorCommandWord`), confirmed by `packing_confined_to_one_site`.

**near-miss-generic-bit-packing-helper (NEAR_MISS). Refuse it, and refuse
it for the specific, narrow reason.** The required reasoning: `PackingKit`
genuinely deduplicates the shift/mask arithmetic into one place -- that
part of the near-miss's motivation is real and not a strawman. But every
field remains a bare `UInt64` at every call site, and every call site
names a raw bit offset and width as a literal integer
(`packing_confined_to_one_site` counts these call sites specifically,
separating "one helper" from "many call sites still reasoning in bit
ranges"). The compiler cannot catch a transposed ticket and lane here any
more than it could in the starting point --
`distinct_field_types_not_interchangeable` shows the exact same swap
compiling without complaint.
**The wrong reason to refuse this variant is "it's risky to use raw
integers" as a generic instinct, or "it's not finished yet, it's a rough
draft of the real fix."** Both miss the specific, checkable point: this
variant solved deduplication and left the type-safety problem completely
untouched, and it is not on a continuum toward the accepted answer --
PackingKit generalizes the mechanism further, it does not introduce
vocabulary the mechanism has no notion of.

**mutant-narrow-lane-mask (MUTANT).** A hard, unmissable Layer-5 case,
not a reviewer-judgment one: it keeps `typed-fields-single-conversion`'s
shape exactly -- same three types, same single boundary type -- but the
lane field's unpack mask is one bit too narrow. `roundtrip_preserved_at_
field_maxima` fails against it specifically, because a lane value with
its top bit set (at or near 65535) is silently truncated on the way back
out. Every ordinary lane value is unaffected, including in this variant's
own bundled `main.swift`, which never exercises a value anywhere near the
field's maximum. A static read that spots the narrowed mask is bonus
credit, not required credit.

## Why one oracle never fails, and what it is instead

Per this corpus's documented four-way oracle taxonomy (control /
discriminator / demonstration / gap), `ordinary_value_midrange_
roundtrips` is a **control**: an ordinary lane value (42) is nowhere near
the mutant's narrow-mask bug, so all four variants pass it, including the
mutant. It would only fail if the fixture itself were broken in a way
that made the other three oracles' results meaningless.

`distinct_field_types_not_interchangeable` and `packing_confined_to_one_
site` are this pack's two discriminators between the accepted answer and
the near-miss; `roundtrip_preserved_at_field_maxima` is the discriminator
between the accepted answer and the mutant. See `oracles.py`'s module
docstring for the full variant-to-expectation mapping.

## Scoring guidance

- **Full credit** needs: typed-fields-single-conversion accepted
  outright; near-miss-generic-bit-packing-helper refused specifically
  because its fields remain untyped and interchangeable despite the real
  deduplication (not merely because it "uses raw integers" as a vague
  instinct); inline-shift-mask-per-site accepted as a correct starting
  point without demanding it be rewritten from scratch.
- **Partial credit:** near-miss-generic-bit-packing-helper refused for
  the right instinct but without naming that the deduplication itself is
  real and the type-safety gap is the actual defect; typed-fields-
  single-conversion accepted without any comment on why it is longer
  than the near-miss.
- **No credit / active miss:** near-miss-generic-bit-packing-helper
  accepted because it is the shortest variant or removes visible
  duplication; near-miss-generic-bit-packing-helper treated as an
  unfinished draft of typed-fields-single-conversion rather than a
  different, incomplete fix.
- mutant-narrow-lane-mask is graded by the hidden oracle
  (`roundtrip_preserved_at_field_maxima`), not by reviewer narrative; do
  not penalize a candidate for missing it in a static read unless they
  also assert with confidence that every lane value round-trips
  correctly.
