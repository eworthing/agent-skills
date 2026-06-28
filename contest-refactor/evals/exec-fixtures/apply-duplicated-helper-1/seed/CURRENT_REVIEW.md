# contest-refactor review

## Discovery
- Source roots: `Sources/`
- Selected lens: `lens-apple.md`
- Test command: none configured; build oracle is `swiftc -typecheck`
- Loop 1 of 10 (cap) — [STATE: CONTINUE]

## Findings

### Finding #1: Collapse the triplicated subtotal/tax computation into single owners

**Why it matters** — A single pricing-rule change (rounding, a discount, a second tax) must be edited in three methods, and the copies can silently drift into returning inconsistent totals to the checkout screen.

**What is wrong** — The subtotal-accumulation loop is copy-pasted verbatim in `subtotal()`, `totalWithTax()`, and `receiptLines()`, and the tax step `sum * taxRate` is duplicated in `totalWithTax()` and `receiptLines()`. No single owner of the pricing arithmetic exists.

**Evidence** — `Sources/OrderCalculator.swift:20-26` (subtotal loop), `:30-35` (duplicated loop + tax), `:41-47` (third loop).

**Severity** — Serious deduction.

**Minimal correction path** — Reuse `subtotal()` inside `totalWithTax()` and `receiptLines()`; add one private `tax(on:)` helper for the `* taxRate` step; add a `lineTotal` computed property on `LineItem`. No new types/protocols/files; behavior-preserving.

**Blast radius** — Change: `Sources/OrderCalculator.swift`. Avoid: `Sources/ReceiptFormatter.swift`.

## Improvement Backlog
1. **Collapse the triplicated subtotal/tax computation into single owners** — structural / needed for winning. Why it matters: removes duplicated authority over the core pricing rule, eliminating drift between the three totals. Score impact: Code simplicity, Architecture quality, and Domain modeling each +1.5 to +2.0.
