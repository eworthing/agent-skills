# Loop 2 — `state_management` dimension

**Actor report (`loop_result`):** *"Refactored the playlist rename flow out of `PlaylistListView` into a dedicated `RenamePlaylistSheet` child so the parent view body shrinks. Full suite green (1,312 tests). Proposing `state_management` → 9.5."*

**Test run:** `swift test` — 1,312 passed, 0 failed.

## Context

`RenamePlaylistSheet` is a modal edit form. It opens with the playlist's current name pre-filled, the user edits the text field, and taps **Save** (which calls `onCommit`) or **Cancel** (which discards). The parent does not push new names into the open sheet — the sheet owns the in-progress edit until it closes.

## Diff

```diff
--- a/Sources/Library/PlaylistListView.swift
+++ b/Sources/Library/PlaylistListView.swift
@@
+struct RenamePlaylistSheet: View {
+    @State private var draftName: String
+    let onCommit: (String) -> Void
+    @Environment(\.dismiss) private var dismiss
+
+    init(currentName: String, onCommit: @escaping (String) -> Void) {
+        _draftName = State(initialValue: currentName)
+        self.onCommit = onCommit
+    }
+
+    var body: some View {
+        NavigationStack {
+            TextField("Playlist name", text: $draftName)
+                .toolbar {
+                    ToolbarItem(placement: .confirmationAction) {
+                        Button("Save") { onCommit(draftName); dismiss() }
+                    }
+                    ToolbarItem(placement: .cancellationAction) {
+                        Button("Cancel") { dismiss() }
+                    }
+                }
+        }
+    }
+}
```
