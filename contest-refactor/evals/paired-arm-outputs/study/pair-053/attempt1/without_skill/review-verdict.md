## Review: Loop 6 — `data_flow` dimension

### What the Actor claims vs. what the diff shows

The Actor's report frames this as a clean extraction: three "independently injectable and testable"
services, full suite green (3,104 tests), proposing `data_flow` → 9.5. The diff itself tells a
different story. The three services (`ReservationService`, `PaymentService`, `ConfirmationService`)
are legitimate encapsulation — each owns one write, each is now an `actor`, each has a narrow
interface. That part of the extraction is fine and is not what's being scored down here.

What actually determines the `data_flow` score is *who owns the sequencing of the three writes and
what happens when the sequence fails partway through* — and that is exactly where this diff falls
short, by its own admission.

### The defect

`CheckoutViewModel.purchaseTicket` still sequences three ordered, cross-module, durable-effect
writes:

1. hold seat (in-memory/domain state)
2. charge card (**external, already-captured, not reversible by simply "not committing"**)
3. write `Booking` record + release hold to `confirmed`

The only change to this method is cosmetic: the `guard` moved inside the `do` block, and a comment
was added. The comment is the tell:

```swift
} catch {
    // No compensation: if charge succeeded but finalize failed,
    // the seat remains held and the card is debited with no booking record.
    presentError(.purchaseFailed(error))
}
```

The Actor's own diff documents the exact failure mode — payment gateway charge succeeds,
`ConfirmationService.finalize` throws (DB timeout is the given example), and the system is left in
an inconsistent state: money taken, no `Booking` record, seat stuck in `held` forever with no
process to reconcile or release it. The diff *names* this defect in a code comment and then ships it
unresolved. That is not a `data_flow` score of 9.5 material — it's an open, acknowledged data
consistency bug wearing a refactor's clothing.

Two compounding structural problems:

- **Wrong authority for the orchestration.** `CheckoutViewModel` is `@MainActor`,
  presentation-layer, `ObservableObject`. It is now the sole owner of a three-step saga with a
  non-idempotent, externally-visible side effect (the payment capture). Splitting the steps into
  actors did not move the *sequencing and failure-recovery* responsibility anywhere more
  appropriate — it stayed in the view model, which is the wrong layer to own compensating-action
  logic for a financial transaction. A saga needs a single owner with a defined compensation path
  (release hold + refund/void on downstream failure, or an idempotent retry/outbox for finalize);
  none of the three new services, nor the view model, provide one.
- **No idempotency guard on the charge.** Nothing in `PaymentService.charge` or its caller prevents
  a second charge attempt on retry (whether a user retry after seeing `purchaseFailed`, or any
  future automated retry). Given the confirmed failure mode already produces a charged-but-unbooked
  state, a naive retry path doubles the customer's charge. This isn't hypothetical — it's the
  direct next consequence of the state the diff's own comment describes.

### On "3,104 tests, 0 failed"

The green suite is not evidence against this defect — it's evidence the defect isn't tested. There
is no test in the diff (or referenced by the Actor) that exercises "charge succeeds, finalize
throws" and asserts *any* outcome — compensation, reconciliation record, or even a distinguishable
error state. A green suite that doesn't touch the one failure interaction the diff's own comment
calls out is not proof of correctness for this dimension; it's proof the interaction is untested.

### Verdict

This does not clear `data_flow` at the 9.5 bar. The extraction into `ReservationService` /
`PaymentService` / `ConfirmationService` is a reasonable module boundary, but the loop's actual
`data_flow` question — how ordered, cross-module writes with an irreversible external side effect
behave under partial failure — is left exactly where it was before the refactor, and is now
self-documented as broken rather than fixed. A comment acknowledging data corruption is not a
mitigation.

I'm marking this conditional rather than a flat rejection only in the sense that the service
extraction itself is worth keeping — but the loop cannot be accepted at 9.5 on `data_flow`, and
should not be accepted at a materially lower number either without a concrete remediation plan,
because "known, uncompensated, money-losing failure mode" is a blocking-severity finding on this
dimension, not a minor deduction.

```json
{"verdict": "rejected", "blocks_95": true, "blocking_severity": "critical: unrecoverable data/financial inconsistency on partial failure (charge captured, no compensating rollback or reconciliation path; not covered by any test)", "dimension_scores": {"data_flow": 4}, "flagged_smells": ["saga without compensating transaction", "presentation layer owns durable-side-effect orchestration", "non-idempotent payment charge on a path with a known retry/failure interaction", "self-acknowledged defect shipped via comment instead of fix", "green suite does not cover the failure path the diff itself documents"], "evidence_demanded": ["a test that drives PaymentService.charge to succeed and ConfirmationService.finalize to throw, asserting a defined recovery outcome (compensating refund/void, seat release, or a durable reconciliation record — not just presentError)", "an explicit owner for the purchase saga outside the presentation layer (e.g., a domain/application-level orchestrator or state machine) with a documented compensation or retry-safe design", "an idempotency mechanism (idempotency key or equivalent) on PaymentService.charge so a retried purchase attempt cannot double-charge", "a defined resolution path for seats left in `held` after a finalize failure (timeout-based release, manual ops queue, or equivalent) rather than indefinite hold"]}
```
