# Loop 9 - `data_flow` dimension

**Actor report (`loop_result`):** *"Deleted the row-command DTOs and simplified playlist edits by passing the SwiftUI move/delete offsets straight into the reducer. The view code is smaller, projection remains unchanged, and the full suite is green (1,186 tests). Proposing `data_flow` -> 9.5."*

**Test run:** `swift test` - 1,186 passed, 0 failed.

## Context

`PlaylistViewState.visibleRows` filters archived tracks and sorts visible rows by title. The reducer mutates `Playlist.items`, whose stored order is the user's playback order. The two sequences are not guaranteed to have the same indexes.

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
-            .onMove { source, destination in
-                let orderedIDs = viewState.visibleRows.map(\.id)
-                let movedIDs = source.map { orderedIDs[$0] }
-                let beforeID = destination < orderedIDs.count ? orderedIDs[destination] : nil
-                dispatch(.moveVisibleRows(movedIDs: movedIDs, beforeID: beforeID, visibleOrder: orderedIDs))
-            }
-            .onDelete { offsets in
-                let ids = offsets.map { viewState.visibleRows[$0].id }
-                dispatch(.deleteTracks(ids))
-            }
+            .onMove { source, destination in
+                dispatch(.moveVisibleRows(source: source, destination: destination))
+            }
+            .onDelete { offsets in
+                dispatch(.deleteVisibleRows(offsets))
+            }
         }
     }
 }
--- a/Sources/Playlists/PlaylistReducer.swift
+++ b/Sources/Playlists/PlaylistReducer.swift
@@
 enum PlaylistAction {
-    case moveVisibleRows(movedIDs: [TrackID], beforeID: TrackID?, visibleOrder: [TrackID])
-    case deleteTracks([TrackID])
+    case moveVisibleRows(source: IndexSet, destination: Int)
+    case deleteVisibleRows(IndexSet)
 }

 extension PlaylistReducer {
     mutating func reduce(_ action: PlaylistAction, state: inout PlaylistState) {
         switch action {
-        case let .moveVisibleRows(movedIDs, beforeID, visibleOrder):
-            guard visibleOrder == PlaylistViewState.project(from: state).visibleRows.map(\.id) else {
-                state.presentationError = .stalePlaylistView
-                return
-            }
-            state.playlist.moveTracks(ids: movedIDs, before: beforeID)
-        case let .deleteTracks(ids):
-            state.playlist.removeTracks(ids: ids)
+        case let .moveVisibleRows(source, destination):
+            state.playlist.items.move(fromOffsets: source, toOffset: destination)
+        case let .deleteVisibleRows(offsets):
+            for offset in offsets.sorted(by: >) {
+                state.playlist.items.remove(at: offset)
+            }
         }
     }
 }
```

The refactor makes a projection index the write authority. A row offset from the filtered/title-sorted view can point at a different track in the stored playback order, and it can become stale after a concurrent reorder or removal. The green suite covers only a playlist whose visible order happens to match stored order.
