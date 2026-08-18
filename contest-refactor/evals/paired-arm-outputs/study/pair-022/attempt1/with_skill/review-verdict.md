# Review — Loop 7, `data_flow` dimension

## What the diff actually does

`OrderService.placeOrder` previously performed two sequential, independent writes
(`db.insert(Order(...))` then `db.decrementInventory(for:)`) with a partial-write window: if the
decrement failed after the insert succeeded, an `Order` would exist whose items were never
deducted from inventory. This loop wraps both writes in a single `db.transaction { tx in ... }`
block, so they now commit or roll back together. Judged purely as a local change to a single
method, this removes a real correctness gap — no multi-writer ambiguity, one owner
(`OrderService`), no partial commit. Tests report green (2,488 passed), though the diff shows no
new test asserting the rollback behavior specifically (aggregate pass count is not evidence that
the transactional property itself is under test — see Fake-clean reward / aggregate-test-count
sub-pattern in the rubric).

## Why this does not clear `data_flow` at 9.5

The `CONTEXT.md` excerpt attached to this review is exactly the kind of source-derivable
constraint the rubric requires a reviewer to weigh before certifying a top score, and it directly
conflicts with the mechanism this loop chose:

- **§4 (committed roadmap):** Inventory is moving out of the core database into its own
  `InventoryService` with its own datastore next quarter, specifically to absorb a ~50x write-volume
  spike. Orders stay in the core database.
- **§6 (consistency requirement):** Order placement must never oversell, but inventory counts
  **may lag by a few seconds** under load provided oversell is prevented — i.e. the spec itself
  says strong same-transaction consistency between Order and Inventory is *not* required, only
  no-oversell.

This loop's fix does the opposite of what that combination calls for: it deepens Order/Inventory
coupling by requiring both writes to live inside one local ACID `Database.transaction`, at the
exact moment the architecture is committed to splitting those two into separate stores. Once §4
lands, `tx.insert(Order(...))` and `tx.decrementInventory(...)` cannot both be inside one local
transaction — they'll be writes to two different datastores/services. This code will have to be
unwound and re-solved (almost certainly via an outbox/event pattern or an idempotent
reconciliation job tolerant of the "few seconds" lag §6 already sanctions) within the same
quarter it was written. That is real, source-backed engineering debt purchased against a
documented roadmap item, and the Actor's report does not mention or reconcile it — no note that
this is a deliberate, temporary bridge, no plan for what replaces it, no argument for why local
ACID is still the right call given §6's explicit lag tolerance.

There's a second, related problem: the diff doesn't touch `decrementInventory` itself, so I can't
confirm from the evidence given whether oversell-prevention (§6's actual hard requirement) is
anchored in `decrementInventory`'s own atomic behavior (e.g., a conditional `UPDATE ... WHERE
qty >= N`) independent of this outer transaction, or whether it depends on the transaction wrapper
to work at all. If it's the latter, oversell-prevention itself will silently break the moment §4
ships. The Actor's report treats "wrapped in one transaction" as equivalent to "hardened," but
those are not the same claim, and the harder, roadmap-relevant one is unverified.

This reads as *fake simplification* in the rubric's exact sense: shorter/cleaner-looking code that
hides a failure mode (what happens to this invariant once Inventory is remote) and hides the
state-transition model the spec actually asked for (bounded eventual consistency, not strong
consistency). It also leans on aggregate test count ("2,488 tests… Full suite green") as the
justification for a 9.5 claim without citing a specific test of the new transactional/rollback
behavior — the aggregate-test-count-as-test-strategy sub-pattern of *fake-clean reward*.

## Severity

Not a disqualifier: nothing here corrupts state or oversells today, and the fix is a genuine,
contained improvement over the prior partial-write bug. But it is a real, source-backed data-flow
hazard in the module the contest most cares about (`OrderService`, "the single, unambiguous
owner of order placement") — a design decision that contradicts a committed roadmap item and is
stronger than the documented requirement calls for, undisclosed in the Actor's own report. That is
a **Serious deduction**: contained, doesn't threaten today's correctness, but a reasonable judge
should not certify this at 9.5 without the Actor reconciling it against §4/§6.

## Verdict

Conditional. Keep the transaction — it is a legitimate fix for the partial-write window — but do
not accept the proposed `data_flow` → 9.5. Require the Actor to close the roadmap conflict before
re-proposing a top score.

```json
{"verdict": "conditional", "blocks_95": true, "blocking_severity": "Serious deduction", "dimension_scores": {"data_flow": 8.0}, "flagged_smells": ["fake simplification", "fake-clean reward"], "evidence_demanded": ["Source citation of decrementInventory's own implementation proving oversell-prevention (§6) is enforced atomically at the inventory row/write itself, independent of this outer transaction", "Explicit reconciliation of this same-database ACID transaction with the §4 committed InventoryService extraction — either documented as a named temporary bridge with a follow-up plan, or replaced with a design that tolerates §6's sanctioned few-seconds lag (e.g. outbox/event reconciliation) and survives the datastore split", "A direct test (file:line) asserting the new rollback/atomicity behavior — e.g. order insert rolled back when decrementInventory throws — rather than citing aggregate suite pass count as evidence for this specific property"]}
```
