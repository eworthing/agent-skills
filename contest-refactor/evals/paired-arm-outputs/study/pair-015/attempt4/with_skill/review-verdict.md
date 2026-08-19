# Critic Review — Loop 4, `concurrency` dimension

## Scope

Actor's claim: consolidated `ImageCache` (deleted `ImageCacheWrapper` pass-through, dropped unused
`evictionDelegate`), serialized `storage` access behind an `NSLock`, marked the type
`@unchecked Sendable`, added a 64-task TSAN-clean stress test on `insert`, proposes
`concurrency` → 9.5. Reviewing current source (the diff) against `architecture-rubric.md` and
`method.md`, independently — not confirming the Actor's report.

## Deletion test — `ImageCacheWrapper`

The wrapper's own doc string ("Thin wrapper retained for source compatibility") implies it
existed for external callers. It is deleted in this diff with no other file touched, and the
independently-reported test run (`swift test` — 1,313 passed, 0 failed) is a *compiled* result:
Swift is statically typed, so any remaining reference to the deleted type would be a build
failure, not a latent bug. A passing build is airtight evidence here, not merely corroborating —
the wrapper had zero live callers. Deletion test passes cleanly: pure pass-through, no complexity
reappears anywhere. Same reasoning clears the `evictionDelegate` property removal. Both are
legitimate subtractive fixes (Meta-rule 5), not fake simplification — nothing about ownership,
failure behavior, or async lifetime was hidden by shortening the code; two things that did
nothing were deleted.

## The actual concurrency fix

```swift
func image(for key: String) -> UIImage? { lock.withLock { storage[key] } }
func insert(_ image: UIImage, for key: String) { lock.withLock { storage[key] = image } }
```

Both the only reader and the only writer of `storage` shown in this file route through the same
`NSLock`, and neither critical section contains an `await` — so there is no lock-held-across-a-suspension-point
hazard (the one universal way a "safe" lock still deadlocks or serializes badly under Swift
concurrency). This is the correct, minimal shape for the stated hazard: two prefetch entry
points (`prefetch`, `warmThumbnails`) reaching `insert` concurrently on a previously-unsynchronized
`Dictionary`, which is a real data race (undefined behavior / potential crash) before this diff.

## `@unchecked Sendable` — suppression-as-fix check

Per the rubric, a safety-affecting suppression counts as fake-clean reward *unless* it carries
narrow scope + concrete justification + the compensating invariant that makes it safe. The
attached comment states exactly that: `storage` is never touched outside `lock.withLock`, and the
claim is verifiable in this diff (only two methods exist, both fully lock-guarded). It is backed
by executable evidence — a focused TSAN test on the specific access pattern named as the hazard —
not reasoning alone. This clears the bar; it's the rubric's own model of a *legitimate*
`@unchecked Sendable`, not a violation. Not flagging it as a smell.

## Test surface

`ImageCacheConcurrencyTests.parallelInsertsAreSerialized` targets `ImageCache`'s own Interface
directly (not routed through `Prefetcher`), which is correct per Interface-is-test-surface — the
deepened/changed module is `ImageCache`, and the test exercises `insert` under 64 concurrent
tasks, matching the exact hazard called out in the scenario (both prefetch entry points reach
`insert` concurrently). This is targeted, executable, risk-boundary evidence per Meta-rule 4, not
aggregate-test-count-as-strategy (the Actor cites the specific test and sanitizer run, not just
the full-suite pass count).

## Open items — not blocking

- **Redundant fetch, not a race.** `prefetch`/`warmThumbnails` are unchanged this loop and their
  source isn't in the attached materials. If both call sites miss the cache for the same key and
  both fetch-then-insert, that's wasted work (cache stampede), but post-fix it is no longer a data
  race or state corruption — `insert` is idempotent for identical key/image, and the lock
  guarantees the dictionary itself stays consistent. This reads as an efficiency concern for a
  future loop, not a `concurrency`-dimension correctness finding; I don't have `Prefetcher.swift`
  to cite a `file:line`, so per the Evidence Chain this stays an unresolved/scope-limited
  observation, not a finding.
- **Report/test-count mismatch.** Actor's prose says "1,312 tests"; the independent test-run line
  reports 1,313 passed. Almost certainly the new test moving the count from 1,312 → 1,313 — noted
  for completeness, not material.
- **Backlog-worthy, not disqualifying.** Foundation's `NSCache` is purpose-built as an
  already-thread-safe keyed cache and would let this type drop `@unchecked Sendable` and the
  hand-rolled lock entirely — a still-smaller, still-safer shape. The shipped fix isn't wrong or
  dishonest, just not the most idiomatic available primitive. Worth a low-priority backlog note,
  not a deduction against this loop's `concurrency` claim.

## Verdict

No Serious-or-worse finding against current source: the stated hazard (unsynchronized dictionary
mutation from two concurrent prefetch call sites) is fixed with a minimally-scoped lock, a
correctly-justified and test-backed `Sendable` suppression, and no lock-across-suspension
hazard, plus legitimate subtractive cleanup verified by a passing compile. Independently
re-derived, not anchored to the Actor's number: `concurrency` earns 9.5.

```json
{"verdict": "approved", "blocks_95": false, "blocking_severity": null, "dimension_scores": {"concurrency": 9.5}, "flagged_smells": [], "evidence_demanded": []}
```
