# Grading — swift-collections-ordered-replace-primitive

Grader-only. Not shown to a candidate (see `provenance.json`'s
`grader_only_files`).

## What this pack is actually testing

Not "can the candidate confirm a shared move primitive didn't break
anything." Confirming that is real work, and it's the easy half. **The real
test is what the candidate does with a delegation that reads as an even
cleaner deduplication than the accepted change.** `near-miss-delegates-to-roster-replace`
does not just factor out the mechanical move -- it calls the sibling
container's whole public checked operation, which looks like it removes
even more duplication than `shared-move-primitive` does. It is wrong on two
independent, concrete, checkable grounds, and neither shows up on a
success/failure check alone.

## The real-world table this pack is built from

The real PR's author pre-emptively compared the shipped approach against
calling the sibling container's public method directly, in a table (not
reproduced verbatim in any candidate-visible file -- it lives only here and
in `provenance.json`):

| | Direct public-method call | Shared internal primitive (what shipped) |
| --- | --- | --- |
| Duplicate label | traps with `member already present` | keeps `label already in use: '<label>'` |
| Out-of-range index | traps with `position outside roster` | keeps `no entry at that position` |
| Hash lookup | re-runs the lookup inside the callee | reuses the bucket the caller already resolved |

This fixture's `Roster`/`Ledger` translate that table directly:
`Roster.replace`'s own wording is `member already present` / `position
outside roster`; `Ledger.replaceLabel`'s own wording is `label already in
use: '<label>'` / `no entry at that position`. The near-miss is exactly the
left column; the green is exactly the right column.

## What full credit looks like, per variant

**duplicated-inline-move (RED). Accept it as a correct, if duplicated,
starting state.** `Roster.replace` and `Ledger.replaceLabel` each perform
the identical three-step move inline, with their own checks and their own
diagnostics. Nothing is wrong with this code; the duplication is real and
worth naming, but fixing it is exactly what the next variant does.

**shared-move-primitive (GREEN). Accept it outright.** The three-step move
is factored into one generic `moveIntoPlace`, taking an already-resolved
position; each container keeps its own checks and its own diagnostic
wording. `Ledger.replaceLabel` resolves the label's position once and
reuses it for both the labels move and the values move -- no repeated
lookup.

**near-miss-delegates-to-roster-replace (NEAR_MISS). Refuse it, and refuse
it for both real reasons, not just the easiest one.** This is the pack's
centerpiece, and it is built to be genuinely persuasive: `Roster.replace`
already bundles duplicate checking, not-found checking, and the move
together, so having `Ledger.replaceLabel` just call it looks like it
removes *more* duplication than the accepted change does. A full-credit
review separates two distinct failures:

1. **Ledger's own diagnostics silently change.** A duplicate label now
   traps with `member already present` instead of `label already in use: '<label>'`; a
   missing label now traps with `position outside roster` instead of `no
   entry at that position`. Nothing crashes, and no test that only checks *whether*
   a call trapped -- not *what it said* -- will ever notice.
   `oracles.py`'s `diagnostic_wording_preserved` checks the wording
   directly and fails only here.
2. **The lookup work doubles.** `Roster.replace` resolves the label's
   position internally to do its own move, but that resolved position is
   not returned to the caller. `Ledger.replaceLabel` still needs a
   position for its own values-array move, so it looks it up again --
   `oracles.py`'s `lookup_work_count` reports 2 here against
   `shared-move-primitive`'s 1. This is invisible to anything but counting
   directly.

A review that only catches one of these two has done real work but not
full-credit work. **Neither failure shows up as a wrong return value on the
success path** -- both are strictly about *what the diagnostic says* and
*how much redundant work happens*, which is exactly why this near-miss is
harder to catch than a near-miss that changes visible behavior.

**mutant-reordered-move-primitive (MUTANT).** This one is a hard,
unmissable Layer-5 case, not a reviewer-judgment one: identical in shape to
`shared-move-primitive` -- same checks, same diagnostics, same single
lookup -- with `moveIntoPlace`'s three steps reordered (append, remove,
*then* swap, instead of append, swap, *then* remove). The newly appended
member is discarded before it is ever swapped into place, and an unrelated
member is corrupted into the old member's slot instead. The call still
reports `.success`; `oracles.py`'s `replace_semantics_preserved` checks the
*resulting contents*, not the return value, and fails only here. A static
read that catches the reordering is bonus credit, not required credit.

## Oracle taxonomy

Per this corpus's own four-way oracle classification (control /
discriminator / demonstration / gap):

- **`diagnostic_wording_preserved`** and **`lookup_work_count`** are
  **discriminators** for the near-miss -- each fires against exactly
  `near-miss-delegates-to-roster-replace` and nowhere else.
- **`replace_semantics_preserved`** is a **discriminator** for the mutant
  -- fires against exactly `mutant-reordered-move-primitive`.
- **`ordinary_replace_matches_across_non_mutant_variants`** is a
  **control**: a second, independent replace scenario, checked only across
  the three non-mutant variants, which must all agree. It holds everywhere
  by design -- it would only fail if this fixture itself were broken in a
  way that made the other three oracles' results meaningless.
  `mutant-reordered-move-primitive` is deliberately excluded from this
  control's scope, since it is known to diverge and
  `replace_semantics_preserved` is the check built to catch exactly that.

Every non-control oracle in this pack has an observed RED: each was run
against its target variant and watched fail, then run against
`shared-move-primitive` and watched pass, before being considered done.

## Scoring guidance

- **Full credit** needs: shared-move-primitive accepted outright;
  near-miss-delegates-to-roster-replace refused for *both* the diagnostic-wording
  change and the doubled lookup, not just one; duplicated-inline-move
  accepted as a correct, if duplicated, starting state.
- **Partial credit:** near-miss-delegates-to-roster-replace refused for
  only one of the two reasons (usually the diagnostic wording, since it is
  easier to notice by inspection than counting lookup calls), or refused
  correctly but with vague "delegating to another type feels risky"
  reasoning rather than naming what specifically changes.
- **No credit / active miss:** near-miss-delegates-to-roster-replace
  accepted because it looks like a more thorough deduplication than the
  shared primitive; shared-move-primitive's per-container checks and
  diagnostics treated as duplication that should be collapsed further.
- mutant-reordered-move-primitive is graded by the hidden oracle
  (`replace_semantics_preserved`), not by reviewer narrative; do not
  penalize a candidate for missing it in a static read unless they also
  assert with confidence that the move primitive is correct without
  checking the resulting contents of an ordinary replace.
