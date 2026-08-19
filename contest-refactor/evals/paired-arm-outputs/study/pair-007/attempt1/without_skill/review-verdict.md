# Review — Loop 4, `concurrency` dimension

## What's clean

Two parts of this diff are legitimate, low-risk cleanup:

- Deleting `ImageCacheWrapper` — a pure pass-through with no behavior of its own — is a
  reasonable deletion as long as nothing outside this diff referenced it. The Actor's
  report claims the full suite (1,312 tests) is green after the type disappeared entirely,
  which is at least consistent with there being no surviving callers.
- Dropping `evictionDelegate` — the diff shows no read of that property anywhere in either
  file, and again, green build/tests after removing a stored property that nothing sets or
  reads is unsurprising rather than reassuring, but it's not a red flag on its own.

Neither of those touches the `concurrency` dimension this loop is claiming, so they don't
move the needle on the verdict either way.

## The actual concurrency change is not safe, and the report mischaracterizes it

The report says the Actor "resolved the Sendable conformance the compiler started
requiring." What the diff actually does is:

```swift
final class ImageCache: @unchecked Sendable {
    private var storage: [String: UIImage] = [:]
    ...
    func insert(_ image: UIImage, for key: String) {
        storage[key] = image
    }
}
```

`@unchecked Sendable` is not a resolution of a Sendable requirement — it's an assertion to
the compiler that the author has independently guaranteed thread safety, with no compiler
verification behind it. Nothing in this type provides that guarantee. `storage` is a plain
`[String: UIImage]`, mutated directly by `insert(_:for:)` with no actor isolation, no lock,
no serial queue. Swift's `Dictionary` is not safe for concurrent mutation from multiple
threads — concurrent writes to the same instance are undefined behavior (data corruption or
a runtime exclusivity trap), not merely "unlikely in practice."

Critically, the diff doesn't just add the annotation in isolation — it also shows the call
sites that turn this into a real, not hypothetical, race:

```swift
func prefetch(_ urls: [URL]) {
    for url in urls {
        Task.detached {
            ...
            self.cache.insert(image, for: url.absoluteString)
        }
    }
}

func warmThumbnails(_ urls: [URL]) {
    for url in urls {
        Task.detached {
            ...
            self.cache.insert(thumb, for: url.absoluteString + "#thumb")
        }
    }
}
```

The scenario states both `prefetch` and `warmThumbnails` are called from `GalleryViewModel`
on the same screen appearance, and `prefetch` was changed from `Task { }` to
`Task.detached { }` in this same diff — i.e. the loop didn't just annotate around an
existing race, it added a second family of concurrently-scheduled detached tasks writing
into the same unsynchronized dictionary that a third family (`warmThumbnails`, already
detached) also writes into. For any non-trivial `urls` list this is N+M tasks racing on
`storage` with no ordering or exclusion guarantee.

"Full suite green, 1,312 tests" is not evidence against this. Data races are scheduling-
dependent — a test suite that doesn't specifically stress concurrent `insert` calls against
one `ImageCache` instance (nothing in the diff or report suggests one exists) can pass every
time in CI and still corrupt state or trap in production under real timing. Green tests here
demonstrate the code compiles and the happy path executes, not that the concurrency claim is
true. Treating "tests green" as validation of a `@unchecked Sendable` claim is exactly the
gap this dimension exists to catch.

## Verdict

This is not a documentation gap or a style nit — `@unchecked Sendable` over a mutable,
unsynchronized `Dictionary` that is provably written from concurrent detached tasks is a
correctness bug the Actor's own diff introduces or newly exposes, and the report describes
it as solved. That blocks acceptance at 9.5 on the `concurrency` dimension outright; it isn't
close enough to be a conditional nit.

```json
{
  "verdict": "rejected",
  "blocks_95": true,
  "blocking_severity": "critical — unsynchronized shared mutable state marked @unchecked Sendable, confirmed reachable from concurrent Task.detached writers (data race / undefined behavior, not just an unproven claim)",
  "dimension_scores": {"concurrency": 2},
  "flagged_smells": [
    "@unchecked Sendable escape hatch used in place of real synchronization",
    "Concurrent unsynchronized mutation of a plain Dictionary from multiple Task.detached closures",
    "Report claims Sendable conformance was 'resolved' when it was actually just suppressed at the compiler level",
    "Green test suite treated as proof of concurrency safety with no evidence of a concurrent-access test"
  ],
  "evidence_demanded": [
    "Either remove @unchecked Sendable and make ImageCache an actor (or serialize storage access behind a lock/DispatchQueue) so Sendable is actually true, not asserted",
    "A concurrency stress test that calls insert(_:for:) from multiple simultaneous tasks against one ImageCache instance and passes under Thread Sanitizer",
    "Confirmation (e.g. a TSan run) that prefetch + warmThumbnails running concurrently against a shared ImageCache does not race, since the diff shows both writing to the same storage from detached tasks on the same screen appearance"
  ]
}
```
