<!-- Spliced into CURRENT_REVIEW.md under "## Findings" as the targeted Priority-1
finding. The "Discovery lens:" line is spliced into the Discovery section the
reviewer reads at step 7 of its prompt. -->

Discovery lens: lens-apple.md

### F1 — Duplicate source of truth: `SearchResultsViewModel.filters` is a manual copy of `SearchFilterViewModel.activeFilters` (Priority 1)

- **Claim:** `SearchResultsViewModel` maintains its own `@Published var filters: [String]` populated by a one-shot `applyFilters(from:)` call; any mutation of `SearchFilterViewModel.activeFilters` after that call is invisible to `SearchResultsViewModel`.
- **Source:** `Sources/SearchResultsViewModel.swift:6` (`@Published var filters`), written at `:10` inside `applyFilters(from:)`; `Sources/SearchFilterViewModel.swift:6` (`@Published var activeFilters`) is the authoritative owner — two independent arrays tracking the same logical state.
- **Consequence:** stale filter state — results can display data inconsistent with the visible filter selection when the user modifies filters without triggering a fresh `applyFilters` call; a correctness bug on the primary search flow.
- **Severity:** Serious deduction.
- **Remedy (minimal_correction_path):** eliminate `SearchResultsViewModel.filters` as a stored property; have `SearchResultsViewModel` hold a reference to `SearchFilterViewModel` (or subscribe via Combine) and derive filters from the single authoritative source.
