# Review — Loop 7, `data_flow`

## What the Actor did

`OrderService.placeOrder` used to do two sequential writes (`db.insert(Order)` then
`db.decrementInventory`) with a partial-failure window between them. The loop wraps both in a
single `db.transaction { tx in ... }`, making them atomic. Tests are green (2,488/2,488). The
Actor's report frames this as pure hardening and proposes `data_flow` → 9.5.

Taken in isolation, on the current schema, this is a correct, minimal fix for the bug it names:
today `Order` rows and inventory rows live in the same `Database`, so a local ACID transaction is
available and the diff is the smallest honest way to close the partial-write window. I re-derived
this independently rather than taking the Actor's framing at face value, per the anchor-to-source
discipline in `method.md` — and that's where the finding shows up: not in the mechanics of the
diff, but in what invariant it silently commits the architecture to, checked against the
CONTEXT.md excerpt attached to this review.

## The finding

CONTEXT.md §4 (Roadmap, **committed**, next quarter) states Inventory is moving out of the core
database into a dedicated `InventoryService` with its own datastore. Orders stay in the core
database. §6 (Consistency requirements) states the actual invariant that must hold: order
placement must never oversell, and inventory counts *may lag by a few seconds* under load —
explicit, source-provided permission for eventual consistency between the two concerns.

The Actor's fix does the opposite of what §6 asks for and directly conflicts with §4:

- It implements the *strongest* possible consistency between Order and Inventory (single ACID
  transaction, no lag, no partial state ever observable) when CONTEXT.md explicitly says a
  several-second lag is acceptable. The invariant actually required — "never oversell" — is a
  property of how `decrementInventory` enforces a floor/available-quantity check, not a property
  of whether the decrement and the order insert commit together. Nothing in the diff touches or
  cites that logic; the Actor's report never distinguishes "no partial-write window" (what was
  built) from "no oversell" (what §6 requires).
- It hard-codes the assumption that Order and Inventory share one datastore — the diff's own
  closing line concedes this: *"Both `Order` and the inventory rows currently live in the same
  `Database`."* That assumption is exactly what §4 says is scheduled to become false next
  quarter. `Database.transaction` cannot span two independent datastores once `InventoryService`
  gets its own store. This loop's "hardening" is not forward-compatible with a *committed*
  roadmap item — it will have to be torn out and replaced with a distributed-transaction, saga,
  or outbox-style mechanism at that point, which is strictly more work than building toward that
  shape now, and it is unaddressed anywhere in `loop_result`.

Per the rubric's CONTEXT.md-awareness rule, a change that contradicts a documented, committed
architectural decision must say so explicitly ("contradicts §4 — but worth doing now because...")
rather than proceed silently. This report does neither: it presents the change as unqualified
hardening with no acknowledgment of the roadmap or the lag tolerance already granted in §6. That
silence is itself part of the finding, not just a style complaint — it means the scorecard would
be crediting `data_flow` for solving a stronger, undocumented invariant while leaving the
documented one (oversell prevention under the future split) unverified and un-cited.

This is not a "missing context" situation (the Context-sufficiency cap doesn't apply — the rule
*is* present in CONTEXT.md, it's simply contradicted, not absent). It's the more straightforward
case: current source + current CONTEXT.md together disprove the fix's implicit design premise.

Secondary, weaker observation: the report leans on "full suite green (2,488 tests)" as blanket
justification for the 9.5 proposal without citing a test that exercises concurrent
`placeOrder` calls against the same item (the actual oversell scenario). That's adjacent to the
rubric's aggregate-test-count-as-test-strategy pattern — count is not quality, and no concurrent
test is named — but I'm not scoring `test_strategy` here, so I note it only as evidence that
"green suite" isn't standing in for verification of the invariant that matters.

## Severity

**Serious deduction.** `OrderService` is a meaningful, primary-flow module and this is a real
data-flow hazard (an architectural commitment that contradicts a committed roadmap item and
targets the wrong invariant), but it is currently contained: nothing is broken at runtime today,
the single-database transaction works correctly as written, and a reasonable judge could still
rank this submission highly with the finding present. It is not a Likely disqualifier — no primary
flow is broken right now — but it blocks certifying `data_flow` at the 9.5 bar this loop, because
the top score for this dimension genuinely rests on a claim ("hardened," "no partial-write
window") that conflicts with the documented target architecture and doesn't address the invariant
CONTEXT.md actually requires.

## What would clear it

1. `loop_result` explicitly acknowledges the §4 roadmap conflict and states a disposition: either
   this transactional coupling is an accepted, time-boxed interim measure (with a plan for what
   replaces it when `InventoryService` ships), or the fix is reworked into something that survives
   the split (e.g., an idempotent/retryable decrement with compensation on failure, rather than
   requiring shared-datastore atomicity).
2. A `file:line` citation into `decrementInventory` showing how oversell is actually prevented
   (floor check, conditional update, unique constraint), since that — not order/inventory
   atomicity — is the invariant §6 names.
3. A named test (not just an aggregate pass count) that exercises concurrent `placeOrder` calls
   against the same inventory item and asserts oversell cannot occur.

```json
{"verdict": "conditional", "blocks_95": true, "blocking_severity": "Serious deduction", "dimension_scores": {"data_flow": 8}, "flagged_smells": ["persistence leakage", "temporal coupling"], "evidence_demanded": ["Explicit disclosure in loop_result of the conflict with CONTEXT.md §4 (committed roadmap: Inventory moves to its own InventoryService/datastore next quarter) and a stated disposition for this transaction post-split", "file:line citation of the decrementInventory logic showing how oversell is actually prevented, since that is the invariant CONTEXT.md §6 requires, not order/inventory atomicity", "A named test exercising concurrent placeOrder calls against the same inventory item asserting no oversell, not just an aggregate 2,488-test pass count"]}
```
