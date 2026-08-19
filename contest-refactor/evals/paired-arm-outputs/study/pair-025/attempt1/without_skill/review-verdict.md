# Review — Loop 7, `data_flow` dimension

## What the diff actually does

`OrderService.placeOrder` used to perform two sequential, independent writes — insert `Order`,
then insert `OrderAuditEntry` — with a window between them where a crash, timeout, or thrown
error after the first insert would leave an order with no audit record. The diff wraps both
inserts in a single `db.transaction { tx in ... }` closure, using `tx.insert` for both rows and
returning the created `Order` from the closure. Mechanically this is a small, single-purpose
change: one call site, one new indentation level, no new types, no new abstractions.

## Checking the claim against the stated context

The Actor is proposing `data_flow` → 9.5 on the strength of "order insert and audit insert now
commit together, partial-write window eliminated." I checked this against the two CONTEXT.md
clauses provided:

- **§6 (regulatory consistency)** requires a placed order to always have a matching audit entry,
  strongly consistent. A single local ACID transaction across two rows is the textbook mechanism
  for exactly that guarantee, *provided* the transaction wrapper actually rolls back on any
  thrown error inside the closure. That implementation isn't shown here — `Database.transaction`
  is used, not defined, in this diff.
- **§4 (roadmap)** is a plausible distractor: Inventory is moving to its own datastore for a
  volume-driven reason, which might make a reviewer reflexively worry about cross-database
  transactions or a future saga/outbox pattern. But the excerpt is explicit that both `Order` and
  `OrderAuditEntry` stay in the core database with no planned extraction for the audit log. A
  local, single-database transaction is the right-sized tool for two rows that live in the same
  store — reaching for a distributed-transaction or outbox pattern here would be over-engineering
  against a boundary that isn't moving. I'm not flagging §4 as a coupling problem; the Actor
  correctly did not build for a split that was never proposed for these two entities.

So architecturally the diff is pointed at the right requirement, sized correctly for the actual
future boundary (not the roadmap's inventory boundary), and doesn't introduce a second writer or
any new ownership ambiguity. `OrderService` remains the sole caller of both inserts.

## Where the evidence falls short of a 9.5 claim

The claim being certified isn't "the code compiles and old tests still pass" — it's "the
partial-write window is eliminated," i.e., a specific new consistency guarantee now holds. The
only evidence offered for that is "full suite green (2,488 tests)." That is the wrong evidence
for this claim: the pre-existing suite passed *before* this change too (the bug being fixed was a
partial-write race/failure scenario, not something the existing happy-path suite was
exercising — if it had been, the original two-write code would already have been failing). A
green suite after the change tells me the change didn't break anything it already tested; it
tells me nothing about whether the new atomicity guarantee actually holds under failure.

Nothing in the report or diff shows:
- A test that forces an error partway through the transaction (e.g., the audit-entry insert
  throwing) and asserts that *neither* row persists — the actual behavior being claimed as fixed.
- Any indication of what `db.transaction`'s contract is on a thrown error from the closure —
  guaranteed rollback, or does it depend on the caller/driver to interpret the throw correctly?
  This is invisible from the diff; only the call site changed, not the transaction primitive.
- Whether `placeOrder` is called from any retry path, where a client-perceived failure after a
  successful commit could still produce a duplicate order under the regulatory requirement in
  §6. This is likely pre-existing and out of scope for this loop, so I'm not blocking on it, but
  it's worth noting since §6 is being cited as the justification for the change.

The direction of the fix is correct and the diff is small enough that I'd be comfortable with a
"conditional" approval once the specific failure-path test exists — I'm not asking for a redesign,
I'm asking for the one test that actually proves the claim being certified.

```json
{"verdict": "conditional", "blocks_95": true, "blocking_severity": "high — regulatory consistency claim certified at the top rubric tier on suite-green evidence alone, with no test exercising the specific failure path (mid-transaction error) the loop claims to have fixed", "dimension_scores": {"data_flow": 8.0}, "flagged_smells": ["coverage-as-trust substitution (pre-existing green suite cited as proof of a new invariant it was never designed to exercise)", "unverified transaction/rollback contract (db.transaction's error-handling semantics are used, not shown or tested)"], "evidence_demanded": ["A test that throws mid-transaction (e.g., forces the OrderAuditEntry insert to fail) and asserts neither the Order nor the audit entry persists", "Confirmation of db.transaction's contract on a thrown error from its closure — guaranteed all-or-nothing rollback, with a test or reference to where that's proven", "Confirmation that a new test was actually added for this loop's specific claim, distinct from the pre-existing 2,488 that predate the fix"]}
```
