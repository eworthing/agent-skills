# Critic review — Loop 4, `concurrency` dimension

## What the diff actually does

Two things happen in `ImageCache.swift`: the `ImageCacheWrapper` pass-through is deleted (callers presumably now hold `ImageCache` directly), the unused `evictionDelegate` field is dropped, and `ImageCache` picks up `@unchecked Sendable`. In `Prefetcher.swift`, `warmThumbnails` already used `Task.detached`, and this loop additionally changes `prefetch`'s `Task { }` to `Task.detached { }`.

The Actor's report says it "resolved the Sendable conformance the compiler started requiring." That characterization does not match the diff. `@unchecked Sendable` does not resolve a Sendable requirement — it is an escape hatch that tells the compiler to stop checking and trust the author's promise that the type is safe to share across concurrency domains. Nothing in this diff makes that promise true.

## Why this blocks acceptance at 9.5 for `concurrency`

`ImageCache.storage` is a plain `[String: UIImage]`. There is no actor isolation, no `NSLock`/`os_unfair_lock`, no serial `DispatchQueue`, no `@Sendable`-safe wrapper of any kind guarding reads/writes to `storage`. `image(for:)` and `insert(_:for:)` touch the dictionary directly.

Meanwhile `Prefetcher.prefetch` and `Prefetcher.warmThumbnails` are both stated to be invoked "from `GalleryViewModel` on the same screen appearance," and both now dispatch onto `Task.detached` closures that call `cache.insert(_:for:)`. Two independent families of detached tasks, run concurrently, mutating the same unsynchronized `Dictionary` from potentially different threads. Swift's `Dictionary` is not thread-safe for concurrent mutation — concurrent inserts on the same instance is a data race with undefined behavior (memory corruption / crash), not merely a benign toctou. Marking the class `@unchecked Sendable` doesn't change any of that; it just removes the compiler's ability to warn about it. This is the canonical anti-pattern the `Sendable` diagnostic exists to catch, defeated by suppressing the check rather than by adding synchronization.

`swift test` going green (1,312/0) is not evidence this is safe. Data races are scheduling-dependent; a deterministic unit-test pass with no mention of Thread Sanitizer (`-sanitize=thread` / TSan) or a stress/race-focused test provides essentially no signal about concurrent-mutation safety. Absent a TSan run (or an actual synchronization mechanism), "tests are green" and "concurrency-safe" are unrelated claims here, and the report conflates them.

There's also a disclosure gap: the report describes dropping the wrapper, dropping `evictionDelegate`, and "resolving Sendable conformance." It says nothing about changing `prefetch`'s `Task { }` to `Task.detached { }`, which is a real semantic change (loses structured-task cancellation/priority inheritance from the calling context) and doubles the surface of concurrent writers into the now-`@unchecked` cache. A reviewer relying on the report alone would miss this.

## What's plausibly fine

Removing `ImageCacheWrapper` and `evictionDelegate` look like legitimate dead-code cleanup on their face — nothing in the diff suggests either was doing real work, and the diff is internally consistent about it. I'm not flagging those as blockers; the concurrency defect above is sufficient on its own to block the dimension, and I'm not in a position to verify absence of other call sites for the wrapper from this diff alone.

## Verdict

Reject. The dimension under review is `concurrency`, and the change introduces (or rather, papers over with `@unchecked Sendable`) an unsynchronized shared-mutable-state data race across two concurrent task families, while the report claims the Sendable issue was "resolved." That's not a 9.5-grade concurrency story; it's a suppressed compiler warning plus an undisclosed additional concurrent-writer path.

```json
{"verdict": "rejected", "blocks_95": true, "blocking_severity": null, "dimension_scores": {"concurrency": 2}, "flagged_smells": ["unchecked-sendable-escape-hatch", "unsynchronized-shared-mutable-state", "concurrent-dictionary-mutation-race", "green-tests-conflated-with-thread-safety", "undisclosed-diff-scope-task-to-task-detached"], "evidence_demanded": ["Thread Sanitizer (TSan) run exercising concurrent prefetch(_:) and warmThumbnails(_:) against a shared ImageCache instance", "actual synchronization for ImageCache.storage (actor, NSLock/os_unfair_lock, or serial DispatchQueue) in place of @unchecked Sendable, or a substantiated proof obligation for why @unchecked is sound here", "explicit justification for the prefetch Task -> Task.detached change, since it was not mentioned in the Actor's report", "confirmation evictionDelegate and ImageCacheWrapper have no remaining call sites elsewhere in the codebase"]}
```
