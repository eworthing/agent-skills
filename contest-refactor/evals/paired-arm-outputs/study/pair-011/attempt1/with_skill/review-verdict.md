# Critic Review — Loop 4, `concurrency` dimension

## Scope

Reviewed against `scenario.md`'s diff and the Actor's report only, per the sandbox for this
task. Applying `architecture-rubric.md` (Severity Anchors, Vocabulary — Smells) and
`method.md` (Evidence Chain, Meta-Rules, Step 5/8 concurrency and test guardrails).

## What the diff gets right

- **`ImageCacheWrapper` deletion** passes the deletion test: its three members were pure
  forwarding (`image(for:)`, `insert(for:)` each one line, calling straight into `inner`). No
  complexity reappears at a caller — it's a pass-through Module removed correctly. Subtractive
  fix, no finding.
- **`evictionDelegate` removal** — a stored optional with no read site in the diff shown is
  consistent with *state with no authority*; removing unused surface is the right direction (I
  can't verify "unused" beyond what the diff shows, since I'm scoped to `scenario.md` only, but
  nothing here contradicts the claim).

Both are legitimate simplification, not fake simplification — they shrink the Interface without
hiding ownership or lifetime.

## Finding: `@unchecked Sendable` suppresses a real, reachable data race

**Claim.** `ImageCache` is declared `@unchecked Sendable` to satisfy the compiler, but the type
has no actual synchronization. The conformance is asserted, not earned — this is the
rubric's *suppression-as-fix* sub-pattern of fake-clean reward, and it leaves a live
concurrency hazard in place while the loop reports it as resolved.

**Source.**
- `Sources/Gallery/ImageCache.swift`: `final class ImageCache: @unchecked Sendable { private
  var storage: [String: UIImage] = [:] ... func insert(_ image: UIImage, for key: String) {
  storage[key] = image } }` — no lock, no actor, no serial queue anywhere in the type.
- `Sources/Gallery/Prefetcher.swift`: `prefetch(_:)` was changed from `Task { ... }` to
  `Task.detached { ... self.cache.insert(image, for: url.absoluteString) }`; `warmThumbnails(_:)`
  already used `Task.detached { ... self.cache.insert(thumb, for: url.absoluteString +
  "#thumb") }`. Both loop over `urls` and spawn one detached task per URL.
- `scenario.md`'s closing line: "The two prefetch entry points (`prefetch`,
  `warmThumbnails`) are called from `GalleryViewModel` on the same screen appearance." — so
  concurrent invocation of both methods, each fanning out N detached tasks, is the *expected*
  runtime shape on a primary flow (gallery screen load), not an edge case.

**Consequence.** `Task.detached` tasks run unserialized on the concurrent thread pool. Swift's
`Dictionary` is documented as unsafe for concurrent mutation from multiple threads — even to
distinct keys — because an insert can trigger the shared storage buffer to resize/rehash.
With both `prefetch` and `warmThumbnails` firing overlapping detached tasks that all call
`storage[key] = image` on the same `ImageCache` instance, concurrent writes can race the
internal hash table, producing nondeterministic crashes or corrupted cache reads on a primary
user flow (screen appearance). This matches the rubric's Likely-disqualifier anchor verbatim:
"racing async flows that can corrupt user-visible state." It is also exactly the *fake-clean
reward → suppression-as-fix* smell: a safety-affecting suppression (`@unchecked Sendable`)
standing in for a real fix, carrying none of the required narrow scope, concrete justification,
or compensating invariant — no comment, no lock, no actor, no removal condition. The Actor's
report treats the conformance as resolved ("resolved the Sendable conformance the compiler
started requiring... Full suite green... Proposing `concurrency` → 9.5"), which is scoring the
silenced warning rather than the underlying hazard.

Per Meta-Rule 4, this change crosses a named risk boundary (Sendable/thread-safety) and the
Actor was required to record preservation evidence — ideally executable (a focused concurrency
test or TSAN run), reasoning-only only if tooling is genuinely unavailable and that limitation
is stated. The report cites none of this: "1,312 passed, 0 failed" is a single-config green run,
which by the rubric's own language "does not prove preservation of every invariant: a data race
passes nondeterministically." No concurrency-specific evidence is offered at all.

**Remedy.** Smallest behavior-preserving repair: convert `ImageCache` to an `actor`. Its two
methods are simple synchronous reads/writes with no held state across an `await`, so
actor-izing costs nothing structurally — call sites `await cache.insert(...)` /
`await cache.image(for:)`. If a synchronous read is required somewhere not visible in this
diff, the fallback is a private serial `DispatchQueue` or `os_unfair_lock` guarding `storage`,
with `@unchecked Sendable` retained only alongside a comment naming the compensating invariant.
Either way, the fix is establishing real isolation, not asserting it away.

## Secondary note (Cosmetic on its own, compounds the credibility read)

`prefetch`'s task creation changed from `Task { ... }` to `Task.detached { ... }`. This is a
real behavioral change (detached tasks drop parent priority and cancellation propagation) that
the Actor's report does not mention — the report describes only the wrapper/delegate removal
and "the Sendable conformance." Undisclosed scope creep on a risk-boundary-adjacent line, worth
naming even though it isn't independently disqualifying.

## Verdict

The loop targets the `concurrency` dimension and proposes `9.5`. A Likely-disqualifier-class
hazard — an unsynchronized dictionary shared and mutated by concurrent detached tasks on a
primary flow, masked by a bare `@unchecked Sendable` — is present and reachable. This blocks
acceptance at the 9.5 threshold outright; it is not a documentation/evidence gap that a
"conditional" accept-with-follow-up could resolve, because the hazard is structural (no
synchronization exists) rather than merely unproven.

```json
{"verdict": "rejected", "blocks_95": true, "blocking_severity": "Likely disqualifier", "dimension_scores": {"concurrency": 3}, "flagged_smells": ["fake-clean reward (suppression-as-fix: bare @unchecked Sendable with no compensating invariant)", "racing async flows that can corrupt user-visible state (unsynchronized Dictionary storage mutated by concurrent Task.detached writers on a primary flow)"], "evidence_demanded": ["Real synchronization for ImageCache.storage — convert to actor or add a serial queue/lock, replacing the bare @unchecked Sendable", "If @unchecked Sendable is retained for any reason, a narrow-scope justification comment plus the compensating invariant that makes it safe", "Executable concurrency evidence for the risk-boundary crossing (a focused concurrent-insert test or TSAN run), since the 1,312-test green run is single-config and does not exercise the race", "Disclosure/justification for the undisclosed prefetch() Task -> Task.detached change and its cancellation/priority-propagation implications"]}
```
