# Review — Loop 6, `data_flow` dimension

## What the diff actually does

The refactor pulls three previously-inline steps (`isAvailable`/`hold`, `charge`, `finalize`) into
three new `actor` types — `ReservationService`, `PaymentService`, `ConfirmationService` — each in
its own file/layer (`Domain`, `Infrastructure`, `Domain`). On its own, that's a reasonable module
split: each concern is independently named, injectable, and (per the Actor's report) testable in
isolation. If the ask were "extract these three responsibilities into separate types," this would
clear the bar.

But `data_flow` is not just "are the pieces named well" — it's "does data move through the system
correctly, especially across the write boundaries this loop just multiplied." The diff makes that
question worse, not better, and the Actor's own inline comment proves they knew it.

## The defect

`CheckoutViewModel.purchaseTicket` is the *only* place that knows the seat-hold, the charge, and
the booking record must succeed or fail together. It is a presentation-layer `ObservableObject`
orchestrating a three-step saga with a durable, external side effect (the payment gateway) in the
middle step. The diff's own before/after only moves a `guard` inside the `do` block — it adds zero
compensation logic — and then adds this comment on the catch block:

```swift
} catch {
    // No compensation: if charge succeeded but finalize failed,
    // the seat remains held and the card is debited with no booking record.
    presentError(.purchaseFailed(error))
}
```

That is a self-documented, shipped data-integrity bug: on a `ConfirmationService.finalize` failure
(the scenario cites a DB timeout — not a rare edge case, an expected failure mode of any datastore)
the customer's card has already been captured by an external gateway, no `Booking` row exists to
reconcile against, and the seat sits in `held` forever with no TTL, retry, or release path shown
anywhere in this diff or the referenced services. There is no idempotency key on the charge call,
so even a client-side retry of the whole flow would double-charge. This is a real-money defect, not
a style nit.

Splitting the steps into three actors, without also giving *someone* — a saga/coordinator type that
owns the transaction, not a `@MainActor ObservableObject` — the authority and the compensating
actions (refund the charge, release the seat, or at minimum enqueue a reconciliation record), is a
regression in `data_flow` terms: the write path across module boundaries got longer and more
distributed (three actors instead of one inline sequence) while the consistency guarantee across
that path stayed at zero. Actor isolation on each service also doesn't buy anything here — it
protects each actor's *internal* state, not the cross-actor sequence, which is exactly what's
broken.

## On "tests green"

3,104 passing tests is not evidence against this finding. Nothing in the diff shows a test that
drives `PaymentService.charge` to succeed and `ConfirmationService.finalize` to throw and then
asserts on the resulting system state (seat status, absence of a refund, presence/absence of a
booking). The Actor's report doesn't cite such a test either. A green suite that never exercises
the partial-failure interleaving is not evidence the interleaving is handled — it's evidence it's
untested, which lines up exactly with the comment admitting no compensation exists.

## Verdict

Reject at the 9.5 bar for `data_flow`. The module boundaries are cleaner, but the loop introduced
(or at minimum failed to close) an unrecoverable, financially-impactful data-consistency hole
across those boundaries, and flagged it in a comment rather than fixing it. A 9.5 acceptance on
`data_flow` requires that cross-module writes with external durable side effects either be atomic,
be compensated on partial failure, or be made safely retryable/idempotent with a reconciliation
path for the stuck state — none of which is present.

```json
{"verdict": "rejected", "blocks_95": true, "blocking_severity": "critical — data-integrity/financial-correctness defect: partial-failure across the charge/finalize boundary leaves a captured payment with no booking record and a seat held indefinitely, self-acknowledged in a code comment and shipped anyway", "dimension_scores": {"data_flow": 3}, "flagged_smells": ["orchestration authority in presentation layer", "missing saga/compensating-transaction across durable cross-module writes", "non-idempotent external payment call (retry = double charge)", "silently swallowed partial-failure state (comment admits it, catch just presents an error)", "unbounded resource leak: seat held indefinitely with no TTL/release path"], "evidence_demanded": ["A test that makes PaymentService.charge succeed and ConfirmationService.finalize throw, then asserts the system reaches a consistent state (booking committed via retry, or charge reversed, or seat released) rather than just asserting an error is presented", "A named owner for the transaction (saga/coordinator in Domain, not CheckoutViewModel) with explicit compensating actions on downstream failure", "Idempotency key or equivalent on PaymentService.charge so a retried purchaseTicket call cannot double-charge", "A reconciliation or expiry mechanism for seats stuck in .held state (TTL, background sweep, or alerting) if full atomicity is not achievable"]}
```
