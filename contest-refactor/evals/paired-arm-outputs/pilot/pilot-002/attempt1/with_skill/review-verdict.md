# Critic Review — Loop 6, `data_flow`

## What the loop got right

The extraction itself passes the structural tests I'm required to run before crediting anything:

- **Deletion test**: delete `PurchaseCoordinator` and the reserve/charge/confirm sequencing plus its compensation logic reappears verbatim in `CheckoutViewModel` (it lived there before this diff). The Module earns its keep.
- **Shallow-module test**: `purchase(seat:paymentMethod:buyer:)`'s Interface (one method, one typed throw) is much smaller than its Implementation (three ordered writes, two distinct compensation branches). Deep, not shallow.
- **Costume-layer check**: this isn't a sidecar or a protocol-soup wrapper — `CheckoutViewModel` now holds no saga logic and calls through a single owner. Genuine ownership consolidation, not a fake-clean rename.
- **Real improvement over the prior state**: the pre-diff `CheckoutViewModel.purchaseTicket` had *no* compensation at all — any failure after `hold()` left the seat permanently held and, on a post-charge failure, left the buyer's charge captured forever with no comment even acknowledging it. The new coordinator's pre-capture path (charge fails → release hold) and its confirm-fails-void-succeeds path (void, then release) are both correct and are real progress.

So the core claim — "single process owner, presentation calls through it" — holds up. I did not just take the Actor's report on the word "full suite green (3,104 tests)"; that count is Actor-cited aggregate coverage with no test file or assertion named against this specific Interface, which the rubric treats as evidence to investigate, not evidence of correctness (canon: *aggregate-test-count-as-test-strategy* sub-pattern of fake-clean reward). I looked at the failure-branch code directly rather than accepting "full suite green" as proof the compensation logic is honest.

## What blocks 9.5

**The double-failure branch silently drops the one signal the file's own doc comment promises exists.**

```swift
do {
    try await paymentService.void(chargeID: chargeID)
    await reservationService.release(seat: seat)
} catch {
    // Void failed; hold intentionally retained so seat is not resold
    // while the captured charge is outstanding.
}
throw PurchaseError.confirmationFailed(booking: booking, underlyingError: error)
```

`Sources/Domain/PurchaseCoordinator.swift`, the inner `catch` (diff lines ~58-61): the block body is a comment, nothing else. The void error is captured into the catch's implicit `error` and then never read — not logged, not attached to any thrown value, not passed to any reconciliation seam. Immediately after, the method unconditionally throws `PurchaseError.confirmationFailed(booking: booking, underlyingError: error)` — and because Swift scopes a bare `catch { }`'s implicit `error` to that block, the `error` in the `throw` statement resolves to the **outer** catch's variable (the original `confirmationService.finalize` failure), not the void failure. The void failure is gone the instant that inner catch block ends.

That contradicts the type's own header doc, which is the loop's stated design intent:

> "Confirm failed after capture → void the charge first, then release the hold... If the void itself fails, the hold stays and **the error surfaces for ops-level reconciliation (ADR-0031)**."

Nothing in the diff surfaces it. There is no logging call, no telemetry emit, no distinct `PurchaseError` case, no write to any reconciliation queue. "The error surfaces" is asserted in prose and contradicted by the code directly beneath it — this is the canon **Fake simplification** smell ("shorter code that hides... failure behavior"): the catch block is short precisely because it discards the one piece of information the comment claims it preserves.

**Why this matters for data_flow specifically, and why it's not cosmetic:** the double-failure case (confirm fails *and* the compensating void fails) is the worst state this saga can land in — buyer's charge is captured, no `Booking` was persisted, and the seat hold is retained. That's exactly the state `PurchaseCoordinator` exists to prevent or at least make visible. But from `CheckoutViewModel`'s side, this case is observationally identical to the safe case (confirm failed, void succeeded, hold released): both throw `PurchaseError.confirmationFailed`, and the view model's catch does undifferentiated `presentError(.purchaseFailed(error))`. There is no way for anything downstream — UI, logs, or an eventual ops reconciliation job — to tell "money is stuck, nobody's looking" apart from "handled cleanly." A gateway blip during `void` (the realistic trigger — the same class of transient failure that can hit `charge` or `finalize`) silently produces an untracked captured payment. This is squarely a primary-flow hazard (ticket purchase is the domain's core transaction) in money-handling code, and it directly falsifies the loop's own headline claim of owning "the compensating rollback path."

I'm treating this as `Likely disqualifier`, not merely `Serious deduction`: the property broken ("the compensating rollback path is honest and its failures are observable") is exactly the property this loop was created to deliver, the harm sits on the primary purchase flow, and the doc comment actively misrepresents what the code does — which is the meta-rule 6 violation ("Honesty beats polish") in its most direct form: don't score up because a comment and a method name suggest correctness that the branch itself doesn't have.

## Secondary observation (not scored against `data_flow`, flagged for backlog)

`purchase()` opens with:

```swift
guard await reservationService.isAvailable(seat) else { throw ... }
...
await reservationService.hold(seat: seat, for: booking)
```

This is the shape of the canon *reservation after suspension* smell — check availability, suspend on `await`, then claim afterward, with a task-switch window in between where a second purchase of the same seat could pass the same `isAvailable` check. This pattern predates this loop's diff (it was already in `CheckoutViewModel` verbatim) and I don't have `ReservationService`'s source, so I can't confirm or rule out the carve-out (that `hold` itself does an atomic recheck-and-claim). I'm not scoring this against `data_flow` — the rubric maps this smell to `concurrency`, a dimension this loop didn't touch and materials don't provide source for. Flagging as smoke for whichever loop scores `concurrency`.

## Verdict

Reject the 9.5 claim for `data_flow`. The saga-ownership consolidation is real and should bank the improvement over the prior no-compensation state, but the confirm+void double-failure branch's silently-dropped error — contradicting the type's own documented guarantee — is a source-backed, primary-flow, money-handling defect that a 9.5 acceptance cannot stand next to. Smallest honest fix: capture the void error in the inner catch and either add a distinct `PurchaseError` case (e.g. `confirmationAndVoidFailed(booking:confirmError:voidError:)`) or route it through whatever concrete mechanism ADR-0031 specifies, before the `throw` — and add a test that fails both `confirmationService.finalize` and `paymentService.void` in the same call and asserts the distinguishing signal actually fires.

```json
{
  "verdict": "rejected",
  "blocks_95": true,
  "blocking_severity": "Likely disqualifier",
  "dimension_scores": {"data_flow": 7.0},
  "flagged_smells": ["Fake simplification", "reservation after suspension"],
  "evidence_demanded": [
    "Test file + test name exercising PurchaseCoordinator.purchase's confirm-fails path where paymentService.void ALSO throws, asserting some distinguishing signal (log/telemetry/error case) fires, not merely that the hold is retained",
    "Concrete implementation or citation of the ADR-0031 reconciliation mechanism the doc comment claims 'the error surfaces' to — a log call, telemetry emit, queue write, or distinct thrown error case, not just the retained hold",
    "ReservationService.hold's source, to confirm whether it performs an atomic recheck-and-claim (satisfying the reservation-after-suspension carve-out) or whether the isAvailable/hold split is genuinely reentrant"
  ]
}
```
