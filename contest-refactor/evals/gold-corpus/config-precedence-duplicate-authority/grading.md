# Grading — config-precedence-duplicate-authority

Grader-only. Not shown to a candidate (see `provenance.json`'s `grader_only_files`).

## What this pack is actually testing

Not "can the candidate spot two functions that look similar." **The real test
is whether a candidate who has learned to leave deliberate separation alone
can still recognise duplicate authority and say so.**

Every other pack in this corpus makes restraint the right answer on the
collapse axis. A 2026-08-26 scan of all 25 manifests found **no** `must_find`
or `residual_findings` item anywhere requiring a reviewer to recommend
consolidating two sites. That is a property of how the corpus was harvested,
not of real code, and it leaves a hole with teeth: **a reviewer that refuses
every merge scores perfectly on the other 25 packs, and nothing in the corpus
notices.** This pack is the detector for that failure.

So it is deliberately the mirror image. `effective_value` and
`describe_source` answer the same question — which layer owns this key — and
answering it twice is what let them drift. Consolidation is the remedy, and
`must_find` item 2 requires the candidate to **recommend** it.

## The trap, and who falls into it

`must_not_find` item 1 is the one to watch. The two functions **do** serve
different callers: the ordinary read path and the `--explain` command. That
difference is real, and it is the honest-sounding reason to decline the merge.
It is also irrelevant — different callers is not different policy. A candidate
carrying a "resemblance is not duplication" rule from elsewhere will find that
difference and stop, and stopping there is the over-correction this pack is
built to catch.

The second trap is `must_not_find` item 2: repairing `describe_source`'s
truthiness test in place. It makes the observable symptom go away and the
oracle pass, and it leaves two owners of the layer order. A candidate who
proposes it has diagnosed a condition bug where the defect is structural.

## Why the near-miss is hard

`near-miss-shared-presence-only` is not a strawman. Its `_carries` helper is
genuine consolidation of a genuine duplicate, and it really does fix the
empty-override case that `two-owners-drifted` gets wrong. Its bundled suite
passes. What it does not consolidate is the **order**, and its second copy of
the order puts user ahead of project — so the same defect class survives on an
input the suite never constructs (one key carried by two layers at once). A
candidate crediting it for removing visible duplication has graded the
appearance of the fix.

## Why one oracle would not be enough

Agreement and order fail independently, and each certifies half the variants
on its own:

- `mutant-reordered-precedence` resolves **self-consistently** against the
  wrong order. `value_and_reported_source_agree` passes it.
- `near-miss-shared-presence-only` keeps the **right order** in
  `effective_value` and still disagrees with itself.
  `env_outranks_project` passes it.

Only the pair separates all four. `default_when_no_layer_carries` is the
control: it holds everywhere and stops a variant satisfying the other two by
degenerating to the default.

## Known weakness

Constructed, not harvested — the only such pack here. There is no maintainer's
judgment behind it, only the canon's own duplicate-authority smell. It should
be replaced by a harvested equivalent if one is found. Until then it is the
corpus's only guard against a reviewer that has learned restraint too well.
