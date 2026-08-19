# Review — Loop 7, `data_flow` dimension

## What the diff actually does

`OrderService.placeOrder` used to perform two sequential, independent writes —
`db.insert(Order(...))` then `db.insert(OrderAuditEntry(...))` — with a window in which the
order could exist without its audit entry (or vice versa) if the process died between the two
calls. The diff replaces this with a single `db.transaction { tx in ... }` closure that performs
both inserts against the same transaction handle `tx` and returns the order. If the guarantee
holds as described, this is the correct, minimal shape for the stated requirement in the supplied
CONTEXT.md §6: *"A placed order must always have a matching audit entry... strongly consistent
with their orders."* The diff is small, single-purpose, and doesn't touch anything beyond
`OrderService.placeOrder`.

## What I checked and cleared

**The §4 roadmap note is a plausible trap, and it doesn't apply.** CONTEXT.md flags that
`Inventory` is moving to a separate `InventoryService`/datastore next quarter for a 50x
write-volume spike. A reviewer could be tempted to flag this transaction as a future landmine —
"don't build new cross-table transactional coupling right before a service split." But the diff
never touches inventory at all, and the same CONTEXT.md excerpt is explicit that both `Order` and
`OrderAuditEntry` stay in the core database with "no planned extraction" for the audit log. So
this transaction is not spanning a boundary that's about to become a network call; it's two
tables in the same datastore today and, per the stated roadmap, for the foreseeable future. I'm
clearing this concern rather than flagging it.

**Ownership and scope are clean.** The change doesn't introduce a second writer, doesn't touch
call sites outside `OrderService`, and doesn't expand scope into inventory or anything else. The
report's "single, unambiguous owner" framing matches what the diff shows.

## What blocks a 9.5 on this dimension

The whole point of this loop is a *consistency guarantee*: order and audit entry either both
persist or neither does. That guarantee is entirely a property of two things neither of which is
visible in the attached material:

1. **`Database.transaction`'s actual contract.** The diff assumes it rolls back all writes inside
   the closure on any thrown error. That's the standard meaning of the name, but naming a method
   `transaction` doesn't make it atomic — nothing in `scenario.md` shows its implementation or
   documents that guarantee. I can't independently confirm it from what I was given, and the
   sandbox for this review doesn't let me look at the rest of the source to check.
2. **No test exercises the failure path this loop exists to fix.** "Full suite green (2,488
   tests)" is evidence of *no regression*, not evidence of the *new property*. Nothing in the
   diff adds a test that forces the audit insert (or the order insert) to fail mid-transaction and
   asserts the other write did not persist. Without that, "eliminated a latent partial-write
   window" is an assertion about behavior the test suite doesn't exercise — the same 2,488 tests
   would have been just as green under the old sequential-write code for every case that doesn't
   specifically inject a mid-sequence failure.

For a regulatory-consistency requirement being certified at a 9.5 bar, an assertion that the
fix works is not the same as evidence that it works. That gap is what I'm withholding full
sign-off on — not because the diff looks wrong, but because its central claim is unverified by
anything in front of me.

## Evidence that would close this

- A test that injects a failure into the audit-entry insert (or the order insert) inside the
  transaction and asserts the other row is not persisted — i.e., a rollback test, not just a
  happy-path test.
- The contract/implementation of `Database.transaction` (or a pointer to where it's documented)
  confirming it provides real rollback semantics on thrown errors, not just a naming convention.
- Confirmation that `OrderService.placeOrder` is the only code path that creates `Order` /
  `OrderAuditEntry` rows, so the "single owner" claim actually holds repo-wide and not just for
  this file.

```json
{"verdict": "conditional", "blocks_95": true, "blocking_severity": null, "dimension_scores": {"data_flow": 8.5}, "flagged_smells": ["unverified atomicity claim", "green-suite used as proof of an untested code path", "opaque transaction contract"], "evidence_demanded": ["failure-injection test proving rollback of the Order insert when the audit insert throws (and vice versa)", "documented contract for Database.transaction confirming rollback-on-throw semantics", "confirmation that OrderService.placeOrder is the sole write path creating Order/OrderAuditEntry rows"]}
```
