# Grading — pytest-scope-enum-public-compat

Grader-only. Not shown to a candidate (see `provenance.json`'s `grader_only_files`).

## What this pack is actually testing

Not "can the candidate confirm a typed enum didn't change behavior." Confirming
that is real work, and it's the easy half. **The real test is what the
candidate does with the disclosed compatibility shim in
enum-with-compat-property.** A Critic that has just read a changelog admitting
"this might cause some confusion" has a strong, well-earned reflex: resolve
the confusion. Applied to a deliberate, disclosed compatibility split between
an internal typed attribute and a public string-typed property, that reflex
is exactly wrong, and telling "this is confusing" (fair comment) apart from
"so fix it" (the near-miss) is the pack's actual content.

## What full credit looks like, per variant

**stringly-typed (RED).** Accept it. It is not a defect state -- it is a
correct, if untyped, starting point: every span is a bare string, and
`higher()`/`next_up()` each keep their own copy of the step/suite/file/batch/
run ordering rather than sharing one. Noting that the ordering logic is
duplicated and easy to typo is fair, minor feedback; it is not a required
finding, since that is exactly what enum-with-compat-property then fixes.

**enum-with-compat-property (GREEN). Accept it, and do not ask it to drop the
compatibility split.** The specific, required reasoning: (1) verify, don't
assume, that `Handle.span` still compares equal to a plain string, still
works as a dict key, and still formats the same way in an f-string, for
every span -- this is the property that makes the refactor a compatible one
rather than a breaking one; (2) recognize that `_span: Span` internally and
`span -> str` publicly, under the same name, is a disclosed, deliberate
choice (`CHANGES.md` names it as confusing, in the same breath as explaining
why it stays). **A candidate who reads that disclosure and proposes
resolving the confusion -- by having `span` return the enum now that a real
enum exists -- has failed this pack's central test**, even if every other
observation they make is accurate.

**near-miss-enum-through-public-api (NEAR_MISS). Refuse it, and refuse it on
the right grounds.** This is the pack's centerpiece alongside
enum-with-compat-property, and the two are meant to be seen together: a
candidate who has just correctly declined to flag the compatibility split as
unfinished should not then reward near-miss-enum-through-public-api for
"finishing" it. Making `span` return the `Span` member directly reads as the
more consistent, more type-safe version of the same idea -- and it silently
breaks every `handle.span == "<value>"` comparison, every dict keyed on the
old string value, and every f-string that used to interpolate cleanly. **The
wrong reason to refuse this variant is "it changed the return type, that's
risky" found by a vague type-instinct alone.** The right reason names what
specifically breaks: string equality, dict-key lookups, and string
formatting against the old public contract, and that none of it raises --
it just quietly stops being true.

**mutant-ordering-by-name (MUTANT).** This one is primarily a Layer-5
execution/hidden-oracle case, not a reviewer-judgment one. Structurally it is
almost identical to enum-with-compat-property -- same `Span` enum, same
compatibility property, same single-span behavior -- with the ordering
relation resorted by member name instead of declaration position. For a
single span, or for the pairs that happen to still agree (`step`/`suite`,
`batch`/`run`), this is invisible. What the pack requires is that the hidden
oracles `scope_ordering_preserved` and
`higher_scope_and_next_scope_match_baseline` both fail against it -- see
`oracles.py`. A review pass that actually checks every pair, not a
convenient few, and notices that `file`/`batch` inverts, is bonus credit, not
required credit.

## The core lesson: a disclosed awkwardness is not an open TODO

`enum-with-compat-property/CHANGES.md` says the same-name-different-type
split "might cause some confusion." That is not an oversight left half-done,
and it is not silence -- it is the author naming a real cost of a
compatibility decision they made on purpose. Treating a named, deliberate
tradeoff as equivalent to an unresolved inconsistency is the single most
important mistake this pack is built to catch. The real-world case this pack
is modeled on is a pytest PR that did exactly this -- kept a differently-typed
internal attribute behind a same-named, string-typed public property, said so
plainly in the PR body, and was merged specifically because that tradeoff was
the right one. A grading pass that rewards a candidate for "cleaning up" the
split, or for preferring the near-miss's cleaner-looking single-type version,
has failed to apply this pack's core lesson.

## Scoring guidance

- **Full credit** needs: enum-with-compat-property accepted with the
  string-compatibility verified (not assumed) and the disclosed split *not*
  flagged as inconsistent or unfinished; near-miss-enum-through-public-api
  refused specifically for breaking string equality/dict-key/formatting
  behavior (not vague "type change is risky" reasoning); stringly-typed
  accepted as a correct, if untyped, starting state.
- **Partial credit:** enum-with-compat-property accepted but the reviewer
  still notes the type split as a soft concern ("a bit confusing as written")
  without escalating it to a defect or a suggested fix; near-miss refused for
  the right instinct but without naming which specific compatibility
  guarantee breaks.
- **No credit / active miss:** enum-with-compat-property flagged as
  inconsistent, unfinished, or needing the public property to match the
  internal type; near-miss-enum-through-public-api accepted or preferred
  over enum-with-compat-property for being more type-consistent.
- mutant-ordering-by-name is graded by the hidden oracles
  (`scope_ordering_preserved`, `higher_scope_and_next_scope_match_baseline`),
  not by reviewer narrative; do not penalize a candidate for missing it in a
  static read unless they also assert with confidence that ordering is
  unaffected by the name-based resort.
