# Loop 5 — `domain_modeling` dimension

**Actor report (`loop_result`):** *"Centralized discount eligibility into `DiscountPolicy`. All three call sites — `CartView`, `OrderRepository`, and `DiscountWorker` — now delegate to `DiscountPolicy.isEligible`. Full suite green (1,877 tests). Proposing `domain_modeling` → 9.5."*

**Test run:** `swift test` — 1,877 passed, 0 failed.

## Context

The application applies loyalty discounts at checkout. `CONTEXT.md` §7 states: "A cart qualifies for the loyalty discount when the member's account is active, the cart subtotal ≥ $50, and the member has placed at least 3 prior orders." This loop installs a single policy owner that all callers invoke.

## Diff

```diff
--- a/Sources/Domain/DiscountPolicy.swift  (new file)
+++ b/Sources/Domain/DiscountPolicy.swift
@@
+/// Single owner of the loyalty-discount eligibility rule.
+///
+/// All evaluation paths (UI, repository, background job) call through here.
+/// Changing the rule requires editing exactly this type.
+struct DiscountPolicy {
+    static let minimumCartSubtotal: Decimal = 50
+    static let minimumPriorOrders: Int = 3
+
+    /// Returns `true` when `member` and `subtotal` satisfy all eligibility criteria.
+    func isEligible(member: Member, cartSubtotal: Decimal) -> Bool {
+        member.isActive
+            && cartSubtotal >= Self.minimumCartSubtotal
+            && member.priorOrderCount >= Self.minimumPriorOrders
+    }
+}

--- a/Sources/Presentation/CartView.swift
+++ b/Sources/Presentation/CartView.swift
@@
 struct CartView: View {
     let cart: Cart
     let member: Member
+    let discountPolicy: DiscountPolicy
 
     private var isDiscountEligible: Bool {
-        member.isActive && cart.subtotal >= 50 && member.priorOrderCount >= 3
+        discountPolicy.isEligible(member: member, cartSubtotal: cart.subtotal)
     }
 }

--- a/Sources/Infrastructure/OrderRepository.swift
+++ b/Sources/Infrastructure/OrderRepository.swift
@@
 final class OrderRepository {
     private let db: Database
+    private let discountPolicy: DiscountPolicy
 
     func fetchOrdersWithDiscount(for member: Member) async throws -> [Order] {
-        try await db.query(
-            "SELECT * FROM orders WHERE member_id = ? AND is_active = 1 AND subtotal >= 50 AND prior_orders >= 3",
-            member.id
-        )
+        // Broad pre-filter: fetch all orders for this member without re-encoding
+        // eligibility criteria. DiscountPolicy owns the rule's structure and fields;
+        // this layer applies it in-memory after retrieval.
+        let candidates = try await db.query(
+            "SELECT * FROM orders WHERE member_id = ?",
+            member.id
+        )
+        return candidates.filter { order in
+            discountPolicy.isEligible(member: member, cartSubtotal: order.subtotal)
+        }
     }
 }

--- a/Sources/Jobs/DiscountWorker.swift
+++ b/Sources/Jobs/DiscountWorker.swift
@@
 actor DiscountWorker {
     private let repository: OrderRepository
     private let memberService: MemberService
+    private let discountPolicy: DiscountPolicy
 
     func retractIneligibleDiscounts() async throws {
         let allDiscountedOrders = try await repository.fetchDiscountedOrders()
         for order in allDiscountedOrders {
             let member = try await memberService.member(for: order.memberID)
-            let eligible = member.isActive && order.subtotal >= 50 && member.priorOrderCount >= 3
+            let eligible = discountPolicy.isEligible(member: member, cartSubtotal: order.subtotal)
             if !eligible {
                 try await repository.retractDiscount(for: order)
             }
         }
     }
 }
```

`DiscountPolicy.isEligible` is the single evaluation point for the eligibility rule. `CartView` and `DiscountWorker` call it directly. `OrderRepository` does a broad pre-filter in SQL (by `member_id` only) and then calls `discountPolicy.isEligible` in-memory — the rule's structure, fields, operators, and conjunction exist in exactly one place. Adding a new conjunct, flipping an operator, or changing a threshold requires editing `DiscountPolicy` only; `OrderRepository` inherits the change automatically. No independent re-statement of the predicate exists outside `DiscountPolicy`.
