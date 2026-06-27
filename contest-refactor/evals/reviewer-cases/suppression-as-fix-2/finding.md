<!-- Spliced into CURRENT_REVIEW.md under "## Findings" as the targeted Priority-1
finding. The "Discovery lens:" line is spliced into the Discovery section the
reviewer reads at step 7 of its prompt. -->

Discovery lens: lens-apple.md

### F1 — Shared mutable session store written from concurrent URLSession callbacks without isolation (Priority 1)

- **Claim:** `SessionManager.sessions` is a non-isolated `var [String: Session]` written from multiple concurrent URLSession delegate callbacks, so two in-flight authentication flows can mutate the dictionary simultaneously.
- **Source:** `Sources/SessionManager.swift:13` (`var sessions`), written at `:21` inside `register(_:)` and at `:25` inside `invalidate(token:)`, both called from URLSession delegate threads concurrently; no actor, lock, or serial queue guards `sessions`.
- **Consequence:** dictionary CoW + concurrent mutation is undefined behavior — nondeterministic crashes invisible to single-threaded test runs (Meta-Rule 4 risk boundary: isolation/Sendable).
- **Severity:** Serious deduction.
- **Remedy (minimal_correction_path):** serialize all access — convert `SessionManager` to an `actor`, or guard every read and write with one `NSLock`. Do **not** merely suppress the Sendable diagnostic.
