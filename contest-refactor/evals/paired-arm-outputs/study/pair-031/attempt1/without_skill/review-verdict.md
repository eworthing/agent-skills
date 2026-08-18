# Review — Loop 7, `data_flow` dimension

## What the Actor claims

Wrapping the order insert and inventory decrement in one `Database.transaction` removes a
partial-write window: an order can no longer exist without its inventory having been
decremented (and vice versa). Framed as "hardened," full suite green (2,488 tests), proposing
`data_flow` → 9.5.

## What the diff actually does

Two previously-sequential writes (`db.insert(Order)`, `db.decrementInventory`) are moved inside
a single `db.transaction { tx in ... }` closure, using `tx.insert` / `tx.decrementInventory`
instead of the top-level `db` methods. That's the entire change. No availability/oversell check
is added or shown; `decrementInventory`'s internal behavior is unchanged and out of view.

## Why this doesn't clear the bar, checked against the supplied CONTEXT.md

The attached CONTEXT.md excerpt makes this a straightforward reject, not a judgment call:

1. **§4 — committed roadmap.** Inventory is moving out of the core database into a dedicated
   `InventoryService` with its own datastore next quarter, specifically to absorb a ~50x
   write-volume spike. Orders stay in the core database. That means Order and Inventory are
   about to become two different systems of record. This loop does the opposite of preparing
   for that: it takes two writes that were already only loosely sequenced and welds them into a
   single local ACID transaction. A local `Database.transaction` cannot span two datastores —
   the moment `InventoryService` lands, this code cannot function as written and has to be torn
   out and replaced with some cross-service pattern (saga, reservation + confirm, outbox, etc.).
   The Actor's own diff comment even flags the fragile assumption ("Both `Order` and the
   inventory rows currently live in the same `Database`") without noting that assumption has an
   already-committed expiration date. This is a refactor that actively works against a known,
   documented architectural direction rather than being neutral to it — that's a real
   regression in the `data_flow` dimension, not an improvement, regardless of what the local
   diff looks like in isolation.

2. **§6 — actual consistency requirement.** The stated requirement is "never oversell," and it
   explicitly permits inventory to *lag by a few seconds* under load. That's a deliberate,
   already-relaxed consistency bar — eventual consistency is fine as long as oversell is
   prevented. The Actor's fix imposes something stricter than required (synchronous ACID
   coupling of the two writes) while not visibly addressing the thing that's actually required
   (an availability/oversell guard). Nothing in the diff shows `decrementInventory` refusing to
   go negative or checking stock before decrementing — the transaction only guarantees the two
   writes commit or roll back together, which is a different property than "never oversell."
   "2,488 tests green" tells us the existing suite didn't regress; it says nothing about
   whether a concurrency/oversell scenario (two buyers racing for the last unit) is now
   correctly handled, and no such test is mentioned as having been added.

3. **Net effect.** The loop over-solves a problem the requirements doc says is tolerable (a few
   seconds of inventory lag) and, in doing so, adds exactly the kind of tight synchronous
   coupling that will be the first thing to break under the 50x write spike the roadmap is
   preparing for — and the first thing that has to be unwound when `InventoryService` ships.
   That's a `data_flow` architecture score going the wrong direction while presenting itself as
   a hardening improvement.

This is precisely the class of defect a green test suite and a clean-looking diff cannot surface
— it only shows up by checking the change against the project's own stated near-term
architecture and consistency requirements, which the Actor's report does not reference at all.

## Verdict

Not acceptable at the 9.5 bar for `data_flow`. The change should not be scored as a hardening
improvement; if anything it needs to be reworked (or explicitly scoped/flagged as a deliberate,
temporary bridge with a documented unwind plan) before it can be credited.

```json
{"verdict": "rejected", "blocks_95": true, "blocking_severity": "critical — change contradicts a committed architectural roadmap decision (CONTEXT.md §4) and does not demonstrate the actual named invariant (CONTEXT.md §6 oversell prevention); passing tests do not cover either concern", "dimension_scores": {"data_flow": 4}, "flagged_smells": ["roadmap-contradicting coupling (ties Order+Inventory into one local ACID transaction while committed §4 plan splits them into separate services/datastores next quarter)", "over-tightened consistency (imposes synchronous ACID consistency where §6 explicitly permits a few seconds of lag)", "narrow/local fix mismatched to the stated requirement (solves partial-write atomicity, not the named 'never oversell' invariant)", "unverified invariant (no oversell/availability check shown or tested; green suite doesn't exercise the concurrent-oversell case)", "unscoped temporary architecture (no migration/unwind plan for when InventoryService lands)"], "evidence_demanded": ["A concurrency test demonstrating two simultaneous orders competing for the last unit of inventory cannot oversell", "Confirmation the Actor read CONTEXT.md §4 and either has a documented plan for decomposing this transaction when InventoryService is extracted, or an explicit rationale for why the roadmap doesn't apply here", "Evidence (code or design note) that decrementInventory enforces a non-negative/availability constraint independent of the transaction wrapper", "A decoupling boundary (e.g., an InventoryPort/protocol OrderService calls) so the future cross-service split doesn't require rewriting placeOrder's control flow"]}
```
