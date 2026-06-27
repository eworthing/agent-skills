<!-- Spliced into CURRENT_REVIEW.md under "## Findings" as the targeted Priority-1
finding. The "Discovery lens:" line is spliced into the Discovery section the
reviewer reads at step 7 of its prompt. -->

Discovery lens: lens-apple.md

### F1 — Duplicate source of truth: `OrderSummary.itemCount` is hand-synced stored state (Priority 1)

- **Claim:** `OrderSummary` keeps a stored `itemCount` maintained in parallel to `items` via manual `+= 1` / `-= 1` in every mutator; it is a second source of truth for a value already fully determined by `items`.
- **Source:** `Sources/OrderSummary.swift` — `private(set) var itemCount` is written in `add(_:)` and `remove(at:)` alongside the `items` mutation.
- **Consequence:** the two can diverge — any future mutator that updates `items` but forgets `itemCount` (e.g. a bulk `removeAll` or `insert(contentsOf:)`) leaves a silently wrong count; classic duplicate-source-of-truth hazard.
- **Severity:** Noticeable weakness.
- **Remedy (minimal_correction_path):** delete the stored `itemCount` and its manual sync; derive it as a computed `var itemCount: Int { items.count }`.
