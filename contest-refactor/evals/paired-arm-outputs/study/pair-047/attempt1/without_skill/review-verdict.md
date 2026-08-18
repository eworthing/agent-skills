# Review: Loop 7 — data_flow dimension (OrderService transactional hardening)

## What the diff does

Wraps the previously sequential `db.insert(Order(...))` + `db.decrementInventory(...)` calls in a
single `Database.transaction` closure, so both writes commit or roll back together. In isolation
this is a clean, minimal change: it removes the partial-write window where an order could exist
with un-decremented inventory, and the closure-based transaction API is idiomatic. The diff is
small and focused, and the reported test run (2,488/2,488 green) is consistent with a mechanically
correct change against the *current* schema, where `Order` and inventory rows share one
`Database`.

## Why I don't accept the Actor's framing

The Actor's report describes this purely as a local hardening ("eliminated a latent partial-write
window") and asks for `data_flow` → 9.5. The CONTEXT.md excerpt supplied with this review directly
undercuts that framing on two counts:

1. **§4 (committed roadmap, next quarter).** Inventory is scheduled to move out of the core
   database entirely into a dedicated `InventoryService` with its own datastore, specifically to
   absorb a ~50x write-volume spike from the flash-sale feature. Once that migration lands,
   `tx.decrementInventory` and `tx.insert(Order(...))` can no longer participate in one local ACID
   transaction — they will be different services, most likely reached over a network boundary, not
   two tables in one `Database`. This diff bets the design on precisely the coupling assumption
   ("Order and inventory share one Database") that the org has already committed to breaking next
   quarter. That is not a neutral simplification that will merely need touching later — it moves
   the code in the opposite direction from the stated architecture, and it will have to be ripped
   out (or replaced by a saga / outbox / compensating-transaction pattern) at exactly the moment
   the InventoryService ships. Nothing in the Actor's report indicates this tradeoff was
   considered.

2. **§6 (the actual consistency requirement).** The real invariant is "never oversell," and the
   spec explicitly states inventory counts *may lag by a few seconds under load*, provided oversell
   is still prevented. That is an eventual-consistency-friendly requirement. The Actor solved a
   strictly stronger problem than was asked for — full ACID atomicity between two writes — which
   §6 does not call for, and which is exactly the guarantee that stops being available once
   inventory is externalized. A same-database transaction is the version of "prevent oversell"
   that only works before the roadmap item ships; the version that survives the migration
   (reservation/decrement-then-verify, idempotent calls into the future InventoryService, an
   outbox event, optimistic recheck, etc.) is not what got built.

## On the test suite

2,488 green tests is good evidence the change didn't regress anything the current suite can
observe. It is not evidence for the `data_flow` claim under review, because the suite necessarily
exercises today's single-database topology — it has no way to exercise or guard the cross-service
consistency behavior this code will need in one quarter. Green tests answer "did I break today's
code," not "did I move data_flow toward its committed target architecture," which is the actual
claim being scored.

## Net assessment

This is a local-optimum-vs-system-context miss: a change that is correct and reasonably written in
isolation, but that *increases* coupling between two subsystems at exactly the moment the roadmap
calls for decoupling them, and over-delivers on consistency in a way that will need to be unwound
rather than extended. Accepting it as a 9.5 `data_flow` result would bake a false architectural
invariant ("order + inventory writes are atomic") into the codebase that next quarter's migration
will have to actively fight. A defensible fix here either (a) solves oversell prevention in a way
compatible with inventory living in a separate datastore, or (b) explicitly scopes this transaction
as a deliberate, time-boxed stopgap with a tracked follow-up tied to the InventoryService ticket —
neither of which the Actor's report or diff does.

## Verdict

Rejected at the 9.5 threshold for `data_flow`. The chosen mechanism directly conflicts with a
committed architectural roadmap item supplied in this review's own context, and over-solves the
documented consistency requirement in a way that creates rework rather than durable progress.

```json
{"verdict": "rejected", "blocks_95": true, "blocking_severity": null, "dimension_scores": {"data_flow": 5}, "flagged_smells": ["roadmap-conflicting coupling (hard-couples Order+inventory writes right before a committed service split)", "over-engineered consistency (delivers ACID atomicity when spec only requires bounded-lag oversell prevention)", "hidden single-datastore assumption baked into implementation", "local optimization at the expense of systemic/roadmap direction", "test-suite blind spot: current suite cannot exercise the post-migration topology"], "evidence_demanded": ["Explicit acknowledgment that this transaction is an interim stopgap, tied to a tracked follow-up for the InventoryService migration in §4, not a permanent design", "A concrete plan for how oversell prevention will work once inventory lives in a separate datastore (reservation counters, idempotent decrement calls, outbox/saga pattern, optimistic recheck) that does not depend on a shared local transaction", "Confirmation the Actor read CONTEXT.md §4/§6 before choosing full ACID atomicity over the documented lag-tolerant requirement, or a rationale for overriding that requirement", "A test or contract pinned to the actual invariant (no oversell under concurrent load) independent of the transaction mechanism, so the fix is verified against the real requirement rather than against 'writes are atomic'", "An estimate of the rework cost this coupling adds to the committed §4 migration, so the 'hardening' isn't quietly growing next quarter's migration bill"]}
```
