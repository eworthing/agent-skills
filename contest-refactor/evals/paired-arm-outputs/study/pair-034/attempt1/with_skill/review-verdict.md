# Critic Review — Loop 6, `data_flow` dimension

## Step 1 — Inspect current code (independent of Actor's report)

The Actor's report claims the extraction of `ReservationService`, `PaymentService`, and `ConfirmationService` makes each "independently injectable and testable," cites a green 3,104-test suite, and proposes `data_flow` → 9.5. I re-derive the score from current source rather than accepting that framing.

Reading the diff: `CheckoutViewModel.purchaseTicket` still performs the full three-step sequence — `hold` → `charge` → `finalize` — as a single unbroken chain of awaits, with a bare `catch` that only calls `presentError`. Critically, this is not a new defect this loop introduced; the pre-refactor code (the `-` lines) already lacked compensation. What this loop actually changed is: (1) split three previously-inline operations into three separate `actor` types, and (2) moved the `guard isAvailable` check inside the `do` block. Per Step 1's "inspect current code only" rule, I score current state regardless of when the defect was introduced — and the loop's own report claims a 9.5 for `data_flow` based on work that left the dimension's central defect completely untouched.

## Step 2 — Map mutable runtime concerns (Authority Map)

| Concern | Owner | Writers | Durable side effect |
|---|---|---|---|
| Seat status (`open`/`held`/`confirmed`) | `SeatInventory` via `ReservationService` | `hold`, `release` (never called on the failure path) | Yes — persists indefinitely once `held` |
| Payment capture | External gateway via `PaymentService.charge` | `gateway.capture` | Yes — irreversible without a separate void/refund call, none exists |
| `Booking` record | `BookingStore` via `ConfirmationService.finalize` | `insert` | Yes |
| **The saga itself** (ordering + compensation across the above three) | **None** | `CheckoutViewModel.purchaseTicket` sequences the calls but owns no recovery authority | — |

The three per-resource writers are each cleanly actor-isolated with a single owner. But the *composite* concern — "has this purchase attempt left the system consistent" — has no owner at all. `CheckoutViewModel` is a `@MainActor` presentation type: transient, recreated on navigation, and not a place where a durable saga with financial side effects belongs. This is stated almost verbatim in the scenario's own Context section, and the shipped code even carries a comment admitting it: *"No compensation: if charge succeeded but finalize failed, the seat remains held and the card is debited with no booking record."* The defect is not hidden from the codebase — it is hidden from the Actor's report, which omits it entirely while proposing a 9.5.

## Step 3 — Architecture / Deletion test (secondary observation)

Each new actor is close to a pass-through: `ReservationService.hold` is one line (`inventory.mark(...)`), `PaymentService.charge` is one line (`gateway.capture(...)`), `ConfirmationService.finalize` is one line (`bookingStore.insert(...)`). Applying the deletion test: if these three actors were deleted and inlined, no complexity would reappear at any other caller — each is single-call-site. That is not disqualifying by itself (actor isolation around I/O boundaries is a legitimate reason for a thin wrapper), but it reinforces the main finding: the refactor added three files of ceremony around the *uninteresting* part of this flow (single-resource writes) while leaving the *interesting* part — cross-resource sequencing and failure recovery — exactly where it was, now scored as if it had been fixed.

## Step 5 — Concurrency note (out of scope for this dimension, flagged as smoke only)

`isAvailable` and `hold` are two separate actor-isolated calls with a synchronous `Booking(...)` construction between them and no re-check inside `hold`. That is a "reservation after suspension" shape (maps to `concurrency`, not `data_flow`) and pre-dates this loop's diff. Not scored here, but it compounds the same root problem: no atomic authority over the purchase sequence.

## Step 8 — Test-absence check

The Actor's report cites only an aggregate pass count (3,104/3,104) as evidence `data_flow` is sound. Per the Authority-Map cross-check and mutation-test mental model: naming one path current tests would not catch — `PaymentService.charge` succeeds, then `ConfirmationService.finalize` throws — and no evidence exists that any of the 3,104 tests exercises this partial-failure branch (no compensation code exists to exercise, and none is cited). Central mutable runtime behavior (a financial transaction with durable side effects) with no test on its failure path, on the primary purchase flow, is exactly the case the severity anchors call out by name: *"test absence around central mutable runtime behavior with realistic regression risk."* Citing aggregate test count as strategy here is the canon `aggregate-test-count-as-test-strategy` sub-pattern of fake-clean reward.

## Verdict

**Claim:** The checkout saga (reserve → charge → confirm) has no owner with recovery authority; it is sequenced in `CheckoutViewModel`, a presentation-layer type, with no compensating transaction on partial failure.

**Source:** `Sources/Presentation/CheckoutViewModel.swift`, `purchaseTicket(seat:paymentMethod:)` — the `catch` block's own comment: *"No compensation: if charge succeeded but finalize failed, the seat remains held and the card is debited with no booking record."* `ReservationService.hold`/`release` (Sources/Domain/ReservationService.swift) — `release` is never invoked from the failure path. `PaymentService` (Sources/Infrastructure/PaymentService.swift) exposes no void/refund capability at all.

**Consequence:** A transient failure (e.g., a DB timeout) after payment capture — on the primary "buy a ticket" flow — leaves the customer charged with no `Booking` record and no seat, and leaves the seat permanently `held`, blocking every other buyer from ever purchasing it. This is a live, reachable, financially-harmful inconsistency on a primary user flow, not a theoretical edge case. It meets the rubric's **Likely disqualifier** anchor verbatim: *"a core architectural property... broken at runtime AND the harm is reachable from a primary user flow."*

**Remedy:** Give the saga a durable owner outside the presentation layer — an application/domain-level coordinator (not a "Coordinator" pattern for its own sake; the smallest honest fix is putting the existing three `await` calls plus explicit compensation under one non-presentation authority) that, on `finalize` failure after `charge` succeeds, durably enqueues a refund/void through `PaymentService` and calls `reservationService.release(seat:)` — durable meaning it survives the view model being deallocated or the app being backgrounded, not merely a `catch` block that shows an error and stops. Add a test that drives exactly this branch (charge succeeds, finalize throws) and asserts the seat is released and a compensating refund is issued.

This is not a case of a clean extraction with one remaining rough edge — the extraction touched none of the actual data-flow problem it was scored against. The Actor's report is silent about a defect its own diff comments on, and backs the 9.5 claim with an aggregate test count that provides no coverage of the failure path in question.

```json
{"verdict": "rejected", "blocks_95": true, "blocking_severity": "Likely disqualifier", "dimension_scores": {"data_flow": 3.5}, "flagged_smells": ["Fake simplification", "Fake-clean reward", "unclear ownership", "temporal coupling"], "evidence_demanded": ["A durable, non-presentation-layer owner for the reserve→charge→confirm saga with an explicit compensation path", "A compensating action on finalize failure after charge succeeds: refund/void via PaymentService and reservationService.release(seat:), surviving view-model deallocation", "A test exercising PaymentService.charge succeeding followed by ConfirmationService.finalize throwing, asserting seat release and refund/void, cited by file and assertion range — not inferred from aggregate pass count", "A lease/expiry mechanism for held seats, or evidence one already exists, since release() is never called on the failure path shown"]}
```
