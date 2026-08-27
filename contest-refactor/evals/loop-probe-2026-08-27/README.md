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
