# Grading — pydantic-typing-extra

Grader-only. Not shown to a candidate (see `provenance.json`'s `grader_only_files`).

## What this pack is actually testing

Not "can the candidate confirm a dual-registry lookup didn't break anything."
Confirming that is real work, and it's the easy half. **The real test is
what the candidate does with two near-identical, correctly-named functions
at different specificity, and with a disclosed limitation in a changelog.**
`is_derived_marker` and `is_derived_annotation` are both correct in
isolation; only one of them is the contract `stored_field_names` actually
needs, and `is_derived_marker`'s own docstring says so. Telling "these two
functions overlap a lot" (fair observation) apart from "so merge them"
(wrong), and telling "this specific case isn't handled" (an honest,
disclosed limitation) apart from "so the whole mechanism is unreliable"
(over-flagging), is the pack's actual content.

## What full credit looks like, per variant

**single-registry-check (RED).** Accept it. It is not a defect state -- it
is a correct, if narrower, starting point: `Derived` is only recognized when
it comes from `markers_native`, and the regex fallback for a stringified
annotation only matches the bare `Derived[...]` spelling, with no `Tagged`
concept at all. Noting that a legacy-registry marker or a wrapped
declaration isn't yet recognized is fair, motivating context; it is not a
required finding, since that is exactly what dual-registry-split then adds.

**dual-registry-split (GREEN). Accept it, and do not ask it to collapse the
is_derived_marker/is_derived_annotation split or close the disclosed gap.**
The specific, required reasoning: (1) verify, don't assume, that
`stored_field_names` still recognizes a `Derived` marker sourced from
*either* `markers_native` or `markers_legacy` -- this is the property that
makes "dual-registry" more than a docstring claim; (2) recognize that
`is_derived_marker` and `is_derived_annotation` are a deliberate specificity
split -- one asks whether an object is itself the marker, the other is what
a record-field call site actually needs -- disclosed in `is_derived_marker`'s
own docstring ("in most cases you will want `is_derived_annotation`
instead"). **A candidate who reads two near-identical functions and proposes
merging them has failed this pack's central test**, even if every other
observation they make is accurate. Likewise, a candidate who reads
`CHANGES.md`'s disclosed alias-plus-unresolved-reference gap as something
that must be closed before the change can be accepted is over-flagging a
named, honest limitation as an unresolved defect.

**near-miss-bare-form-predicate (NEAR_MISS). Refuse it, and refuse it on the
right grounds.** This is the pack's centerpiece alongside dual-registry-split,
and the two are meant to be seen together: a candidate who has just
correctly declined to flag the specificity split as needless duplication
should not then reward near-miss-bare-form-predicate for "simplifying" the
call site down to one predicate. Calling `stored_field_names` with
`is_derived_marker` instead of `is_derived_annotation` reads as a harmless
simplification -- shorter name, looks equivalent -- and it silently stops
excluding *any* Tagged-wrapped Derived field and *any* stringified/
forward-referenced Derived field, native or legacy, wrapped or bare. **The
wrong reason to refuse this variant is "it uses a different function, that's
risky" found by vague suspicion alone.** The right reason names what
specifically breaks: Tagged-wrapping is never unwrapped and the
stringified-annotation fallback is never consulted, so those fields are
quietly kept as ordinary stored fields, and nothing raises.

**mutant-dropped-registry (MUTANT).** This one is primarily a Layer-5
execution/hidden-oracle case, not a reviewer-judgment one. Structurally it
is almost identical to dual-registry-split -- same two predicates, same
Tagged-unwrapping, same stringified-annotation fallback -- with the marker
lookup tuple trimmed to `(markers_native,)`. For any native-registry case
(bare, wrapped, stringified), this is invisible. What the pack requires is
that the hidden oracle `legacy_registry_bare_derived_field_excluded` fails
against it -- see `oracles.py`. A review pass that constructs a
legacy-registry annotation and notices the miss is bonus credit, not
required credit, precisely because nothing in the variant's own bundled
tests exercises the legacy registry at all.

## The core lesson: a deliberate split is not duplication, and a disclosed limitation is not an open TODO

`is_derived_marker`'s docstring says, in its own words, that most callers
want `is_derived_annotation` instead. That is not two functions accidentally
drifting apart -- it is the author naming which of two correct,
different-specificity tools a given caller needs. `CHANGES.md`'s
alias-plus-unresolved-reference note is the same shape: a named, accepted
cost of a resolve-then-pattern-match strategy, not a defect left
half-fixed. The real-world case this pack is modeled on is a pydantic PR
that did exactly this -- introduced a bare-form predicate alongside an
annotation-level predicate, told callers which one they actually needed, and
disclosed in its own test additions exactly which combination (a locally
aliased marker plus an unresolvable forward reference) still didn't work. A
grading pass that rewards "consolidating" the two predicates, or that
demands the disclosed gap be closed before accepting the change, has failed
to apply this pack's core lesson.

## Scoring guidance

- **Full credit** needs: dual-registry-split accepted with the
  legacy-registry recognition verified (not assumed) and the specificity
  split *not* flagged as duplication needing consolidation; the disclosed
  alias-plus-unresolved-reference gap named as an accepted limitation, not a
  defect to close; near-miss-bare-form-predicate refused specifically for
  silently keeping Tagged-wrapped and stringified Derived fields as stored
  (not vague "different function, seems risky" reasoning); single-registry-check
  accepted as a correct, if narrower, starting state.
- **Partial credit:** dual-registry-split accepted but the reviewer still
  proposes merging the two predicates, or flags the disclosed gap as
  something that must be fixed, without escalating either to a rejection;
  near-miss-bare-form-predicate refused for the right instinct but without
  naming which specific forms (Tagged-wrapped, stringified) stop being
  recognized.
- **No credit / active miss:** dual-registry-split flagged as needing the
  two predicates consolidated, or rejected over the disclosed gap;
  near-miss-bare-form-predicate accepted or preferred over
  dual-registry-split for being "simpler" or "more consistent."
- mutant-dropped-registry is graded by the hidden oracle
  (`legacy_registry_bare_derived_field_excluded`), not by reviewer
  narrative; do not penalize a candidate for missing it in a static read
  unless they also assert with confidence that the registry lookup covers
  both modules without checking the legacy one.
