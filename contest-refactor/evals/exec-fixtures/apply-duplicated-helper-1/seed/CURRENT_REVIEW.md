# contest-refactor review

## Discovery
- Source roots: `Sources/`
- Selected lens: `lens-apple.md`
- Test command: none configured; build oracle is `swiftc -typecheck`
- Loop 1 of 10 (cap) — [STATE: CONTINUE]

## Contest Verdict
Promising, but architecturally immature

A clean immutable value type using Foundation.Decimal for money, but the core pricing arithmetic is copy-pasted across all three public methods. Fixable without new structure.

## Scorecard (1-10)
- Architecture quality: 7 | SAME | Sources/OrderCalculator.swift:20-58 — pricing computation re-derived in three methods; otherwise a clean single value type
- State management and runtime ownership: 8 | SAME | Sources/OrderCalculator.swift:17-18 — items/taxRate are let; no mutable runtime concern
- Domain modeling: 7 | SAME | Sources/OrderCalculator.swift:23,32,43,51 — anemic LineItem; line-total inlined 4x
- Data flow and dependency design: 8 | SAME | Sources/OrderCalculator.swift:17-18 — explicit inputs/outputs, pure, no globals
- Framework / platform best practices: 8 | SAME | Sources/OrderCalculator.swift:13,18,23 — Decimal money arithmetic, not Double
- Concurrency and runtime safety: 8 | SAME | Sources/OrderCalculator.swift — no Task/actor/async; synchronous value type, vacuously race-free
- Code simplicity and clarity: 6 | SAME | Sources/OrderCalculator.swift:20-26,30-35,41-47 — subtotal loop copy-pasted 3x; dominant defect
- Test strategy and regression resistance: 8 | SAME | Sources/OrderCalculator.swift:20-58 — public methods compile under swiftc -typecheck; no planted regression test in this fixture
- Overall implementation credibility: 8 | SAME | Sources/OrderCalculator.swift:5-9 — honest doc comment, but triplication is a real leak

## Authority Map
- Concern: Order pricing computation (per-line total, subtotal, tax, grand total)
  - Owner: OrderCalculator (value type)
  - Allowed writers: OrderCalculator.subtotal(), OrderCalculator.totalWithTax(), OrderCalculator.receiptLines()
  - Observers / readers: checkout screen (caller of the three methods)
  - Persistence seam: None
  - Async mutation entry points: []
  - Verdict: Split and ambiguous

## Strengths That Matter
- Money handled with Foundation.Decimal, not Double — avoids binary-float rounding error on currency (Sources/OrderCalculator.swift:13,18,23)

## Findings

### Finding #1: Collapse the triplicated subtotal/tax computation into single owners

**Why it matters** — A single pricing-rule change (rounding, a discount, a second tax) must be edited in three methods, and the copies can silently drift into returning inconsistent totals to the checkout screen.

**What is wrong** — The subtotal-accumulation loop is copy-pasted verbatim in `subtotal()`, `totalWithTax()`, and `receiptLines()`, and the tax step `sum * taxRate` is duplicated in `totalWithTax()` and `receiptLines()`. No single owner of the pricing arithmetic exists.

**Evidence** — `Sources/OrderCalculator.swift:20-26` (subtotal loop), `:30-35` (duplicated loop + tax), `:41-47` (third loop).

**Severity** — Serious deduction.

**Minimal correction path** — Reuse `subtotal()` inside `totalWithTax()` and `receiptLines()`; add one private `tax(on:)` helper for the `* taxRate` step; add a `lineTotal` computed property on `LineItem`. No new types/protocols/files; behavior-preserving.

**Blast radius** — Change: `Sources/OrderCalculator.swift`. Avoid: `Sources/ReceiptFormatter.swift`.

## Simplification Check
- Structurally necessary: Collapsing the triplicated subtotal/tax computation into single owners removes duplicated authority over the pricing rule — one change site instead of three. Simplification (deletion of duplication), not deepening; no Module is removed.
- New seam justified: False
- Helpful simplification: Replace the hand-rolled accumulation loops with reduce; give LineItem a lineTotal property.
- Should NOT be done: Do not introduce a PricingStrategy protocol, a Calculator interface, or separate Subtotal/Tax modules — a costume layer for pure synchronous arithmetic.
- Tests after fix: The consolidation is behavior-preserving and verified by swiftc -typecheck Sources/OrderCalculator.swift.

## Improvement Backlog
1. **Collapse the triplicated subtotal/tax computation into single owners** — structural / needed for winning. Why it matters: removes duplicated authority over the core pricing rule, eliminating drift between the three totals. Score impact: Code simplicity, Architecture quality, and Domain modeling each +1.5 to +2.0.
## Builder Notes
None this loop — no structural lessons beyond the findings themselves.

## Final Judge Narrative
The structure is sound where it exists, but the entry's one job — computing an order total — is authored three times. The honest repair is deleting duplication and giving the per-line total a home, not erecting a PricingStrategy Seam over pure arithmetic.
