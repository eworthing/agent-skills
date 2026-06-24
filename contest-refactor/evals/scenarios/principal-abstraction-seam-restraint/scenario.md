# Loop 8 — `architecture_quality` dimension

**Actor report (`loop_result`):** *"Unified time access behind a single `Clock.now()`. Removed three direct `Date()` call sites (checkout, shipping, account) that each read the system clock. One owner, DRY, and now injectable for tests. Full suite green (1,940 tests). Proposing `architecture_quality` → 9.5."*

**Test run:** `swift test` — 1,940 passed, 0 failed.

## CONTEXT.md excerpt (provided to this review)

> **§5 — Roadmap (committed, this quarter — Q4).** Region-specific notification rules go live
> (EU opt-in + audit, Region A SMS-only, Region B push-first). No other subsystems are changing
> this quarter. Timestamps are UTC system-wide with no planned regional or per-feature variation.

## Context

Time was previously read via scattered `Date()` calls. This loop introduces one owner — `Clock`
— with a single `now()` method that all call sites use. Time is uniform across the product.

## Diff

```diff
--- a/Sources/Time/Clock.swift  (new file)
+++ b/Sources/Time/Clock.swift
@@
+/// Single owner of "current time". All call sites read time through `now()`.
+protocol Clock {
+    func now() -> Date
+}
+
+struct SystemClock: Clock {
+    func now() -> Date { Date() }
+}

--- a/Sources/Checkout/CheckoutFlow.swift
+++ b/Sources/Checkout/CheckoutFlow.swift
@@
-        let placedAt = Date()
+        let placedAt = clock.now()
```

(Shipping and account flows collapse the same way.) One owner, one path, no duplicated clock
reads, and now test-injectable; the suite passes.
