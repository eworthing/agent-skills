# Critic Review — Loop 7, `data_flow`

## What the diff actually does

`OrderService.placeOrder` used to perform two sequential writes (`db.insert(Order)` then
`db.decrementInventory`) with a crash/partial-failure window between them. The loop wraps both
in one `db.transaction { tx in ... }` call. As a **local** fix, for **today's** topology (Order
and Inventory rows live in the same `Database`), this closes a real bug: a crash between the two
statements used to leave an `Order` row with no matching inventory decrement. That part of the
claim is accurate and I'm not contesting it.

The Actor's report goes further, though: it frames this as "hardened," proposes `data_flow` →
9.5, and characterizes the result as "one owner, no multi-writer ambiguity, no partial-write
window." That framing is where this loop overreaches, for two reasons — one well-evidenced from
the attached `CONTEXT.md` excerpt, one an unresolved evidence gap.

## Finding 1 — the fix optimizes for the wrong invariant and contradicts the committed roadmap

`CONTEXT.md §4` states, as a **committed** (not speculative) roadmap item: Inventory is moving
out of the core database into its own `InventoryService` with its own datastore next quarter,
specifically to absorb a ~50× write-volume spike. Orders stay in the core database. Per the
rubric's Dependency Categorization table, that is a change of dependency category for the
Inventory write from `in-process` (no seam needed, freely mergeable) to `remote-owned` (needs a
port at the seam — HTTP/gRPC/queue adapter for prod, in-memory adapter for test). A single local
ACID `Database.transaction` cannot span a local table and a remote service's datastore; once the
migration lands, `tx.decrementInventory(for:)` inside this same closure is not constructible in
the form this loop just wrote. This loop's "fix" is therefore not a step toward the roadmap, it's
a step that must be entirely unwound the moment `InventoryService` ships — and unwound under
harder conditions, since whoever does that migration now also has to re-derive the
oversell-prevention story that this loop just papered over with transactional atomicity.

That leads to the second half of the problem: `CONTEXT.md §6` gives the actual consistency
contract for this flow — *"Order placement must never oversell. Inventory counts may lag by a
few seconds under load, provided oversell is still prevented."* That is explicitly an
eventual-consistency contract with a targeted invariant (no oversell), not a same-transaction
atomicity requirement. The Actor's fix reaches for the strongest possible consistency tool (a
shared local ACID transaction) for a problem statement that was already scoped to tolerate lag.
Strong same-transaction consistency between Order and Inventory is not what §6 asks for, and it
is specifically the thing §4's migration is about to make impossible. The right target for
`data_flow` here is a decrement/reservation mechanism that stays correct when Inventory is a
separate, laggy, remote-owned store — e.g., an atomic conditional decrement or a
reserve-then-confirm flow that can tolerate the future seam. Wrapping both writes in one
transaction sidesteps that design question rather than answering it, and the report shows no
awareness of the tension — it doesn't mention `InventoryService`, the migration, or lag tolerance
at all.

This is a `data_flow` finding on `OrderService.placeOrder`, which the scenario itself describes
as "the single, unambiguous owner of order placement" — i.e. a primary, revenue-bearing flow, not
an off-path helper. Per the Severity Anchors: nothing is broken at runtime today (the transaction
is locally correct against the current, same-database topology), so I don't read this as a
*Likely disqualifier*. But it is a real, source-backed data-flow/coupling hazard in a meaningful,
primary-flow module that is contained to `placeOrder` today and will surface as forced rework
next quarter — that is squarely **Serious deduction**, and it blocks certifying `data_flow` at
9.5 this loop. Per the rubric's CONTEXT.md-awareness clause ("findings contradicting an existing
ADR must say so explicitly"), I'm treating the §4 roadmap the same way: this loop's chosen
remedy conflicts with a committed architectural direction, and that conflict was not surfaced or
reasoned about.

## Finding 2 (evidence gap, not asserted as a defect) — oversell protection under concurrency is unproven

The diff doesn't show `decrementInventory`'s body, and the scenario gives no isolation-level
detail for `db.transaction`. Wrapping the order insert and the decrement in one transaction only
protects against the crash/partial-write window; it does **not** by itself prevent two concurrent
`placeOrder` calls from both proceeding on stale availability unless `decrementInventory` performs
an atomic conditional update (e.g., a single `UPDATE ... WHERE quantity >= n`) or the transaction
runs at an isolation level that serializes the two decrements. That is exactly the risk the
rubric's *reservation after suspension* smell describes (check-then-claim across a suspension
point) — with the carve-out that it's fine if "the actual authority rechecks and atomically
claims in one transactional... step." I can't confirm from the given material whether that carve
-out is satisfied, so I am not asserting this as a confirmed finding — only as a required piece of
evidence before `data_flow` can be scored, since it bears directly on §6's actual requirement
("must never oversell").

## Simplify Pressure Test (Q5)

Q1–Q4 pass locally (it does fix a real crash-window ambiguity, it's a small diff, no duplicate
layer, and the transaction's runtime behavior is honest as far as it goes). Q5 fails: the
concrete gain — closing a rare crash-window partial write — is smaller than what's being
foreclosed on: a design that would still work once Inventory becomes `remote-owned`, and explicit
handling of the oversell-under-lag contract §6 actually asks for. "Tidier ownership on paper" is
not, by itself, the product improvement Q5 requires when it's purchased by taking on architecture
debt against a committed migration.

## Verdict

Conditional. The crash-window fix itself is a legitimate, small, defensible change and I'm not
asking for it to be reverted outright — but the loop's claim of `data_flow` → 9.5 is not
supportable given (a) the unacknowledged conflict with the committed `InventoryService` migration
in `CONTEXT.md §4`, and (b) unresolved evidence on whether the actual §6 contract (no oversell,
lag tolerated) is honored under concurrent order placement. Both must be addressed — either by
redesigning toward a decrement mechanism that survives the Inventory migration (and dropping the
same-transaction framing as the "fix"), or by explicitly recording this as a deliberate, time-
boxed stopgap with a named unwind plan — before `data_flow` can be certified at 9.5.

```json
{
  "verdict": "conditional",
  "blocks_95": true,
  "blocking_severity": "Serious deduction",
  "dimension_scores": {
    "data_flow": 7.5
  },
  "flagged_smells": [],
  "evidence_demanded": [
    "decrementInventory implementation (file:line): does it perform a single atomic conditional update (e.g. `UPDATE inventory SET qty = qty - n WHERE qty >= n`) that prevents oversell under concurrent transactions, or does it read-then-write across a separate step?",
    "Isolation level configured for db.transaction, and whether it alone would serialize two concurrent placeOrder calls against the same inventory row absent an atomic conditional decrement",
    "An explicit design note or migration plan reconciling this same-transaction coupling with the committed CONTEXT.md §4 move of Inventory to its own InventoryService/datastore next quarter — specifically how oversell-prevention will be re-implemented once decrementInventory can no longer share a local ACID transaction with the order insert",
    "Confirmation of whether this loop intends the transaction wrap as a permanent data_flow answer or a named, time-boxed stopgap pending the InventoryService migration"
  ]
}
```
