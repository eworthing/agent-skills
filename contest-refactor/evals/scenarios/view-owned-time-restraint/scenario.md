# Loop 8 - `data_flow` dimension

**Actor report (`loop_result`):** *"Added a transient 'Saved' toast to the live screen that fades itself out after a couple of seconds. Pure presentation — the domain already persisted the change. Full suite green (1,541 tests). Proposing `data_flow` -> 9.5."*

**Test run:** `swift test` - 1,541 passed, 0 failed.

## Context

Board expiration, sync windows, and other durable workflow clocks are owned by `LiveStore` and its coordinators. The toast here is purely a visual confirmation; dismissing it early or late has no domain consequence.

## Diff

```diff
--- a/Sources/Live/SavedToast.swift
+++ b/Sources/Live/SavedToast.swift
@@
 struct SavedToast: View {
     @Binding var isVisible: Bool

     var body: some View {
         if isVisible {
             Text("Saved")
                 .transition(.opacity)
+                .task {
+                    try? await Task.sleep(for: .seconds(2))
+                    withAnimation { isVisible = false }
+                }
         }
     }
 }
```

`isVisible` drives only this overlay. Nothing durable depends on when the toast disappears; if the view goes away first, the toast is gone anyway. `SavedToastTests` assert the label renders when `isVisible` is true.
