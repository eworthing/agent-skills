<!-- Spliced into CURRENT_REVIEW.md under "## Findings" as the targeted Priority-1
finding. The "Discovery lens:" line is spliced into the Discovery section the
reviewer reads at step 7 of its prompt. -->

Discovery lens: lens-apple.md

### F1 — Duplicate source of truth: `CheckoutViewModel.lineItems` is a manual copy of `CartViewModel.items` (Priority 1)

- **Claim:** `CheckoutViewModel` maintains an independent `@Published var lineItems: [CartItem]` populated by a one-shot `sync(from:)` call; items added to the cart after that call do not appear in the checkout total.
- **Source:** `Sources/CheckoutViewModel.swift:6` (`@Published var lineItems`), written at `:13` inside `sync(from:)`; `Sources/CartViewModel.swift:12` (`@Published var items`) is the only authoritative write target — two independent arrays tracking the same cart state.
- **Consequence:** stale checkout state — items added after `sync()` are invisible to `total`, producing an incorrect purchase total on the primary checkout flow.
- **Severity:** Serious deduction.
- **Remedy (minimal_correction_path):** remove the stored `lineItems` copy from `CheckoutViewModel`; have it hold a `let cart: CartViewModel` reference and expose `var lineItems: [CartItem] { cart.items }` as a computed property.
