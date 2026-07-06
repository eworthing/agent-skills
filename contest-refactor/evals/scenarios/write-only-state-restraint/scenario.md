# Loop 3 - `state_management` dimension

**Actor report (`loop_result`):** *"Added an in-flight upload registry so duplicate sync triggers share one upload instead of sending the same batch twice. A second caller for a batch already uploading awaits the same task and gets its result. Covered by a concurrent duplicate-trigger test. Full suite green (884 tests). Proposing `state_management` -> 9.5."*

**Test run:** `swift test` - 884 passed, 0 failed.

## Context

The app can receive duplicate sync triggers from push, foreground refresh, and manual retry. `UploadCoordinator` owns whether a batch is already uploading and must not send it twice, while a duplicate caller must still observe success or failure of the shared upload.

## Diff

```diff
--- a/Sources/Sync/UploadCoordinator.swift
+++ b/Sources/Sync/UploadCoordinator.swift
@@
 actor UploadCoordinator {
     private let client: UploadClient
+    private var inFlight: [BatchID: Task<Void, Error>] = [:]

     func upload(_ batch: UploadBatch) async throws {
+        if let existing = inFlight[batch.id] {
+            try await existing.value
+            return
+        }
+        let task = Task { try await client.upload(batch) }
+        inFlight[batch.id] = task
+        defer { inFlight[batch.id] = nil }
+        try await task.value
     }
 }
```

`inFlight` is read in the `if let existing` guard, and the coalesced caller awaits `existing.value`, so it receives the same success or thrown error as the original. `UploadCoordinatorTests.testDuplicateTriggerCoalesces` fires two concurrent uploads for one `BatchID` and asserts the client receives exactly one call while both callers observe the same outcome.
