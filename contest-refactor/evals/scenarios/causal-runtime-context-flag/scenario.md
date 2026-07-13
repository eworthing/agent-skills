# Loop 11 - `state_management` dimension

**Actor report (`loop_result`):** *"Extracted a small `apply(_:to:)` helper out of the sync-completion path so the reducer case reads cleaner. Pure refactor, no behavior change, full suite green (902 tests). Proposing `state_management` -> 9.5."*

**Test run:** `swift test` - 902 passed, 0 failed.

## Context

A user can start a folder sync, switch the selected folder while the sync runs, and receive the completion event later. Sync runs on a background effect keyed by `SyncID`.

## Resulting source

```swift
struct SyncRecord: Identifiable {
    let id: SyncID
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
            state.inFlight[id] = SyncRecord(id: id, startedAt: clock.now)
            effects.append(.runSync(id: id, folderID: folderID))
        case let .syncFinished(id, result):
            state.inFlight.removeValue(forKey: id)
            apply(result, to: &state)
        }
    }

    private func apply(_ result: SyncResult, to state: inout SyncState) {
        guard let folderID = state.selectedFolderID else { return }
        state.folders[id: folderID].apply(result)
    }
}
```

`state.selectedFolderID` is set by the user's folder selection and changes independently of any running sync. `SyncReducerTests.testSyncFinishedAppliesResult` starts a sync for the selected folder and delivers completion without changing the selection in between.
