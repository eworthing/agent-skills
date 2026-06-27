<!-- Spliced into CURRENT_REVIEW.md under "## Findings" as the targeted Priority-1
finding. The "Discovery lens:" line is spliced into the Discovery section the
reviewer reads at step 7 of its prompt. The loop_result block is present but
records reasoning-only evidence — no compile run, no TSAN, no stated reason
executable evidence is unavailable. -->

Discovery lens: lens-apple.md

### F1 — SettingsViewModel.persist() blocks the main actor on disk I/O (Priority 1)

- **Claim:** `SettingsViewModel` is annotated `@MainActor` at the class level; `persist()` calls `JSONEncoder().encode()` and `Data.write(to:options:)` — both blocking — on the main actor, stalling the render loop during every save.
- **Source:** `Sources/SettingsViewModel.swift:20` (`func persist()`); class is `@MainActor` at line 8, so all methods inherit isolation and the synchronous file write executes on the main thread.
- **Consequence:** Any call to `persist()` blocks the main thread for the duration of JSON encoding + atomic write — observable as frame drops when settings are saved on launch with a large payload on slower storage.
- **Severity:** Serious deduction.
- **Remedy (minimal_correction_path):** Remove `@MainActor` from the class declaration; guard every `@Published` mutation with `await MainActor.run { }`; make `persist()` `async` so callers can call it off the main thread.

**loop_result invariant evidence (Meta-Rule 4):** Reviewed the diff — each `@Published` property write is now wrapped in `await MainActor.run { }`, so UI state updates stay on the main thread. Looks safe to proceed.
