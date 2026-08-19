# Review — Loop 7, `data_flow` dimension

## What the diff actually does

`OrderService.placeOrder` previously issued two sequential, independent writes — an `Order`
insert and an `OrderAuditEntry` insert — with no atomicity between them. The diff replaces that
with a single `db.transaction { tx in ... }` block that performs both inserts against the same
`Database` and returns the order. Structurally this is a small, well-scoped change: it touches
only the two statements it needs to, doesn't fold in unrelated writes (e.g. no inventory
decrement, no payment step), and doesn't change the shape of either write beyond routing it
through `tx` instead of `db`.

## Checked against CONTEXT.md

- **§4 (roadmap):** Inventory is the thing scheduled to leave the core database; `Order` and
  `OrderAuditEntry` are explicitly called out as staying. The diff keeps both in the same
  `Database` and does not entangle this transaction with anything inventory-related. That's the
  correct scope — a local ACID transaction is only valid while both rows live in the same
  datastore, and this change doesn't reach past that boundary or need to be re-architected when
  the inventory split happens.
- **§6 (consistency requirement):** "A placed order must always have a matching audit entry" is
  a regulatory requirement, and the stated defect (partial-write window between two sequential
  writes) is a plausible, real violation of it. Wrapping both inserts in one transaction is the
  textbook fix for that class of problem, *if* the underlying `transaction` primitive actually
  rolls back on failure.

So the direction of the change is right, and it's aimed at the correct requirement. That's the
good part of the report and it isn't hollow — the diff matches what the Actor describes, there's
no gap between the narrated change and the actual code.

## Where the report overreaches

The Actor's report states this as settled fact: *"Eliminated a latent partial-write window."*
That is a claim about failure-mode behavior — what happens when one of the two inserts throws
partway through. Nothing in the evidence provided demonstrates that behavior:

1. **No test exercises the failure path.** "Full suite green (2,488 tests)" tells us the happy
   path still works. It says nothing about whether an induced failure in the audit-entry insert
   actually rolls back the order insert (or vice versa). The diff adds no test, and the report
   cites no existing test that forces `tx.insert(OrderAuditEntry(...))` to throw and then asserts
   the order row was not persisted. Without that, the regulatory guarantee this loop exists to
   satisfy is asserted, not demonstrated.
2. **`Database.transaction`'s own semantics are taken on faith.** The atomicity claim rests
   entirely on that primitive rolling back correctly on a thrown error inside the closure. We're
   given no visibility into it (not even a reference to its own test coverage) — it's simply
   trusted to do the right thing because it's named `transaction`.
3. **"One owner, no multi-writer ambiguity"** is stated in the diff's own commentary but not
   substantiated. There's no confirmation that `OrderService` is in fact the only writer of
   `OrderAuditEntry` rows elsewhere in the codebase — if some other path also inserts audit
   entries outside this transaction, the consistency guarantee this loop claims doesn't actually
   hold system-wide.

None of this means the change is wrong. It means the loop's central, regulatory-grade claim — the
one the whole diff exists to satisfy — has zero direct evidence behind it beyond "the pre-existing
suite still passes," which was true before this change too and doesn't test the thing that
changed.

## Verdict reasoning

For a dimension like `data_flow`, where the entire point of this loop is a consistency/atomicity
guarantee tied to a regulatory requirement (§6), a 9.5 bar should require the guarantee to be
demonstrated, not just architecturally plausible. It isn't here. The fix is very likely correct,
but "very likely correct" on a compliance-relevant data-integrity claim is a gap, not a rounding
error. I'm not rejecting the direction of the work — it's sound and well-scoped — but I can't sign
off at 9.5 on an unverified atomicity claim for exactly the property the loop was assigned to fix.

```json
{"verdict": "conditional", "blocks_95": true, "blocking_severity": "major: regulatory consistency guarantee (§6) is asserted by the report but not demonstrated by any test that exercises the rollback path", "dimension_scores": {"data_flow": 7.5}, "flagged_smells": ["unverified atomicity/rollback claim", "green suite used as evidence for an untested failure path", "unsubstantiated sole-writer assumption for OrderAuditEntry"], "evidence_demanded": ["A test that forces the OrderAuditEntry insert to fail mid-transaction and asserts the Order row was not committed", "A test that forces the Order insert to fail and asserts no OrderAuditEntry row was written", "Confirmation (via existing test coverage or a repo-wide check) that Database.transaction rolls back all statements in the closure on any thrown error, not just returns early", "Confirmation that OrderService.placeOrder is the only code path that writes OrderAuditEntry rows"]}
```
