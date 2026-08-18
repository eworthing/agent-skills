# Review — Loop 7, `data_flow`

## What changed

`OrderService.placeOrder` used to perform two sequential writes (order insert, then
inventory decrement) with a partial-failure window between them. This loop wraps both
in a single `Database.transaction`, so the order row and the inventory decrement now
commit or fail together. Taken purely as a local fix to the two-write race that existed
before, this is a real improvement: one ACID unit, one commit point, no orphan order
without a matching inventory decrement. The Actor reports 2,488 tests green and proposes
`data_flow` → 9.5.

## Why I'm not certifying 9.5

The CONTEXT.md excerpt attached to this review is not incidental background — it directly
bears on the exact two pieces of state this diff just coupled, and the Actor's report never
engages with it.

**§4 (committed roadmap):** Inventory is scheduled to move out of the core database into a
dedicated `InventoryService` with its own datastore next quarter, specifically to absorb a
~50× write-volume spike. Orders stay in the core database. That means Order and Inventory
are about to become two separate physical stores — a `remote-owned` dependency relationship
in this rubric's own categorization, not an `in-process` one.

**§6 (actual consistency requirement):** the only hard requirement is "order placement must
never oversell." Inventory counts are explicitly allowed to lag by a few seconds under load.
Strong cross-aggregate atomicity is not the documented requirement — bounded staleness with
an oversell guard is.

The diff at `Sources/Domain/OrderService.swift:35-39` does the opposite of both of these
facts: it reaches into `db.transaction { tx in ... tx.decrementInventory(...) }`, binding
Order-write and Inventory-write into one local ACID unit at the exact moment a committed
decision says these two are being physically split. A single `Database.transaction` cannot
span two independent datastores — when the §4 migration lands, this "hardening" has to be
torn out and replaced with whatever consistency mechanism spans `Database` and
`InventoryService` (outbox, saga, reservation-then-confirm, etc.). The Actor's fix spends
more consistency strength than the spec asks for (§6 tolerates lag; this buys atomicity)
and, in doing so, adds a coupling liability directly on the checkout write path that
someone has to pay down next quarter. That is a real data-flow/ownership cost in a
meaningful module (`OrderService` is described as "the single, unambiguous owner of order
placement" — the primary checkout flow), not a cosmetic nit.

This is not a case where the governing rule is *absent* from CONTEXT.md (which would only
cap the score and demand the missing rule) — the rule is *present*, and the change runs
counter to it without acknowledgment. The Actor's report ("Hardened order placement... Full
suite green... proposing 9.5") leans on the green suite and a plausible-sounding narrative
to ask for a top score without ever touching the one piece of provided context that
contradicts the direction of the fix. That is the shape of a fake-clean ask: a passing test
count and tidy prose standing in for an architectural judgment that the same context page
already complicates.

To be clear about what this finding is *not* saying: the transaction wrap is not a bug, and
I'm not asserting oversell is currently broken — nothing in this diff touches
`decrementInventory`'s own oversell guard, and I have no evidence that guard is missing or
wrong. The finding is scoped to the *data_flow* shape of the fix: joint local-DB atomicity
was chosen where the spec tolerates lag, and that choice actively conflicts with a committed
migration this loop's own review packet discloses.

## Evidence chain

- **Claim:** This loop's transactional coupling of Order and Inventory writes conflicts with
  a committed roadmap decision to split those two into separate datastores next quarter, and
  spends more consistency strength than the documented requirement calls for.
- **Source:** `scenario.md` CONTEXT.md §4 ("Inventory moves out of the core database into a
  dedicated `InventoryService`... Orders remain in the core database"); §6 ("Inventory counts
  may lag by a few seconds under load, provided oversell is still prevented"); diff
  `Sources/Domain/OrderService.swift:35-39` (`db.transaction { tx in ... tx.decrementInventory
  ... }`).
- **Consequence:** Locks two aggregates into one physical transaction right before a committed
  decision separates their datastores; the mechanism cannot survive that migration unmodified
  and will require rework. Also over-delivers consistency strength the spec doesn't require,
  adding coupling cost on the primary checkout write path without being asked to.
- **Remedy:** Either (a) implement the oversell guarantee at the inventory-row level (an
  atomic/conditioned decrement, e.g. a constrained update) decoupled from order-row atomicity,
  so the mechanism is `remote-owned`-compatible and survives the §4 split unchanged, or (b) if
  joint atomicity is a deliberate near-term choice, record it explicitly (ADR or CONTEXT.md
  addendum) as a disclosed, temporary tradeoff with a named removal condition tied to the §4
  migration. Either path is a smaller, more honest fix than certifying the current diff as a
  9.5 "hardening."

## Verdict rationale

`data_flow` does not clear 9.5 this loop. The change is a real, contained improvement over
the prior two-write race, but it is blocked from the top anchor by an unaddressed conflict
with disclosed, committed architecture — a Serious deduction, not a disqualifier (nothing is
broken at runtime today, and the harm is a future rework cost rather than a live defect).
Conditional on redesigning the decrement to be split-compatible, or explicitly disclosing and
scoping the tradeoff, this could clear a high score next loop.

```json
{"verdict": "conditional", "blocks_95": true, "blocking_severity": "Serious deduction", "dimension_scores": {"data_flow": 7.5}, "flagged_smells": ["temporal coupling", "overbuilding", "fake-clean reward"], "evidence_demanded": ["Explicit reconciliation of this Database.transaction design with CONTEXT.md §4 (Inventory moving to a dedicated InventoryService/datastore next quarter) — how does this mechanism survive Order and Inventory no longer sharing a database?", "Justification for choosing single-database ACID strength when §6 only requires oversell prevention and explicitly tolerates inventory lag, rather than a lighter, migration-compatible mechanism (e.g. an atomic/conditioned decrement at the inventory row, decoupled from order-insert atomicity)", "A disclosed-tradeoff record (ADR or CONTEXT.md addendum) if the joint transaction is a deliberate near-term choice, naming the removal condition tied to the §4 migration"]}
```
