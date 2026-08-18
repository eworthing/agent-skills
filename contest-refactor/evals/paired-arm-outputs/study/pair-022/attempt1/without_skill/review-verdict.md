# Review — Loop 7, `data_flow` dimension

## What the Actor actually built

The diff wraps the order insert and the inventory decrement in a single `Database.transaction`
closure, replacing two sequential top-level `await` calls with one local ACID transaction. Taken
purely as a diff against the *current* schema, this is a real and defensible fix: it closes a
genuine partial-write window (order committed, inventory decrement lost to a crash/timeout) that
existed in the prior code. Tests are green. Nothing about the mechanics of the diff is wrong.

The Actor's report, however, only argues from that narrow frame ("one owner, no multi-writer
ambiguity, no partial-write window") and never engages with the two CONTEXT.md excerpts that were
handed to this review alongside the diff. Both of them matter, and together they turn this from a
clean win into a change that should not be certified at 9.5 for `data_flow`.

## Why this doesn't clear the bar

**1. It hard-couples two tables that a *committed* roadmap item is about to split apart.**
§4 isn't a maybe — it's phrased as committed, next quarter: Inventory is moving out of the core
database into its own `InventoryService` with its own datastore, specifically to absorb a ~50×
write-volume spike. `Order` stays in the core database. A single local `Database.transaction`
spanning `tx.insert(Order)` and `tx.decrementInventory` is only expressible because both rows
currently live in the same physical database — the diff's own closing line concedes this
("Both `Order` and the inventory rows currently live in the same `Database`"). The moment
Inventory moves to its own datastore, this exact transaction is impossible to express as written;
it has to be torn out and replaced with some cross-service mechanism (saga, outbox, reservation
hold, etc.). That's not a hypothetical edge case someone might get to — it's on the committed
roadmap for next quarter. Shipping tighter coupling *now*, one quarter before a documented plan to
split these two concerns, is the textbook shape of a change that scores well on a narrow "is this
diff internally consistent" check and fails the "does this survive the architecture we already
said we're building" check.

**2. It solves a stricter invariant than the spec asks for, using the mechanism that's about to be barred.**
§6 explicitly says inventory counts *may lag by a few seconds* under load, provided oversell is
prevented. That's the actual consistency requirement. The Actor reached for the strongest possible
tool — synchronous cross-table ACID commit — to satisfy a requirement that was deliberately
specified to *not* need synchronous strong consistency. A reservation/hold check, an idempotent
async decrement, or any pattern that enforces "never oversell" without requiring both writes to
land in one local transaction would satisfy §6 just as well today, and would still work once
Inventory is on its own datastore. The Actor picked the one design that only works in the topology
that's being dismantled.

**3. The report shows no evidence CONTEXT.md was consulted at all.** The loop_result frames this as
an unambiguous hardening with no caveats, no mention of §4, no acknowledgment that the "one owner"
claim in the report ("single owner of order placement... no multi-writer ambiguity") is about to
become false when a second service owns inventory. A 9.5-quality change in this dimension should
either design around the documented future topology or explicitly flag the tension and scope the
transaction as a known-temporary bridge with a tracked follow-up. This diff does neither — it
presents an interim, soon-to-be-invalidated shortcut as a finished, durable architectural
improvement.

**Net effect:** this loop trades a real but bounded bug (partial-write window) for a coupling that
guaranteed rework will have to undo within a quarter, and it does so by over-satisfying a
requirement that was explicitly relaxed to avoid needing exactly this kind of coupling. That's a
regression in `data_flow` quality relative to where the codebase's own stated direction is headed,
even though it's an improvement relative to the immediately preceding code. Green tests don't
surface this — nothing in the current test suite exercises the post-migration topology, so passing
2,488 tests is orthogonal to the finding.

## Scope of what I can verify

I only have the diff and the Actor's report, not the full `Database`/`Order`/`InventoryService`
source, so I can't confirm exactly how `Database.transaction` is implemented, whether any
abstraction already exists that could make this forward-compatible, or whether `decrementInventory`
already has reservation/hold semantics elsewhere. My finding rests on what the diff and CONTEXT.md
excerpts show directly: the transaction assumes co-located storage, and the roadmap commits to
decolocating it.

## Verdict

Not a 9.5 `data_flow` result. The transactional hardening is legitimate as a narrow bug fix, but
certifying it as the dimension's target score would bless a design that contradicts a committed,
already-scheduled architectural change and over-solves a requirement the spec explicitly loosened.
This needs to go back with either (a) a design that enforces "never oversell" without assuming
co-located storage, or (b) an explicit, tracked acknowledgment that this is a temporary bridge with
a concrete plan for how it unwinds when `InventoryService` ships.

```json
{"verdict": "conditional", "blocks_95": true, "blocking_severity": "high — introduces coupling that directly contradicts a committed, dated architectural roadmap item (§4) and over-satisfies a relaxed consistency requirement (§6) using the exact mechanism the roadmap will make impossible", "dimension_scores": {"data_flow": 6}, "flagged_smells": ["roadmap-blind coupling (couples Order+Inventory writes tighter just before a committed split)", "over-engineered consistency (ACID transaction used where §6 explicitly permits eventual consistency)", "unacknowledged context (loop_result never reconciles the change with CONTEXT.md §4/§6)", "temporary-fix-presented-as-final (no tracked follow-up for the post-migration unwind)"], "evidence_demanded": ["A design (or explicit interim-bridge note with a tracked ticket) for how oversell prevention will work once Inventory moves to its own datastore, given the transaction as written cannot span two datastores", "Justification for choosing synchronous ACID coupling over a reservation/hold or idempotent-async pattern that would satisfy §6's 'may lag a few seconds' allowance and remain valid post-migration", "Confirmation of what Database.transaction actually guarantees (local-only vs. distributed) so the co-location assumption is explicit rather than implied by the diff's closing sentence", "An updated loop_result that shows CONTEXT.md §4/§6 were read and reconciled, not just the narrow before/after diff framing"]}
```
