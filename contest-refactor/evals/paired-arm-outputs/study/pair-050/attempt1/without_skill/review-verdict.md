# Review — Loop 4, `concurrency` dimension (`ImageCache` consolidation + locking)

## What the diff actually does

Three changes land in one hunk against `Sources/Gallery/ImageCache.swift`:

1. `ImageCacheWrapper` (a pass-through class kept "for source compatibility") is deleted, folding its two forwarding methods into `ImageCache` directly.
2. `evictionDelegate: ImageCacheEvictionDelegate?` is deleted as "unused."
3. `ImageCache` is marked `final class ImageCache: @unchecked Sendable`, gains a `private let lock = NSLock()`, and both `image(for:)` and `insert(_:for:)` now wrap their dictionary access in `lock.withLock { ... }`.

The stated goal is fixing a real race: `prefetch` and `warmThumbnails` in `Prefetcher.swift` both reach `insert` concurrently from the same screen-appearance path. Serializing `storage` access behind a single lock does fix *that specific* race, and it's backed by real evidence — a dedicated `ImageCacheConcurrencyTests.parallelInsertsAreSerialized` test hammering 64 concurrent inserts, run clean under `--sanitize=thread`. That part of the work is sound and I have no basis to dispute it from what's shown.

## Where I stop short of 9.5

**1. The safety guarantee is a documented invariant, not a compiler-enforced one.** `@unchecked Sendable` is precisely the escape hatch that tells the compiler "trust me, I manually synchronized this" — it works here because *today*, every line that touches `storage` happens to go through `lock.withLock`. Nothing stops a future edit (a new method, a fast-path optimization, a debug helper) from touching `storage` directly and silently reintroducing the exact race this loop just closed, with zero compiler diagnostic — the only backstop is the comment above the class and the hope that CI runs the TSAN-tagged test on every change. For a dimension score claiming near-perfect concurrency rigor, a compiler-checked alternative (an `actor ImageCache`, or a `Mutex`-wrapped stored dictionary with only a synchronized accessor exposed) would make the invariant structural rather than a trust exercise. This is a legitimate architecture-quality gap, not a nitpick — it's the difference between "safe because someone remembered to lock" and "safe because it doesn't compile otherwise."

**2. The `evictionDelegate` removal is an unverified, out-of-scope behavior change riding along with the concurrency fix.** The Actor asserts it was "unused," but nothing in the attached diff demonstrates that — I can't see the delegate protocol, any conformers, or whether some other type registered itself to evict entries under memory pressure. If that delegate was actually wired up elsewhere, this loop just deleted memory-pressure eviction and mislabeled it as dead-code cleanup bundled into a "concurrency" loop. Removing a hook and removing a race are two different claims; only the second is what this loop is supposed to be certifying.

**3. `ImageCacheWrapper`'s removal isn't shown to be complete.** The diff touches exactly one file. If any other file referenced `ImageCacheWrapper` by name (a stored property type, a DI registration, a test double, a protocol conformance), deleting it here would not compile — yet the report claims "full suite green (1,313 tests)." Either there truly were zero other references, or the diff shown is incomplete. From `scenario.md` alone I can't distinguish these, and the task says not to trust the Actor's report at face value.

**4. The concurrency test doesn't match the actual concurrent-access pattern described.** The scenario explicitly says the race is between two *insert* paths (`prefetch`, `warmThumbnails`), and the added test matches that (`parallelInsertsAreSerialized`, insert-vs-insert). But a cache's normal hot path is concurrent *reads* (UI display code calling `image(for:)`) racing against concurrent *writes* (prefetch calling `insert`) — the lock should cover this by construction, but "should, by inspection" is exactly the kind of claim this loop is supposed to replace with a test. No mixed read/write concurrency test is reported.

None of these four points contradicts the core claim that the reported insert/insert race is fixed — the lock does that, and the TSAN evidence is real. But taken together they're enough that I wouldn't sign off on treating `concurrency` as closed at the top of the scale without follow-up.

## Verdict

Conditional. The specific race is closed with credible evidence; the loop still needs (a) a decision on `@unchecked Sendable`+`NSLock` vs. a compiler-enforced alternative — or at minimum an explicit rationale for why the manual-lock trust model is acceptable here, (b) confirmation `evictionDelegate` had no live conformers before deletion, (c) confirmation no other file referenced `ImageCacheWrapper`, and (d) a mixed read/write concurrency test, not just insert-vs-insert.

```json
{"verdict": "conditional", "blocks_95": true, "blocking_severity": "High", "dimension_scores": {"concurrency": 7}, "flagged_smells": ["@unchecked Sendable backed only by a comment-documented invariant, not compiler-enforced isolation (actor alternative not considered/justified)", "unverified dead-code removal: evictionDelegate deleted with no evidence of zero remaining conformers/callers, bundled into a concurrency-labeled loop", "incomplete diff visibility: ImageCacheWrapper deleted with no shown update to any external call sites", "test coverage mismatch: only insert-vs-insert concurrency is tested; no concurrent read+write (image(for:) vs insert) test"], "evidence_demanded": ["repo-wide reference check proving evictionDelegate and ImageCacheEvictionDelegate have no remaining conformers/callers before removal", "confirmation (or diff) that every ImageCacheWrapper call site was updated, not just this file", "a concurrency test that interleaves image(for:) reads with insert() writes under TSAN, not just concurrent inserts", "explicit rationale for @unchecked Sendable + NSLock over an actor or Mutex-backed accessor, including what prevents a future method from touching storage outside the lock"]}
```
