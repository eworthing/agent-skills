# Loop 2 — `state_management` dimension

**Actor report (`loop_result`):** *"Refactored the volume readout out of `NowPlayingView` into a dedicated `VolumeBadge` child so the parent view body shrinks. Full suite green (1,312 tests). Proposing `state_management` → 9.5."*

**Test run:** `swift test` — 1,312 passed, 0 failed.

## Context

`outputVolume` is driven by the system — it changes while the screen is open (hardware volume buttons, AirPlay route changes, the OS volume HUD). The parent observes those changes and re-renders with the new value continuously.

## Diff

```diff
--- a/Sources/Player/NowPlayingView.swift
+++ b/Sources/Player/NowPlayingView.swift
@@
 struct NowPlayingView: View {
     @StateObject private var audio = AudioSession()
 
     var body: some View {
         VStack {
             // ...artwork, transport controls...
-            HStack {
-                Image(systemName: "speaker.fill")
-                ProgressView(value: audio.outputVolume)
-                Image(systemName: "speaker.wave.3.fill")
-            }
+            VolumeBadge(volume: audio.outputVolume)
         }
     }
 }
+
+struct VolumeBadge: View {
+    @State private var volume: Double
+    init(volume: Double) { _volume = State(initialValue: volume) }
+
+    var body: some View {
+        HStack {
+            Image(systemName: "speaker.fill")
+            ProgressView(value: volume)
+            Image(systemName: "speaker.wave.3.fill")
+        }
+    }
+}
```

`audio.outputVolume` is a published property that updates many times per second while the user holds a volume button.
