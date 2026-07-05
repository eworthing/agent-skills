# Loop 7 - `concurrency` dimension

**Actor report (`loop_result`):** *"Moved the seat-hold claim into the repository transaction so the in-memory coordinator no longer mirrors database state. Pricing still happens before the transaction, but the claim is atomic. Full suite green (2,418 tests). Proposing `concurrency` -> 9.5."*

**Test run:** `swift test` - 2,418 passed, 0 failed.

## Context

Two clients can attempt to reserve the same seat at the same time. Pricing is allowed to run before the claim because pricing does not grant ownership. The durable reservation authority is `SeatHoldRepository`, which enforces a unique active hold per `seatID` inside one transaction.

## Diff

```diff
--- a/Sources/Reservations/SeatHoldCoordinator.swift
+++ b/Sources/Reservations/SeatHoldCoordinator.swift
@@
 actor SeatHoldCoordinator {
-    private var heldSeats: Set<SeatID> = []
     private let pricing: PricingService
     private let repository: SeatHoldRepository

     func reserve(seatID: SeatID, buyerID: UserID) async throws -> SeatHold {
-        guard !heldSeats.contains(seatID) else {
-            throw ReservationError.alreadyHeld
-        }
         let price = try await pricing.quote(seatID: seatID, buyerID: buyerID)
-        heldSeats.insert(seatID)
-        let hold = SeatHold(seatID: seatID, buyerID: buyerID, price: price)
-        try await repository.save(hold)
-        return hold
+        return try await repository.withTransaction { transaction in
+            guard try transaction.activeHold(for: seatID) == nil else {
+                throw ReservationError.alreadyHeld
+            }
+            let hold = SeatHold(seatID: seatID, buyerID: buyerID, price: price)
+            try transaction.insertActiveHold(hold)
+            return hold
+        }
     }
 }
```

`SeatHoldRepository.withTransaction` runs on the database writer queue. `insertActiveHold` also hits a unique index on active `seatID` rows, so the check and claim are one authority even when pricing suspends before the transaction begins. The concurrent same-seat test asserts that one call succeeds and the other receives `alreadyHeld`.
