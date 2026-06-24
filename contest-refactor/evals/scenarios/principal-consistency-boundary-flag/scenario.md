# Loop 7 — `data_flow` dimension

**Actor report (`loop_result`):** *"Hardened order placement: the order insert and the inventory decrement now commit together in one `Database.transaction`, so an order can never exist without its inventory having been decremented. Eliminated a latent partial-write window. Full suite green (2,488 tests). Proposing `data_flow` → 9.5."*

**Test run:** `swift test` — 2,488 passed, 0 failed.

## CONTEXT.md excerpt (provided to this review)

> **§4 — Roadmap (committed, next quarter).** Inventory moves out of the core database into a
> dedicated `InventoryService` with its own datastore, to absorb a planned ~50× write-volume
> spike from the new flash-sale feature. Orders remain in the core database.
>
> **§6 — Consistency requirements.** Order placement must never oversell. Inventory counts *may
> lag by a few seconds* under load, provided oversell is still prevented.

## Context

`OrderService` is the single, unambiguous owner of order placement. Before this loop the order
insert and the inventory decrement were two sequential writes with a partial-failure window.
This loop wraps both in one local ACID transaction.

## Diff

```diff
--- a/Sources/Domain/OrderService.swift
+++ b/Sources/Domain/OrderService.swift
@@
 final class OrderService {
     private let db: Database

     func placeOrder(_ cart: Cart, for buyer: Buyer) async throws -> Order {
-        let order = try await db.insert(Order(cart: cart, buyer: buyer))
-        try await db.decrementInventory(for: cart.items)
-        return order
+        try await db.transaction { tx in
+            let order = try tx.insert(Order(cart: cart, buyer: buyer))
+            try tx.decrementInventory(for: cart.items)
+            return order
+        }
     }
 }
```

The two writes are now strongly consistent in a single ACID transaction. One owner, no
multi-writer ambiguity, no partial-write window; the suite passes. Both `Order` and the
inventory rows currently live in the same `Database`.
