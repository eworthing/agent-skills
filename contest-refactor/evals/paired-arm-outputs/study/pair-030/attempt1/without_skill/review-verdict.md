# Review — Loop 4, `concurrency` dimension

## What the diff actually does

The Actor's report frames this as two things: (1) an API consolidation (fold
`ImageCacheWrapper` into `ImageCache`, drop the unused `evictionDelegate`
hook) and (2) "resolved the Sendable conformance the compiler started
requiring once the cache is shared across the prefetch tasks." Tests are
reported green (1,312/1,312) and `concurrency` is proposed at 9.5.

The consolidation part is plausible on its face — removing a pass-through
wrapper and a delegate hook is a reasonable simplification, though nothing in
this diff proves the delegate was actually unused or that whatever called
`ImageCacheWrapper` was migrated (the deleted type's own doc comment says it
was "retained for source compatibility," which is a specific claim that
something else depended on it — that claim isn't addressed here).

The Sendable part is the actual problem, and it's the part this loop is
being scored on.

## The core finding: `@unchecked Sendable` is masking a real data race

`ImageCache` is now declared:

```swift
final class ImageCache: @unchecked Sendable {
    private var storage: [String: UIImage] = [:]
    ...
    func insert(_ image: UIImage, for key: String) {
        storage[key] = image
    }
}
```

`@unchecked Sendable` is a promise to the compiler — "trust me, this type is
safe to share across concurrency domains" — it adds zero actual
synchronization. There is no lock, no serial queue, no actor isolation
anywhere in this type. `storage` is a plain `Dictionary`, and `Dictionary` is
not safe for concurrent mutation from multiple threads; concurrent writers
racing on it is undefined behavior (memory corruption / crash), not just a
correctness nit.

And the diff doesn't just leave that pre-existing risk in place — it
increases the chance of it firing. `Prefetcher.prefetch` was changed from:

```swift
Task { ... self.cache.insert(image, for: url.absoluteString) }
```

to:

```swift
Task.detached { ... self.cache.insert(image, for: url.absoluteString) }
```

`Task.detached` drops actor-context inheritance from the caller, so this is
no longer implicitly serialized by whatever context `prefetch` used to run
in. Combined with `warmThumbnails`, which was already `Task.detached`, and
the note that "the two prefetch entry points ... are called from
`GalleryViewModel` on the same screen appearance," we now have two families
of unstructured, detached tasks that can both call `cache.insert` on the
same shared dictionary concurrently, with nothing serializing the writes.
That is a textbook data race, and `@unchecked Sendable` is exactly the
annotation that hides it from the compiler instead of fixing it.

The report's own words — "resolved the Sendable conformance the compiler
started requiring" — describe compiler-appeasement, not a thread-safety fix.
The correct fix here is either converting `ImageCache` to an `actor` (letting
the compiler enforce serialized access) or adding real synchronization
(`NSLock`/`os_unfair_lock`/serial `DispatchQueue`) around `storage` before
the `@unchecked Sendable` claim would be true. As shipped, the annotation is
false.

## Why "tests green" doesn't clear this

1,312 passing unit tests are not meaningful evidence against a data race.
Races are timing-dependent; a unit suite that doesn't specifically hammer
`prefetch`/`warmThumbnails` with concurrent load under Thread Sanitizer will
pass every time right up until it doesn't in production. Citing suite-green
as support for a `concurrency`-dimension 9.5 is the wrong kind of evidence
for the claim being made — it would need a TSan-enabled stress run, not a
green functional suite.

## Verdict

Reject. The change under review is specifically scoped to the `concurrency`
dimension, and it introduces (or at minimum, fails to close, while making
more likely to trigger) an unsynchronized shared-mutable-state data race,
masked behind an `@unchecked Sendable` annotation that isn't backed by any
actual synchronization. That's disqualifying for a concurrency-dimension
accept at any threshold, let alone 9.5. The API-consolidation half of the
diff is fine in isolation but doesn't offset the correctness problem in the
half it's actually being scored on.

```json
{
  "verdict": "rejected",
  "blocks_95": true,
  "blocking_severity": "critical — unsynchronized shared mutable state (data race) hidden behind @unchecked Sendable, with Task.detached widening the exposure window",
  "dimension_scores": {"concurrency": 3},
  "flagged_smells": [
    "@unchecked Sendable without any backing synchronization",
    "data race on shared mutable Dictionary (ImageCache.storage)",
    "compiler-appeasement Sendable fix mistaken for a thread-safety fix",
    "Task -> Task.detached scope creep (loses actor-context inheritance) bundled into an 'API consolidation' change",
    "tests-green cited as evidence for a claim (thread safety) the test suite doesn't exercise"
  ],
  "evidence_demanded": [
    "Either an actor-based ImageCache or explicit synchronization (NSLock/os_unfair_lock/serial DispatchQueue) around storage, so the Sendable claim is actually true rather than asserted",
    "A Thread Sanitizer (TSan) run exercising concurrent prefetch(_:) and warmThumbnails(_:) calls against the same cache instance, showing no race",
    "Justification for switching prefetch from Task {} to Task.detached {}, and confirmation that dropping actor-context inheritance there is intentional and safe",
    "Confirmation that all former callers of ImageCacheWrapper (a type whose own doc comment claimed it was 'retained for source compatibility') were migrated before its deletion"
  ]
}
```
