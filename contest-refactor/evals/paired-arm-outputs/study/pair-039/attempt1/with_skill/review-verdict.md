# Review — Loop 6, `data_flow`

## What the Actor did

The diff extracts the ticket-purchase sequence out of `CheckoutViewModel` into three new actor
types — `ReservationService`, `PaymentService`, `ConfirmationService` — each wrapping one
concern (seat inventory, payment gateway, booking persistence). The only change to
`CheckoutViewModel.purchaseTicket` itself is cosmetic: the `guard` that was previously ahead of
the `do` block is now inside it, and a comment was added to the `catch` arm. The orchestration —
the ordered sequence "reserve → charge → confirm" and all error handling for it — still lives
entirely in `CheckoutViewModel`, a presentation-layer type.

## Independent assessment (not just echoing the Actor's report)

The Actor's report claims the suite is green (3,104 tests) and proposes `data_flow → 9.5`. Test
count is not evidence of the property actually being scored here (Meta-Rule 2, "counts are not
quality") — a passing suite says nothing about whether the failure path was ever exercised, and
no test evidence for the failure path is cited anywhere in the report.

**The actual defect is unchanged by this refactor, and the diff's own comment admits it:**

```
} catch {
    // No compensation: if charge succeeded but finalize failed,
    // the seat remains held and the card is debited with no booking record.
    presentError(.purchaseFailed(error))
}
```

Walking the Evidence Chain:

- **Claim.** The three-step purchase saga (reserve seat → charge card → write booking) is a
  sequence of ordered, dependent, cross-module durable writes with no process owner and no
  compensating rollback. Splitting the steps into three actor-isolated services did not resolve
  this; it relocated the same unowned orchestration into a presentation-layer view model, which
  is the wrong authority for a saga with durable, externally-visible side effects (a captured
  payment-gateway charge cannot be un-happened by the presentation layer catching an error).

- **Source.** `Sources/Presentation/CheckoutViewModel.swift`, `purchaseTicket(seat:paymentMethod:)`:
  the `catch` block calls only `presentError`, with no call to `paymentService` or
  `reservationService` to reverse prior steps. `Sources/Infrastructure/PaymentService.swift`,
  `charge(amount:to:)` calls `gateway.capture(...)` — an irreversible external effect — with no
  corresponding `refund`/`void` method exposed anywhere in the diff. `Sources/Domain/ReservationService.swift`
  exposes `release(seat:)`, so a compensating release *is* available in principle, but it is
  never invoked from the failure path.

- **Consequence.** If `ConfirmationService.finalize` throws after `PaymentService.charge`
  succeeds (the scenario names a database timeout as a realistic trigger), the result is: the
  user's payment method has been debited, no `Booking` record exists, and the seat sits in
  `.held` state with no scheduled release. This is not a contained/local issue — ticket purchase
  is the primary user flow the checkout stack exists to serve, and the harm (money taken,
  inventory permanently locked, no product record) is directly reachable by any transient error
  on the last of three network/DB-dependent steps, not a contrived edge case.

- **Remedy.** Move saga ownership out of the presentation layer into a domain-level coordinator
  (or apply the existing `ReservationService.release` and add a `PaymentService.refund`/`void` as
  compensating actions invoked from the failure path — a saga/outbox pattern, or reordering so
  the irreversible step commits last against a durably recorded reservation). At minimum, the
  catch arm needs to call the compensating actions that already exist (`release(seat:)`) and gain
  the one that doesn't (payment reversal), backed by a reconciliation sweep for holds that outlive
  their compensation attempt.

This is a **Likely disqualifier** under the rubric's severity anchor: "durable state written from
multiple places with no owner" on "a primary user flow," where "the harm is reachable" — not
theoretical. A `data_flow` score at or near 9.5 cannot be certified while this remains true; the
9-and-up anchor requires ownership and honest failure behavior to survive source inspection, and
here the failure behavior is admittedly absent (the Actor's own inline comment says so), yet the
Actor's report does not mention this gap at all and proposes acceptance anyway.

**Secondary note (out of the scored dimension, flagged for completeness):** the same code path
also shows a **reservation-after-suspension** race — `isAvailable(seat)` is checked (an
actor-isolated `await`) and `hold(seat:for:)` is called (a separate `await`) with a suspension
point between them, and `hold` unconditionally overwrites `inventory.mark(seat, .held, ...)`
without rechecking status at the point of claim. Two concurrent purchases of the same seat can
both pass the check and both proceed to hold, with the second silently clobbering the first
booking's claim. This compounds the harm above (a customer can be charged for a seat that has
since been reassigned) but maps to `concurrency`, not `data_flow` — noted, not scored here.

**What would change the verdict:** a compensating-transaction path (or reordering to make the
irreversible step commit last against a durable, already-persisted reservation) exercised by a
test that asserts the seat is released and the charge is reversed when `finalize` throws after
`charge` succeeds. Until that exists, `data_flow` stays capped well below acceptance regardless
of how clean the three-way service split looks.

```json
{
  "verdict": "rejected",
  "blocks_95": true,
  "blocking_severity": "Likely disqualifier",
  "dimension_scores": {"data_flow": 3.5},
  "flagged_smells": ["fake-clean reward", "reservation after suspension"],
  "evidence_demanded": [
    "A compensating action (seat release + payment reversal/void) invoked from the purchaseTicket catch path when finalize fails after charge succeeds",
    "A test that asserts seat state returns to .open and the charge is reversed/refunded when ConfirmationService.finalize throws after PaymentService.charge succeeds",
    "Either an atomic recheck-and-claim inside ReservationService.hold (reject if seat is no longer open) or evidence the check-then-claim window cannot be raced in practice"
  ]
}
```
