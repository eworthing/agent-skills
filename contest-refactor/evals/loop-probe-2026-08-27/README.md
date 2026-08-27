# Loop probe — does a restraint miss reach the code? (n=1, 2026-08-27)

The 23-pack review sweep measured **5 restraint misses**: cases where a blind
single-shot reviewer proposed removing structure the pack declares load-bearing. That
measurement stopped at the Critic. It never asked the question that matters for output
quality: **does such a proposal survive to become an applied edit?**

This probe asks it once.

## Setup

Specimen: `store-core-composition-residual/core-composition-with-dead-isolation`, the
accepted variant, copied out to a throwaway SwiftPM package (102 lines, 2 candidate-
visible files, plus a generated `Package.swift`). Known ground truth from its manifest:

- `must_find` #3 — the unreferenced `actor QuietQueue` is a real residual and naming it
  is required for full credit.
- `must_not_find` #2 — treating the `Panel` protocol and its two marker types as
  ceremony to delete is the restraint miss. `Panel`'s generic constraint is what buys
  the compile-time key-path check.

In the blind sweep, 1 of 3 reviewers took the bait and proposed deleting `Panel`.

A sonnet agent ran the skill's own Critic → Architect → Execution flow from
`method.md`, `architecture-rubric.md` and `lens-generic.md`, blind (no manifest, no
`evals/` access), and applied its own fixes.

## Result

**The loop improved the code and did not commit the restraint miss.**

- **Deleted `QuietQueue`** — the correct find, matching `must_find` #3.
- **Left `Panel` / `EditorPanel` / `InspectorPanel` untouched**, and justified it
  unprompted in its own scorecard: *"the generic `Panel`/`Workspace` design is justified
  by a real compile-time safety property, not costume."*
- **Added a real test target**, moving regression assertions out of `main.swift` (where
  `swift test` could never see them) into XCTest. Verified: `Executed 1 test, with 0
  failures`. `swift build` passes.

## The precise finding, which is narrower than the good news

**The Simplify Pressure Test rejected nothing — because nothing bad was proposed.** The
guard that prevented the bad edit was not SPT; the bad proposal never arose. Running the
full method, the Critic recognised `Panel` as load-bearing where a single-shot reviewer
given only the review prose did not. SPT remains **unverified as a backstop**: it has
not yet been observed catching an over-merge, because it has not yet had to.

## The result the corpus cannot see

The loop's most valuable contribution here is not in the pack's `must_find` at all.
Regression assertions were hidden in an executable's `main.swift`, invisible to
`swift test` — real, shippable tests that no tooling would ever run. The loop found that,
moved them to the right Interface, and the corpus has no opinion about it either way.

The corpus grades find / don't-find against seeded defects. On this specimen the loop's
actual quality contribution was structural work outside that frame entirely.

## Limits

n=1. One 102-line specimen, far smaller than the repos the skill targets. This ran the
skill's **prose** applied by an agent, not the full harness with `LOOP_STATE.json` and
the 50 gates — deliberately, because a real invocation writes loop state into the
current working directory. Gates check emission shape rather than code quality, so they
are not load-bearing for this question, but this is not evidence about them.

One run is not a rate. It is the first evidence in this project connecting Critic
judgment to final output, and it points the opposite way from the worry that prompted it.

---

# Extension to n=3 — 2026-08-27

Pre-registered in `PREREG_N3.md` before either run. Same method, two more specimens.

## Specimen 2 — `pytest-scope-enum-public-compat` / `enum-with-compat-property`

**No miss.** Verified in the file: `_span` still holds the enum, `span` still returns
`str` via `self._span.value`. Applied: deleted `value_of` (zero callers anywhere,
including its own tests); `__lt__` now reuses the module-level `SPANS` instead of
rebuilding `list(self.__class__)` — a *measured* `allowed_findings` entry, pre-registered
as not-a-miss; added a reflexivity test that catches a `<` → `<=` mutation the original
suite passed. 8/8 tests pass.

**First observed SPT rejection.** Inlining `span_from_value`, a thin pass-through, was
proposed and **rejected** on Q5 (no measurable gain) plus insufficient evidence to
certify safety given a live call site. Inlining a pass-through is precisely the collapse
instinct the failed prose clause targeted. After the n=1 probe this file recorded SPT as
"unverified as a backstop"; it is no longer. Caveat: `span_from_value` is not one of the
pack's `must_not_find` items, so this is SPT declining a subtractive change on its own
merits, not a graded save.

## Specimen 3 — `pydantic-typing-extra` / `dual-registry-split`

**No miss**, on all three pre-registered criteria. Verified: `markers_native` and
`markers_legacy` each still instantiate their own `Derived` (no re-export collapse);
`is_derived_marker` and `is_derived_annotation` both survive as separate functions; the
disclosed alias gap was not demanded closed. Two further fixes were **SPT-rejected** —
formalizing the dual registry behind a `MarkerRegistry` Protocol (failed the Unified
Seam Policy: no second adapter, no policy/failure/platform isolation) and extracting a
two-line loop body into a helper (Q2, ceremony).

## And it found a fifth fixture bug the blind sweep missed

The loop reported that a **bare, unsubscripted** `Derived` forward reference was kept as
a stored field. Verified against pristine corpus source: true, and true in **all four**
variants. `behavior_contract` item 1 covers a Derived marker "bare or Tagged-wrapped,
evaluated **or an unresolved forward reference**", so this is a direct contract
violation.

The pack already had an oracle named `bare_unresolved_derived_field_excluded` — and it
does not cover this. "Bare" there means *not Tagged-wrapped*; its input is
`Derived[Missing]`, still subscripted. The fallback pattern required a trailing `[`, so
the one spelling with no bracket at all fell through every check while an
authoritative-sounding oracle name suggested otherwise.

**This is the fifth instance of the identical shape**: a defect surviving because no
oracle combined two conditions the author had only exercised separately — here *bare*
and *unresolved*.

Fixed in all four variants (`Derived(?:\[|(?!\w))`), each staying isolated to its
intended difference: three now exclude it, and `near-miss-bare-form-predicate` still
stores it, which is correct — its defect *is* the bare-form predicate, so it legitimately
fails on unresolved forms. Guarded by
`unsubscripted_unresolved_derived_field_excluded`, which deliberately bypasses the
shared `_namespace_for` helper: that namespace carries `Derived`, so the annotation would
resolve and never reach the unresolved path the oracle exists to cover.

## Where n=3 leaves it

Three specimens, three no-misses, two SPT rejections observed, one new fixture bug found
by the loop that three blind single-shot reviewers did not report.

The restraint misses measured on single-shot reviewers **did not reach the code in any
of the three cases**. Still not a rate: three specimens, one model, one attempt each,
skill prose rather than the gate harness. But the direction is consistent, and the
mechanism is now visible — SPT rejects subtractive and additive over-reach at
fix-application time, which is a stage no measurement in this project had examined.
