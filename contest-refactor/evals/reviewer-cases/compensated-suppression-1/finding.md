<!-- Spliced into CURRENT_REVIEW.md "## Findings" as the targeted Priority-1
finding. SAME finding as the suppression-as-fix twin — only the head/ diff
differs. The loop_result evidence (below the finding) records the invariant
proof the reviewer's Check 2 looks for. -->

Discovery lens: lens-apple.md

### F1 — Shared mutable cache mutated from concurrent tasks without isolation (Priority 1)

- **Claim:** `ImageCache.store` is a non-isolated `var [URL: Data]` read and written from multiple concurrent `Task` contexts, so two in-flight `image(for:)` calls can mutate the dictionary simultaneously.
- **Source:** `Sources/ImageCache.swift:6` (`var store`), written at `:14` inside `image(for:)`; no actor, lock, or serial queue guards `store`.
- **Consequence:** classic data race — dictionary CoW + concurrent insert is undefined behavior; nondeterministic crashes invisible to a single-config test run (Meta-Rule 4 risk boundary: isolation/Sendable).
- **Severity:** Serious deduction.
- **Remedy (minimal_correction_path):** give `store` a single owner — serialize access behind one lock (or convert to an actor).

**loop_result invariant evidence (Meta-Rule 4):** changed an isolation boundary (added `@unchecked Sendable`). Compensating invariant: all reads/writes of `store` now go through `lock.withLock { }`; ran ThreadSanitizer on `ImageCacheConcurrencyTests.testConcurrentInsertsAreSerialized` (200 concurrent inserts) — 0 races reported. Evidence recorded, not reasoning-only.
