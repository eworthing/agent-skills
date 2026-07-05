# Loop 8 - `data_flow` dimension

**Actor report (`loop_result`):** *"Kept hold expiration in `HoldExpirationCoordinator` and changed the SwiftUI view to render the coordinator-owned deadline with `TimelineView`. Full suite green (1,541 tests). Proposing `data_flow` -> 9.5."*

**Test run:** `swift test` - 1,541 passed, 0 failed.

## Context

A seat hold expires after 10 minutes unless the purchase completes. `HoldExpirationCoordinator` owns the durable workflow and receives an injected `Clock` in tests. The view only displays the current remaining time.

## Diff

```diff
--- a/Sources/Checkout/HoldExpirationCoordinator.swift
+++ b/Sources/Checkout/HoldExpirationCoordinator.swift
@@
 actor HoldExpirationCoordinator {
     private let clock: any Clock<Duration>
     private let repository: SeatHoldRepository

     func scheduleExpiration(for hold: SeatHold) async {
         await clock.sleep(until: hold.expiresAt)
         await repository.expireHold(hold.id)
     }
 }

--- a/Sources/Checkout/HoldCountdownView.swift
+++ b/Sources/Checkout/HoldCountdownView.swift
@@
 struct HoldCountdownView: View {
     let hold: SeatHold

     var body: some View {
+        TimelineView(.periodic(from: .now, by: 1)) { context in
+            Text(timeString(remainingUntil: hold.expiresAt, now: context.date))
+        }
     }
 }
```

`TimelineView` is presentation-only: it redraws text from the coordinator-owned `expiresAt` deadline and never calls `expireHold`. `HoldExpirationCoordinatorTests.testExpiresHoldAfterDeadline` advances the test clock and asserts the repository state changes even with no view alive.
