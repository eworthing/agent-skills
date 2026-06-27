<!-- Spliced into CURRENT_REVIEW.md under "## Findings" as the targeted Priority-1
finding. The "Discovery lens:" line is spliced into the Discovery section the
reviewer reads at step 7 of its prompt. -->

Discovery lens: lens-apple.md

### F1 — Shared mutable cache mutated from concurrent tasks without isolation (Priority 1)

- **Claim:** `ImageCache.store` is a non-isolated `var [URL: Data]` read and written from multiple concurrent `Task` contexts, so two in-flight `image(for:)` calls can mutate the dictionary simultaneously.
- **Source:** `Sources/ImageCache.swift:6` (`var store`), written at `:14` inside `image(for:)` which is called from unstructured `Task { }` sites; no actor, lock, or serial queue guards `store`.
- **Consequence:** classic data race — dictionary CoW + concurrent insert is undefined behavior; crashes are nondeterministic and invisible to a single-config test run (Meta-Rule 4 risk boundary: isolation/Sendable).
- **Severity:** Serious deduction.
- **Remedy (minimal_correction_path):** give `store` a single owner — convert `ImageCache` to an `actor`, or guard every access with one `NSLock`/serial queue. Do **not** merely suppress the isolation diagnostic.
