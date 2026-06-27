<!-- Spliced into CURRENT_REVIEW.md under "## Findings" as the targeted Priority-1
finding. The "Discovery lens:" line is spliced into the Discovery section the
reviewer reads at step 7 of its prompt. -->

Discovery lens: lens-apple.md

### F1 — DataSyncManager.start() fires an unbound Task with no stored reference and no cancellation path (Priority 1)

- **Claim:** `DataSyncManager.start()` creates a `Task { }` containing the main sync loop but does not store the task or provide any cancellation path; the loop runs indefinitely even after the manager is deinitialized.
- **Source:** `Sources/DataSyncManager.swift:13` — `Task { while true { ... } }` with no assignment to a stored property; no `deinit` present to cancel.
- **Consequence:** unclear task lifetime — the sync loop outlives the manager, cannot be stopped on demand (e.g., on logout), and fires after test teardown, causing flaky test state (Meta-Rule 4 risk boundary: unclear async lifetime).
- **Severity:** Serious deduction.
- **Remedy (minimal_correction_path):** store the returned task (`var syncTask: Task<Void, Never>?`), assign in `start()`, cancel in `deinit`; guard the loop body with `Task.isCancelled`.
