# Critic Review — Loop 4, `concurrency` dimension

## Independent re-derivation (Method Step 1)

Ignoring the Actor's self-report and re-deriving from the diff alone.

**Claim.** `ImageCache` is marked `final class ImageCache: @unchecked Sendable` while its only
mutable state, `private var storage: [String: UIImage] = [:]`, remains a plain unsynchronized
dictionary — no `actor`, no serial `DispatchQueue`, no lock. The Actor's report frames this as
having "resolved the Sendable conformance the compiler started requiring," but the diff does not
resolve the underlying data race; it silences the compiler's warning about it.

**Source.**
- `Sources/Gallery/ImageCache.swift` diff: `final class ImageCache: @unchecked Sendable { private var storage: [String: UIImage] = [:] ... func insert(_ image: UIImage, for key: String) { storage[key] = image } }` — no synchronization primitive anywhere in the type.
- `Sources/Gallery/Prefetcher.swift` diff: `prefetch(_:)` spawns one `Task.detached` per URL calling `self.cache.insert(...)`; `warmThumbnails(_:)` spawns one `Task.detached` per URL calling `self.cache.insert(...)` on the same cache instance.
- Scenario note (authoritative, given): "The two prefetch entry points (`prefetch`, `warmThumbnails`) are called from `GalleryViewModel` on the same screen appearance." This establishes that the two loops are not hypothetically concurrent — they are launched together, each fanning out N detached tasks against the same `storage` dictionary, with zero mutual exclusion.

**Consequence.** Concurrent, unsynchronized mutation of a Swift `Dictionary` from multiple tasks is undefined behavior — at best a Swift exclusivity-enforcement crash, at worst silent corruption of cached image data surfaced to the user. `@unchecked Sendable` does not make this safe; it only tells the compiler to stop checking. This is the rubric's named **suppression-as-fix** sub-pattern of *fake-clean reward*: "`@unchecked Sendable` ... count[s] as fake-clean reward unless they carry narrow scope + concrete justification + the compensating invariant that makes them safe." No compensating invariant is offered anywhere in the diff or the report — no lock, no actor isolation, no removal condition. It also fails the Simplify Pressure Test's own named anti-example verbatim: "Silence the strict-concurrency warning ... with `@unchecked Sendable` ... while the underlying race ... still exists → fails Q4 (runtime behavior is not honest; the hazard is intact, just unreported)." Because the hazard is reachable from a primary flow (image prefetch/thumbnail-warm on screen appearance, not an off-path helper), this meets the **Likely disqualifier** anchor's own example almost word for word: "racing async flows that can corrupt user-visible state."

**Remedy.** Either (a) make `ImageCache` an `actor` (or serialize `storage` access behind a private `DispatchQueue`/lock) so `insert`/`image(for:)` are genuinely race-free, and only then is `Sendable` conformance honest — no `@unchecked` needed; or (b) if `@unchecked Sendable` is kept, prove the compensating invariant in the loop record (e.g., an external actor-isolation guarantee) and cite it. Smallest honest fix is (a): the type is small, two methods, trivial to make an `actor`.

## Secondary finding — undisclosed risk-boundary change

**Claim.** `prefetch(_:)`'s `Task { ... }` was changed to `Task.detached { ... }` in this diff. This is a task-lifetime/isolation change (loses priority inheritance and cancellation propagation from the caller's task) and sits squarely in the Meta-Rule 4 risk-boundary list ("actor/isolation ... conditional compilation ... lock/ordering" class of change), yet the Actor's report says nothing about it — the report only mentions Sendable conformance and the wrapper/delegate cleanup.

**Source.** `Prefetcher.swift` diff hunk: `-            Task {` / `+            Task.detached {` inside `prefetch(_:)` only (`warmThumbnails` was already `Task.detached` and is unchanged).

**Consequence.** An undisclosed change to cancellation semantics on a primary-flow entry point is exactly the class of change Meta-Rule 4 requires evidence for ("the Actor ... must preserve that invariant and record evidence in `loop_result`"). None was recorded. Independent of the data-race finding above, this is at minimum a credibility/evidence-chain gap on the same dimension being scored.

**Remedy.** Either revert `prefetch` to structured `Task { }` (matching its own stated purpose of Sendable cleanup only) or, if detachment is intentional, disclose why caller-cancellation no longer needs to propagate into prefetch work.

## Test evidence review

"Full suite green (1,312 tests)" is exactly the guardrail case the method calls out: "A green single-config test run does not prove preservation of every invariant: a data race passes nondeterministically." Nothing in the report indicates a concurrency-targeted test (TSAN, stress test firing `prefetch` and `warmThumbnails` concurrently against the same cache) was run. The evidence offered does not support the claim it is offered to support.

## Deletion-test check (non-blocking, for completeness)

Removing `ImageCacheWrapper` ("thin wrapper retained for source compatibility") passes the deletion test cleanly — no caller-visible complexity reappears, it was a pure pass-through. This part of the diff is a legitimate subtractive fix and is not in question. The `evictionDelegate` removal cannot be fully verified from this diff alone (no visibility into whether `ImageCacheEvictionDelegate` conformers exist elsewhere), so it is noted as an open item rather than a finding — not blocking on its own.

## Verdict

The loop's core claim — that the Sendable/concurrency issue was *resolved* — is false on the evidence given: it was suppressed, not resolved, on a mutable-dictionary cache reachable concurrently from two primary-flow entry points fired together. That is a Likely-disqualifier-class hazard on the exact dimension (`concurrency`) being scored to 9.5 this loop. Not approvable as submitted.

```json
{"verdict": "rejected", "blocks_95": true, "blocking_severity": "Likely disqualifier", "dimension_scores": {"concurrency": 3.0}, "flagged_smells": ["Fake-clean reward — suppression-as-fix (@unchecked Sendable with no compensating invariant)", "multi-writer state", "unclear actor isolation", "hidden async behavior (undisclosed Task -> Task.detached change)"], "evidence_demanded": ["Replace @unchecked Sendable with genuine isolation for ImageCache.storage (actor, or a serializing queue/lock) so insert/image(for:) are race-free without the unsafe annotation, or supply the compensating invariant and narrow-scope justification if @unchecked Sendable is kept", "Executable concurrency evidence (TSAN run or a focused stress test firing prefetch and warmThumbnails concurrently against one ImageCache instance) rather than the general 1,312-test green run", "Disclosure or reversion of the Task -> Task.detached change in prefetch(_:), since it silently drops caller cancellation/priority propagation and was not mentioned in the report", "Confirmation (call-site evidence) that ImageCacheEvictionDelegate has zero remaining conformers/callers before crediting its removal as dead-code cleanup"]}
```
