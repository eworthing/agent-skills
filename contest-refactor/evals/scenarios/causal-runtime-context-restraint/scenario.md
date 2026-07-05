# Loop 12 - `state_management` dimension

**Actor report (`loop_result`):** *"Made sync completion record-owned. In-flight records capture their request, and completion applies through that captured context instead of whichever folder is selected later. Full suite green (947 tests). Proposing `state_management` -> 9.5."*

**Test run:** `swift test` - 947 passed, 0 failed.

## Context

A user can start a folder sync, switch folders while the sync runs, and then receive the completion event later. Selection is valid for new user commands, but completion/error/progress events for an existing runtime record must use the context that started that record.

## Diff

```diff
--- a/Sources/Sync/SyncReducer.swift
+++ b/Sources/Sync/SyncReducer.swift
@@
 struct SyncRecord: Identifiable {
     let id: SyncID
+    let request: SyncRequest
     var startedAt: Date
 }

 enum SyncAction {
     case startSync(folderID: FolderID)
     case syncFinished(SyncID, SyncResult)
 }

 extension SyncReducer {
     mutating func reduce(_ action: SyncAction, state: inout SyncState) {
         switch action {
         case let .startSync(folderID):
             let id = SyncID()
-            state.inFlight[id] = SyncRecord(id: id, startedAt: clock.now)
+            state.inFlight[id] = SyncRecord(id: id, request: SyncRequest(folderID: folderID), startedAt: clock.now)
             effects.append(.runSync(id: id, folderID: folderID))
         case let .syncFinished(id, result):
-            state.inFlight.removeValue(forKey: id)
-            guard let folderID = state.selectedFolderID else { return }
-            state.folders[id: folderID].apply(result)
+            guard let record = state.inFlight.removeValue(forKey: id) else { return }
+            state.folders[id: record.request.folderID].apply(result)
         }
     }
 }
```

The reducer still uses `selectedFolderID` for new "start sync" commands. Existing sync events use the captured request on the runtime record, and `SyncReducerTests.testCompletionAppliesToOriginalFolderAfterSelectionChange` covers the selection-change path.
