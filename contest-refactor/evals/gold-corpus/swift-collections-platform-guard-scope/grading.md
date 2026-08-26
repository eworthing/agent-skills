# Grading — swift-collections-platform-guard-scope

Grader-only. Not shown to a candidate (see `provenance.json`'s
`grader_only_files`).

## This pack's near-miss is not synthetic

Every near-miss in every other pack in this corpus — twelve packs before
this one — was authored by us and graded by us. That is a real, standing
gap in the corpus: it measures whether a reviewer catches a defect we
invented, never whether a reviewer's judgment matches a real maintainer's.
This pack's near-miss is `near-miss-capability-guard-broad-admit`, drawn
directly from a real external contributor's pull request
(`apple/swift-collections#298`), closed unmerged by the real maintainer,
with the maintainer's reasoning on the public record. The grading below is
not our own invented standard — it is a fixture-vocabulary translation of
an actual, adjudicated real-world review outcome.

## Why the platform conditional is modelled as data, not real `#if`

The real code's outer condition only produces a different answer on
platforms this machine cannot compile for at all: the newly-shipped
platform, and any non-vendor platform. Built on real `#if os(...)` /
`canImport(...)`, every variant would behave identically at runtime on
this machine, and no oracle could discriminate between them. So this
fixture models the compile-time guard as ordinary data instead: a
`Platform` enum with six cases (the four originally-affected platforms,
the newly-shipped one, and a platform outside the vendor's runtime family
entirely), a `Version` struct, and a `guardAdmits(_:)` predicate per
variant standing in for the `#if`. The disagreement between the real PR's
three positions is entirely a question of *which platforms a predicate
admits* and *whether the outer guard changes anything the inner check
doesn't already decide on its own* — both fully expressible, and fully
testable, as plain set-membership and equality checks over this data. A
reader should understand this substitution going in: nothing here recovers
real Swift's actual `#if`/`#available` compilation behavior, only the
judgment structure it produces.

## What full credit looks like, per variant

**explicit-platform-list (RED). Accept it as a correct, if verbose,
starting state.** An outer guard admits exactly the four platform
families that share the underlying bug; an inner check reports whether
each one's runtime is new enough that the bug no longer applies. Nothing
is wrong with this code. It *looks* like it needs a fifth case once a new
platform ships — that appearance is the trap the rest of the pack is built
around, not a defect in this variant.

**guard-removed-availability-only (GREEN). Accept it outright, and
recognize it as the actual correct answer, not merely an acceptable
alternative to the near-miss.** The outer guard is gone; the inner check
runs unconditionally for every platform. This is demonstrably safe, not
just plausible-looking:
`oracles.py`'s `threshold_preserved_vs_baseline` confirms the answer is
unchanged on all four originally-guarded platforms at both an old and a
new version, and `guard_removal_is_behaviorally_neutral` confirms the
answer is *also* unchanged on the two platforms the old guard excluded —
because the inner check's own default already reports "not affected" for
anything it holds no threshold for. Both checks holding is what makes
"just delete it" correct rather than merely convenient.

**near-miss-capability-guard-broad-admit (NEAR_MISS). Refuse it, and
refuse it for all three of the real reasons, not just the easiest one.**
This is the pack's centerpiece, and it is built to be genuinely
persuasive — a new platform family shipped, spelling out a fifth case by
hand does not scale, and a single capability predicate looks DRY and
future-proof. A full-credit review separates three distinct failures:

1. **The premise is false.** The four-platform list was never
   incomplete. The underlying bug never affects the newly-shipped
   platform, so no fifth entry was ever needed. The change solves a
   problem that does not exist.
2. **The substitute is not an exact equivalent.** The broad predicate
   admits the newly-shipped platform; the deliberate four-platform list
   excluded it. `oracles.py`'s `guard_admits_exactly_legacy_four` checks
   the two guards' admitted sets directly and confirms they differ, even
   though — and this is the subtle part — no current inner-check *output*
   exposes that difference, because the platform in question has no
   recorded version threshold either way. A reviewer who only checked
   outputs and found none of them changed has not checked the thing that
   actually differs.
3. **Explicitness was the point.** Naming the four platforms directly
   documents the exact scope of a specific, known workaround. A broad
   runtime-family predicate erases that documentation value from the
   code, independent of whether it currently changes any answer.

**And then the part most reviews will miss even after getting all three
of those right: the correct response is not "keep the original list."**
The maintainer's own counter-proposal — this pack's GREEN — is *smaller*
than the original, not a defense of it. A review that refuses the
near-miss correctly on all three grounds above, but concludes the
four-platform list should simply stay as it was, has earned partial
credit: it caught the wrong turn without finding the actually-better road.
Full credit requires naming `guard-removed-availability-only`'s shape —
delete the guard, keep only the inner check — as the correct outcome.

**mutant-dropped-threshold (MUTANT).** This one is a hard, unmissable
Layer-5 case, not a reviewer-judgment one: identical in shape to the
accepted variant, with one platform's recorded version threshold dropped,
so every version of that platform — including a genuinely old, still-buggy
one — reports unaffected. `oracles.py`'s `threshold_preserved_vs_baseline`
fails against it specifically and only for that one platform; every other
platform is untouched. A static read that catches the missing dictionary
entry is bonus credit, not required credit.

## Oracle taxonomy — two of these are meant to never fail

Per this corpus's own documented four-way oracle classification (control /
discriminator / demonstration / gap), two of this pack's four checks are
designed to hold for every variant, and that is not an oversight:

- **`guard_removal_is_behaviorally_neutral` is a demonstration.** Its
  uniformity — every variant agrees on the two platforms the original
  guard excluded — is the empirical fact `guard-removed-availability-only`
  rests on. An oracle that fired here would be undermining the pack's own
  green, not testing it.
- **`old_affected_version_still_reported_affected` is a control.** It
  confirms a genuinely old, affected platform version still reports
  affected in every variant. It would only fail if this fixture itself
  were broken in a way that made the other three oracles' results
  meaningless — mutant's threshold drop specifically targets a different
  platform (wrist, not the anchor platform this control checks), so this
  control correctly never fires in this pack's design.

`guard_admits_exactly_legacy_four` and `threshold_preserved_vs_baseline`
are the pack's two discriminators, and each fires against exactly one
variant (the near-miss and the mutant respectively) — see `oracles.py`'s
module docstring for the full mapping.

## Scoring guidance

- **Full credit** needs: guard-removed-availability-only accepted outright
  as the correct answer; near-miss-capability-guard-broad-admit refused
  for all three reasons (false premise, non-equivalent substitute, lost
  explicitness) *and* with explicit-platform-list's original guard also
  recognized as not the correct stopping point.
- **Partial credit:** near-miss-capability-guard-broad-admit refused only
  for non-equivalence ("not exactly the same predicate") without the
  false-premise or lost-explicitness reasoning, or refused correctly on
  all three grounds but with explicit-platform-list's original list
  treated as the right place to stop rather than guard-removed-
  availability-only's smaller shape.
- **No credit / active miss:** near-miss-capability-guard-broad-admit
  accepted because a new platform shipped and the change looks DRY;
  guard-removed-availability-only rejected or treated as riskier than
  keeping an explicit list, without checking the two oracles that
  demonstrate its safety.
- mutant-dropped-threshold is graded by the hidden oracle
  (`threshold_preserved_vs_baseline`), not by reviewer narrative; do not
  penalize a candidate for missing it in a static read unless they also
  assert with confidence that every platform's threshold is intact.
