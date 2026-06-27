<!-- Spliced into CURRENT_REVIEW.md under "## Findings" as the targeted Priority-1
finding. The "Discovery lens:" line is spliced into the Discovery section the
reviewer reads at step 7 of its prompt. -->

Discovery lens: lens-apple.md

### F1 — FavoritesService has no Seam; recording stub does not constitute a second Adapter (Priority 1)

- **Claim:** `FavoritesService` is a concrete `final class` injected directly into `FavoritesViewModel`, `SearchResultsViewModel`, and `ProfileViewModel` with no protocol boundary. The diff introduces `FavoriteTracking` protocol and a `RecordingFavoriteTracker` test double, but the double is a recording stub: `allFavorites()` always returns `[]` regardless of what has been added, so it does not faithfully simulate the store's state.
- **Source:** `Sources/FavoritesService.swift:8` (`final class FavoritesService: FavoriteTracking`); `Sources/RecordingFavoriteTracker.swift:16` (`func allFavorites() -> [Track] { [] }`) — state written via `add()` is silently discarded in the stub.
- **Consequence:** Tests that inject `RecordingFavoriteTracker` cannot assert on `allFavorites()` output; the stub only records call counts, not behavior. A protocol whose only two conformers are the prod impl and a non-behavioral recording stub fails the Two-Adapter rule (architecture-rubric.md § Unified Seam Policy). No policy/failure/platform isolation carve-out applies to an in-process `[Track]` array.
- **Severity:** Serious deduction.
- **Remedy (minimal_correction_path):** replace `RecordingFavoriteTracker` with a behavior-faithful fake that actually stores tracks in its own `[Track]` array so `allFavorites()` reflects prior `add()` calls. Only then does the Two-Adapter rule pass.
