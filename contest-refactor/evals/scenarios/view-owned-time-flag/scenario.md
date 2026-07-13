# Loop 8 - `data_flow` dimension

**Actor report (`loop_result`):** *"Wired up board-artwork prefetch on the live screen. It kicks off from a background view task after a short delay so it doesn't fight first render. Full suite green (1,541 tests). Proposing `data_flow` -> 9.5."*

**Test run:** `swift test` - 1,541 passed, 0 failed.

## Context

`LiveContent` is the live-screen root view. Board artwork is prefetched so it is warm before the user scrolls. Prefetch should not contend with the screen's first render.

## Diff

```diff
--- a/Sources/Live/LiveContent.swift
+++ b/Sources/Live/LiveContent.swift
@@
 struct LiveContent: View {
     let store: LiveStore

     var body: some View {
         LiveBoardGrid(store: store)
+            .task(priority: .background) {
+                try? await Task.sleep(for: .milliseconds(300))
+                await store.prefetchAllBoardArtwork()
+            }
     }
 }
```

`store.prefetchAllBoardArtwork()` warms a cache and is safe to call once per appearance. `LiveContentTests` assert the grid renders; there is no test around prefetch timing.
