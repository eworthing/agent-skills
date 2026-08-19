# Critic Review — Loop 7, `data_flow`

## Step 0/1 — independent read (not anchored to the Actor's report)

`OrderService.placeOrder` previously performed two sequential, independently-committed writes:
`db.insert(Order(...))` then `db.insert(OrderAuditEntry(...))`. That is a genuine partial-write
hazard — if the process dies, throws, or the second write fails after the first commits, an order
exists with no audit entry. CONTEXT.md §6 states this is not a stylistic preference but a
regulatory consistency requirement: *"A placed order must always have a matching audit entry
(regulatory: order history must be reconstructable). Audit entries must be strongly consistent
with their orders."* §4 confirms `Order` and `OrderAuditEntry` both stay in the core database with
no planned extraction (only `Inventory` is being pulled out), so a single local transaction is the
right-shaped fix — this is not a case where the correct consistency model is undocumented (the
rubric's context-sufficiency cap for an undocumented "eventual vs. transactional" choice does not
apply here; CONTEXT.md already answers the question).

The new code:

```swift
try await db.transaction { tx in
    let order = try tx.insert(Order(cart: cart, buyer: buyer))
    try tx.insert(OrderAuditEntry(orderID: order.id, action: .placed))
    return order
}
```

wraps both inserts in one `Database.transaction` closure. Structurally this is the smallest honest
fix for the stated problem: no new Seam, no new protocol, no repository layer, no renamed
manager/service pair. Running the Simplify Pressure Test — (1) fixes a real ambiguity (partial
write), (2) smallest honest form (no ceremony added, uses an existing `Database.transaction`
primitive rather than inventing one), (3) no duplicate layers, (4) runtime behavior is *more*
honest than before, not less, (5) the product measurably improves on the exact dimension named in
CONTEXT §6 — passes on all five questions. `OrderService` remains the sole writer of both `Order`
and `OrderAuditEntry`; no multi-writer ambiguity is introduced. No architecture-costume, repository-theater,
protocol-soup, or fake-simplification smell applies to this diff.

## Where the claim outruns the evidence

The Actor's report makes a specific factual claim: *"Eliminated a latent partial-write window... a
placed order always has a matching audit record."* That is precisely the regulatory-consistency
property CONTEXT §6 requires, and it is precisely the property this diff is supposed to establish.
The only evidence offered for it is: *"Full suite green (2,488 tests)."*

- **Claim:** the transaction closure makes order-insert + audit-insert atomic (all-or-nothing).
- **Source:** `Sources/Domain/OrderService.swift`, `OrderService.placeOrder` — the diff shown is
  the *call site* of `db.transaction { tx in ... }`. The implementation of `Database.transaction`
  (isolation level, actual rollback-on-throw semantics) is not in the attached diff or scenario at
  all — it is asserted by the Actor's report and the "Context" prose, not shown as source.
- **Consequence:** an aggregate pass count of 2,488 tests proves the happy path still works (order
  row exists, audit row exists). It does not prove the new property — that a failure *during* the
  audit insert (constraint violation, disk error, thrown validation) leaves *no* order row behind.
  Per the mutation-test check (Method Step 8): swap `tx.insert(OrderAuditEntry(...))` for
  `db.insert(OrderAuditEntry(...))` (i.e., silently drop it back outside the transaction) — would
  the existing suite catch that regression? On the evidence given, no: a suite that only exercises
  the success path would still see both rows written and stay green. That is a nameable,
  source-backed mutation on a primary user flow (order placement is the textbook example of a
  "persistence writer" in the rubric's own Severity Anchors), and current tests, as reported,
  would not catch it. Per the Method's mutation-test mental model this is a "Noticeable-or-worse"
  finding, not a non-finding — an aggregate test count standing in for proof of a specific new
  consistency guarantee is the same shape as the rubric's flagged "aggregate-test-count-as-a-test-strategy"
  fake-clean pattern, applied here to the `data_flow` claim rather than to `test_strategy` scoring.
- **Remedy:** cite (or add) a focused test that forces the audit-entry insert to fail inside the
  transaction and asserts the order row does not persist — i.e., proof of rollback, not just proof
  of the happy path. This is mechanically testable (fault-injection or a constraint violation on
  `OrderAuditEntry`), so Meta-Rule 4's preference for executable evidence over reasoning-only
  applies once such a test exists it should be cited by name in `loop_result`.

## Severity and scope

This is contained to one specific, well-defined evidence gap on an otherwise minimal, correctly-targeted
diff — not a broken runtime property, not a pattern repeated across the codebase, and not a
misjudged architecture decision (the transaction-wrapping approach itself is exactly right per
CONTEXT §4/§6). That places it at **Serious deduction**: a real data-flow verification hazard in a
meaningful module (order placement, the primary revenue flow), local to this one untested failure
branch. A reasonable judge could still rank the entry highly with this present, but it is not
disqualifying, and it is also not nothing — the entire point of this loop was to close a
regulatory-flagged consistency gap, and the specific guarantee claimed is not the one thing the
loop's own evidence actually demonstrates.

## Verdict

Approve the direction — the transactional wrap is the correct, minimal, CONTEXT-aligned fix and
should stay. Do not certify `data_flow` at the 9.5 the Actor proposes until the rollback/atomicity
behavior is backed by a named, executable test rather than an aggregate suite count.

```json
{
  "verdict": "conditional",
  "blocks_95": true,
  "blocking_severity": "Serious deduction",
  "dimension_scores": {"data_flow": 8.5},
  "flagged_smells": ["fake-clean reward (aggregate-test-count-as-test-strategy sub-pattern, applied to the data_flow atomicity claim)"],
  "evidence_demanded": [
    "A named test that forces the OrderAuditEntry insert to fail inside the transaction and asserts the Order row does not persist (proof of rollback, not just the happy path)",
    "Citation of Database.transaction's actual isolation/rollback semantics (not shown in the attached diff) supporting the 'eliminated a latent partial-write window' claim"
  ]
}
```
