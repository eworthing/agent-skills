# Review — Loop 4, `concurrency` dimension (ImageCache)

## What changed

The diff does two things: (1) deletes `ImageCacheWrapper`, a pass-through class that added
no behavior of its own, and drops an `evictionDelegate` property the Actor reports as unused;
(2) adds an `NSLock` around both `storage` accessors (`image(for:)` and `insert(_:for:)`) and
marks `ImageCache` `@unchecked Sendable` with a comment asserting `storage` is never touched
outside `lock.withLock`.

The dead-wrapper deletion is a clean, low-risk simplification — it removes an indirection layer
that did nothing but forward two calls, which is exactly the kind of thing that should not have
survived a prior refactor pass. No objection there.

## The concurrency fix itself

The lock placement is correct as far as the diff shows: both the read path and the write path
route through the same `NSLock`, so any interleaving of `image(for:)` and `insert(_:for:)` on
`storage` is serialized. That is a sound, minimal fix for a shared-mutable-dictionary race, and
it directly addresses the scenario described (two prefetch entry points reaching `insert`
concurrently from the same screen appearance). I have no correctness objection to the mechanism.

## Where the evidence falls short of a 9.5 claim

1. **The added test doesn't exercise the race it's supposed to prove is fixed.**
   `ImageCacheConcurrencyTests.parallelInsertsAreSerialized` hammers `insert` from 64 concurrent
   tasks — that's write/write concurrency. The actual hazard this loop is fixing is read/write
   concurrency: prefetch tasks calling `insert` while something else (`GalleryViewModel`,
   presumably) calls `image(for:)` to render. A TSAN run that only calls `insert` concurrently
   cannot detect a race between `image(for:)` and `insert`, because the test never invokes
   `image(for:)` under contention. The lock happens to make this safe by construction (same
   lock instance guards both accessors), but the *evidence offered* — "hammers insert... under
   TSAN — clean" — does not actually cover the scenario the loop's own report cites as the
   motivating case. Claiming `concurrency → 9.5` on a test that never race-tests the read path
   against the write path is a gap between claim and proof, not just a nice-to-have.

2. **The `@unchecked Sendable` justification can't be fully verified from a diff hunk.** The
   comment asserts "`storage` is never accessed except inside `lock.withLock`" — true for the
   two methods shown, but a diff hunk only proves that for the lines it touches. If `ImageCache`
   has any other member (a `count` property, a `removeAll()`, a subscript, anything not touched
   this loop) that reads or writes `storage` directly, the `@unchecked Sendable` claim is false
   and the type is not actually data-race-free. Nothing in the material rules this out.

3. **Minor, non-blocking:** hand-rolled `NSLock` + `@unchecked Sendable` forfeits
   compiler-checked isolation in favor of a manually-asserted invariant. That's a legitimate
   choice for a synchronous, non-async cache (an `actor` would force `insert`/`image(for:)` to
   become `async`, which may not be desirable for callers), so I'm not treating this as a defect
   — just noting it's the kind of pattern that needs the test coverage in (1) to actually earn
   trust, since the compiler isn't backing it up.

4. **Not concurrency-specific, but worth a checked box:** `ImageCacheWrapper` and
   `evictionDelegate` were deleted on the Actor's assertion that they're unused. The full suite
   passing is decent evidence the build still compiles, but "unused" for a `public`/internal
   delegate hook is worth a one-line grep confirmation rather than taking the report at face
   value, given the rest of the codebase isn't visible here.

## Bottom line

The mechanism is right and the dead-code deletion is a genuine improvement. What's missing is
proof that matches the claim: a concurrency dimension asking for 9.5 needs the test to actually
race the two accessor paths against each other (not just one accessor against itself), and needs
the `@unchecked Sendable` invariant confirmed against the whole type, not a partial diff. Neither
gap suggests the fix is wrong — they suggest the verification is incomplete relative to what's
being signed off on.

```json
{"verdict": "conditional", "blocks_95": true, "blocking_severity": "major: concurrency-evidence-insufficient — added test covers write/write serialization only, not the read/write interleaving (prefetch insert vs. render-path image(for:)) that motivates the fix, and the @unchecked Sendable invariant is unverifiable from a partial diff", "dimension_scores": {"concurrency": 7.5}, "flagged_smells": ["evidence-claim-mismatch (TSAN test doesn't cover the scenario cited as motivating it)", "unverifiable-sendable-invariant-from-partial-diff", "unverified-dead-code-removal (evictionDelegate/ImageCacheWrapper deletion asserted, not shown to be reference-free)"], "evidence_demanded": ["Full contents of ImageCache.swift (not just the diff hunk) to confirm no member other than image(for:)/insert(_:for:) touches storage outside lock.withLock", "A concurrency test that races image(for:) reads against insert(_:for:) writes concurrently (not just insert against insert), matching the described prefetch+render usage", "Grep/compile evidence that no remaining references to ImageCacheWrapper or evictionDelegate exist elsewhere in the codebase", "Confirmation that the project's minimum deployment target supports the NSLock.withLock closure API used here"]}
```
