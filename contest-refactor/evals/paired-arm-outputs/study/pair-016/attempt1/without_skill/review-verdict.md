## Review — Loop 7, `data_flow`

**Claim under review:** wrapping the order insert and inventory decrement in a single
`Database.transaction` "hardens" order placement, eliminates a "latent partial-write window,"
and should raise `data_flow` to 9.5. Evidence offered: 2,488 tests green.

**Independent assessment: the claim does not survive contact with the CONTEXT.md excerpt
attached to this same review, and I do not accept the report's framing.**

### 1. The diff actively works against a committed architectural roadmap

§4 states, as a *committed, next-quarter* item: Inventory is moving out of the core database
into its own `InventoryService` with its own datastore, specifically to absorb a ~50× write
spike. Orders stay in the core database. The diff's own closing note confirms the precondition
this depends on: "Both `Order` and the inventory rows currently live in the same `Database`."

A single local ACID `Database.transaction` spanning both writes is *only* expressible because
Order and Inventory happen to share a datastore today. That is exactly the arrangement §4 says
is going away. Once Inventory moves to its own service/store, this transaction cannot survive
unmodified — there is no single local ACID scope across two datastores; the two writes will have
to be pulled back apart (likely into a saga/outbox/compensating-action shape) at real cost. This
loop spends effort tightening a coupling that a already-committed near-term migration is going to
have to cut back out. That is architecture debt manufactured in the same quarter it will be
paid down, not "hardening."

A refactor loop grading a `data_flow` dimension should be reading exactly this kind of
roadmap signal before increasing cross-boundary coupling. The report shows no evidence this was
considered.

### 2. The diff does not implement the actual stated requirement, and over-shoots the wrong one

§6 is explicit about what "correct" means here: order placement must never oversell, and
inventory counts *may lag by a few seconds under load* — i.e., strict synchronous consistency
between the order write and the inventory write is explicitly **not** the requirement. The spec
tolerates eventual consistency in exchange for scalability (consistent with the §4 write-spike
motivation).

The Actor's fix imposes strict same-transaction atomicity — stricter than the spec asks for —
while the diff shows no change to `decrementInventory`'s actual logic. Wrapping two existing
calls in a transaction closure guarantees atomicity/durability of the pair (both happen or
neither), but it does **not** by itself guarantee no oversell: absent a conditional/guarded
decrement (e.g., `WHERE qty >= :n` with a rowcount check) and correct isolation level, two
concurrent `placeOrder` transactions against the same low-stock item can each read sufficient
stock and each successfully decrement, oversubscribing inventory — transaction boundaries alone
don't prevent this. The report's "eliminated a latent partial-write window" language is about
atomicity, not the oversell race, so the one consistency requirement the spec actually names is
not shown to be addressed by this change at all.

### 3. Evidence gap

"Full suite green (2,488 tests)" is offered as the only support. Nothing in the diff or report
indicates any of those tests exercise concurrent `placeOrder` calls against contended inventory,
or otherwise targets the oversell scenario named in §6. A green suite that predates this change's
actual risk surface is not evidence the risk is closed — it's evidence the change didn't break
anything the suite already checked.

### Net assessment

This loop trades a real, near-term architectural cost (tighter coupling against a committed
service split) for a consistency guarantee stronger than the spec requires, while leaving the
spec's actual named risk (oversell under concurrent load) unaddressed and unverified. That is a
net regression on `data_flow`, not a 9.5-grade hardening, regardless of test-suite color.

```json
{"verdict": "rejected", "blocks_95": true, "blocking_severity": "critical", "dimension_scores": {"data_flow": 3}, "flagged_smells": ["roadmap-conflicting coupling", "stricter-than-spec over-engineering", "wrong-problem-solved (atomicity substituted for oversell prevention)", "green-suite-as-proof without targeted test evidence"], "evidence_demanded": ["Sign-off from the owner of the §4 InventoryService migration that this transactional coupling is an acceptable interim step, with a stated unwind plan (e.g. outbox/saga) for when Inventory moves to its own datastore", "A concurrency test demonstrating no oversell occurs under N parallel placeOrder calls against the same low-stock item, since transaction wrapping alone does not guarantee this", "The body of decrementInventory (not shown in the diff), confirming an atomic conditional decrement rather than a blind read-then-write, since oversell risk persists inside the transaction otherwise", "Identification of which of the 2,488 passing tests actually exercise the new transaction path or any oversell scenario"]}
```
