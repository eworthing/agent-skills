# Review — Loop 7, `data_flow` dimension

## What the diff actually does

`placeOrder` used to run two independent, sequential writes (`db.insert(Order)` then
`db.insert(OrderAuditEntry)`) with a window in which the order could commit and the audit
write could fail (or vice versa). The loop replaces that with a single
`db.transaction { tx in ... }` block that inserts both rows through the transaction handle
`tx` and returns the order. That is a real, targeted fix for a real defect class
(partial-write / dual-writer inconsistency), and it is scoped tightly — only the two rows
that need to be atomic are inside the transaction.

## Checked against CONTEXT.md — no roadmap conflict

§4 says Inventory is being pulled into its own service and datastore next quarter, but it
explicitly says Orders and `OrderAuditEntry` **both** stay in the core database
indefinitely ("no planned extraction" for the audit log). The diff never touches Inventory,
so the upcoming extraction does not threaten this transaction's validity now or after the
migration — `Order` and `OrderAuditEntry` remain co-located, so a plain local ACID
transaction stays the correct mechanism (no premature two-phase-commit / saga machinery is
needed, and none was added). I'm calling this out explicitly because it would be easy for a
reviewer to either miss the roadmap section or over-apply it as a false blocker; on inspection
it isn't one.

§6 is the actual target: "a placed order must always have a matching audit entry" and
"audit entries must be strongly consistent with their orders." Wrapping both inserts in one
transaction is a direct, correct implementation of that requirement — if either insert fails,
neither commits, so there is no code path left that can produce an order without a matching
audit row (or an audit row without an order).

## The gap: the claimed invariant is asserted, not demonstrated

The Actor's report leans entirely on "full suite green (2,488 tests)" as evidence the fix
works. That's not evidence for *this* fix specifically. The suite passed before this change
too, when the two writes were still sequential and non-atomic — passing tests were never
sensitive to the defect being fixed, because nothing in a green suite exercises "the audit
insert fails midway through `placeOrder`." A green run confirms the happy path didn't
regress; it says nothing about whether the new transactional guarantee actually holds (does
`Database.transaction` really roll back the order insert when the audit insert throws? Is
the abort/rollback path even reachable and tested?).

For a change whose entire justification is "eliminates a partial-write window" on a
regulatory consistency requirement, I'd expect a test that forces a failure inside the
transaction (e.g., a fault-injected audit insert) and asserts the order row is *also* absent
afterward — proving atomicity, not just proving the old two calls still each succeed in the
normal case. Without that, "eliminated a latent partial-write window" is the Actor's
inference from reading the diff, not a demonstrated property.

Two smaller, non-blocking notes:
- The diff gives no visibility into `Database.transaction`'s retry semantics. If it ever
  re-invokes the closure on conflict, `Order(cart:buyer:)` construction would need to be
  side-effect-free per invocation (no ID/counter side effects outside the transacted state) —
  plausible from what's shown, but not confirmed by the diff alone.
- This fix only prevents *new* order/audit divergence going forward. Any already-existing
  orders that predate this fix and lack a matching audit row (if such rows exist) are
  untouched by a code-only change — that's a data-remediation concern, not a data_flow code
  defect, so I'm not treating it as blocking, just flagging it as an out-of-scope residual.

## Verdict

The design is right-sized and doesn't conflict with the committed roadmap. What's missing is
proof of the one property the loop exists to deliver. That's enough to hold the dimension
below the 9.5 convergence bar until a rollback/atomicity test is added — this is a
conditional approval, not a rejection, since no rework of the transaction itself is implied.

```json
{"verdict": "conditional", "blocks_95": true, "blocking_severity": "major", "dimension_scores": {"data_flow": 8}, "flagged_smells": ["green-suite-as-proof (existing tests don't exercise the new atomicity/rollback path)", "unverified critical invariant on a regulatory consistency requirement"], "evidence_demanded": ["A test that induces a failure inside the transaction (e.g. the OrderAuditEntry insert throwing) and asserts the Order row is also absent afterward, proving rollback actually occurs", "Confirmation that Database.transaction does not re-invoke the closure body on retry/conflict in a way that would duplicate non-idempotent side effects in Order construction"]}
```
