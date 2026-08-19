# Review — Loop 4, `concurrency` dimension

## What the diff actually does

`ImageCache` gains an `NSLock` and both `image(for:)` and `insert(_:for:)` now route
through `lock.withLock { ... }`. That is a real, substantive fix: the previous
`storage: [String: UIImage]` dictionary was mutated from whatever thread called
`insert`, with no synchronization, which is a genuine data race once more than one
caller touches the same cache instance concurrently. Wrapping both the read and the
write path in the same lock closes that specific race for the two operations shown.
`ImageCacheWrapper` (a pure pass-through) and the apparently-unused `evictionDelegate`
property are also deleted, which is a reasonable simplification if both really are
dead weight.

So the headline claim — "storage access is now serialized" — is credible for the code
shown. But "safe to share across the prefetch tasks," rated at 9.5, is a stronger claim
than what's actually been verified, and several things in this diff and report don't
add up cleanly enough to sign off on that score.

## Concerns

**1. The `@unchecked Sendable` conformance is un-auditable from this diff alone.**
`@unchecked Sendable` is a manual promise, not a compiler-checked one — its whole
correctness rests on "every stored mutable property is only ever touched inside
`lock.withLock`." The diff hunk shows exactly one stored var (`storage`) protected
correctly, but a hunk is not the whole file. If `ImageCache` has any other stored
property elsewhere in the class body (a counter, a size limit, a last-access
timestamp — nothing in the report rules this out) that isn't shown in this hunk,
the `@unchecked Sendable` claim is false and the class is still racy. This needs the
full current file, not just the diff, before it can be accepted at a 9.5 bar.

**2. The concurrency test doesn't test the concurrency pattern that's actually in play.**
The scenario itself states the real risk: `prefetch` and `warmThumbnails` both reach
`insert` from concurrent tasks. But an image cache's other classic race is
reader/writer, not just writer/writer — some caller (very plausibly the view layer,
reading a thumbnail to display while prefetch is still populating the cache) calls
`image(for:)` while another task calls `insert`. The added test,
`parallelInsertsAreSerialized`, hammers only `insert` from 64 tasks — writer vs.
writer. There's no test shown that interleaves `image(for:)` reads with concurrent
`insert` writes. A TSAN-clean writer/writer test does not substantiate a "safe to
share" claim that includes concurrent reads, and the lock as implemented should
handle that fine — but "should" is exactly what a 9.5 concurrency score shouldn't
rest on without the test to back it.

**3. Removing `ImageCacheWrapper` isn't evidenced.**
The deleted type's own doc comment says "retained for source compatibility" — i.e.
it existed because something depended on it under that name. This diff touches only
`ImageCache.swift`; there's no accompanying hunk in any caller updating a reference
from `ImageCacheWrapper` to `ImageCache`. Either nothing else in the repo referenced
it (fine, but unverified here) or something does, in which case "full suite green"
would be inconsistent with a build that no longer compiles. This is exactly the kind
of claim a Critic shouldn't wave through on the Actor's say-so — it needs a
repo-wide grep for `ImageCacheWrapper`, not just this file's diff.

**4. Same gap, smaller stakes, for `evictionDelegate`.**
`private` in Swift extends to the whole file (including extensions in that file), not
just the class body, so "unused" needs to be confirmed for the whole
`ImageCache.swift` file, not assumed from a diff hunk that only shows the property's
declaration and deletion. Lower severity than #3 since it's private and therefore
can't be reached from outside the file, but still asserted rather than shown.

**5. The Actor's own report is internally inconsistent.**
`loop_result` claims "Full suite green (1,312 tests)"; the test-run line right below
it reports "1,313 passed, 0 failed." That's a one-test discrepancy in the Actor's own
paragraph. It's plausibly just the newly-added concurrency test not being folded into
the headline count when the prose was written, and it cuts in the safe direction (more
tests passed than claimed, not fewer) — but a report that can't even keep its own
test count straight is a reason to verify the rest of it independently rather than
take "tests green" at face value, which is exactly what's being asked here.

## Assessment

The core mechanism (lock-protected storage access) is legitimate progress and, as far
as it's shown, correct. This isn't a rejection of the approach. But a 9.5 claim on the
`concurrency` dimension implies the safety argument is fully closed, and it isn't:
the `@unchecked Sendable` promise can't be checked against the full file, the test
covers writer/writer but not the reader/writer pattern that's the more realistic race
for a UI image cache, and a compatibility shim was deleted with no visible evidence
that its callers were migrated. Any one of these would be a minor nit; together they
add up to "not yet verifiable at this bar."

```json
{"verdict": "conditional", "blocks_95": true, "blocking_severity": "major", "dimension_scores": {"concurrency": 7.5}, "flagged_smells": ["unchecked Sendable claim unverifiable from partial diff", "test coverage mismatched to claim (writer/writer tested, reader/writer untested)", "compatibility shim removed with no diff evidence of call-site migration", "private-scope dead-code claim unverified against whole file", "self-inconsistent test count in Actor report (1,312 vs 1,313)"], "evidence_demanded": ["full current source of ImageCache.swift confirming no mutable stored property is touched outside lock.withLock", "repo-wide grep for ImageCacheWrapper confirming no remaining caller depends on the removed compatibility shim", "a concurrency test that interleaves image(for:) reads with concurrent insert writes, not just insert-vs-insert", "repo-wide grep for evictionDelegate / the eviction-delegate protocol confirming it is genuinely dead code, not just file-local unused within the shown hunk", "reconciliation of the claimed 1,312-test figure against the reported 1,313-passed run output"]}
```
