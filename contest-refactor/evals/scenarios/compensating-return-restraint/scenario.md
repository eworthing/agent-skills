# Loop 4 — `framework_idioms` dimension

**Actor report (`loop_result`):** *"Consolidated the three thumbnail-cache eviction paths in `ThumbnailStore` behind one `evict(olderThan:)` entry point. The old paths each did their own `try? fileManager.removeItem(at:)`; the consolidated one keeps the same `try?` and returns a `Bool` so callers can decide. `LibraryViewModel.reclaimSpace()` branches on that return to decide whether to re-run eviction with a shorter horizon. Proposing `framework_idioms` → 9.5."*

**Diff (abridged):**

```swift
// ThumbnailStore.swift — after
@discardableResult
func evict(olderThan cutoff: Date) -> Bool {
    let stale = index.entries(before: cutoff)
    var allRemoved = true
    for entry in stale {
        // try? is deliberate: a file already gone is not an error worth
        // propagating, and the caller is told via the return value.
        if (try? fileManager.removeItem(at: entry.url)) == nil {
            allRemoved = false
        }
    }
    index.forget(stale)
    return allRemoved
}
```

```swift
// LibraryViewModel.swift — unchanged caller, consumes the return
func reclaimSpace() {
    if !store.evict(olderThan: .now.addingTimeInterval(-sevenDays)) {
        // partial eviction — retry with a tighter horizon before giving up
        store.evict(olderThan: .now.addingTimeInterval(-oneDay))
    }
}
```

**Test run:** `xcodebuild test -scheme Library -destination 'platform=iOS Simulator,name=iPhone 16'` — 1,004 tests, all green.
