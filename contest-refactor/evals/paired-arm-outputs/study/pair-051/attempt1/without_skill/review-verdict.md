## Independent review — Loop 4, `concurrency` dimension

### What the diff actually does

Three things happen in one hunk, only one of which is a concurrency change:

1. Deletes `ImageCacheWrapper`, a pass-through class.
2. Deletes the `evictionDelegate` property from `ImageCache`.
3. Adds an `NSLock` and wraps both `image(for:)` and `insert(_:for:)` bodies in
   `lock.withLock { ... }`, then marks `ImageCache` as `@unchecked Sendable` with a
   comment justifying the escape hatch.

### The locking mechanism itself checks out

This part is genuinely solid, and verifiably so from the diff alone rather than by
taking the Actor's word for it:

- `storage` is declared `private`. In Swift, `private` is *file-scoped*, not just
  type-scoped — only code in this same file can touch `storage` directly, and every
  line in this file that touches it now goes through `lock.withLock`. That's not a
  convention the Actor is hoping holds; it's a language-enforced invariant the
  reviewer can confirm just by reading the diff. The `@unchecked Sendable` comment's
  claim ("storage is never accessed except inside lock.withLock") is therefore
  actually checkable, and it holds for what's shown.
- No nested/reentrant locking, no lock-then-call-into-another-locking-method pattern
  that would deadlock on `NSLock` (which is non-reentrant).
- TSAN-clean under 64 concurrent inserts, plus a full green suite (1,313 tests),
  is real evidence, not just an assertion.

If the loop were scoped to *only* "add a lock around storage," I'd score this near
the top of the range and see no blocker.

### Where I'd stop short of approving as-is

**1. Test coverage doesn't match the described access pattern.** The scenario says
the actual production hazard is `prefetch` and `warmThumbnails` both reaching
`insert` concurrently — and that's what `parallelInsertsAreSerialized` tests
(insert-vs-insert). But a gallery cache's other real caller is UI code reading via
`image(for:)` while prefetch is still writing — a read/write interleaving, not
write/write. Because both methods share one lock, this is *logically* covered by
the same reasoning that makes the write/write case safe — but it's asserted, not
demonstrated. The one test added exercises the narrower case, and TSAN only flags
races that occur in the interleavings it actually executes, so nothing here
empirically rules out a regression if a future edit gives `image(for:)` an
unlocked fast path. I'd ask for either a mixed read+write TSAN test or an explicit
written note that the read path was intentionally excluded from the test scope
and why that's still sufficient.

**2. Two unrelated deletions are riding along in a "concurrency" loop, and neither
is backed by shown evidence.** The Actor's report frames both as cleanup
("consolidated," "dropped the unused ... hook"), but the code itself contradicts
that framing in one case: the deleted `ImageCacheWrapper` carried the comment
*"Thin wrapper retained for source compatibility."* That is not decorative —
it's a note from whoever added it that something outside this file's normal call
graph may depend on `ImageCacheWrapper` continuing to exist (a separate module,
downstream package consumer, or Objective-C-visible surface, for instance). A
green `swift test` run for this package proves nothing about consumers outside
that package's test target. Deleting a type explicitly labeled as a compatibility
shim, in the same diff as an unrelated concurrency fix, without showing that its
callers were migrated or that no external consumer exists, is exactly the kind
of claim I'd want grep/build evidence for before accepting.

Similarly, "dropped the unused `evictionDelegate` hook" is asserted, not shown.
The diff proves the *property* is gone; it doesn't show that `ImageCacheEvictionDelegate`
has zero remaining references elsewhere, nor does it address whether removing the
hook silently drops memory-pressure eviction behavior the type used to support.
If the property really had no external assignees, the build would have failed
without it — the green suite is at least consistent with "no local caller"— but
that's weaker evidence than an explicit reference check, and it says nothing
about whether eviction behavior itself now regresses.

Neither of these is a concurrency defect in the strict sense — they don't affect
whether `storage` is race-free. But they are unverified, non-trivial deletions
smuggled into a loop that's scoped and reported as a concurrency fix, which is
itself worth naming: it makes the "full suite green" claim do more work than it
can actually support, since the suite wasn't shown to cover the compatibility
surface that motivated `ImageCacheWrapper`'s existence in the first place.

### Verdict

The locking change is correct, well-reasoned, and well-evidenced on its own
terms — I would not block on the mechanism itself. What blocks a clean 9.5 is the
gap between "full suite green" and what that phrase is being asked to cover here:
a compatibility shim explicitly labeled as load-bearing, deleted with no shown
migration evidence, plus a delegate hook removed with no reference check, both
riding inside a diff whose report only accounts for the lock. Conditional
approval: land the locking change, but require the two deletions to either be
independently verified (grep for remaining references / confirm no out-of-package
consumer of `ImageCacheWrapper`) or be split into their own loop where their risk
can be assessed on its own merits instead of borrowing the concurrency test's
green checkmark.

```json
{"verdict": "conditional", "blocks_95": true, "blocking_severity": "major", "dimension_scores": {"concurrency": 8.5}, "flagged_smells": ["compatibility shim removed without call-site verification (ImageCacheWrapper's own doc comment said 'retained for source compatibility')", "unverified dead-code claim (evictionDelegate/ImageCacheEvictionDelegate removed with no shown reference check)", "scope creep in a dimension-scoped loop (two unrelated deletions bundled into a concurrency-only loop)", "test coverage narrower than the described/real access pattern (insert-vs-insert tested, no concurrent read-vs-write test)"], "evidence_demanded": ["Proof (grep or build across all consuming targets, not just this package's test suite) that ImageCacheWrapper has zero remaining callers before treating its removal as safe", "Proof that evictionDelegate and ImageCacheEvictionDelegate have no remaining references anywhere, plus confirmation eviction/memory-pressure behavior doesn't regress without the hook", "A TSAN test (or explicit written justification) covering concurrent image(for:) reads interleaved with insert writes, not just insert-vs-insert", "Explicit sign-off statement that NSLock's acquire/release is being relied on for storage visibility across threads, since @unchecked Sendable is a manually-audited claim, not a compiler-checked one"]}
```
