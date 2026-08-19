# Critic Review — Loop 4, `concurrency` dimension

## Scope note

Per the sandbox for this review, I have exactly three inputs: `scenario.md` (diff + Actor
report), `architecture-rubric.md`, and `method.md`. I do not have `findings_registry.json`,
`REVIEW_HISTORY.json`, `CONTEXT.md`/ADRs, `Prefetcher.swift`, or the rest of the repository.
Steps 1.5/1.6/1.7 (registry lookup, per-finding retirement, anchor-check) and the Step 0
CONTEXT.md/ADR read are not performable with these inputs and are skipped rather than faked.
"Current source" for this review means the diff hunk given in `scenario.md`, read directly —
not the Actor's prose summary of it.

## Authority Map (Method Step 2)

- **Owner:** `ImageCache.storage: [String: UIImage]`, a private dictionary.
- **Writers:** `insert(_:for:)`, called (per the scenario's own note) from both `prefetch` and
  `warmThumbnails` in `Prefetcher.swift`, invoked concurrently on the same screen appearance.
- **Readers:** `image(for:)`. Caller not shown in the diff, but by construction (a UIImage
  cache) is the display path.
- **Persistence seam:** none — in-memory only. Dependency category is `in-process` per the
  rubric's Dependency Categorization table: pure computation, in-memory state, no I/O. No
  Seam/port is warranted here, and the diff correctly does not introduce one — it goes the
  other way and *removes* an indirection (`ImageCacheWrapper`). That direction is correct
  under the Unified Seam Policy: a bare concrete class needs no protocol when there's one
  production Adapter and no policy/failure/platform-isolation reason for a seam.
- **Async mutation entry points:** the two prefetch call sites, unchanged this loop.
- Single owner, single writer path (all writes go through `insert`, all reads through
  `image(for:)`), no ambiguity about who owns `storage`. This is a clean Authority Map going
  in — no *state with no authority*, no multi-writer smell.

## Architecture review (Method Step 3 / Step 6)

**Deletion test on `ImageCacheWrapper`:** its four-line body was a pure delegate to `inner`
with no added policy, so the deletion test passes cleanly — complexity does not reappear
anywhere, it just vanishes. Removing a pass-through wrapper and an unused `evictionDelegate`
hook is exactly the subtractive move Meta-rule 5 asks for, and it's the right call here.

**Doc-vs-code flag on that same deletion.** The removed type's own doc comment read: *"Thin
wrapper retained for source compatibility."* That phrase exists to signal exactly one thing —
some caller, at some point, needed the `ImageCacheWrapper` type name to keep compiling. The
Actor's evidence for safe removal is `swift test` — 1,313 passed — which only proves the
*tested target* still compiles and passes. It says nothing about whether `ImageCacheWrapper`
was consumed as public API surface by a separate target (an app target, a second package
consumer) that this test run wouldn't touch. This is precisely the class of risk Meta-rule 4
calls out: *"a narrowed Sendable/visibility boundary is invisible to a passing suite"* — the
same logic applies to a symbol deleted outright. The Actor's report doesn't mention checking
for out-of-target references, so the compatibility claim the type's own doc comment made is
retired without being addressed. I don't have the rest of the repo to confirm or falsify this
myself, so I'm not treating it as a proven defect — it's a scope-limited, evidence-demanded
gap, not a finding of actual breakage.

**`@unchecked Sendable` — evaluated against the suppression-as-fix carve-out.** The rubric
treats `@unchecked Sendable` as a safety-affecting suppression that counts as fake-clean
reward *unless* it carries narrow scope + concrete justification + the compensating invariant
that makes it safe. Checking the actual diff against that bar:

- Narrow scope: yes — the annotation sits on exactly the one type, with no broader `@unchecked`
  spread.
- Concrete justification: yes — the comment states the invariant directly.
- Compensating invariant: verifiable from the same diff — both `image(for:)` and
  `insert(_:for:)` route through `lock.withLock { … }`; there is no code path in the diff that
  touches `storage` outside the lock.
- Removal condition when temporary: not applicable — this isn't presented as a temporary shim,
  it's the permanent design (lock-protected storage is data-race-free by construction).

This passes the carve-out. Read from source, not from the Actor's characterization: the
suppression is honest, not a hazard hidden behind an annotation. This is the correct minimal
fix for a mutable dictionary that legitimately needs cross-task sharing — no unwarranted new
Seam, no protocol soup, just a lock and an honest annotation on the type it protects.

## Concurrency review (Method Step 5) / Test review (Method Step 8)

The stated hazard this loop fixes is concurrent `insert` calls from `prefetch` and
`warmThumbnails`. The added test (`parallelInsertsAreSerialized`, 64 concurrent tasks under
TSAN) matches that hazard precisely and the report says it's clean.

**Mutation-test mental model, applied to the *test*, not just the code.** Name one mutation on
this primary-flow, central mutable runtime behavior (a cache shared between background
prefetch and the display path) that current tests would not catch: delete
`lock.withLock` from `image(for:)` only, leaving `insert` locked. Would
`parallelInsertsAreSerialized` catch it? No — that test never calls `image(for:)`, so no
reader-writer race is ever exercised during the run, and TSAN can only report a race it
actually observes. Per this method's own Step 8 branch: a nameable mutation on a primary-flow,
central mutable runtime behavior that current tests don't catch is a Noticeable-or-worse
finding, not a hypothetical one to wave off.

To be clear about what this is and isn't: reading the diff directly, `image(for:)` **is**
correctly locked, so I'm not asserting a live race exists. The gap is evidentiary — the Actor's
report leans on "full suite green" plus a TSAN run that only stresses the write side to back a
claim ("safe to share across the prefetch tasks") that implicitly covers the read side too.
Meta-rule 4 prefers executable evidence for exactly this kind of risk-boundary (Sendable /
thread-safety) change, and allows reasoning-only "just when the invariant is not mechanically
testable or tooling is unavailable." Neither excuse applies — the Actor already has TSAN wired
up and clearly knows how to write this test; the reader/writer interleaving just wasn't
included.

## Findings

**Finding 1 — Concurrency test covers writer/writer serialization only, not reader/writer.**
- *Claim:* the added `ImageCacheConcurrencyTests.parallelInsertsAreSerialized` test, offered as
  evidence for "safe to share across the prefetch tasks," exercises only concurrent `insert`
  calls. It does not exercise `image(for:)` concurrently with `insert(_:for:)`, so it cannot
  detect a regression that desynchronizes the read path.
- *Source:* diff — `insert` calls only in the described test; `image(for:)`'s
  `lock.withLock { storage[key] }` has no concurrent-read counterpart in the described test
  suite.
- *Consequence:* reduces regression resistance and overstates what the TSAN run actually
  proves; a future edit that drops the lock from `image(for:)` alone would ship green.
- *Remedy:* add a focused TSAN test that runs `insert` and `image(for:)` concurrently from
  multiple tasks (mirrors the real display-during-prefetch pattern this cache exists for).
- Severity: **Noticeable weakness** — the shipped code is correct on inspection; this is a
  coverage/evidence gap, not a live defect.

**Finding 2 — Deletion of a "retained for source compatibility" wrapper is verified only
against the tested target.**
- *Claim:* `ImageCacheWrapper` carried a doc comment stating its purpose was source
  compatibility; its removal is backed only by a same-target `swift test` pass.
- *Source:* diff — deleted doc comment text; Actor's own test evidence is `swift test`, no
  mention of a cross-target/workspace check.
- *Consequence:* Meta-rule 4's risk-boundary guidance (cross-file visibility changes are
  invisible to a single passing suite) applies to a deleted symbol the same way it applies to
  a narrowed access modifier — a consumer outside the tested target wouldn't show up here.
- *Remedy:* grep the workspace (not just the tested target) for `ImageCacheWrapper` before
  treating the deletion as fully verified, or state explicitly that no other target references
  it.
- Severity: **Noticeable weakness**, scope-limited — I cannot confirm or falsify this from the
  three attached files; flagging it as an open, evidence-demanded question rather than a proven
  defect.

Neither finding is a *Likely disqualifier*: no reachable race was demonstrated against the
diffed source, and both prod code paths (`image(for:)`, `insert(_:for:)`) are correctly locked.
Neither is merely *Cosmetic* either — both bear directly on whether the loop's own evidence
("full suite green," "TSAN clean," "retained for source compatibility" quietly dropped)
actually supports the certainty the Actor's report claims.

## Verdict

The underlying fix is real and well-reasoned: a genuine multi-writer hazard (concurrent
`insert` from two prefetch entry points) gets a correctly-scoped lock, a narrowly-justified
`@unchecked Sendable` that meets the rubric's carve-out on inspection, and a real (if partial)
TSAN test. This is not fake-clean reward and not architecture costume — it's a legitimate,
subtractive, single-owner concurrency fix. But the loop's own evidence doesn't fully cover the
claim it's being scored on: the TSAN test proves writer/writer safety, not the reader/writer
safety the cache's actual usage pattern requires, and the wrapper deletion's "source
compatibility" rationale is retired without cross-target verification. Two Noticeable-weakness,
evidence-backed gaps, both closable with a small addition (one more test; one grep), are enough
to hold this dimension just below the 9.5 bar until closed.

```json
{"verdict": "conditional", "blocks_95": true, "blocking_severity": "Noticeable weakness", "dimension_scores": {"concurrency": 9.0}, "flagged_smells": [], "evidence_demanded": ["A TSAN-covered concurrency test that runs image(for:) reads concurrently interleaved with insert(_:for:) writes (not just insert-vs-insert), to substantiate the 'safe to share' claim for the cache's actual read+write access pattern.", "Confirmation (cross-target grep or multi-target build/test) that no consumer outside the tested target still references the deleted ImageCacheWrapper type, given its doc comment explicitly stated it was retained for source compatibility."]}
```
