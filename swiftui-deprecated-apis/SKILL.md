---
name: swiftui-deprecated-apis
author: eworthing
original-author: Antoine van der Lee (AvdLee)
source: https://github.com/AvdLee/SwiftUI-Agent-Skill
description: >-
  Replaces deprecated SwiftUI and Swift APIs with supported equivalents across
  iOS, macOS, and tvOS. Use when Xcode reports deprecation warnings, when
  modernizing older code, when editing code that uses APIs such as
  NavigationView, foregroundColor, cornerRadius, accentColor, onChange,
  GeometryReader, UIImpactFeedbackGenerator, Text("a") + Text("b"), or older
  onChange/Task.sleep/sheet(isPresented:) signatures.
allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Bash
---

# API Deprecation Remediation

## Purpose

Systematically replace deprecated Swift and SwiftUI APIs with modern equivalents to eliminate build warnings and ensure forward compatibility.

## When to Use This Skill

Use this skill when:
- Xcode shows deprecation warnings
- Updating to a new iOS SDK version
- User says "fix deprecation", "modernize code", "update deprecated APIs"
- Preparing for App Store submission with warning-free build
- Code review flags deprecated API usage

Do NOT use this skill when:
- The deprecated API has no direct replacement yet
- Maintaining backward compatibility with older OS versions is required
- The replacement API has different behavior that needs careful migration

## Workflow

### Step 1: Identify Deprecated APIs

```bash
# Build to surface warnings
xcodebuild build -scheme YourScheme -destination 'generic/platform=iOS' 2>&1 | grep -i deprecat

# Or search for known deprecated patterns
grep -rn "foregroundColor\|\.cornerRadius\|NavigationView" --include="*.swift" Sources/
```

### Step 2: Apply Replacements

Use the replacement table below. For each deprecated API:

1. Search for all occurrences
2. Apply the modern replacement
3. Verify the behavior is equivalent
4. Build to confirm no new warnings

### Step 3: Verify

```bash
# Build to confirm warnings are resolved
xcodebuild build -scheme YourScheme -destination 'generic/platform=iOS'
```

## Deprecated API Replacement Table

### SwiftUI Modifiers (Deprecated in iOS 26)

| Deprecated | Modern Replacement | Notes |
|------------|-------------------|-------|
| `.foregroundColor(_:)` | `.foregroundStyle(_:)` | Accepts `ShapeStyle` (gradients, etc.) |
| `.cornerRadius(_:)` | `.clipShape(.rect(cornerRadius:))` | More flexible shape clipping |
| `NavigationView` | `NavigationStack` or `NavigationSplitView` | Use `NavigationSplitView` for sidebar patterns |
| `.accentColor(_:)` | `.tint(_:)` | Direct replacement |
| `.onAppear { }` with async | `.task { }` | Automatic cancellation on disappear |

### Overlay API

| Deprecated | Modern Replacement | Notes |
|------------|-------------------|-------|
| `.overlay(Text("Hi"), alignment:)` | `.overlay(alignment:) { Text("Hi") }` | Use trailing closure form |

### Presentation & Dialogs

| Deprecated Pattern | Modern Replacement | Notes |
|-------------------|-------------------|-------|
| `sheet(isPresented:)` with optional data | `sheet(item:)` | Safely unwraps the optional |
| `confirmationDialog` on unrelated view | Attach to the triggering UI element | Enables Liquid Glass source animations on iOS 26 |

### Text

| Deprecated | Modern Replacement | Notes |
|------------|-------------------|-------|
| `Text("A") + Text("B")` | `Text("\(textA)\(textB)")` (string interpolation) | `+` concatenation is deprecated; use interpolation or compose with `Group { Text(...); Text(...) }` if styling differs |

### Scroll

| Deprecated | Modern Replacement | Notes |
|------------|-------------------|-------|
| `ScrollView(showsIndicators: false)` | `.scrollIndicators(.hidden)` | Modifier-based approach |

### Shape Rendering

| Deprecated Pattern | Modern Replacement | Notes |
|-------------------|-------------------|-------|
| Fill + stroke overlay | Chain `.fill().stroke()` | Single-pass since iOS 17 |

### Haptics (iOS/macOS only, not tvOS)

| Deprecated | Modern Replacement | Notes |
|------------|-------------------|-------|
| `UIImpactFeedbackGenerator` | `.sensoryFeedback(_:trigger:)` modifier | SwiftUI-native haptic API (iOS 17+). tvOS has no haptics hardware — no replacement, gate with `#if !os(tvOS)`. |

### Environment Keys

| Deprecated Pattern | Modern Replacement | Notes |
|-------------------|-------------------|-------|
| Manual `EnvironmentKey` + `defaultValue` + computed property | `@Entry` macro on `EnvironmentValues` | Also works for `FocusValues`, `Transaction`, `ContainerValues` |

### onChange Variants

| Deprecated | Modern Replacement |
|------------|-------------------|
| `.onChange(of:) { newValue in }` | `.onChange(of:) { }` (zero-param) |
| `.onChange(of:) { newValue in }` | `.onChange(of:) { old, new in }` (two-param) |

**Note:** Both modern variants require iOS 17+

### Task.sleep

| Deprecated | Modern Replacement |
|------------|-------------------|
| `Task.sleep(nanoseconds: 1_000_000_000)` | `Task.sleep(for: .seconds(1))` |

### ForEach with enumerated()

| Deprecated Pattern | Modern Replacement |
|-------------------|-------------------|
| `ForEach(Array(items.enumerated()), id: \.offset)` | `ForEach(items.indices, id: \.self) { index in` |

### Layout Alternatives (iOS 16+/17+)

| Deprecated Pattern | Modern Replacement | Availability | Notes |
|-------------------|-------------------|-------------|-------|
| `GeometryReader` (measuring) | `.onGeometryChange(for:of:action:)` | iOS 16+ | Fires only on value change |
| `GeometryReader` (sizing) | `containerRelativeFrame()` | iOS 17+ / tvOS 17+ / macOS 14+ | When only relative sizing needed. On tvOS: only sees `ScrollView`/`NavigationStack`/`List` as containers — not arbitrary parents |
| `GeometryReader` (effects) | `.visualEffect { }` | iOS 17+ / tvOS 17+ / macOS 14+ | For position-based visual changes. Safe with the tvOS focus system — does not interfere with focus animation |

### Accessibility

| Deprecated | Modern Replacement |
|------------|-------------------|
| Custom tap gestures | `Button` with proper traits |
| Manual focus handling | `@FocusState` bindings |

## Common Mistakes to Avoid

1. **Forgetting platform availability** -- `onChange` two-param requires iOS 17+, `@Entry` macro requires Xcode 16+
2. **Breaking onChange behavior** -- Two-param variant gives access to old value; zero-param doesn't
3. **NavigationView -> NavigationStack blindly** -- Use `NavigationSplitView` for sidebar patterns
4. **Applying clipShape twice** -- `RoundedRectangle(cornerRadius:)` already has corners; don't add `.clipShape` on top

## Examples

### Example 1: foregroundColor -> foregroundStyle

**Before:**
```swift
Text("Hello")
    .foregroundColor(.blue)
```

**After:**
```swift
Text("Hello")
    .foregroundStyle(.blue)
```

### Example 2: cornerRadius -> clipShape

**Before:**
```swift
Image("photo")
    .cornerRadius(8)
```

**After:**
```swift
Image("photo")
    .clipShape(.rect(cornerRadius: 8))
```

### Example 3: onChange Migration

**Before:**
```swift
.onChange(of: searchText) { newValue in
    performSearch(newValue)
}
```

**After (zero-param, if old value not needed):**
```swift
.onChange(of: searchText) {
    performSearch(searchText)
}
```

**After (two-param, if old value needed):**
```swift
.onChange(of: searchText) { oldValue, newValue in
    if oldValue != newValue {
        performSearch(newValue)
    }
}
```

### Example 4: Task.sleep

**Before:**
```swift
try await Task.sleep(nanoseconds: 500_000_000)
```

**After:**
```swift
try await Task.sleep(for: .milliseconds(500))
```

### Example 5: @Entry Macro for Environment Keys

**Before:**
```swift
struct MyValueKey: EnvironmentKey {
    static let defaultValue: String = ""
}
extension EnvironmentValues {
    var myValue: String {
        get { self[MyValueKey.self] }
        set { self[MyValueKey.self] = newValue }
    }
}
```

**After:**
```swift
extension EnvironmentValues {
    @Entry var myValue: String = ""
}
```

### Example 6: sheet(item:) for Optional Data

**Before:**
```swift
.sheet(isPresented: $showDetail) {
    if let item = selectedItem {
        DetailView(item: item)
    }
}
```

**After:**
```swift
.sheet(item: $selectedItem) { item in
    DetailView(item: item)
}
// Or even: .sheet(item: $selectedItem, content: DetailView.init)
```

### Example 7: sensoryFeedback

**Before:**
```swift
let generator = UIImpactFeedbackGenerator(style: .medium)
generator.impactOccurred()
```

**After:**
```swift
Button("Action") { doSomething() }
    .sensoryFeedback(.impact(flexibility: .solid), trigger: triggerValue)
```

## Bulk Replacement Commands

For large-scale replacements, use careful regex:

```bash
# Find all foregroundColor usages
grep -rn "\.foregroundColor(" --include="*.swift" Sources/

# Count occurrences
grep -rc "\.foregroundColor(" --include="*.swift" Sources/ | grep -v ":0"
```

**Note:** Do NOT use sed for bulk replacement -- use the Edit tool for precise, verified changes.

## Constraints

- Some deprecated APIs may still be needed for backward compatibility
- Test UI behavior after replacements -- some have subtle differences
- Document any intentional deprecated API usage with comments
