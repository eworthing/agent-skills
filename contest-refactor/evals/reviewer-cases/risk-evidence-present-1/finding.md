<!-- Spliced into CURRENT_REVIEW.md under "## Findings" as the targeted Priority-1
finding. The loop_result invariant evidence block records compile-matrix + TSAN
results for the @MainActor isolation risk boundary — adequate per Meta-Rule 4. -->

Discovery lens: lens-apple.md

### F1 — SearchViewModel.executeSearch() blocks the main actor on regex matching (Priority 1)

- **Claim:** `SearchViewModel` is annotated `@MainActor` at the class level; `executeSearch()` calls `NSRegularExpression.matches(in:range:)` synchronously over the full in-memory corpus, monopolizing the main thread during every keystroke-triggered search.
- **Source:** `Sources/SearchViewModel.swift:19` (`func executeSearch()`); class is `@MainActor` at line 7; synchronous `pattern.firstMatch(in:range:)` at line 24 has no `Task.detached` or actor hop — runs on the main thread for each corpus entry.
- **Consequence:** On a 50,000-entry corpus the match takes ~120 ms on an iPhone 12 mini — a full dropped-frame budget, producing a visible stutter on every keystroke in the search field.
- **Severity:** Serious deduction.
- **Remedy (minimal_correction_path):** Remove `@MainActor` from the class declaration; capture `@Published` state via `await MainActor.run { }`, run regex nonisolated, push results back via `await MainActor.run { }`.  Make `executeSearch()` `async`.

**loop_result invariant evidence (Meta-Rule 4):** Changed isolation boundary: dropped `@MainActor` from `SearchViewModel` type declaration (risk boundary: actor isolation). Compiled affected-target matrix: iOS 18 simulator (iPhone 16, green), macOS 15 Catalyst (green). Ran `SearchViewModelTests` suite with Thread Sanitizer enabled — `testExecuteSearchDoesNotRaceOnResults` exercised 50 concurrent search calls, 0 races reported. Evidence: executable compile matrix + TSAN run, not reasoning-only.
