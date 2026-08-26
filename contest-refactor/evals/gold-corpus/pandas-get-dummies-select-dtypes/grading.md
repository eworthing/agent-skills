# Grading — pandas-get-dummies-select-dtypes

Grader-only. Not shown to a candidate (see `provenance.json`'s `grader_only_files`).

## What this pack is actually testing

Not "can the candidate spot that calling a general-purpose selector with a
hardcoded alias list is a bit indirect." **The real test is whether the
candidate notices that `alias-list-coupling` gets the right answer only by
accident** -- it depends on `column_subset`'s internal unwrap of a `Packed`
kind, a detail `column_subset` never promised to any caller. Nothing
declared that dependency, and it was one unrelated change to
`column_subset` away from silently breaking.

**This pack's other half is a companion to `pandas-groupby-plot-imperfect-gold`,
not a repeat of it.** That pack's accepted, merged fix carried a real
residual -- its "no user-visible change" claim was false for one group
shape. `local-predicate` here makes the same *kind* of claim, and this
time **the claim is true**. A candidate who has internalized "verify
neutrality claims, don't trust them" from that pack must apply the other
half of the same lesson here: verifying a claim can also confirm it. A
reviewer who refuses or hedges on `local-predicate` out of reflexive
suspicion, having learned the wrong general lesson from a different pack,
fails this one just as surely as a reviewer who accepts every claim on
faith fails that one.

## What full credit looks like, per variant

**alias-list-coupling (RED).** Flag it. The specific, required reasoning:
`encode_categoricals` calls `column_subset` with a fixed list of type
aliases (`"text"`, `"masked_text"`, `"choice"`), and that call also
happens to pick up `Packed("text")` and `Packed("choice")` columns --
*only* because `column_subset` internally unwraps a `Packed` kind to its
primitive before matching. `encode_categoricals` never asked for that
unwrap and never declared it needed it. A candidate who flags this purely
as "should use a predicate instead of a selector call, for style" without
naming the accidental dependency on the unwrap gets partial credit, not
full.

**local-predicate (GREEN). Accept it, and verify its equivalence claim
rather than assume it either way.** `should_encode` expresses the same
"text, masked-text, or choice, plain or packed" set directly, unwrapping
`Packed` itself instead of relying on `column_subset` to do it as a side
effect. Run it against one column of each of the six kinds this pack
models and the encodable set is byte-for-byte identical to
`alias-list-coupling`'s. `CHANGES.md`'s "no change in which columns get
encoded" is a claim exactly like `dedicated-path-incomplete`'s in the
sibling pack -- **the difference is this one holds up.** A candidate who
accepts it without checking has gotten the right verdict for the wrong
reason (the reason that pack rewards, not this one); a candidate who
refuses it, or hedges it with an invented residual, has failed this pack's
central point by importing a lesson from the wrong pack.

**near-miss-widened-aliases (NEAR_MISS). Refuse it, and refuse it on the
right grounds.** This is the pack's centerpiece. It reads as the *laziest*
correct-looking fix: don't write a new predicate, just widen the list
already being passed to `column_subset` to include `"number"`, reasoning
that flag/indicator columns behave like a small set of choices. Two things
are wrong with it, and a full-credit review names both: (1) it still calls
`column_subset` and still depends on its internal unwrap for the packed
columns -- the exact coupling under review is untouched, just papered
over; (2) it now also encodes the plain numeric column, which must never
be one-hot encoded. **The size of this diff (a one-line list edit) is
itself a trap** -- a candidate scanning only for "is this smaller and
does it still work" would credit it over `local-predicate`, which is a
larger diff that adds a new function. Smaller is not a tiebreaker here;
correctness of the *set* is.

**mutant-drops-wrapped (MUTANT).** This one isn't primarily a
reviewer-judgment case -- it's an execution/hidden-oracle case (Layer 5).
Its own local predicate, `should_encode`, checks `col.kind in {"text",
"masked_text", "choice"}` directly, without unwrapping a `Packed` kind
first. A `Packed("text")` column's `.kind` is a `Packed` instance, not the
string `"text"`, so it never matches -- the column is silently dropped
from encoding. A static read of the diff might reasonably call this "the
same refactor as local-predicate, just written slightly differently";
the pack does not require a static reviewer to catch the drop by
inspection alone. What the pack requires is that the hidden oracles
`wrapped_extension_columns_encoded` and `encodable_set_matches_baseline`
both fail against this variant -- see `oracles.py`. A review pass that
notices `should_encode` never unwraps `Packed` is bonus credit, not
required credit.

## Why the discriminator is the encodable *set*, not any single column

`oracles.py`'s `encodable_set_matches_baseline` runs one column of each of
the six kinds this pack models -- plain-object, masked/nullable,
wrapped-extension string, wrapped-extension dictionary/categorical, native
categorical, and numeric -- through every variant's `encode_categoricals`
and compares the resulting sets. **A grading pass that checks only "does
this variant still encode plain text columns" will pass all four
variants** -- that's true and uninteresting. The set has to include the
packed columns (or the mutant's drop is invisible) and has to exclude the
numeric column (or the near-miss's over-match is invisible). Grading a
single column kind in isolation cannot distinguish RED/GREEN from
NEAR_MISS/MUTANT; only the full six-kind set can.

## Making "no dependency on the selector's internals" mechanical

`no_dependency_on_selector_internals` does not eyeball code style. It
parses `encode_categoricals`'s own function body with `ast` and checks for
a literal `Call` node targeting `column_subset` inside it. `red` and
`near_miss` both call it (`True`); `green` and `mutant` both express the
column set locally instead (`False`). This is checkable independent of
comments, docstrings, or naming -- it is the one place in this pack's
oracle battery that turns "does this depend on the other function's
internals" from a judgment call into a fact.

## Scoring guidance

- Full credit needs: alias-list-coupling flagged (the accidental unwrap
  dependency, not just "should be a predicate"); local-predicate accepted
  with its equivalence *verified* against the full six-kind set, not
  assumed true or false; near-miss-widened-aliases refused for **both**
  reasons (still coupled, and now over-matches) rather than one.
- Partial credit: alias-list-coupling flagged as merely "indirect" or
  "could be simpler" without naming the unwrap dependency; local-predicate
  accepted without any verification step named; near-miss-widened-aliases
  refused for only one of its two problems.
- No credit / active miss: alias-list-coupling approved; local-predicate
  refused or hedged with an invented residual (importing the sibling
  pack's lesson into a case where it doesn't apply); near-miss-widened-aliases
  accepted as an equally valid, simpler alternative to local-predicate.
- mutant-drops-wrapped is graded by the hidden oracles
  (`wrapped_extension_columns_encoded`, `encodable_set_matches_baseline`),
  not by reviewer narrative; do not penalize a candidate for missing it in
  a static read unless they also assert with confidence that every packed
  column is still encoded.
