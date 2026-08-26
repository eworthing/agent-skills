# Grading — pandas-select-dtypes-predicates

Grader-only. Not shown to a candidate (see `provenance.json`'s `grader_only_files`).

## What this pack is actually testing

Not "can the candidate confirm two ways of matching a type produce the same
result." Confirming the equivalence is real work and worth credit, but it is
the easy half of this pack. **The real test is what the candidate does with
per-type-callables: a refactor that adds indirection, gets slightly longer,
and whose entire stated justification is enabling a change that has not
happened yet.** A Critic trained to be suspicious of unexplained complexity
will want to flag exactly this shape -- "why does this need its own callable
per type, nothing here uses that flexibility" -- and that reflex, applied
here, is wrong. The benefit is disclosed (`CHANGES.md`) and real; it just
isn't cashed in by this diff.

## What full credit looks like, per variant

**frozenset-predicate (RED).** Accept it. It is not a defect state -- it is
a correct, if tangled, starting point: one frozenset per include/exclude
list, one predicate function that special-cases the flag/count distinction
twice (once for the include check, once for the exclude check). Noting that
the flag-vs-count logic is duplicated and could be consolidated is fair,
minor feedback; it is not a required finding.

**per-type-callables (GREEN). Accept it, and do not flag the indirection as
speculative.** The specific, required reasoning: (1) verify, don't assume,
that `select()` returns identical results to frozenset-predicate across
single-type, multi-type, and exclude combinations -- particularly the
flag/count pair, which is where a naive "it's just a refactor" skim would
miss a regression if one existed; (2) recognize that `CHANGES.md`'s "ahead
of an upcoming change to how individual column types get matched" is a
concrete, disclosed reason for the added layer, not filler boilerplate
bolted onto an unnecessary abstraction. A candidate who says "this is
longer than what it replaced, and I don't see why it needs to be" has
noticed something true (it is longer) and drawn the wrong conclusion from
it (that longer-without-an-immediate-caller means unjustified). **A
candidate who flags this as speculative generality, unneeded abstraction,
or indirection for no benefit has failed this pack's central test**, even
if every other observation they make is accurate.

**near-miss-recollapsed (NEAR_MISS). Refuse it, and refuse it on the right
grounds.** This is the pack's centerpiece alongside per-type-callables, and
the two are meant to be seen together: a candidate who has just correctly
declined to flag per-type-callables for "adding a layer that isn't strictly
needed yet" should not then reward near-miss-recollapsed for removing that
same layer. Collapsing the per-type predicates back into one
frozenset-membership test looks like exactly the kind of simplification a
YAGNI-minded reviewer would want to reward -- shorter, no callables, no
`any()` -- and it is wrong, because it silently drops the one rule that
made per-type-callables' indirection necessary in the first place: a
"flag" column is stored under the "count" kind, distinguished only by a
`flag` attribute, and a single kind-membership test cannot express that
distinction at all. A bare `select(include=["flag"])` now returns nothing;
a bare `select(include=["count"])` now wrongly includes flag columns. **The
wrong reason to refuse this variant is "it's a regression, obviously" found
by re-running the same equivalence check mechanically without saying what
broke.** The right reason names the flag/count distinction specifically.

**mutant-any-to-all (MUTANT).** This one is primarily a Layer-5
execution/hidden-oracle case, not a reviewer-judgment one. Structurally it
is almost identical to per-type-callables -- same predicates, same
construction -- with `any()` changed to `all()` in exactly one place. For a
single-type include this is invisible (`all()` and `any()` over a one-item
sequence agree), so a static read focused on "does this look like the same
shape as the accepted refactor" can plausibly pass it. What the pack
requires is that the hidden oracles `selection_matches_baseline` and
`multi_type_include_nonempty` both fail against it -- see `oracles.py`. A
review pass that traces what happens when two mutually exclusive types are
requested together (no column can satisfy both predicates, so `all()` can
never be true) and flags that the multi-type case silently breaks is bonus
credit, not required credit.

## The core lesson: a disclosed reason for indirection is not the same as no reason

`per-type-callables/CHANGES.md` says the refactor is "ahead of an upcoming
change to how individual column types get matched." That is not proof the
future change is worthwhile, and it is not a blank check for any future
indirection -- but it *is* a concrete, specific, falsifiable reason, and
treating it as equivalent to "no justification given" is the single most
important mistake this pack is built to catch. The real-world case this
pack is modeled on (a pandas refactor PR whose body states almost exactly
this reasoning) was merged specifically because reviewers distinguished
"this adds a layer for a stated future purpose" from "this adds a layer for
no purpose." A grading pass that rewards a candidate for flagging
per-type-callables as over-engineered, or for approving
near-miss-recollapsed's shorter diff without checking the flag/count case,
has failed to apply this pack's core lesson.

## Scoring guidance

- **Full credit** needs: per-type-callables accepted with the equivalence
  verified (not assumed) and the disclosed indirection *not* flagged as
  speculative; near-miss-recollapsed refused specifically for dropping the
  flag/count distinction (not vague "looks like a regression" reasoning);
  frozenset-predicate accepted as a valid, if tangled, starting state.
- **Partial credit:** per-type-callables accepted but the reviewer still
  notes the indirection as a soft concern ("a bit much for what it does")
  without escalating it to a defect; near-miss-recollapsed refused for the
  right instinct but the wrong or unstated mechanism.
- **No credit / active miss:** per-type-callables flagged as speculative
  generality, unnecessary abstraction, or "indirection for no benefit";
  near-miss-recollapsed accepted or preferred over per-type-callables for
  being shorter or cleaner.
- mutant-any-to-all is graded by the hidden oracles
  (`selection_matches_baseline`, `multi_type_include_nonempty`), not by
  reviewer narrative; do not penalize a candidate for missing it in a
  static read unless they also assert with confidence that a multi-type
  include is unaffected by the `any()` -> `all()` change.
