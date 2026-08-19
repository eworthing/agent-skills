# Critic Review — Loop 6, `data_flow`

## Method walk

**Step 1 — current source only.** The diff is the source of truth here; I am not taking the Actor's report ("independently injectable and testable... Proposing `data_flow` → 9.5") at face value. I re-derive from the diff itself.

**Step 2 — map mutable runtime concerns (Authority Map).**

| Concern | Owner (writer) | Reader | Persistence seam | Async entry point |
|---|---|---|---|---|
| Seat status (`open`/`held`/`confirmed`) | `SeatInventory` via `ReservationService.hold`/`.release` (actor-isolated) | `ReservationService.isAvailable` | in-memory/`SeatInventory` | `await reservationService.hold(...)` |
| Payment capture | `PaymentGateway` via `PaymentService.charge` | n/a (fire-and-forget capture) | true-external (payment gateway) | `try await paymentService.charge(...)` |
| `Booking` record | `BookingStore` via `ConfirmationService.finalize` | n/a shown | remote-owned/local store | `try await confirmationService.finalize(...)` |
| **Saga orchestration** (the sequence itself, and any compensation) | **`CheckoutViewModel`**, a `@MainActor` presentation type | — | — | `purchaseTicket(seat:paymentMethod:)` |

Three separate durable authorities (seat inventory, external payment gateway, booking store) are written in sequence by a single caller with **no fourth owner responsible for the sequence's atomicity or recovery**. That owner is the finding.

**Step 3 — architecture review.** `ReservationService`, `PaymentService`, `ConfirmationService` are concrete actors (not protocol/port abstractions), so the Unified Seam Policy's two-adapter rule doesn't strictly gate them — wrapping `SeatInventory`/`PaymentGateway`/`BookingStore` in actors is legitimate failure/concurrency isolation (policy path (b)(ii)/(iii)). Shallow-module test: each method (`hold`, `charge`, `finalize`) is close to a one-line delegation to the wrapped dependency — Interface ≈ Implementation. That's a **Noticeable weakness** at most (thin but not harmful), not the blocking issue.

**Step 4 — ownership.** The actual writer of "does this purchase succeed as a whole" is nobody. `CheckoutViewModel.purchaseTicket` sequences three independent-authority writes and, per the diff's own added comment, explicitly does not attempt recovery when the sequence fails partway:

```swift
} catch {
    // No compensation: if charge succeeded but finalize failed,
    // the seat remains held and the card is debited with no booking record.
    presentError(.purchaseFailed(error))
}
```

This is the Evidence Chain's Source, in the diff itself, admitting the Consequence. The Actor's own change documents the defect and ships it unresolved while proposing a 9.5 for the dimension the defect belongs to.

**Step 5 — concurrency review (reservation after suspension).** `purchaseTicket` awaits `reservationService.isAvailable(seat)`, then — after synchronous `Booking` construction — awaits `reservationService.hold(seat:for:)`. `ReservationService.hold` does **not** recheck availability atomically; it unconditionally calls `inventory.mark(seat, .held, booking: booking)`. Two concurrent `purchaseTicket` calls for the same seat can each observe `isAvailable == true` before either calls `hold`, and both then mark the seat held — one booking silently overwrites seat ownership. This is exactly the canon **reservation after suspension** smell (`architecture-rubric.md`): "a check-then-claim flow that suspends between 'available' and 'claimed' is reentrant... unless the claim step rechecks and atomically claims in one actor-isolated step." `hold` does not recheck; the carve-out does not apply. On a ticket-purchase flow, double-booking a seat under contention is a realistic, primary-flow-reachable race.

**Step 6 — simplification / diff scope.** The actual code delta is nearly a no-op: the pre-existing `guard`+`do/catch` sequence was reshuffled (guard moved inside the `do` block — behaviorally inert, since the guard still returns before entering the try chain) and a comment was added. The three new actor files did not exist before this loop (per the diff's `new file` markers), so this loop is the one that dispersed the sequence across three modules while leaving the orchestration/compensation gap fully intact and now explicitly labeled. Restructuring that makes ownership look more separated while the actual cross-module write authority gets no better (and is now on record as broken) is a **fake-clean reward** pattern: new files, "independently injectable and testable" framing, and a green suite are being used to justify a top score on the dimension whose central defect the diff itself documents as unresolved.

**Meta-rule 4 (risk boundary).** This loop crosses an actor/isolation boundary by introducing three new actors. "Full suite green (3,104 tests)" is generic, single-config evidence; there is no cited concurrent-access test proving the reservation race is absent, and no cited compensation/idempotency test proving recovery behavior on partial failure. Per meta-rule 4, a fix that crosses a risk boundary needs recorded, preferably executable, evidence for that specific invariant — not an aggregate pass count.

## Severity

Matches the **Likely disqualifier** anchor on two independent counts:
1. "Durable state written from multiple places with no owner" — seat inventory, payment gateway, and booking store are three durably-written authorities with no saga owner or compensation, reachable from the primary purchase flow, and the gap is admitted in-diff.
2. "Multi-writer authority over a primary domain concern; racing async flows that can corrupt user-visible state" — the reservation-after-suspension race on seat inventory.

Either alone blocks `data_flow` (and, for the second, `concurrency`) from a 9.5 acceptance. Both present together is not a close call.

## Verdict rationale

The Actor's report should not be taken as ground truth: it claims the extraction makes each step "independently injectable and testable" and reports a green suite, but neither claim addresses the actual `data_flow` question — who owns the correctness of the sequence as a whole. The diff's own comment concedes the defect exists. This is a rejection, not a request for more evidence: the evidence needed to disqualify is already in the attached diff.

```json
{"verdict": "rejected", "blocks_95": true, "blocking_severity": "Likely disqualifier", "dimension_scores": {"data_flow": 4.0, "concurrency": 4.5}, "flagged_smells": ["reservation after suspension", "unclear ownership", "fake-clean reward"], "evidence_demanded": ["A durable saga owner (domain-layer coordinator, not CheckoutViewModel) for purchaseTicket with a persisted purchase-intent record written before charging, so a crash/timeout mid-sequence is reconcilable instead of silently stuck.", "Explicit compensating actions (refund via PaymentService, seat release via ReservationService.release) invoked when ConfirmationService.finalize fails after a successful charge, with idempotency guarantees against duplicate compensation or duplicate refund.", "ReservationService.hold must atomically recheck-and-claim inside the actor-isolated call (not rely on a prior isAvailable check across an await gap), closing the reservation-after-suspension race.", "An executable concurrency test issuing two simultaneous purchaseTicket calls for the same seat, proving only one succeeds — not just the generic 3,104-test pass count, per meta-rule 4's risk-boundary evidence requirement for newly introduced actor isolation."]}
```
