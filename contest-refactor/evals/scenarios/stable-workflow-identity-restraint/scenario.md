# Loop 10 - `data_flow` dimension

**Actor report (`loop_result`):** *"Moved playlist row shaping into `PlaylistViewState.project` and kept write commands ID-based. The reducer validates the projection snapshot before mutating, so stale views fail closed. Full suite green (1,214 tests). Proposing `data_flow` -> 9.5."*

**Test run:** `swift test` - 1,214 passed, 0 failed.

## Context

`PlaylistViewState.visibleRows` filters archived tracks and sorts visible rows by title. SwiftUI still reports move offsets, but the view immediately resolves those offsets to durable IDs and sends the full visible ID slice to the reducer.

## Diff

```diff
--- a/Sources/Playlists/PlaylistView.swift
+++ b/Sources/Playlists/PlaylistView.swift
@@
 struct PlaylistView: View {
     let viewState: PlaylistViewState
     let dispatch: (PlaylistAction) -> Void

     var body: some View {
         List {
             ForEach(viewState.visibleRows) { row in
                 PlaylistRow(row: row)
             }
+            .onMove { source, destination in
+                let orderedIDs = viewState.visibleRows.map(\.id)
+                let movedIDs = source.map { orderedIDs[$0] }
+                let beforeID = destination < orderedIDs.count ? orderedIDs[destination] : nil
+                dispatch(.moveVisibleRows(movedIDs: movedIDs, beforeID: beforeID, visibleOrder: orderedIDs))
+            }
+            .onDelete { offsets in
+                dispatch(.deleteTracks(offsets.map { viewState.visibleRows[$0].id }))
+            }
         }
     }
 }
--- a/Sources/Playlists/PlaylistReducer.swift
+++ b/Sources/Playlists/PlaylistReducer.swift
@@
 enum PlaylistAction {
+    case moveVisibleRows(movedIDs: [TrackID], beforeID: TrackID?, visibleOrder: [TrackID])
+    case deleteTracks([TrackID])
 }

 extension PlaylistReducer {
     mutating func reduce(_ action: PlaylistAction, state: inout PlaylistState) {
         switch action {
+        case let .moveVisibleRows(movedIDs, beforeID, visibleOrder):
+            let currentVisibleOrder = PlaylistViewState.project(from: state).visibleRows.map(\.id)
+            guard visibleOrder == currentVisibleOrder else {
+                state.presentationError = .stalePlaylistView
+                return
+            }
+            state.playlist.moveTracks(ids: movedIDs, before: beforeID)
+        case let .deleteTracks(ids):
+            state.playlist.removeTracks(ids: ids)
         }
     }
 }
```

The write authority never trusts an offset as identity. It receives durable track IDs, recomputes the authoritative visible ordered slice, and refuses to mutate if the slice changed before the action arrived. `PlaylistReducerTests.testMoveFromStaleProjectionFailsClosed` covers the stale-slice path.
