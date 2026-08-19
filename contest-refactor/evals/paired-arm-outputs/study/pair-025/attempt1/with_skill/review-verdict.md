# Critic Review — Loop 7, `data_flow`

## What the change does

`OrderService.placeOrder` previously issued two sequential, independent writes —
`db.insert(Order(...))` then `db.insert(OrderAuditEntry(...))` — with a window in which
the order could exist without its audit entry (crash, throw, or process death between the
two calls). The diff replaces this with a single `db.transaction { tx in ... }` block, and
critically both inserts are routed through the transaction-scoped `tx` (not the outer `db`),
so both participate in the same atomic unit rather than one accidentally escaping it. That is
the correct way to use this pattern — a common bug here is closing over `db` instead of `tx`
for one of the two writes, which would silently defeat the whole fix. That bug is not present.

## What I cleared

- **Ownership.** `OrderService` remains the single, unambiguous writer of both `Order` and
  `OrderAuditEntry` for this flow. No multi-writer ambiguity introduced or left behind.
- **CONTEXT.md alignment (§4, §6).** §6 requires a placed order to always have a matching
  audit entry, strongly consistent. A single local ACID transaction is the direct, correctly
  scoped implementation of that requirement. §4 confirms `OrderAuditEntry` has no planned
  extraction out of the core database (only Inventory moves out, and Orders/audit stay put) —
  so a *local* transaction is not a fragile shortcut that a near-future roadmap item will break;
  it is the durable answer for this pair of entities. The Actor's report explicitly notes both
  entities "live in the same `Database` and stay there," showing the loop actually consulted the
  roadmap rather than getting lucky.
- **No seam/costume creep.** Nothing new was introduced — no protocol, no repository, no
  wrapper type. This is an inline fix inside the existing owner, which is the smallest honest
  fix available (Simplify Pressure Test Q1–Q4 pass: fixes real ambiguity, smallest form, no
  duplicate layer, runtime behavior is honestly changed — order placement now fails atomically
  with the audit write instead of silently orphaning an order, which is the intended tightening,
  not a smuggled behavior change).
- **No concurrency smell in scope.** This is a straight-line write, not a check-then-claim
  across a suspension point, so *reservation after suspension* does not apply. No inventory
  reservation or availability check appears in this diff to evaluate.

## What blocks certifying `data_flow` at 9.5

The entire value of this loop is a claim about *failure-path* behavior: "a placed order always
has a matching audit record," "eliminated a latent partial-write window." That is exactly the
kind of property ordinary happy-path tests do not exercise by accident — you need either (a) a
test that injects a failure into the audit insert and asserts the order insert did not survive
(proves rollback), or a test that asserts an audit entry always exists after `placeOrder`
returns, or (b) a citable guarantee that `db.transaction` provides real multi-statement
rollback. Neither is in evidence here.

The diff touches only `Sources/Domain/OrderService.swift` — no test file is added or modified.
The Actor's sole evidence is "Full suite green (2,488 tests)," an aggregate pass count. Per the
rubric this is the named smell **fake-clean reward**, sub-pattern *aggregate-test-count-as-
test-strategy*: a loop sees N passing tests and treats that as proof of a specific behavioral
claim without citing a test that actually exercises it. Naming the mutation directly: delete
the line `try tx.insert(OrderAuditEntry(orderID: order.id, action: .placed))`, or unwrap the
`db.transaction` back to two sequential `db.insert` calls — would any currently-passing test
fail? Nothing in the materials shows that it would. `OrderService.placeOrder` is a persistence
writer on the primary order-placement flow with an explicit regulatory stake (CONTEXT.md §6:
"order history must be reconstructable") — squarely the class of central mutable runtime
behavior the severity anchors call out for test-absence scrutiny.

I am not treating this as a "likely disqualifier" — nothing here is demonstrably broken at
runtime; the transaction usage is correct as written, and the hazard is a regression/evidence
gap rather than a live defect. That makes it a **Serious deduction**: a real, contained
data-flow verification hazard in a meaningful module (the regulatory consistency guarantee this
loop exists to deliver rests entirely on an unverified assumption about `db.transaction`'s
semantics, with no regression test locking in the fixed behavior for future refactors).

## Verdict

Conditional. The structural fix is correct, minimal, and CONTEXT-aware — I would not ask for a
different implementation. But the loop cannot be certified at `data_flow` → 9.5 on "tests are
green" alone when the claim is specifically about atomicity/rollback behavior that no cited test
exercises. Close the evidence gap (or point to where it already exists) and this clears.

```json
{
  "verdict": "conditional",
  "blocks_95": true,
  "blocking_severity": "Serious deduction",
  "dimension_scores": {"data_flow": 8.5},
  "flagged_smells": ["fake-clean reward (aggregate-test-count-as-test-strategy)"],
  "evidence_demanded": [
    "A test proving the mutation 'delete the OrderAuditEntry insert' or 'unwrap the transaction back to two sequential db.insert calls' would fail — i.e. direct coverage of the atomicity claim, not aggregate pass count.",
    "A fault-injection or rollback test showing that when the audit insert throws inside db.transaction, the Order insert does not persist (proves the partial-write window is actually closed).",
    "A citation (doc, test, or existing usage) establishing that Database.transaction provides real multi-statement atomic rollback, since that guarantee is the load-bearing assumption behind the whole fix and its implementation is not part of this diff."
  ]
}
```
