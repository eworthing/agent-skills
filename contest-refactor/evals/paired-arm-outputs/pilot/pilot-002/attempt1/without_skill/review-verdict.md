# Review — Loop 6, `data_flow` dimension (`PurchaseCoordinator` extraction)

## What the diff actually does

`CheckoutViewModel` previously called `ReservationService`, `PaymentService`, and
`ConfirmationService` directly and sequenced the reserve → charge → confirm saga itself.
The diff extracts that sequencing into a new `actor PurchaseCoordinator`, and
`CheckoutViewModel` now calls a single `coordinator.purchase(...)` method and handles a
typed error. On the stated goal — stop the presentation layer from owning multi-step
transactional orchestration — this is a real and correctly-targeted improvement. The
compensation logic also correctly encodes the invariant the comment states: pre-capture
failure releases the hold only; post-capture failure voids the charge *before* releasing
the hold, so the seat is never freed while a captured charge is outstanding. That ordering
is not trivial to get right and the diff gets it right.

That said, I don't think this clears a 9.5 on `data_flow` as submitted, for three
independent reasons — none of which the Actor's report acknowledges or the "3,104 passed"
test run demonstrates it addressed.

## 1. No test evidence for the new logic this loop actually introduced

The diff touches two files: the new `PurchaseCoordinator.swift` and the trimmed
`CheckoutViewModel.swift`. There is no test file in the diff. "Full suite green, 3,104
tests" tells us the refactor didn't *break* anything the existing suite already covered —
it says nothing about whether the new compensation branches are covered at all, because
before this loop those branches didn't exist as a single unit to test. Specifically
untested by anything shown here:
- charge fails → hold released, no charge to void (straightforward, but still new code)
- confirm fails, void succeeds → charge voided, then hold released
- confirm fails, void *also* fails → hold retained, first error still surfaces

That third branch is the one most likely to have a bug (it's the deepest nesting, the one
most likely to be wrong on paper), and it's the one with zero test evidence.

## 2. The void-failure branch is silently swallowed, and the comment overclaims what the code does

```swift
do {
    try await paymentService.void(chargeID: chargeID)
    await reservationService.release(seat: seat)
} catch {
    // Void failed; hold intentionally retained so seat is not resold
    // while the captured charge is outstanding.
}
```

Retaining the hold on void-failure is the right call. But the `catch` block does nothing
else — no log, no metric, no write to any reconciliation queue. The doc comment on the
type claims the confirm-failure path "surfaces for ops-level reconciliation (ADR-0031)."
It doesn't. The outer `PurchaseError.confirmationFailed` does surface the *original*
confirmation error to the UI, but the *second* failure (the void call itself failing) is
discarded with no trace. For a path that handles a captured, un-refunded charge sitting in
an inconsistent state, silently dropping that specific failure is a real gap between what
the code says it does and what it does. This is exactly the kind of code a
process-owner/saga extraction is supposed to make *more* auditable, not less.

## 3. `actor` is the wrong primitive for what this type actually needs, and it invites a false safety assumption

`PurchaseCoordinator` holds no mutable state — three `let` service references. Making it
an `actor` buys isolation for state it doesn't have, at the cost of every caller needing
`await` across an actor hop it didn't need before. That alone is a minor "wrong tool"
smell, not a blocker.

The real concern: Swift actors are *reentrant* across suspension points. Two concurrent
`purchase()` calls on the same `PurchaseCoordinator` instance can interleave at each
`await` — including between `reservationService.isAvailable(seat)` and
`reservationService.hold(seat:for:)`. Wrapping the saga in an `actor` reads, to a reviewer
skimming this diff, as "now this is safe against concurrent purchases of the same seat."
It isn't — the TOCTOU gap between availability-check and hold is preserved verbatim from
the pre-refactor code, and `actor` isolation does not close it. That gap predates this
loop, so I'm not counting it as a regression. But choosing `actor` here, in a diff whose
entire stated purpose is tightening the correctness story around a money-and-inventory
saga, without a comment acknowledging that the actor does *not* make concurrent purchases
of the same seat safe, is a real omission on a dimension (`data_flow`) that's supposed to
be judging exactly this kind of correctness.

## Bottom line

The single-owner extraction and the compensation *ordering* are genuinely good and are
the right shape for the dimension. But "full suite green" is being used as proof of
correctness for logic the full suite doesn't exercise, a failure path is silently dropped
while its doc comment claims otherwise, and the concurrency primitive chosen invites a
safety assumption the code doesn't back up. None of these say "revert this" — they say
"this isn't a 9.5 yet."

```json
{
  "verdict": "conditional",
  "blocks_95": true,
  "blocking_severity": "major — unverified correctness of new saga/compensation logic plus a silently-dropped error path in a financial transaction handler (no formal rubric severity scale was included in the provided materials, so this is a plain-language equivalent, not a quoted rubric anchor)",
  "dimension_scores": {
    "data_flow": 7.5
  },
  "flagged_smells": [
    "claim-code mismatch (doc comment asserts ops-level reconciliation surfacing that the code does not implement)",
    "silent error swallow on a payment-void failure path",
    "untested new compensation branches (especially confirm-fail + void-fail)",
    "actor chosen for a stateless type, implying reentrancy-safety it does not provide",
    "pre-existing TOCTOU race between availability check and hold, unacknowledged in the new saga's documentation"
  ],
  "evidence_demanded": [
    "unit/integration tests exercising each compensation branch: charge-fail→release, confirm-fail+void-succeed→void-then-release, confirm-fail+void-fail→hold-retained",
    "an actual log, metric, or reconciliation-queue write for the void-failure branch, matching what the doc comment claims happens",
    "either a fix for or an explicit documented acknowledgment of the actor-reentrancy gap between isAvailable and hold for concurrent purchases of the same seat",
    "the PurchaseError case definitions, to confirm Sendable-compatibility for throwing across the actor boundary under strict concurrency"
  ]
}
```
