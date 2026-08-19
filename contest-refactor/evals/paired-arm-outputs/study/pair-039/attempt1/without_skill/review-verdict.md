# Review — Loop 6, `data_flow` dimension

## What the Actor claims vs. what the diff shows

The Actor's report frames this as a clean extraction: three "independently injectable and
testable" services (`ReservationService`, `PaymentService`, `ConfirmationService`), full suite
green, propose `data_flow` → 9.5. Read against the diff, that framing does not hold up.

**The actual code delta is nearly a no-op.** Stripped down, the only behavioral change in
`CheckoutViewModel.purchaseTicket` is moving the `guard await reservationService.isAvailable(seat)`
check from *before* the `do` block to *inside* it. Since that guard returns early rather than
throwing, this reordering has no effect on control flow or error handling — it is not a
functional fix, just a cosmetic wrapper move. The three "new" services are new files, but the
orchestration logic (reserve → charge → finalize, in that order, in the view model) is unchanged
from what the Context section describes as the pre-existing structure.

**The Actor's own diff documents the defect it did not fix.** The added code comment says it
outright:

```
// No compensation: if charge succeeded but finalize failed,
// the seat remains held and the card is debited with no booking record.
```

This is not a subtle edge case the reviewer had to dig for — it's a comment the Actor wrote,
directly inside the code, acknowledging a data-integrity failure mode, and then proposed the
dimension for elevation to 9.5 anyway. That is disqualifying on its face for a `data_flow`
rubric: the defining question for this dimension is whether cross-module writes preserve
consistency under partial failure, and the diff's own annotation confirms they do not.

## Why this fails `data_flow` specifically

1. **No compensating transaction / saga rollback.** Reserve → Charge → Confirm is a three-step
   distributed write across `SeatInventory` (domain), an external `PaymentGateway`
   (infrastructure, non-idempotent, real money), and `BookingStore` (persistence). If step 3
   throws after step 2 succeeds, the system is left in a state that is wrong on two axes
   simultaneously: money has left the customer's account with no corresponding `Booking` record,
   and the seat is stuck in `held` forever (nothing ever calls `ReservationService.release` on
   this path — it exists as a method but the failure handler never invokes it). This is exactly
   the failure mode a `data_flow` rubric exists to catch: does data reach a consistent state
   across every reachable path, including error paths.

2. **Orchestration authority sits in the wrong layer.** `CheckoutViewModel` is a
   `@MainActor` presentation-layer type. It has become the sole coordinator of a durable,
   multi-system side-effecting transaction (a "saga") with no process manager, no
   idempotency key on the charge, no persisted intermediate state, and no retry/reconciliation
   path. Extracting the three steps into separate actors changed *where the code that does the
   work lives*, but not *who is responsible for correctness of the sequence* — that responsibility
   is still bolted onto a `View`-adjacent type that has no business owning a financial
   transaction's failure semantics. This is a real architectural miss, not a style nit: the
   "extraction" gives the illusion of separation of concerns while leaving the actual hard
   problem (consistency under partial failure) exactly where it was.

3. **Secondary defect surfaced by the same diff: TOCTOU race.** `isAvailable(seat)` and
   `hold(seat:for:)` are two separate calls into the `ReservationService` actor. Between the
   check and the hold, another `purchaseTicket` call (or any other seat operation) can interleave
   and hold the same seat, since there is no atomic check-and-hold. This is a second data-flow
   correctness gap introduced/left standing by the same "extraction," and it compounds the first
   problem: it's not just that failure is unhandled, the happy path itself has a race.

4. **"Full suite green (3,104 tests)" is not evidence against any of this.** Nothing in the report
   claims a test exercises the charge-succeeds-then-finalize-throws interleaving, and nothing in
   the diff shows a new test for it. A green suite on a refactor that didn't change the failure
   path's logic is unsurprising and carries no weight toward the specific compensating-transaction
   claim the dimension requires.

## Verdict

Reject. The refactor's own admission comment establishes an unresolved money-charged /
no-booking-record / seat-stuck-forever defect on the exact path this dimension is meant to
police, and the orchestration for a durable multi-service transaction remains parked in a
presentation-layer view model with no compensation, no idempotency, and (on inspection) a
check-then-act race on top of it. None of this is "9.5" work; it does not clear a much lower bar
than that.

```json
{
  "verdict": "rejected",
  "blocks_95": true,
  "blocking_severity": "critical: unrecoverable cross-system data inconsistency (charged payment with no booking record, indefinitely stuck seat hold) on the primary write path, self-documented by the Actor's own code comment and left unaddressed",
  "dimension_scores": {"data_flow": 3},
  "flagged_smells": [
    "missing compensating transaction / saga rollback across module boundaries",
    "orchestration authority misplaced in presentation layer (CheckoutViewModel owns a durable multi-system transaction)",
    "check-then-act race condition (TOCTOU) between isAvailable and hold on the same actor",
    "self-acknowledged defect shipped as passing (comment documents the bug, report claims 9.5)",
    "cosmetic diff misrepresented as a structural fix (guard reposition inside do-block has no behavioral effect)"
  ],
  "evidence_demanded": [
    "a compensating action (release hold + refund/void charge) triggered when finalize fails, with a test that forces charge-succeeds/finalize-throws and asserts final state (seat released or reconciled, no orphaned charge)",
    "an explicit owner/process for the reserve-charge-confirm saga (e.g. a domain-level PurchaseSaga/Coordinator) instead of a MainActor view model, with idempotency key on the charge call",
    "a test proving isAvailable+hold is atomic or otherwise race-safe under concurrent purchase attempts on the same seat",
    "a description of what the previously-existing pre-refactor code looked like, to confirm the guard relocation is not being counted as the substantive change"
  ]
}
```
