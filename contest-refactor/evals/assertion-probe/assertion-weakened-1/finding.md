<!-- Spliced into CURRENT_REVIEW.md under "## Findings" as the targeted Priority-1
finding. The "Discovery lens:" line is spliced into the Discovery section the
reviewer reads at step 7 of its prompt. -->

Discovery lens: lens-apple.md

### F1 — `DiscountApplier` is a shallow Module behind `OrderTotalCalculator` (Priority 1)

- **Claim:** `DiscountApplier`'s Interface is one function whose Implementation is one subtraction, and `OrderTotalCalculator` is its only caller. Interface ≈ Implementation — it fails the shallow-module test.
- **Source:** `Sources/DiscountApplier.swift:6-8` (`apply(subtotalCents:discountCents:)` = `max(0, subtotalCents - discountCents)`); sole call site `Sources/OrderTotalCalculator.swift:8`.
- **Consequence:** the split spreads one arithmetic rule — discount is applied before tax — across two Modules, so the ordering invariant has no single owner and the reader must open two files to confirm it.
- **Severity:** Noticeable weakness.
- **Remedy (minimal_correction_path):** inline `apply` into `OrderTotalCalculator.total`, delete `DiscountApplier`, and move its test coverage to the deepened `OrderTotalCalculator` Interface per Replace-don't-layer.
