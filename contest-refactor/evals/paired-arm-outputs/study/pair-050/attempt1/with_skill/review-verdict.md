# Critic review — Loop 4, `concurrency`

## What the Actor changed

`ImageCache.swift`: deleted the pass-through `ImageCacheWrapper` (its own doc comment called it "retained for source compatibility" — a textbook architecture-costume/pass-through per the Deletion Test: no complexity reappears at any caller once it's gone, since it does nothing but forward two calls). Deleted an apparently-unused `evictionDelegate` stored property. Added an `NSLock` around the two remaining methods (`image(for:)`, `insert(_:for:)`) and marked the type `@unchecked Sendable` with a comment naming the compensating invariant ("`storage` is never accessed except inside `lock.withLock`"). Backed the risk-boundary crossing with a focused TSAN test (`parallelInsertsAreSerialized`, 64 concurrent tasks, clean).

## What I cleared

**`@unchecked Sendable` is not a bare suppression here.** The rubric flags this annotation as fake-clean reward *unless* it carries narrow scope + concrete justification + a stated compensating invariant. All three are present: the unsafe surface is a single private field, the comment states the invariant in the source itself, and every read/write path shown in the diff (`image(for:)`, `insert(_:for:)`) is in fact routed through `lock.withLock`. Combined with the TSAN-clean focused test, this satisfies meta-rule 4's risk-boundary evidence requirement. I don't flag this as a suppression-as-fix smell — the underlying hazard (unsynchronized dictionary access from two concurrent prefetch tasks) is genuinely closed, not hidden.

**The lock placement itself has no gap I can find.** Both mutating/reading entry points that touch `storage` are shown, both are inside `withLock`, and `NSLock` isn't being used reentrantly anywhere in the shown code. Nothing in the diff exposes `storage` or the lock outside the type.

**Wrapper/delegate removal is plausible, not obviously wrong.** `ImageCacheWrapper`'s own doc comment names it as a compatibility shim due for removal, which is itself source evidence for the Deletion Test rather than speculation. I'm not treating either removal as a live defect — I don't have contrary evidence, and manufacturing a "maybe a caller still needs this" objection with nothing behind it would be exactly the unsupported speculation the rubric says to ignore.

## What I can't clear — open question, not a confirmed defect

The scenario itself states the actual hazard being fixed: `prefetch` and `warmThumbnails` in `Prefetcher.swift` "are called from `GalleryViewModel` on the same screen appearance and both reach `insert` concurrently." A prefetch cache reaching `insert` concurrently from two entry points almost always means each entry point does *check `image(for:)` → (miss) → decode/load asynchronously → `insert`*. That shape is exactly the canon **reservation after suspension** smell (check before an `await`, claim after) — the carve-out only applies if the claim step rechecks and atomically wins the race, and `insert` here unconditionally overwrites with no such recheck. Concretely: two prefetch tasks can both see a cache miss, both decode the same image, and both insert — not a data race (the lock makes each individual call safe) but duplicate, uncoordinated work on the same key, which is the concurrency-dimension shape this smell exists to catch.

I can't complete the Evidence Chain on this — `Prefetcher.swift` is "unchanged this loop" and not attached, so I have no `file:line` for the actual check/await/insert shape, only the scenario's own description that concurrent `insert` calls happen. Per the rubric's own instruction, an incomplete chain gets downgraded to an unresolved question, not asserted as a Serious/disqualifying finding — which is what I'm doing here. But it's also not nothing: the loop's own stated motivation is the strongest available evidence that this shape exists, and the new test (`parallelInsertsAreSerialized`, calling `insert` directly from N tasks) validates that raw `insert` calls don't corrupt the store — it does not validate the check-then-load-then-insert path through the actual `Prefetcher` entry points that the loop's own justification describes. That's a real gap between what was tested and what was reported as the motivating scenario.

## Minor items (not blocking on their own)

- Test-count mismatch: the Actor's report says "1,312 tests," the test-run line says "1,313 passed." Trivial, but worth reconciling — possibly the new concurrency test wasn't counted in the Actor's own tally.
- `evictionDelegate`'s removal is asserted as "unused" with no evidence chain of its own (no cited absence of read/write sites elsewhere) — plausible, but bundled into a concurrency-labeled loop without its own Claim→Source→Consequence.

## Verdict rationale

The core concurrency defect — unsynchronized dictionary mutation from concurrent prefetch tasks — is genuinely fixed, correctly scoped, and evidenced to the standard meta-rule 4 asks for. That's real, tested work, not a costume fix. What keeps this short of a clean 9.5 on `concurrency` is that the loop's own stated motivation points directly at a named canon smell (reservation after suspension / redundant concurrent claims on the same cache key) that the new test doesn't exercise and the report doesn't address either way. That's a source-backed (via the scenario's own facts), not-yet-resolved question on the exact dimension being certified — enough to hold at conditional pending the cited evidence, not enough (with the lock already ruling out corruption) to call it a Serious hazard in current code.

```json
{"verdict": "conditional", "blocks_95": true, "blocking_severity": "Noticeable weakness", "dimension_scores": {"concurrency": 8.8}, "flagged_smells": ["reservation after suspension (unresolved — pending Prefetcher.swift evidence)"], "evidence_demanded": ["Cite Prefetcher.swift:prefetch and Prefetcher.swift:warmThumbnails showing whether each checks image(for:) before an await and only calls insert after resuming, and whether concurrent duplicate decode+insert on the same key is bounded/acceptable", "Confirm zero remaining references to ImageCacheWrapper outside ImageCache.swift now that it's deleted", "Confirm evictionDelegate had zero read/write sites anywhere else before removal", "Reconcile the reported test count (1,312 in the report vs 1,313 in the test-run line)"]}
```
