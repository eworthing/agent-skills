# Examples & Patterns

Concrete before/after pairs and naming/decision aids for the split workflow.

## Example 1: Extracting Helper Views

**Before (`MainView.swift`, 750 lines):**
```swift
struct MainView: View {
    private var helperView: some View {  // line 450-550
        VStack { ... }
    }

    var body: some View { ... }
}
```

**After split:**

`MainView.swift` (400 lines):
```swift
struct MainView: View {
    var body: some View {
        helperView  // Now accesses from extension
    }
}
```

`MainView+HelperViews.swift` (150 lines):
```swift
import SwiftUI

extension MainView {
    var helperView: some View {  // Changed from private
        VStack { ... }
    }
}
```

## Example 2: Extracting State-Adjacent Members

**Before:**
```swift
struct EditorView: View {
    private var computedValue: Int { ... }  // Used in extension
    private func helperMethod() { ... }      // Used in extension
}
```

**After:**
```swift
struct EditorView: View {
    // Accessed from EditorView+Helpers.swift
    var computedValue: Int { ... }           // Now internal
    func helperMethod() { ... }              // Now internal
}
```

## Example 3: The Visibility Fix Pattern

**Symptom:** Build succeeds before split, fails after.
**Cause:** `private` property accessed from extension file.
**Fix:** Change `private` to `internal` (or drop the modifier).

```diff
- private var lastFocus: FocusAnchor?
+ var lastFocus: FocusAnchor?  // Accessed from +Navigation.swift
```

## File Naming Conventions

| Original | Extension File |
|----------|---------------|
| `SomeView.swift` | `SomeView+Feature.swift` |
| `AppState.swift` | `AppState+Persistence.swift` |
| `ContentView.swift` | `ContentView+Toolbar.swift` |
| `ProfileView.swift` | `ProfileView+Accessibility.swift` |
| `ContentView+Toolbar.swift` | `ContentView+Toolbar+PrimaryActions.swift` |

## Split Decision Tree

```
File over 600 lines?
├── No -> Don't split
└── Yes -> Find logical boundaries
    ├── Has MARK sections? -> Split at MARK boundaries
    ├── Has extensions? -> Extract extensions to files
    └── Large helper methods? -> Extract to +Helpers.swift

After split, check:
├── Any private members accessed cross-file?
│   └── Yes -> Change to internal
├── Build passes?
│   └── Failure? -> Check visibility (see troubleshooting.md)
└── Both files under limits?
```

## Good Split Candidates

- Helper views/subviews
- Extension blocks
- Private helper methods grouped by feature
- Computed properties for complex logic
- Preview providers (move to `+Previews.swift`)
- Conformances (move to `+ProtocolName.swift`)
