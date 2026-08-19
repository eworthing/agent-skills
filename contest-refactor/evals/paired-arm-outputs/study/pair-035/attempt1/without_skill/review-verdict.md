# Review — Loop 4, `concurrency` dimension

## What the diff actually does

Three changes land together:

1. `ImageCacheWrapper` (a pass-through class) is deleted and callers presumably now use `ImageCache` directly.
2. The unused `evictionDelegate` property is dropped from `ImageCache`.
3. `ImageCache` is declared `final class ImageCache: @unchecked Sendable` and, separately, `Prefetcher.prefetch(_:)` switches its per-URL `Task { ... }` to `Task.detached { ... }`, matching the pre-existing `warmThumbnails(_:)`.

The Actor's report frames all of this as "resolved the Sendable conformance the compiler started requiring" and claims a green 1,312-test suite as proof, proposing `concurrency` → 9.5.

## The core problem: `@unchecked Sendable` is asserted, not earned

`ImageCache`'s only state is:

```swift
private var storage: [String: UIImage] = [:]
```

`image(for:)` reads it and `insert(_:for:)` mutates it. Neither method takes a lock, neither type is an `actor`, and nothing else in the diff introduces synchronization. `@unchecked Sendable` is a manual, compiler-trusting promise that the author has independently verified thread safety — it exists specifically to *bypass* the Sendable checker, not to satisfy it. Here nothing was done to make the promise true: `storage` is a bare Swift `Dictionary`, and concurrent mutation of a `Dictionary` from multiple threads is undefined behavior (data race, potential crash/corruption), not merely "unsafe in theory."

And the diff shows exactly the call pattern that will trigger it: `prefetch(_:)` and `warmThumbnails(_:)` both iterate a list of URLs and spin up one `Task.detached` per URL, each of which eventually calls `self.cache.insert(...)`. The scenario states both entry points "are called from `GalleryViewModel` on the same screen appearance" — i.e., in normal operation you get N+M detached tasks, each capable of running concurrently on different threads, all calling `insert` on the same unsynchronized `storage` dictionary. That is a textbook concurrent-write data race, introduced under the banner of a concurrency fix.

The compiler error the Actor describes ("Sendable conformance the compiler started requiring") is itself the signal that this cache is being shared across concurrency domains — exactly the condition Sendable checking is designed to catch. The fix taken silences the diagnostic without addressing what it was warning about. This is a compiler-appeasement fix, not a root-cause fix. The correct shapes here are well known and none were taken: make `ImageCache` an `actor` (free, correct serialization, real unconditional `Sendable`), or keep it a class and add real synchronization (`NSLock`/`os_unfair_lock`/serial `DispatchQueue`) around `storage` access before claiming `@unchecked Sendable`.

"Full suite green (1,312 tests)" is not evidence against this. Unit tests essentially never deterministically reproduce dictionary-corruption races; this needs Thread Sanitizer or a targeted concurrent-stress test to surface, and there's no indication either was run.

## Secondary finding: undisclosed behavioral change

`prefetch(_:)`'s `Task { ... }` → `Task.detached { ... }` is not mentioned anywhere in the Actor's report, which only describes "resolved the Sendable conformance." But this change wasn't required to fix a Sendable error — a structured `Task { ... }` closure is already `@Sendable`-checked the same way a detached one is. Making `prefetch` detached is an unrelated, silent change that strips structured-concurrency benefits (cancellation propagation from the parent, priority inheritance) from that call site and — combined with `warmThumbnails` already being detached — is precisely what maximizes the number of concurrently-racing writers into `storage`. A report that omits a behavioral change bundled into the diff undermines the reliability of the Actor's self-assessment generally, not just on this one line.

## Minor: unverified dead-code claim

`evictionDelegate` is deleted as "unused," and the wrapper class is deleted as retained only "for source compatibility." Neither claim is checkable from this diff alone (no call-graph or grep evidence attached). This is a smaller concern than the race but worth requiring proof for, since removing an eviction hook also has a resource-growth angle if `ImageCache` has no bound on `storage` size and prefetch fires unboundedly on every screen appearance.

## Verdict

This loop does not just fail to reach 9.5 on `concurrency` — it actively regresses it by introducing an unsynchronized shared-mutable-state data race while asserting, via `@unchecked Sendable`, that none exists. That assertion is the single most load-bearing claim in the diff for this dimension, and it is false on the evidence shown. Rejecting rather than conditionally approving, because the fix needed is not a small patch on top of this shape (e.g., a config tweak) — it requires re-deriving the concurrency design for `ImageCache` (actor vs. lock) and re-justifying the `Task.detached` change, which the Actor did not attempt and did not disclose.

```json
{"verdict": "rejected", "blocks_95": true, "blocking_severity": "critical — unsynchronized shared mutable state (Dictionary) declared @unchecked Sendable with no actual locking/actor isolation, concurrently mutated from multiple Task.detached call sites per the scenario's own description of caller behavior", "dimension_scores": {"concurrency": 2}, "flagged_smells": ["false-safety-via-unchecked-Sendable", "compiler-appeasement-fix (silences the Sendable diagnostic instead of fixing the race it flags)", "undisclosed-behavioral-change (Task -> Task.detached in prefetch, not mentioned in Actor report)", "test-suite-blind-spot (green functional tests do not establish thread safety)", "unverified-dead-code-claim (evictionDelegate/ImageCacheWrapper removal unproven from diff alone)"], "evidence_demanded": ["Either conversion of ImageCache to an actor, or explicit synchronization (lock/serial queue) around all storage access, before @unchecked Sendable is justified", "A Thread Sanitizer (TSan)-enabled run exercising prefetch(_:) and warmThumbnails(_:) invoked together (matching the described GalleryViewModel call pattern) showing no data race", "A concurrency-targeted stress test (not just the existing 1,312-test functional suite) that performs concurrent inserts into ImageCache from multiple tasks", "Justification for the Task -> Task.detached change in prefetch(_:), including why structured-concurrency cancellation/priority propagation is safe to drop", "Call-site evidence (grep or call-graph) that evictionDelegate and ImageCacheWrapper truly had zero remaining consumers before deletion"]}
```
