# Grading — pandas-groupby-plot-imperfect-gold

Grader-only. Not shown to a candidate (see `provenance.json`'s `grader_only_files`).

## What this pack is actually testing

Not "can the candidate spot that pinning a label via a side effect is bad
practice." Recognizing that side-effect-pinning is a smell is the easy half
of this pack. **The real test is what the candidate does with
dedicated-path-incomplete: the accepted, merged fix that correctly removes
the side effect and ships its own changelog asserting no user-visible
change -- while that claim is false for one of the two group shapes it has
to handle.**

**Scoring dedicated-path-incomplete a flawless 10 is a failure. Rejecting it
outright is an equal and opposite failure.** The only passing verdict is
accept it, and name the Panel-group residual specifically.

## What full credit looks like, per variant

**side-effect-pinning (RED).** Flag it. The specific, required reasoning:
plotting depends on a side effect (`.label` pinned by `apply_general`) of a
helper whose actual job is aggregation, not display. This is not merely
"redundant work" -- it is an undeclared coupling between two unrelated
concerns that happens to work today because nothing has separated them yet.

**dedicated-path-incomplete (GREEN -- imperfect gold). Accept it, and name
the residual.** This is the pack's centerpiece. `apply_plot` is a real,
directionally-correct fix: plotting no longer depends on `apply_general`'s
side effect. Its `CHANGES.md` says "no user-visible change." **That claim is
false for Panel (multi-column) groups** -- `apply_plot` forwards the key
explicitly for Lane groups and forwards nothing at all for Panel groups, so
`scatter(panel_group, legend=True)` silently returns no label. A candidate
who repeats the changelog's claim without checking both group shapes has
*accepted* a neutrality claim instead of *verifying* it -- exactly the
failure mode this pack is built to catch. A candidate who instead refuses
the whole variant because the claim is false has overcorrected: the fix is
real, it is the accepted state, and the correct verdict is acceptance with
the residual named, not rejection.

**key-forwarded (ALTERNATE_GREEN).** Accept without reservation. It forwards
`(group, key)` uniformly regardless of shape, closing exactly the gap
dedicated-path-incomplete left, and ships a regression test that exercises
the Panel-legend case its predecessor's own test suite never touched.

**near-miss-restore-pinning (NEAR_MISS). Refuse it, and refuse it on the
right grounds.** The legend works again for Panel groups -- that is real,
observable, and exactly what a symptom-focused fix would produce. It gets
there by mutating Panel groups with a pinned `.label` attribute, which is
precisely the side-effect coupling the dedicated path exists to remove, just
scoped to one group shape instead of both. **A candidate that credits this
variant for "fixing the bug" because the legend now displays correctly has
been fooled by a working symptom into missing the structural regression
underneath.** The wrong reason to refuse it is "this looks hacky" or "too
inconsistent between the two branches" -- the right reason is that it
reintroduces the exact coupling under review, and does so while leaving the
Lane path's legitimate fix untouched, so a diff-shape scan alone will not
surface it.

**mutant-mislabeled-groups (MUTANT).** This is primarily a Layer-5
execution/hidden-oracle case, not a reviewer-judgment one. A static read of
its diff might plausibly pass unless the reviewer traces exactly what value
`key` holds at the call site (a sequence position, not the group's own key).
What the pack requires is that the hidden oracle `legend_labels_correct`
fails against it -- see `oracles.py`. Its own bundled test only checks that
a label is *present*, never that it is *correct*, which is why its own
suite passes despite every legend being wrong; a review pass that notices
this test gap is bonus credit, not required credit.

## The core lesson: verify neutrality claims, don't accept them

`dedicated-path-incomplete/CHANGES.md` states "no user-visible change." Run
`plot_legend_labels` against a Panel group and that claim is false. **A
changelog's own claim of behavior-neutrality is not, by itself, evidence of
behavior-neutrality** -- that is the single most important idea this pack
encodes, and it is exactly what happened in the real-world case this pack
is built from: an experienced maintainer wrote "this is a pure refactor (no
behavior change)" in good faith, the change was reviewed and merged, and it
was still wrong for one of the two shapes it had to handle. A grading pass
that treats "the changelog says it's neutral" as any part of the
justification for skipping the Panel-group check has failed to apply this
pack's core lesson.

## Scoring guidance

- **Full credit** needs: side-effect-pinning flagged (the coupling, not just
  "redundant"); dedicated-path-incomplete **accepted** with the Panel-legend
  residual named specifically (not "seems fine" and not "broken, reject");
  key-forwarded accepted without reservation; near-miss-restore-pinning
  refused specifically for reintroducing pinning-as-mutation on Panel
  groups (not for vague "inconsistency" or "looks hacky" reasons).
- **Partial credit:** dedicated-path-incomplete accepted but the residual
  left unnamed, or near-miss-restore-pinning refused for reasons that don't
  identify what it actually reintroduces.
- **No credit / active miss:** dedicated-path-incomplete scored a flawless
  or perfect verdict; dedicated-path-incomplete rejected outright as
  unacceptable; near-miss-restore-pinning accepted as "the fix" because the
  legend displays correctly.
- mutant-mislabeled-groups is graded by the hidden oracle
  (`legend_labels_correct`), not by reviewer narrative; do not penalize a
  candidate for missing it in a static read unless they also assert with
  confidence that every legend label is correct.
