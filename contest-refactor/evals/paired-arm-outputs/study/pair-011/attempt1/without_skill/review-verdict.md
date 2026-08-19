# Critic review — Loop 4, `concurrency` dimension

## What the diff actually does

Two things are bundled under "consolidated the `ImageCache` API":

1. **Dead-code / indirection cleanup** — `ImageCacheWrapper` (a pure pass-through) and the unused
   `evictionDelegate` hook are deleted, and callers presumably now talk to `ImageCache` directly.
   This part is fine on its own: it's pure deletion, the suite still compiles and passes (1,312/1,312),
   and there's nothing in the diff suggesting either symbol was doing real work.

2. **A concurrency-safety change** — `ImageCache` is now declared `final class ImageCache: @unchecked
   Sendable`, and `Prefetcher.prefetch` switches its task spawn from `Task { }` to `Task.detached { }`
   (matching what `warmThumbnails` already did). This is the part the `concurrency` dimension is
   actually about, and it does not hold up.

## The defect

`ImageCache.storage` is a plain, unsynchronized `[String: UIImage]`:

```swift
final class ImageCache: @unchecked Sendable {
    private var storage: [String: UIImage] = [:]
    func image(for key: String) -> UIImage? { storage[key] }
    func insert(_ image: UIImage, for key: String) { storage[key] = image }
}
```

`@unchecked Sendable` is not a fix — it is a promise to the compiler that the author has manually
verified thread-safety, backed by nothing here: no lock, no serial `DispatchQueue`, no `actor`
isolation, no `os_unfair_lock`. Meanwhile `Prefetcher` demonstrably calls `insert` from concurrent,
unsynchronized contexts on the very same object:

- `prefetch(_:)` spawns one `Task.detached` per URL, each eventually calling
  `self.cache.insert(image, for: url.absoluteString)`.
- `warmThumbnails(_:)` spawns another, independent set of `Task.detached` closures, each calling
  `self.cache.insert(thumb, for: url.absoluteString + "#thumb")`.
- The scenario states both entry points are invoked "from `GalleryViewModel` on the same screen
  appearance" — i.e., these two families of detached tasks run concurrently against the same
  `ImageCache` instance, writing to the same backing dictionary from multiple threads with no
  coordination at all.

Concurrent, unsynchronized mutation of a Swift `Dictionary` from multiple threads is undefined
behavior (corrupted hash-table state, crashes, or silently dropped/aliased entries) — this isn't a
style nitpick, it's the exact class of bug Swift's Sendable checking exists to catch, and
`@unchecked Sendable` was used here to make the compiler stop complaining rather than to make the
type actually safe. The Actor's report frames this as "resolved the Sendable conformance" as if it
were a mechanical fix; it's actually a suppression that trades a compile-time error for a runtime
data race.

`swift test` passing (1,312/1,312) is not evidence against this. Data races are non-deterministic
and routinely pass deterministic unit-test suites without a Thread Sanitizer run or an explicit
concurrent-stress test designed to hit the interleaving. Nothing in the diff or the report indicates
TSan was used, or that any test exercises `prefetch` and `warmThumbnails` running concurrently
against the same cache.

## Secondary issue: undisclosed semantic change

`prefetch(_:)`'s `Task { }` → `Task.detached { }` change is not explained anywhere in the report,
and it is not required to fix a Sendable-conformance error — capturing `self.cache` in a `@Sendable`
closure requires `ImageCache: Sendable` regardless of whether the enclosing call is `Task` or
`Task.detached`. The actual effect of this edit is to drop actor/priority/task-local inheritance from
the caller for `prefetch`'s spawned work, making it behave differently from before (and now
identically to `warmThumbnails`, which is a plausible but unstated intent). A behavior-changing edit
bundled silently into a "consolidation" is itself a review smell, independent of whether the new
behavior is desirable.

## Verdict

This loop does not clear `concurrency` at the 9.5 bar. The `@unchecked Sendable` annotation is
applied to a type with genuinely unsynchronized shared mutable state that is concurrently written
from independent detached tasks — a real, demonstrable data race, not a hypothetical one. The
cleanup portions of the diff (wrapper removal, dead delegate removal) are acceptable but don't offset
the core defect. Rejecting pending an actual synchronization fix (actor isolation, a serial queue, or
a lock protecting `storage`) rather than a Sendable suppression.

```json
{
  "verdict": "rejected",
  "blocks_95": true,
  "blocking_severity": "critical",
  "dimension_scores": {"concurrency": 3},
  "flagged_smells": [
    "unchecked-sendable-without-synchronization",
    "unsynchronized-shared-mutable-state-across-concurrent-tasks",
    "undisclosed-behavioral-change (Task -> Task.detached in prefetch)",
    "tests-green-treated-as-concurrency-proof"
  ],
  "evidence_demanded": [
    "Replace @unchecked Sendable with real synchronization: actor-isolate ImageCache, or guard storage with a serial DispatchQueue/NSLock/os_unfair_lock",
    "A Thread Sanitizer (TSan) run exercising prefetch(_:) and warmThumbnails(_:) executing concurrently against the same ImageCache instance",
    "A concurrency-specific test that fails against the current @unchecked Sendable implementation and passes once synchronization is added",
    "Explicit justification (or revert) of the Task -> Task.detached change in prefetch(_:), since it alters actor/priority/task-local inheritance and was not called out in the report"
  ]
}
```
