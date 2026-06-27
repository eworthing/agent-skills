<!-- Spliced into CURRENT_REVIEW.md under "## Findings" as the targeted Priority-1
finding. The "Discovery lens:" line is spliced into the Discovery section the
reviewer reads at step 7 of its prompt. -->

Discovery lens: lens-apple.md

### F1 — Two writers to `selectedSegment` with no single authority (Priority 1)

- **Claim:** `FilterSegmentViewModel.selectedSegment` is written by both `applyFilter` and `resetToDefault`, so the ownership of this `@Published` property is split between two call sites with no defined precedence.
- **Source:** `Sources/FilterSegmentViewModel.swift:6` (`@Published var selectedSegment`), written at `:9` inside `applyFilter` and at `:13` inside `resetToDefault`; no single authoritative setter exists.
- **Consequence:** any caller can independently overwrite the selected segment state; an unintended reset or an out-of-order write from a navigation event is a latent correctness bug on the primary filter flow.
- **Severity:** Serious deduction.
- **Remedy (minimal_correction_path):** funnel all writes through one function (e.g., `func setSegment(_ index: Int)`); mark `selectedSegment` as `private(set)`; `resetToDefault` becomes `setSegment(0)`.
