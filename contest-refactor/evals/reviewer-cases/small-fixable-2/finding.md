<!-- Spliced into CURRENT_REVIEW.md under "## Findings" as the targeted Priority-1
finding. The "Discovery lens:" line is spliced into the Discovery section the
reviewer reads at step 7 of its prompt. -->

Discovery lens: lens-apple.md

### F1 — CartViewModel delegates price formatting to PriceFormatter; unit tests accumulate at the shallow helper layer rather than CartViewModel's interface (Priority 1)

- **Claim:** `PriceFormatter` is a shallow helper with a one-line interface; `CartViewModel` owns it as a dependency, and unit tests exist only at `PriceFormatter`'s layer (`Tests/PriceFormatterTests.swift`) rather than at `CartViewModel`'s interface. This is a Replace-don't-layer violation.
- **Source:** `Sources/PriceFormatter.swift:5–7` — `string(from:)` is a single `String(format:)` call; `Sources/CartViewModel.swift:12` — `totalDisplay = formatter.string(from: cents)`; `Tests/PriceFormatterTests.swift:5–16` tests `PriceFormatter` directly with no corresponding test at `CartViewModel`'s interface.
- **Consequence:** tests at the wrong surface — helper indirection adds one navigation hop with no Leverage; if the formatting logic moves inside `CartViewModel`, the shallow tests become dead weight and may not be cleaned up, degrading regression resistance.
- **Severity:** Noticeable weakness.
- **Remedy (minimal_correction_path):** inline `String(format:)` into `CartViewModel.updateTotal(_:)`, delete `PriceFormatter` and its test file, add tests at `CartViewModel`'s interface.
