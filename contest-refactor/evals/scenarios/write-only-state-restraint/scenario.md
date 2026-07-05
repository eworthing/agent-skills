# Loop 3 - `state_management` dimension

**Actor report (`loop_result`):** *"Added an in-flight upload registry so duplicate sync triggers coalesce instead of sending the same batch twice. The state is private to the coordinator and covered by a duplicate-trigger test. Full suite green (884 tests). Proposing `state_management` -> 9.5."*

**Test run:** `swift test` - 884 passed, 0 failed.

## Context

The app can receive duplicate sync triggers from push, foreground refresh, and manual retry. `UploadCoordinator` owns the decision of whether a batch is already running.

## Diff

```diff
--- a/Sources/Sync/UploadCoordinator.swift
+++ b/Sources/Sync/UploadCoordinator.swift
@@
 actor UploadCoordinator {
     private let client: UploadClient
+    private var inFlightBatchIDs: Set<BatchID> = []

     func upload(_ batch: UploadBatch) async throws {
+        guard inFlightBatchIDs.insert(batch.id).inserted else {
+            return
+        }
+        defer { inFlightBatchIDs.remove(batch.id) }
         try await client.upload(batch)
     }
 }
```

`inFlightBatchIDs` has a clear read site (`guard insert(...).inserted`) and controls the runtime decision to suppress duplicate uploads. `UploadCoordinatorTests.testDuplicateTriggerCoalesces` fires two concurrent uploads for the same `BatchID` and asserts the client receives one call.
