# Review: Loop 4 — concurrency dimension (ImageCache thread-safety)

## What the diff does
- Removes `ImageCacheWrapper`, a redundant pass-through wrapper.
- Removes `evictionDelegate`, described by the actor as unused.
- Adds an `NSLock` and wraps both `storage` accessors (`image(for:)`, `insert(_:for:)`) in `lock.withLock`.
- Marks `ImageCache` as `@unchecked Sendable` with a code comment justifying the annotation.
- Actor adds `ImageCacheConcurrencyTests.parallelInsertsAreSerialized`, stress-testing 64 concurrent `insert` calls under TSAN, and reports the full suite green (1,313 tests) plus a clean TSAN run for the new concurrency test.

## What holds up
The core mechanism is sound as far as it goes. Every access to the mutable `storage` dictionary shown in this diff — both the read path and the write path — goes through the same `NSLock`, so within the boundaries of this class there is no unsynchronized access to shared mutable state. The `@unchecked Sendable` conformance is honestly justified: the comment states the actual invariant (`storage` is only touched inside `lock.withLock`), and that invariant is verifiable directly from the diff — this isn't a rubber-stamped `@unchecked Sendable`, it's backed by a structural guarantee that holds for the code shown. The TSAN-validated stress test on `insert` is real evidence, not a decorative test, and it directly matches the scenario called out in the diff's own trailer (`insert` reached concurrently from two prefetch entry points). Deleting the dead `ImageCacheWrapper` is a legitimate simplification with no functional downside.

## What doesn't hold up yet
1. **The safety claim is broader than the test.** The actor's report says the cache is now "safe to share across the prefetch tasks," and the diff's trailer notes that `prefetch` and `warmThumbnails` both reach `insert` concurrently. But a lock-protected `insert` and a lock-protected `image(for:)` only guarantee that *each individual call* is atomic — they say nothing about a caller that composes the two, e.g. `if cache.image(for: key) == nil { cache.insert(fetch(key), for: key) }`. That check-then-act pattern is exactly what "warm thumbnails vs. prefetch, same screen appearance" suggests is happening, and it's a textbook TOCTOU race: two tasks can both miss the cache, both fetch, and both insert — wasted work at best, a last-writer-wins correctness bug at worst (e.g. a low-res warm-thumbnail insert landing after and clobbering a full-res prefetch insert for the same key). TSAN will not catch this — there's no data race, only a logical one. The submitted test is insert-only and does not exercise the interleaved read/write pattern the real call sites use. "No data race on storage" and "safe to share across the prefetch tasks" are different claims, and only the first is demonstrated here.
2. **`evictionDelegate` removal is asserted, not shown.** The report calls it "unused," and the diff only shows the declaration disappearing from `ImageCache` — nothing in the material provided demonstrates that no other code set or read that hook. It's a stored delegate property, so deleting it is a real behavior change (removing an eviction callback) riding along with a concurrency-labeled loop. Plausibly harmless, but "plausible" isn't the bar for a 9.5 sign-off.
3. **Coarse-grained locking (minor, non-blocking).** A single lock around the whole dictionary is a reasonable, boring first pass — flagging only so it's a named, deliberate tradeoff rather than an implicit one; not a reason to withhold approval on its own.

## Verdict
The mutex/`Sendable` mechanism itself is correct and well-evidenced for what it actually fixes (data races on `storage`). What isn't yet evidenced is the actor's broader claim — "safe to share across the prefetch tasks" — which implies freedom from logical races too, and that requires seeing or testing how `prefetch`/`warmThumbnails` actually call into the cache. Those call sites are unchanged and unseen this loop, and the trailer note explicitly says they hit `insert` concurrently — this is not a hypothetical gap, it's the exact scenario the fix is claimed to cover, tested only in its simplest (insert-only, single-operation) shape. I can't accept "concurrency → 9.5" on a test that doesn't model the composite access pattern the report itself points at.

```json
{
  "verdict": "conditional",
  "blocks_95": true,
  "blocking_severity": "major (untested gap between the claimed guarantee - 'safe to share across the prefetch tasks' - and the demonstrated guarantee - data-race-free single-method access; the TOCTOU-shaped compound read-then-insert pattern implied by the two concurrent prefetch entry points is not covered by the submitted test or diff)",
  "dimension_scores": {"concurrency": 7.5},
  "flagged_smells": ["claim broader than test coverage", "TOCTOU / check-then-act race not addressed by per-call locking", "unverified deletion of evictionDelegate hook", "coarse-grained single-lock (non-blocking, noted for the record)"],
  "evidence_demanded": [
    "A concurrent test (or Prefetcher.swift excerpt) exercising the real call pattern - image(for:) checked, then insert(_:for:) on a miss - invoked concurrently from both prefetch and warmThumbnails on overlapping keys, showing no duplicate or lost work",
    "Confirmation that evictionDelegate has zero external callers/setters before its removal is treated as behavior-neutral",
    "If the compound race is confirmed to exist: either a lock-protected 'insert if absent' API on ImageCache, or evidence that the two entry points never target overlapping keys"
  ]
}
```
