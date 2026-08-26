# Grading — cpython-genexpr-iterability

Grader-only. Not shown to a candidate (see `provenance.json`'s `grader_only_files`).

## What this pack is actually testing

Not "can the candidate spot a redundant `iter()` call." **Noticing the
redundancy is the easy 80% and is worth partial credit at best.** The
redundancy in `eager-guard/lazyselect.py` is real: for any well-behaved
source, the eager `iter(iter(source))` guard in `__init__` does nothing that
`__iter__`'s own `iter(self._source)` doesn't redo. A candidate that stops
there and says "delete this, it's dead work" has found a true fact and
reached the wrong verdict.

**A candidate that only notices the redundancy — without reasoning about
error timing — has failed this pack.** The guard is redundant *and*
load-bearing: deleting it moves a `TypeError` from construction time to
first-iteration time, which is a real, user-visible behavior change, not a
no-op cleanup. Full credit requires the candidate to say *both* halves: yes
this is dead work for the common case, *and* removing it changes what a
caller who never iterates the result will observe.

## What full credit looks like, per variant

**eager-guard (RED).** Flag it. The specific, required reasoning: the eager
check makes `LazySelect` behave inconsistently with every other lazy type in
this module (construction never touches `source` anywhere else), and it has
a real victim — an iterable whose `__iter__()` returns an iterator lacking
its own `__iter__` used to work and now doesn't. A candidate who flags this
purely as "unnecessary double iteration, delete it" without naming either
the timing implication or the legacy-iterable regression gets partial
credit, not full.

**lazy-consistent (GREEN).** Accept it, and *do not* re-flag the timing
change as a regression. It's the same change eager-guard's removal implies,
done right: one line deleted, retention of `self._source` kept exactly as
it was, the one test that had encoded the old (wrong) timing replaced rather
than just deleted, and a short `CHANGES.md` note recording the behavior
change for anyone relying on the old timing. This is the `restraint_reason`
case: treating the disclosed timing shift as a fresh defect, after the pack
just spent eager-guard's review establishing that the *old* timing was the
actual bug, is a coherence failure, not caution.

**near-miss-checked-source (NEAR_MISS). Refuse it, and refuse it on the
right grounds.** This is the pack's centerpiece and the part hardest to get
right. `CheckedSource` looks like an improvement: it's a real class, it has
`__slots__`, it factors validation out of `LazySelect`, and if you ran a
generic "did the redundant check move" scan you might credit it as
addressing the finding. It doesn't. `LazySelect.__init__` still always
wraps `source` in a fresh `CheckedSource` unless it's already one, and
`CheckedSource.__init__` still runs the same `iter(iter(iterable))` double
check. Construction still raises eagerly; the legacy-iterable shape is
still rejected. **The size and apparent care of this diff is itself a
warning sign, not a mitigating factor** — a candidate that credits it for
thoroughness ("look, they even added tests for the new wrapper") has been
fooled by effort into missing that none of the three things wrong with
eager-guard actually changed. This is the pack's #126408 shape: plausible,
well-executed, and wrong, because it moved the check instead of asking
whether the timing itself needed to change.

**mutant-dropped-retention (MUTANT).** This one isn't primarily a reviewer-
judgment case — it's an execution/hidden-oracle case (Layer 5). A candidate
asked to review its diff in isolation might reasonably call it a plausible
simplification (it does remove the double-`iter()` guard, in a sense, and
the code reads cleanly); the pack does not require a static reviewer to
catch the corruption class by inspection alone. What the pack *does*
require is that the hidden oracle `corruption_repro_stays_fixed` fails
against this variant and passes against the other three — see `oracles.py`.
If a review pass on this diff also notices "this caches a single iterator
instead of the source, so the object becomes single-use, and if anything
downstream reassigns the internal handle expecting fresh derivation, this
will misbehave," that is bonus, not required, credit.

## Why the stale test suite must not be trusted

Run `python3 test_lazyselect.py` inside `eager-guard/` and it passes. That
result says the guard code matches its author's own model of correctness,
and nothing else. **Passing tests are not, on their own, an oracle for
"this is right"** — that is the single most important idea this pack
encodes (see `oracles.py`'s `stale_test_trap`, which runs every variant's
own bundled suite and confirms all four pass, deliberately including the
wrong ones). A grading pass that treats "the tests pass" as any part of the
justification for approving eager-guard has failed to apply this pack's
core lesson.

## Scoring guidance

- Full credit needs: eager-guard flagged (redundancy *and* timing *and* the
  legacy-iterable regression), lazy-consistent accepted without a timing
  re-flag, near-miss-checked-source refused on relocation-not-removal
  grounds specifically (not just "too big" or "too clever").
- Partial credit: eager-guard flagged on redundancy alone, or
  near-miss-checked-source refused for vague "over-engineered" reasons
  without identifying that it preserves the exact behavior under review.
- No credit / active miss: eager-guard approved, or lazy-consistent
  re-flagged for the timing change, or near-miss-checked-source accepted as
  "the redundancy is gone now."
- mutant-dropped-retention is graded by the hidden oracle
  (`corruption_repro_stays_fixed`), not by reviewer narrative; do not
  penalize a candidate for missing it in a static read unless they also
  claim the diff is behavior-preserving with confidence a real hidden test
  would contradict.
