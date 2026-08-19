## Review: Loop 6 — `data_flow`

### What the diff actually does

The Actor's report frames this as a clean extraction: three new services
(`ReservationService`, `PaymentService`, `ConfirmationService`) each wrapping one
external dependency (`SeatInventory`, `PaymentGateway`, `BookingStore`) behind an
`actor` boundary. Taken in isolation, that part is reasonable — each service hides
a real unit of complexity (persistence/gateway access + actor isolation) behind a
narrow interface, and "independently injectable and testable" is a fair claim for
each of them individually.

But the dimension under review is `data_flow`, and the diff does not touch the one
thing that matters for that dimension here: the ordering and consistency guarantees
of a three-step, cross-module write with a durable, external, irreversible side
effect (a captured credit-card charge) in the middle of it.

### The actual defect

`CheckoutViewModel.purchaseTicket` still sequences all three writes directly:

```
hold seat → charge card → finalize booking → present confirmation
```

If `charge` succeeds and `finalize` throws (the diff's own example: a database
timeout), the resulting state is:

- The payment gateway has captured money from the user.
- No `Booking` record exists.
- The seat sits in `held` forever — no timeout, no release, no retry.

The diff's own added comment says this outright:

```swift
} catch {
    // No compensation: if charge succeeded but finalize failed,
    // the seat remains held and the card is debited with no booking record.
    presentError(.purchaseFailed(error))
}
```

That is not a review finding I'm inferring — the Actor documented the exact bug in
a code comment and shipped it anyway. This is a silent financial-correctness and
data-integrity defect: real money moves, and the system has no record of why, no
seat freed, no compensating refund, no reconciliation path, and no way for an
operator to detect the drift short of a support ticket or a manual audit.

The only structural change to the orchestration itself is moving the availability
`guard` inside the `do` block — a cosmetic reshuffle that does not change the
failure semantics of the sequence at all.

### Layering problem

Even setting the missing compensation aside, the orchestration of a multi-step
transaction with an external, non-idempotent, money-moving side effect has no
process owner. It lives in `CheckoutViewModel` — a `@MainActor` presentation-layer
type. A saga/transaction coordinator is domain or application-layer
responsibility: it needs to own the transaction boundary, decide what "success"
means, and drive compensation or retry when a downstream step fails. Splitting the
steps into three actors while leaving the *coordination* of those steps in the
view model doesn't fix that — it arguably makes it worse, because the three
services now look domain-clean and independently testable while the one place
that actually needs the harder engineering (the saga) is untouched and framed as
already done.

### Why "3,104 passed, 0 failed" doesn't clear this

Green count is not evidence the failure path is handled — it's evidence the
failure path was never exercised. Nothing in the diff adds a test where `charge`
succeeds and `finalize` throws and asserts the resulting state is consistent
(booking exists, or the charge is refunded, or the seat is released, or *some*
durable record of the inconsistency is created). Given the Actor's own comment
names this exact scenario, its absence from the test suite is not an oversight I'm
speculating about — it's the one test this loop most needed and didn't write. That
is textbook testing-theater: the suite is green because it doesn't touch the
thing that's broken.

### Verdict reasoning

The extraction is a legitimate but orthogonal improvement (better encapsulation
per-service). It does not touch, let alone resolve, the cross-boundary consistency
problem that actually defines `data_flow` quality for this kind of code: what
happens to data and money when step 2 of 3 succeeds and step 3 fails. That problem
is not just unresolved, it's newly *documented and accepted* in-line, which reads
as the Actor recognizing the defect and shipping around it rather than through it.
A dimension score of 9.5 asserts near-flawless data flow; an unrecoverable,
money-losing, self-acknowledged inconsistency is disqualifying at any threshold
above "known broken."

```json
{
  "verdict": "rejected",
  "blocks_95": true,
  "blocking_severity": "critical — unrecoverable data/financial inconsistency (charged customer, no booking record, seat stuck held) self-documented in the diff and left unresolved; no compensating transaction, no idempotency, no reconciliation path",
  "dimension_scores": {
    "data_flow": 3
  },
  "flagged_smells": [
    "Missing compensating transaction / saga anti-pattern (money captured with no rollback or reconciliation on downstream failure)",
    "Orchestration of a durable, external, non-idempotent side effect owned by the presentation layer instead of a domain/application-layer coordinator",
    "Testing theater — green suite has no coverage for the exact partial-failure path the Actor's own comment names",
    "Self-documented known defect shipped as done (\"No compensation\" comment) rather than fixed",
    "Unbounded stuck state — seat held indefinitely with no timeout/expiry/release mechanism on partial failure"
  ],
  "evidence_demanded": [
    "A test that drives PaymentService.charge to succeed and ConfirmationService.finalize to throw, then asserts the system reaches a consistent, recoverable state",
    "A defined transaction/saga owner (domain or application layer, not CheckoutViewModel) responsible for the hold→charge→finalize sequence and its failure semantics",
    "A compensating action on finalize failure: refund the charge, release the seat hold, or persist a durable pending-reconciliation record — at minimum one of these, ideally issued automatically rather than left to manual support",
    "An idempotency key or equivalent guard on PaymentService.charge if retry-based recovery is the chosen strategy, to prevent double-charging on retry",
    "Removal or resolution of the in-line comment documenting the unhandled case — a comment acknowledging a known data-corruption path is not a fix"
  ]
}
```
