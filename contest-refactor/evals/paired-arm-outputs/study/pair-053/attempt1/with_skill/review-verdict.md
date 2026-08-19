# Critic Review — Loop 6, `data_flow` dimension

## Scope

Reviewing the Actor's claim that extracting the ticket-purchase sequence into
`ReservationService`, `PaymentService`, and `ConfirmationService` (orchestrated
from `CheckoutViewModel`) earns `data_flow` → 9.5. Full suite green (3,104
tests) is offered as the sole supporting evidence. Applying the Evidence Chain
(Claim → Source → Consequence → Remedy) from `method.md` and the Severity
Anchors / Smell vocabulary from `architecture-rubric.md`.

## Evidence Chain

**Claim.** The ticket-purchase saga (reserve → charge → confirm) has no
process owner and no compensating-rollback path. `CheckoutViewModel`, a
presentation-layer type, sequences three cross-module writes to durable
systems (seat inventory, external payment gateway, booking store) with only a
single top-level `catch` that surfaces a UI error — it performs no
compensation for any step that already succeeded.

**Source.** `Sources/Presentation/CheckoutViewModel.swift`,
`purchaseTicket(seat:paymentMethod:)`:

```
await reservationService.hold(seat: seat, for: booking)
try await paymentService.charge(amount: seat.price, to: paymentMethod)
try await confirmationService.finalize(booking: booking)
...
} catch {
    // No compensation: if charge succeeded but finalize failed,
    // the seat remains held and the card is debited with no booking record.
    presentError(.purchaseFailed(error))
}
```

The comment is the Actor's own diff — the defect is conceded in the patch
that proposes the 9.5 score. `PaymentService.charge` calls
`gateway.capture(...)` (an external, non-reversible-by-default side effect on
a `true-external` dependency per the rubric's Dependency Categorization
table), and `ConfirmationService.finalize` is the only writer of the
`Booking` record and the only path that flips the seat from `held` back to a
terminal state. There is no fourth type — no saga/transaction/outbox owner —
between these three actors and the presentation layer.

**Consequence.** On any `finalize` failure after a successful `charge` (the
scenario's own example: a database timeout), the system reaches a state that
cannot self-correct: the payment gateway has captured real money, no
`Booking` record exists to reconcile against, and the seat sits in `.held`
indefinitely. This is not a theoretical edge case — it is the ordinary
timeout/partial-failure shape of any three-hop network+DB sequence, and it
sits on the primary user flow of a ticketing application (buying a ticket).
This matches the Severity Anchors' own "Likely disqualifier" example
verbatim: *"durable state written from multiple places with no owner"* where
*"the harm is reachable from a primary user flow."*

**Remedy.** Move the saga's ownership out of the presentation layer into a
domain-level process owner (e.g., a `CheckoutSaga`/`PurchaseCoordinator` that
`CheckoutViewModel` merely invokes) that either (a) performs the steps with
real compensations — refund-on-finalize-failure, release-hold-on-failure,
idempotent retry — or (b) writes an explicit, durable "pending reconciliation"
record the moment `charge` succeeds, so a partial failure is recoverable by a
reconciliation process rather than silently swallowed into a UI error. The
smallest honest fix does not require re-inlining the three services — it
requires giving the *sequence* an owner with failure authority, which
`CheckoutViewModel` is structurally the wrong place for (it is presentation,
not domain).

## Simplify Pressure Test on the Actor's claimed convergence

1. Does it fix real ambiguity? **No.** The ambiguity here — who owns
   compensation when step 3 of 3 fails — is exactly what the refactor left
   untouched; the diff's only functional change is scoping the `guard` inside
   the `do` block, which is orthogonal to the defect.
2. Smallest honest fix? N/A — no fix to the actual defect was attempted this
   loop.
3. Avoids duplicate layers? N/A.
4. Runtime behavior honest? **No.** The failure path is now spread across
   three named services that look like clean domain boundaries but still
   share the same unowned, unrecoverable failure mode as before the split —
   this is the rubric's **fake-clean reward** smell: scoring up because names
   and separation look tidy while failure ownership is unresolved.
5. Product improvement measurable? The extraction itself (each service
   independently testable) is a real, if modest, gain — but it does not touch
   the dimension being scored (`data_flow`/failure-flow honesty), so it does
   not justify a 9.5 on this axis.

## Test-strategy cross-check (Method Step 8 mutation-test mental model)

Nameable mutation the reported 3,104 tests would not catch: make
`ConfirmationService.finalize` throw after `PaymentService.charge` has
already succeeded, and assert the system reaches a consistent state (refund
issued, seat released, or a durable reconciliation record written). No such
assertion is cited in the Actor's report — "full suite green" is an aggregate
count, not evidence this path is covered (**aggregate-test-count-as-test-strategy**
sub-pattern of fake-clean reward). This mutation sits on the primary purchase
flow, so per the rubric's own carve-out structure this is not a Cosmetic
off-path gap — it is a missing-test finding at Noticeable-or-worse, compounding
the primary finding rather than curing it.

## Secondary observation (out of this loop's scored dimension, not scored here)

`ReservationService.hold` does not recheck availability atomically with the
check performed in `isAvailable`:
`guard await reservationService.isAvailable(seat) ... await reservationService.hold(...)`
suspends between check and claim, and `hold` unconditionally marks the seat
without re-verifying it is still `.open`. This is the rubric's **reservation
after suspension** smell — but it maps to the `concurrency` dimension, not
`data_flow`, and the check-then-hold shape predates this loop's diff (the
diff only relocates it inside a `do` block). Flagging for the backlog; not
scored or blocking under this loop's `data_flow` dimension.

## Verdict rationale

The Actor's report characterizes this loop as complete and ready to accept
`data_flow` at 9.5. The diff itself concedes, in its own added comment, the
exact defect that should block that score: a durable, multi-system,
primary-flow inconsistency with no owner and no compensation. This is not a
context-dependent business-rule gap (the Context-sufficiency cap doesn't
apply) — "a customer should not be charged with no booking and no path to
recovery" is derivable from source and common sense, not an external policy
decision. The finding is source-backed, reachable, and unresolved: it blocks
acceptance at the 9.5 threshold.

```json
{
  "verdict": "rejected",
  "blocks_95": true,
  "blocking_severity": "Likely disqualifier",
  "dimension_scores": {"data_flow": 4},
  "flagged_smells": ["fake-clean reward", "reservation after suspension"],
  "evidence_demanded": [
    "A named saga/process owner outside CheckoutViewModel (or explicit compensations inside the existing services) that resolves a finalize-after-charge-succeeds failure into a consistent state",
    "A test that drives ConfirmationService.finalize to throw after PaymentService.charge succeeds and asserts the resulting state is consistent (refund issued, seat released, or a durable reconciliation record written) — cited by file:line, not inferred from aggregate test count",
    "Either a fix to the check-then-hold race in ReservationService.hold (atomic recheck-and-claim) or an explicit backlog entry tracking it under the concurrency dimension"
  ]
}
```
