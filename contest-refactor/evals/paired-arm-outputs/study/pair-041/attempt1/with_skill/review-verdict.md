# Review — Loop 7, `data_flow`

## What the diff actually does

`OrderService.placeOrder` used to perform two sequential writes (`db.insert(Order)` then
`db.decrementInventory`) with a partial-failure window between them. The diff wraps both in
`db.transaction { tx in ... }`, so the pair now commits or rolls back atomically inside the local
`Database`. Taken in isolation, that is a real, correct fix for the partial-write bug the Actor
describes, and nothing in the diff looks dishonest about what it does: one owner (`OrderService`),
one transaction, no new abstraction, no hidden control flow. The 2,488-test green run is
consistent with "did not break anything currently exercised."

The problem is that "in isolation" is not the frame this review is required to use — `CONTEXT.md`
was handed to this review specifically, and it changes the picture.

## Claim

The fix increases transactional coupling between `Order` and inventory precisely where the
project has a **committed, next-quarter roadmap item** to decouple them, and it does not address
the actual named consistency invariant for this dimension.

## Source

- Diff: `Sources/Domain/OrderService.swift` — `try await db.transaction { tx in ... tx.insert(Order...); tx.decrementInventory(...) }`. Both writes are now required to share one local ACID transaction against `Database`.
- `CONTEXT.md` §4: *"Inventory moves out of the core database into a dedicated `InventoryService` with its own datastore... Orders remain in the core database."* This is committed, not speculative — it is scheduled for next quarter, one loop-horizon away.
- `CONTEXT.md` §6: *"Order placement must never oversell. Inventory counts may lag by a few seconds under load, provided oversell is still prevented."* This is the actual consistency requirement for this dimension: no oversell, with explicit tolerance for inventory lag. It does not say "order insert and inventory decrement must be transactionally atomic."
- Actor report: no mention of §4 or §6, no scoping of the transaction as a stopgap, no removal condition tied to the InventoryService migration, no test evidence targeting oversell specifically (the report cites aggregate suite size, not a concurrency/oversell test).

## Consequence

Two independent problems, both landing on `data_flow`:

1. **Architecture direction conflict, undisclosed.** Once `InventoryService` gets its own
   datastore, `db.transaction { tx in ... }` spanning `Order` and inventory becomes structurally
   impossible — they will not share a transaction manager. Everything this loop just built will
   have to be unwound and replaced with a cross-service pattern (saga, outbox, reservation/compensating
   transaction) inside the same quarter. That is not itself disqualifying — code can legitimately be
   a scoped stopgap — but the rubric's CONTEXT.md-awareness requirement is that a finding or fix
   touching a committed decision "must say so explicitly." This diff does the opposite: it deepens
   reliance on same-database atomicity without acknowledging that the database is about to stop
   being "the same" for these two entities, and without a removal condition. That silence is the
   finding, not the transaction itself.
2. **Wrong invariant targeted.** §6's actual requirement is "never oversell," with inventory lag
   explicitly tolerated. A synchronous ACID transaction over the insert+decrement pair guarantees
   *the pair* commits together, but by itself says nothing about oversell unless
   `decrementInventory` performs an atomic conditional decrement (e.g. `WHERE qty >= n`) rather than
   a read-then-write. That implementation detail is invisible in this diff — `decrementInventory`
   is called, not shown. Under a weaker isolation level, two concurrent transactions could each
   read sufficient stock, both proceed, and both decrement — oversell — with the wrapping
   transaction never noticing, because it only guarantees the *pair* is atomic, not that the
   *decrement* is conditioned on current stock. The Actor's report claims "no oversell" the
   invariant addresses in spirit ("no partial-write window") without evidence that the invariant
   named in CONTEXT.md ("never oversell") is actually tested. Framing a partial-write fix as
   "hardened order placement" and asking for `data_flow` → 9.5 leans on suite size (2,488 green)
   as the proof, which is exactly the "counts are not quality" trap: a big green number does not
   establish that the specific, CONTEXT-named invariant is covered.

Both problems are contained to one module (`OrderService`) and do not break anything at runtime
today — both entities genuinely still live in one `Database`, so the transaction is not wrong as
written. That keeps this out of "likely disqualifier" territory. But it is a real, source-backed
data-flow hazard in the primary order-placement path, undisclosed by the Actor, and it directly
touches a committed architectural decision — that is squarely "serious deduction," and it blocks
certifying `data_flow` at 9.5 this loop.

## Remedy

Smallest honest fix, not a rewrite:

- State the tradeoff explicitly in the loop result: this transaction is a stopgap valid only while
  Order and inventory share one `Database`, with an explicit removal condition ("revisit at
  InventoryService migration, §4").
- Add (or cite, if it already exists elsewhere and wasn't touched this loop) a concurrency test
  that actually exercises §6: two competing orders against one remaining unit of stock, asserting
  exactly one commits — not just that the insert+decrement pair is atomic.
- Confirm `decrementInventory`'s write shape (atomic conditional decrement vs. read-then-write) so
  the "no oversell" claim is backed by the transaction's isolation guarantees, not merely its
  atomicity.
- Given §6 tolerates inventory lag, consider whether the long-term-compatible shape (a reservation
  or conditional-decrement call that would survive the service split) is a cheaper investment now
  than a same-database transaction that has a known one-quarter shelf life.

## Verdict

Conditional. The transaction wrap is not actively harmful today and need not be reverted, but this
loop cannot be certified at the 9.5 `data_flow` threshold: the fix contradicts a committed roadmap
item without disclosure, and it does not demonstrate coverage of the actual named consistency
requirement (oversell prevention). Both must be addressed — via explicit scoping/disclosure plus
an oversell-specific test, or a redesign toward a migration-compatible mechanism — before
`data_flow` can be accepted at 9.5.

```json
{"verdict": "conditional", "blocks_95": true, "blocking_severity": "Serious deduction", "dimension_scores": {"data_flow": 6.5}, "flagged_smells": ["fake-clean reward"], "evidence_demanded": ["Explicit acknowledgment/scoping of the CONTEXT.md §4 roadmap conflict: how this transaction-based coupling will be replaced when InventoryService moves to its own datastore next quarter, with a removal condition tied to that migration", "A concurrency/oversell test: two competing orders against a single remaining inventory unit, asserting only one commits — testing the §6 invariant directly rather than relying on aggregate suite size", "Confirmation of decrementInventory's write shape (atomic conditional decrement e.g. WHERE qty >= n, vs. read-then-write) and the transaction's isolation level, since the wrapping transaction only guarantees the insert+decrement pair is atomic, not that oversell is prevented", "Justification for choosing synchronous same-database ACID coupling over a migration-compatible design (reservation/conditional-decrement, outbox, or saga), given §6 explicitly tolerates inventory lag"]}
```
