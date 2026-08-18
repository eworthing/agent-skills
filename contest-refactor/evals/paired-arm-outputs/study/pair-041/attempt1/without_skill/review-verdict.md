# Review — Loop 7, `data_flow`

## What the diff actually does

`OrderService.placeOrder` used to perform two sequential writes (insert order, then
decrement inventory) with a window where the order could exist and the decrement could
still fail. The diff wraps both writes in a single `db.transaction { tx in ... }` closure
so they commit or roll back together. Mechanically this is a real, well-scoped fix for the
specific failure mode described ("order exists, inventory not decremented") and the ownership
story (`OrderService` as sole writer of both entities) doesn't change — it was already true.
Tests are green (2,488/2,488), which validates that the transaction API is used correctly and
that no existing behavior broke. So far, that matches the Actor's report.

## Where the Actor's report and the actual codebase context diverge

The attached `CONTEXT.md` excerpt contains two facts the Actor's report never engages with,
and both are directly relevant to whether this change should land as an architectural
improvement to `data_flow`:

**§4 (committed roadmap, next quarter):** Inventory is moving out of the core database into a
dedicated `InventoryService` with its own datastore, specifically to absorb a ~50× write-volume
spike. Orders stay in the core database.

**§6 (actual consistency requirement):** The hard invariant is "never oversell." Inventory
counts are explicitly permitted to lag by a few seconds under load. Strong atomicity between
the order insert and the inventory decrement was never the stated requirement — no-oversell was.

Given those two facts, this diff is the wrong direction, not a neutral hardening:

1. **It hard-codes a same-database assumption that the roadmap already schedules for removal.**
   `db.transaction { tx in ... }` only works because `Order` and inventory rows currently share
   one `Database`. The moment `InventoryService` gets its own datastore (next quarter, per §4,
   not speculative), this transaction is structurally impossible — there is no such thing as a
   local ACID transaction spanning two separate datastores without introducing a distributed
   transaction/saga, which is a materially different (and harder) problem. This loop just spent
   effort tightening a coupling that a committed plan is about to break apart. That's next
   quarter's rework created this quarter, and the diff shows no seam (interface, event emission,
   outbox) that would make the eventual split cheaper — it does the opposite of what "hardening
   before a known migration" should look like.

2. **It solves a stronger problem than the spec asks for, in the direction the roadmap can't
   afford.** §6 already tells us a few seconds of inventory lag is acceptable as long as oversell
   is prevented. That's an explicit license to use an eventual-consistency mechanism (e.g., a
   reservation/compensation write, an idempotent retry, an outbox event) that would remain valid
   after the `InventoryService` split. Instead the Actor reached for the heaviest tool — a
   synchronous cross-entity ACID transaction — which is *harder* to satisfy post-split, not
   easier, and buys consistency guarantees nobody asked for.

3. **It works against the stated reason for the migration.** §4 says the split is happening to
   absorb a ~50× write-volume spike from flash sales. Wrapping the inventory decrement inside the
   same transaction as the order insert increases lock/contention scope on the inventory rows
   exactly where the roadmap says load is about to spike 50×. Even before the split lands, this
   change makes the current system's hot path more contended, not less — the opposite of what
   you'd want ahead of a known load event.

4. **Minor, non-blocking note:** the diff drops `await` on `tx.insert`/`tx.decrementInventory`
   inside the closure (the original call sites used `try await`). That's plausibly correct if
   `Database.transaction`'s closure is intentionally synchronous (a common constraint for local
   ACID transactions, since suspending mid-transaction is its own hazard), and the green suite
   confirms it compiles and passes. Not a blocker, but the Actor's report doesn't mention this
   API-shape change, and I'd want it stated as deliberate rather than incidental.

## Why this blocks `data_flow` → 9.5

A `data_flow` score at 9.5 should mean the data-ownership and consistency model is *durably*
right, not just locally tidy and green today. This diff produces the opposite of durability: it
increases coupling between two entities that a committed, dated roadmap item is about to
physically separate, it does so in service of a consistency guarantee the spec explicitly says
isn't required, and it does so in the one dimension (write volume/contention) the roadmap is
trying to protect. The Actor's report treats "single ACID transaction, tests green" as
self-evidently better, but never checks the diff against `CONTEXT.md`'s roadmap section — which
is exactly the kind of check a `data_flow` reviewer must perform, because "eliminated a
partial-write window" is true and irrelevant if the fix has to be torn out next quarter.

This isn't a nitpick about style; it's a real architectural liability introduced by the loop
itself, discoverable from the same materials the Actor had. That's disqualifying at the 9.5 bar.

## What I'd need to see before reconsidering

- A design that satisfies §6 ("never oversell," lag tolerated) without assuming `Order` and
  inventory share a datastore — e.g., an idempotent inventory reservation/decrement with retry,
  or an outbox/domain-event pattern emitted from the same local transaction as the order insert,
  so the eventual `InventoryService` split only requires swapping the consumer, not touching
  `OrderService` again.
- Evidence the chosen approach doesn't increase lock contention on inventory rows relative to
  the pre-diff sequential-write version, given the anticipated 50× write spike.
- Confirmation of how oversell is actually prevented today (row locking? a stock check inside
  `decrementInventory`?) — the diff never shows this, and it's the actual hard invariant, not
  the atomicity this loop optimized for.
- An explicit note in the loop's report reconciling the change against `CONTEXT.md` §4, since a
  9.5 claim should show the roadmap was consulted, not just that the suite is green.

```json
{"verdict": "rejected", "blocks_95": true, "blocking_severity": "critical", "dimension_scores": {"data_flow": 4}, "flagged_smells": ["premature coupling against a committed roadmap split", "same-database transaction assumption baked into code the roadmap is about to invalidate", "over-strong consistency guarantee where spec explicitly tolerates lag", "contention increase on the write path the roadmap is trying to protect from a 50x spike"], "evidence_demanded": ["design that satisfies the no-oversell requirement without assuming Order and inventory share a datastore (e.g. idempotent reservation/outbox pattern)", "contention/locking analysis under the anticipated 50x write-volume spike versus the pre-diff sequential writes", "explanation of how oversell prevention actually works today (row locking / stock check) since that is the real invariant, not write atomicity", "explicit reconciliation of this change against CONTEXT.md §4 in the loop report, not just a green test run"]}
```
