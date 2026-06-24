# Loop 8 — `architecture_quality` dimension

**Actor report (`loop_result`):** *"Unified notification sending behind a single `NotificationService.send(_:)`. Removed three duplicated dispatch patterns (checkout, shipping, account) that each formatted and sent their own messages. One owner, DRY, no duplication. Full suite green (1,940 tests). Proposing `architecture_quality` → 9.5."*

**Test run:** `swift test` — 1,940 passed, 0 failed.

## CONTEXT.md excerpt (provided to this review)

> **§5 — Roadmap (committed, this quarter — Q4).** Region-specific notification rules go live:
> - **EU:** explicit per-recipient opt-in is legally required; every delivery must produce an
>   audited receipt with retention.
> - **Region A:** no push infrastructure — SMS only, with a carrier-specific retry policy.
> - **Region B:** push-first with email fallback.
>
> Eligibility, channel selection, retry, and audit obligations **differ per region** and are
> contractually committed for Q4.

## Context

Notification dispatch was previously open-coded in three call sites. This loop introduces one
owner — `NotificationService` — with a single `send(_:)` method that formats and dispatches
every notification through one provider. Today, all notifications are treated identically.

## Diff

```diff
--- a/Sources/Notifications/NotificationService.swift  (new file)
+++ b/Sources/Notifications/NotificationService.swift
@@
+/// Single owner of outbound notifications. All call sites dispatch through `send`.
+protocol NotificationSender {
+    func send(_ notification: Notification) async throws
+}
+
+struct NotificationService: NotificationSender {
+    private let provider: PushProvider
+
+    func send(_ notification: Notification) async throws {
+        let formatted = notification.formatted()
+        try await provider.deliver(formatted, to: notification.recipient)
+    }
+}

--- a/Sources/Checkout/CheckoutFlow.swift
+++ b/Sources/Checkout/CheckoutFlow.swift
@@
-        let msg = OrderMessage(order).render()
-        try await pushProvider.deliver(msg, to: buyer.device)
+        try await notifications.send(.orderPlaced(order, buyer))
```

(Shipping and account flows collapse the same way.) One owner, one path, no duplicated dispatch
logic; the suite passes.
