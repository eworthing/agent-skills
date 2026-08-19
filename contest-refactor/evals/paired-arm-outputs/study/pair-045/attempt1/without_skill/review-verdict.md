# Review — Loop 7, `data_flow`

## What the diff actually does

`OrderService.placeOrder` used to perform two sequential, independent writes — insert the
`Order`, then insert the `OrderAuditEntry` — with a window between them where a crash or
failure would leave an order with no audit record. The diff wraps both inserts in one
`Database.transaction` closure, using the transaction-scoped `tx.insert` instead of `db.insert`.
Mechanically this is the correct, minimal shape for the stated problem: one owner
(`OrderService`), one local ACID unit of work, no new abstraction, no new dependency, and no
data relocated. It matches CONTEXT.md cleanly — §4 says both `Order` and `OrderAuditEntry` stay
in the core database with no planned extraction, so a local transaction is safe against the
roadmap (it doesn't need to survive a future split, because there isn't one for these two
tables), and §6 states the exact invariant this closes: "a placed order must always have a
matching audit entry." I have no objection to the mechanism itself, and no scope creep to flag —
the Actor didn't touch inventory, didn't introduce a saga/outbox pattern that isn't needed for a
same-database write, and didn't restructure anything beyond the one method.

## Where I'm not willing to sign off at 9.5

**1. The fix is unverified by any test the diff shows.** The entire value of this loop is a
concurrency/failure-mode guarantee: "if the audit insert fails, the order insert rolls back too."
That guarantee is exactly the kind of thing that can be wrong in ways `swift test` passing on the
*existing* 2,488 tests would never catch — those tests were written against the old sequential
code and, by construction, cannot exercise the new rollback path, because nothing in the old
world required verifying that a mid-transaction failure leaves zero rows behind. The Actor's
report leans on "full suite green" as if it were evidence for the change, but a green suite that
predates the change is evidence of non-regression, not evidence the new invariant holds. The diff
itself contains no new test — no case that forces the second insert to fail and asserts (a) the
first insert is rolled back and (b) `placeOrder` throws. Without that, "eliminated a latent
partial-write window" is an assertion about `Database.transaction`'s semantics, not a
demonstrated property of this code. I'd want to see `tx` actually roll back on a forced failure
before taking this at face value — `Database.transaction` could, for instance, be a thin wrapper
that doesn't actually roll back on all error types, or could commit the first insert before the
closure returns, and the current suite would not tell us either way.

**2. Scope vs. the stated invariant is narrower than what CONTEXT.md commits to.** §6 has two
sentences, not one: the specific regulatory case ("a placed order must always have a matching
audit entry") *and* a general one ("Audit entries must be strongly consistent with their
orders" — no qualifier restricting that to placement). The diff only touches the `.placed` audit
action inside `placeOrder`. The enum-style call `OrderAuditEntry(orderID: order.id, action:
.placed)` all but confirms `action` has sibling cases (cancellation, shipment, refund, etc.) —
you don't write a `.placed` case on a type unless there's a set of cases. If any other order
mutation writes an `OrderAuditEntry` outside a transaction with its corresponding order write,
the general consistency requirement in §6 is still open, and this loop's report reads as if the
whole invariant is now satisfied ("a placed order always has a matching audit record") when it's
only proven placement is covered. That's a scope/claim mismatch worth surfacing even though I
can't confirm or deny other call sites from this file alone.

Neither of these is a defect in the code that's shown — the transaction wrapping is the right
move and I'm not asking for it to be redone. What I'm withholding is the *score claim*: 9.5 on
`data_flow` is a claim that this dimension is now essentially airtight, and airtight is not
demonstrated by an untested rollback path plus an invariant whose blanket half isn't shown to be
covered.

## Verdict

Conditional approval of the mechanism; not yet at the 9.5 the Actor proposes.

```json
{"verdict": "conditional", "blocks_95": true, "blocking_severity": "HIGH", "dimension_scores": {"data_flow": 8.5}, "flagged_smells": ["unverified-atomicity (transaction rollback claimed but no test forces the mid-transaction failure path)", "narrow-fix-scope-vs-blanket-invariant (§6 covers all audit entries, diff only covers the .placed case)"], "evidence_demanded": ["A test that injects a failure into the OrderAuditEntry insert (or the Order insert) inside the transaction and asserts the whole transaction rolls back with no partial row left in either table, and that placeOrder throws", "Confirmation of every other OrderAuditEntry write site (other action cases implied by the .placed case) and whether each is already wrapped in a transaction with its corresponding order mutation, or an explicit statement that those are out of scope for this loop and tracked separately", "The relevant slice of Database.transaction's implementation/contract (isolation level, rollback-on-throw behavior) since it is not part of this diff and the correctness claim rests entirely on it"]}
```
