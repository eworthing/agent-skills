# Grading — store-core-composition-residual

Grader-only. Not shown to a candidate (see `provenance.json`'s
`grader_only_files`).

## What this pack is actually testing

Not "can the candidate spot that a type-erased container is unsafe." That
is the easiest of three separate judgments this pack asks a reviewer to
hold apart, and get all three right, not just the easiest one:

1. **Architecture recognition** -- prefer the composed, generic-preserving
   `Workspace<Node: Panel>` over the type-erased one, even though it has
   strictly more declarations.
2. **Restraint** -- do not undo the composition for having more protocols
   or types. `near-miss-collapse-back-to-erasure` reverts on a reasonable-
   sounding, genuinely-shorter-diff motivation, and that motivation is
   the trap.
3. **Residual discovery** -- `core-composition-with-dead-isolation` is the
   accepted, architecturally-correct, merged state, and it still carries
   one dead declaration its own author and reviewers did not catch. This
   is this pack's centerpiece, drawn from a real, checked, eleven-month
   gap between the real PR that introduced the dead actor and the real PR
   (by an outside contributor, not the architecture's author) that quietly
   deleted it in a single line.

**Scoring `core-composition-with-dead-isolation` a flawless 10 is a
failure. Refusing the whole architecture over the residual is an equal and
opposite failure.** The only passing verdict is accept the architecture
and name the residual specifically.

## What full credit looks like, per variant

**type-erased-root (RED). Accept it as a correct, if unsafe, starting
point.** Every operation that is actually exercised works. The defect is
what the compiler cannot catch: `child(at:)`'s root type is inferred
purely from whatever key path a caller passes, with nothing tying it to
what a given `Workspace` instance actually boxes.

**core-composition-with-dead-isolation (GREEN -- imperfect gold, 9.5, not
10). Accept the architecture, and name the residual.** `Workspace<Node:
Panel>` pins `child(_:at:)`'s key path root to `Node.State`, so the exact
mistake `type-erased-root` allows is now a compile error
(`key_path_root_type_checked`). The file also declares an actor that
nothing anywhere references (`dead_declaration_unreferenced` confirms this
directly from a source scan). A review that accepts the architecture and
stops has scored `core-composition-clean`'s work and claimed it here.

**core-composition-clean (ALTERNATE_GREEN, the 10). Accept without
reservation, and do not invent a second residual.** Same architecture,
actor removed. `dead_declaration_unreferenced` returns 0 occurrences here
-- if a reviewer reports a dead-code finding against this variant anyway,
that is not caution, it is a hallucination, and it is graded as a miss
just as seriously as failing to find the real one in the previous variant.

**near-miss-collapse-back-to-erasure (NEAR_MISS). Refuse it, and refuse it
on the right grounds.** Its own module comment states the (plausible,
wrong) motivation: the `Panel` protocol and its two marker types are
ceremony this file's own tests never exercise, and removing them shrinks
the type signature surface. **Protocol count and declaration count are not
findings against the composed variants, and they are not a defense of this
one either.** The specific, required reasoning: collapsing back to a
type-erased `Workspace` reintroduces exactly the unsafe key-path handling
the composition exists to remove --
`key_path_root_type_checked` shows the identical unrelated-type key path
that `core-composition-clean` rejects at compile time compiling again
here, silently.

**mutant-scoped-writes-lost (MUTANT).** A hard, unmissable Layer-5 case,
not a reviewer-judgment one: it keeps the composed architecture's exact
shape -- same protocol, same generic container, same compile-time
rejection of an unrelated-type key path -- but `child(_:at:)` captures the
child's state into a local variable at scoping time, so a write through
the scoped child never reaches the root. `scoped_write_reaches_parent`
fails against it specifically. Its own bundled test passes despite the
bug, because that test only checks the scoped child's own state after the
write (which the local cache correctly reflects), never the parent. A
static read that spots the captured-local pattern is bonus credit, not
required credit.

## Why one oracle never fails, and what it is instead

`scoped_child_initial_matches_parent` is a **control**: immediately after
scoping, before any write, the child's value matches what the parent was
constructed with, in every variant including the mutant, whose defect is
confined entirely to the write path. It would only fail if this fixture
itself were broken in a way that made the other three oracles'
results meaningless.

`key_path_root_type_checked` and `dead_declaration_unreferenced` are the
discriminators between the accepted architecture and, respectively, the
near-miss and the imperfect-gold's own residual;
`scoped_write_reaches_parent` is the discriminator between the accepted
architecture and the mutant. See `oracles.py`'s module docstring for the
full variant-to-expectation mapping.

## The core lesson: a correct architecture is not the same claim as a clean one

The real-world case this pack is drawn from is not hypothetical caution
about residuals in general -- it happened, was checked against the
upstream tree, and took eleven months to surface: an actor introduced
alongside a correct, well-reviewed, merged architectural refactor sat
completely unreferenced until an outside contributor, not the original
author, deleted it in a single line. **A candidate who reviews
`core-composition-with-dead-isolation`, correctly prefers it over both
`type-erased-root` and `near-miss-collapse-back-to-erasure`, and reports
nothing further has done the easy two-thirds of this pack's job and
claimed credit for the hard third.**

## Scoring guidance

- **Full credit** needs: `type-erased-root` accepted as a correct starting
  point; `core-composition-with-dead-isolation` accepted **with the dead
  actor named specifically** (not "seems fine" and not "reject the whole
  refactor over one actor"); `core-composition-clean` accepted without a
  fabricated residual; `near-miss-collapse-back-to-erasure` refused
  specifically for reintroducing unchecked key-path roots (not for "too
  many protocols").
- **Partial credit:** `core-composition-with-dead-isolation` accepted but
  the residual left unnamed; `near-miss-collapse-back-to-erasure` refused
  for a vague "too much ceremony" instinct without naming what it
  concretely reintroduces.
- **No credit / active miss:** `core-composition-with-dead-isolation`
  scored a flawless or perfect verdict; the composed architecture refused
  outright for having more types than the type-erased or near-miss
  variants; a dead-code finding reported against `core-composition-clean`,
  `type-erased-root`, `near-miss-collapse-back-to-erasure`, or
  `mutant-scoped-writes-lost`, none of which `dead_declaration_unreferenced`
  supports.
- `mutant-scoped-writes-lost` is graded by the hidden oracle
  (`scoped_write_reaches_parent`), not by reviewer narrative; do not
  penalize a candidate for missing it in a static read unless they also
  assert with confidence that every scoped write reaches the parent.
