# Grading — rope-chunk-stable-identity

Grader-only. Not shown to a candidate (see `provenance.json`'s
`grader_only_files`).

## What this pack is actually testing

Not "can the candidate confirm a custom storage type didn't break
anything." This is a **restraint** pack, built against the reflex that
"fewer custom data structures is always better." `owned-segment-storage`
makes the local code *longer and more complex* than the plain-string
version it replaces -- a managed storage class, a monotonic counter, a
wrapper struct, in place of one `String`. A naive implementation-quality
critic reverts it because the code got shorter without that machinery, and
is wrong. The oracle deliberately does **not** grade "did you keep the
managed buffer" -- that would just reward data-structure cleverness for its
own sake. It grades what the buffer actually buys: after replacing one
chunk in a multi-chunk spool, a diff touches exactly that one chunk, and
the worst-case number of content units it has to read stays under a small,
fixed bound, independent of how many chunks the spool holds.

## What full credit looks like, per variant

**plain-text-single-leaf (RED). Accept it as a correct, if structurally
coarse, starting state.** Every replace produces exactly the right final
text. Nothing is broken. The limitation is invisible until you ask a
question this design has no way to answer -- "which one chunk changed?" --
because chunk boundaries here are pure arithmetic over one shared string,
not separately owned storage, so there is only one identity token per leaf,
shared by every chunk sliced from it. That is real, worth naming, and not
itself a defect to fix by editing this variant; it is exactly the
motivation for the next one.

**owned-segment-storage (GREEN). Accept it outright, as a disclosed
trade.** Each chunk owns a small storage object with a stable identity
token; copying a chunk's value shares that storage and its token, and only
replacing a chunk's own content allocates a fresh one. This costs real
local complexity -- a class, a counter, a wrapper struct -- to buy a global
property neither the RED state nor the near-miss has: a diff can tell
"this chunk is the one I already saw" without reading a single byte of its
text, and only has to read chunks whose tokens don't turn up in the old
set.

**near-miss-content-derived-identity (NEAR_MISS). Refuse it, and refuse it
for both real reasons, not just the easiest one.** This is the pack's
centerpiece, and it is built to be genuinely persuasive: it keeps its own
per-chunk storage type, so on the surface it looks like the same idea as
`owned-segment-storage`, just without needing a counter or a dedicated
storage class -- derive identity from the chunk's own content (a hash of
its text) instead. A full-credit review separates two distinct failures:

1. **Content-equal chunks collide.** Because identity is derived purely
   from text, two chunks holding identical text are indistinguishable by
   identity. If an edit changes some chunk's text to match a *different*
   existing chunk's content, the diff reports **no change at all** at that
   position -- a real, silently dropped edit. `oracles.py`'s
   `content_equal_chunks_are_distinguishable` checks this directly and
   fails only here.
2. **It never avoids the cost it claims to avoid.** The entire point of
   `owned-segment-storage`'s design is that a diff should not need to read
   a chunk's bytes to know whether it changed. Computing a content-derived
   identity requires reading every byte of every chunk, on both sides of a
   diff, every single time -- `oracles.py`'s
   `worst_case_compared_units_bounded` shows this variant's cost (96 units,
   for a 48-unit spool) is *larger* than the RED state's own worst case
   (48 units), not smaller.

A review that only catches one of these two has done real work but not
full-credit work. Neither failure is visible from reading the resulting
text alone -- both are strictly about *what the diff reports* and *how
much work it does to report it*.

**mutant-identity-reset-on-read (MUTANT).** This one is a hard, unmissable
Layer-5 case, not a reviewer-judgment one: identical in shape to
`owned-segment-storage` -- same storage class, same counter, same
identity-set lookup in the diff -- except the chunk list is rebuilt from
scratch, wrapping every chunk's text in brand-new storage, on *every read*
of it, not only when a chunk's content actually changes. A chunk nothing
touched still gets handed a fresh identity token merely by being read. The
stored text is completely unaffected; every replace still produces exactly
the right final content. Only the diff's notion of what changed degrades,
reporting every chunk in the spool as changed instead of just the one that
was. `oracles.py`'s `single_chunk_edit_touches_one_chunk` and
`worst_case_compared_units_bounded` both fail only here (along with RED,
for an unrelated structural reason); `resulting_text_correct_after_replace`
passes here same as everywhere else -- which is exactly why a test that
only checks resulting content cannot see this defect.

## Oracle taxonomy

Per this corpus's own four-way oracle classification (control /
discriminator / demonstration / gap):

- **`single_chunk_edit_touches_one_chunk`** is a **discriminator** for
  `mutant-identity-reset-on-read` (its canonical named target in
  `provenance.json`) and also fails, for an independent structural reason,
  against `plain-text-single-leaf`. It passes for
  `near-miss-content-derived-identity` -- deliberately: this is exactly
  why the near-miss is tempting, since an ordinary non-colliding edit gives
  the right answer even with content-derived identity.
- **`content_equal_chunks_are_distinguishable`** is a **discriminator** for
  `near-miss-content-derived-identity` -- the near-miss killer. It also
  fails against `plain-text-single-leaf` and
  `mutant-identity-reset-on-read`, but by *over*-reporting (both chunks
  flagged) rather than the near-miss's *under*-reporting (no chunks
  flagged) -- a different, less interesting failure mode that a static
  read might reasonably not distinguish from the near-miss's without
  running this exact check.
- **`worst_case_compared_units_bounded`** is a **discriminator** for
  `plain-text-single-leaf` (its canonical named target) and also fails
  against `near-miss-content-derived-identity` and
  `mutant-identity-reset-on-read`, each for its own reason (must descend
  into every chunk's contents; must hash every chunk's contents; over-
  reports so many chunks changed that reporting them costs as much as
  reading the whole spool).
- **`resulting_text_correct_after_replace`** is a **control**: it holds
  across all four variants by design, since none of the four variants ever
  corrupts the stored text itself -- only `owned-segment-storage`'s and
  `mutant-identity-reset-on-read`'s *diff-reporting* differ, and RED and
  the near-miss never claim to track identity correctly in the first
  place. It would only fail if this fixture itself were broken in a way
  that made the other three oracles' results meaningless.

Every non-control oracle in this pack has an observed RED: each was run
against its target variant and watched fail, then run against
`owned-segment-storage` and watched pass, before being considered done.

## Chunk size and bound

This pack's chunk size (8 characters) and worst-case compared-units bound
(20) are chosen for this fixture's own test scenarios and have no
relationship to the real-world case's own benchmark figures (see
`provenance.json`'s `contamination.constants_changed`). The bound sits
comfortably above `owned-segment-storage`'s actual observed cost of 8
(one chunk's worth of content) and comfortably below every other variant's
actual observed cost of 48 or 96 (most or all of the spool's content) --
that separation was confirmed by running the fixture, not assumed from its
design.

## Scoring guidance

- **Full credit** needs: `owned-segment-storage` accepted outright, named
  as a deliberate trade of local complexity for a global diffing property
  (not merely tolerated); `near-miss-content-derived-identity` refused for
  *both* the content-collision defect and the failure to avoid the
  byte-reading cost, not just one; `plain-text-single-leaf` accepted as a
  correct, if structurally coarse, starting state rather than treated as a
  bug in itself.
- **Partial credit:** `near-miss-content-derived-identity` refused for
  only one of the two reasons (usually the content collision, since it is
  easier to construct a concrete failing scenario for by inspection than
  reasoning about comparison cost), or refused correctly but with vague
  "hashing for identity feels fragile" reasoning rather than naming the
  specific collision and the specific unavoided cost.
- **No credit / active miss:** `owned-segment-storage` refused because
  `plain-text-single-leaf` is shorter or has less code, without weighing
  what the added complexity buys; `near-miss-content-derived-identity`
  accepted because it keeps a custom chunk type and looks like a leaner
  version of the same idea.
- `mutant-identity-reset-on-read` is graded by the hidden oracles
  (`single_chunk_edit_touches_one_chunk`,
  `worst_case_compared_units_bounded`), not by reviewer narrative; do not
  penalize a candidate for missing it in a static read unless they also
  assert with confidence that the diff's chunk-level reporting is correct
  without checking which chunks it actually flags.
