# Critic Review — Loop 6, `data_flow` dimension

## Scope note

Applying `method.md`'s Evidence Chain (Claim → Source → Consequence → Remedy) and
`architecture-rubric.md`'s Severity Anchors / Vocabulary to the diff and context in
`scenario.md`. The Actor's report and green suite (3,104 tests) are inputs to
investigate, not a verdict (Meta-Rule 1: "Metrics support judgment; they never decide
it"). I re-derived the assessment from the diff and context rather than accepting the
Actor's "Proposing `data_flow` → 9.5" framing at face value (Step 1: inspect current
code only).

## What the loop actually did

The mechanical part of the extraction is fine: `ReservationService`, `PaymentService`,
and `ConfirmationService` are cleanly separated actors with distinct, non-overlapping
responsibilities (the naming-consistency audit does not flag this cluster — the three
`*Service` names are not fuzzy/overlapping, each owns a distinct concern). The
`CheckoutViewModel` diff itself is functionally inert: moving the availability `guard`
from before the `do` block to inside it changes nothing (`return` inside `do` still
exits normally, doesn't route through `catch`). The only substantive addition in
`CheckoutViewModel` is a code comment disclosing a known gap. That disclosure is the
tell — the Actor's report claims "Full suite green... Proposing `data_flow` → 9.5"
while the diff's own comment admits the defect it's scoring past.

## Finding 1 — No owner for the cross-module write sequence (Likely disqualifier)

**Claim.** `CheckoutViewModel.purchaseTicket` sequences three durable, cross-module
writes (hold seat → charge card → write booking record) with no process that owns the
combined invariant "all three durable effects land, or none do / are compensated."
Each of `ReservationService`, `PaymentService`, `ConfirmationService` correctly owns
its own internal state, but the *multi-step* consistency invariant across all three has
no owner anywhere in the diff.

**Source.** `Sources/Presentation/CheckoutViewModel.swift`, `purchaseTicket(seat:paymentMethod:)`:
```swift
try await paymentService.charge(amount: seat.price, to: paymentMethod)
try await confirmationService.finalize(booking: booking)
presentConfirmation(booking)
} catch {
    // No compensation: if charge succeeded but finalize failed,
    // the seat remains held and the card is debited with no booking record.
    presentError(.purchaseFailed(error))
}
```
The `catch` block's only action is `presentError` — it performs no refund, no seat
release, no reconciliation write, and no durable record of the ambiguous state. This
is the exact scenario described in `scenario.md`'s Context section: `PaymentService.charge`
captures funds from an external gateway (an irreversible, true-external side effect)
before `ConfirmationService.finalize` durably records the booking; a DB timeout on
`finalize` after a successful charge is entirely plausible in production.

**Consequence.** This is reachable on the primary user flow (ticket purchase is the
revenue-critical path this whole module exists for), and the harm is real financial +
state corruption: the customer is charged, receives no confirmation, and the seat sits
in `held` state indefinitely — visible to the user as a paid-for-nothing failure and
to the business as an unreleased seat inventory leak, with no code path that ever
resolves it. Per the Severity Anchors, this matches the "Likely disqualifier" anchor
almost verbatim: *"durable state written from multiple places with no owner"* —
except it's worse, because there isn't even a rollback path once the state diverges,
just a `presentError` that swallows the failure. The `catch` block *reads* as handled
error recovery (Fake simplification: shorter code that presents as honest failure
handling while hiding that the failure is actually unrecoverable) — a reviewer
skimming the diff would see a `do/catch` and assume the failure path is closed. It
is not.

**Remedy.** The compensation/saga owner does not belong in `CheckoutViewModel`
(presentation layer, `@MainActor ObservableObject` — not a durable-side-effect
authority). Smallest honest fix: a domain-layer orchestrator (or one of the existing
actors, e.g. `ConfirmationService`, extended to own the compensating path) that on
`finalize` failure invokes `paymentService.refund(...)` and
`reservationService.release(seat:)` before surfacing the error, with the compensation
attempt itself durably logged so an irrecoverable failure (refund *also* fails) leaves
an auditable trail rather than silent inconsistency. This is not "add a Coordinator for
ceremony's sake" (which would fail the Simplify Pressure Test) — friction is proven by
the concrete reachable defect above, not speculative future need.

## Finding 2 — Reservation after suspension in `ReservationService` (Likely disqualifier)

**Claim.** The check-then-claim pattern across `isAvailable(_:)` and `hold(seat:for:)`
is reentrant: two concurrent `purchaseTicket` calls for the same seat can both pass
the availability check before either claims the hold, because the check and the claim
are two separate actor-isolated calls with an awaited gap between them, and `hold`
does not recheck status before marking the seat held.

**Source.** `Sources/Domain/ReservationService.swift` (new file this loop):
```swift
actor ReservationService {
    private var inventory: SeatInventory
    func isAvailable(_ seat: Seat) -> Bool { inventory.status(of: seat) == .open }
    func hold(seat: Seat, for booking: Booking) { inventory.mark(seat, .held, booking: booking) }
    ...
}
```
called from `CheckoutViewModel` as two independent `await`ed hops:
```swift
guard await reservationService.isAvailable(seat) else { ... }
...
await reservationService.hold(seat: seat, for: booking)
```
`hold` unconditionally calls `inventory.mark(seat, .held, booking:)` — it does not
verify `inventory.status(of: seat) == .open` before writing. Between the `isAvailable`
hop returning and the `hold` hop being scheduled, the actor can interleave another
task's `isAvailable`/`hold` pair for the same seat (this is exactly the canon
"Reservation after suspension" smell, and the stated carve-out — "the actual authority
rechecks and atomically claims in one transactional/actor-isolated/unique-constraint
step" — does not apply, because `hold` performs no recheck).

**Consequence.** Two buyers can both observe `isAvailable == true`, both proceed to
`hold`, both go on to `paymentService.charge` (both cards get charged), and only the
last `hold` call wins in `SeatInventory` — the other flow's local `booking` reference
is now stale relative to inventory truth, yet that flow still calls
`confirmationService.finalize(booking:)` for a seat it no longer legitimately holds.
This is a double-booking / duplicate-charge race on the exact primary flow this loop
touched, matching the Severity Anchors' own disqualifier example verbatim: *"racing
async flows that can corrupt user-visible state."* Splitting this logic into a
separate `actor` this loop is what introduces the cross-hop suspension window — code
that ran synchronously on one actor before now has an interleaving gap it didn't
necessarily have previously, so this is a defect newly exposed (if not newly created)
by this loop's own module-boundary change, squarely in scope for this review.

**Remedy.** Fuse check-and-claim into one atomic actor-isolated call: replace the
`isAvailable` / `hold` pair with a single `ReservationService.reserve(seat:for:) throws`
that checks `status(of: seat) == .open` and marks it held inside one non-suspending
actor method body, throwing `.seatUnavailable` on failure. Delete the separate
`isAvailable` call from the caller.

## On the green test suite

3,104 passing tests is not evidence against either finding (Meta-Rule 4: "A green
single-config test run does not prove preservation of every invariant: a data race
passes nondeterministically"). Neither defect is exercised by an ordinary sequential
test: Finding 1 requires injecting a `finalize` failure *after* a successful `charge`
and asserting compensation occurs — no such test is evidenced. Finding 2 requires two
concurrent `purchaseTicket` invocations racing for the same seat — no such test is
evidenced. Citing aggregate pass count in support of a `data_flow` → 9.5 proposal
without either test is the canon "aggregate-test-count-as-test-strategy" sub-pattern
of fake-clean reward.

## Verdict

Both findings are source-backed (current diff, not speculation), reachable from the
primary purchase flow, and match the rubric's own "Likely disqualifier" anchor
language directly. The `data_flow` dimension cannot be certified at 9.5 with an
unowned, uncompensated multi-write failure mode sitting in the exact code this loop
touched. Reject the Actor's proposed score; both findings need a fix (or an explicit,
justified deferral with compensating evidence) before this dimension is re-scored.

```json
{
  "verdict": "rejected",
  "blocks_95": true,
  "blocking_severity": "likely disqualifier",
  "dimension_scores": {
    "data_flow": 3.0
  },
  "flagged_smells": [
    "fake simplification",
    "reservation after suspension"
  ],
  "evidence_demanded": [
    "A compensating-action owner (domain layer, not CheckoutViewModel) that on ConfirmationService.finalize failure after a successful PaymentService.charge refunds the charge and releases the seat hold, with the compensation attempt durably logged.",
    "A regression test that forces ConfirmationService.finalize to throw after PaymentService.charge succeeds and asserts the seat is released and the charge is refunded (or the ambiguous state is durably recorded for reconciliation) rather than silently swallowed by presentError.",
    "ReservationService.isAvailable and .hold fused into one atomic, non-suspending actor-isolated claim (e.g. reserve(seat:for:) throws) that rechecks status inside the same call that marks the seat held.",
    "A concurrency regression test issuing two concurrent purchaseTicket calls for the same seat and asserting exactly one succeeds and one receives .seatUnavailable."
  ]
}
```
