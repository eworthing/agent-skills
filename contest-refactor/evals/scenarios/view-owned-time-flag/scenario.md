# Loop 8 - `data_flow` dimension

**Actor report (`loop_result`):** *"Simplified hold expiration by moving the countdown into `HoldCountdownView`. The view now owns the timer and calls the checkout client when time runs out. Full suite green (1,541 tests). Proposing `data_flow` -> 9.5."*

**Test run:** `swift test` - 1,541 passed, 0 failed.

## Context

A seat hold expires after 10 minutes unless the purchase completes. Expiration is a domain workflow: when time runs out, the hold must be released so the seat can be sold to someone else.

## Diff

```diff
--- a/Sources/Checkout/HoldCountdownView.swift
+++ b/Sources/Checkout/HoldCountdownView.swift
@@
 struct HoldCountdownView: View {
     let hold: SeatHold
     let checkoutClient: CheckoutClient
+    @State private var secondsRemaining = 600

     var body: some View {
         Text(timeString(secondsRemaining))
+            .task(id: hold.id) {
+                while secondsRemaining > 0 {
+                    try? await Task.sleep(for: .seconds(1))
+                    secondsRemaining -= 1
+                }
+                await checkoutClient.expireHold(hold.id)
+            }
     }
 }
```

The view lifecycle now owns the durable expiration clock. Dismissing the view, navigating away, or SwiftUI recreating the task can cancel or restart the timer; the domain has no independent owner for releasing the hold. Tests cover the rendered countdown text only, not expiration when the view disappears.
