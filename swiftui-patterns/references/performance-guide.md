# SwiftUI Performance & View Composition Guide

Performance optimization and view composition patterns for iOS apps.

## Table of Contents

- [Avoiding Redundant State Updates](#avoiding-redundant-state-updates)
- [Optimizing Hot Paths](#optimizing-hot-paths)
- [Passing Only Needed Values](#passing-only-needed-values)
- [Equatable Views](#equatable-views)
- [POD Views for Fast Diffing](#pod-views-for-fast-diffing)
- [Lazy Loading](#lazy-loading)
- [Task Cancellation](#task-cancellation)
- [Debugging View Updates](#debugging-view-updates)
- [View Composition Rules](#view-composition-rules)
- [Container View Pattern](#container-view-pattern)
- [ZStack vs overlay/background](#zstack-vs-overlaybackground)
- [ForEach Identity and Stability](#foreach-identity-and-stability)
- [Anti-Patterns](#anti-patterns)

---

## Avoiding Redundant State Updates

SwiftUI doesn't always compare values before triggering body re-evaluation:

```swift
// BAD - triggers update even if value unchanged
.onReceive(publisher) { value in
    self.currentValue = value
}

// GOOD - only update when different
.onReceive(publisher) { value in
    if self.currentValue != value {
        self.currentValue = value
    }
}
```

---

## Optimizing Hot Paths

Hot paths are frequently executed code (scroll handlers, animations, gestures):

```swift
// BAD - fires on every scroll position change
.onPreferenceChange(ScrollOffsetKey.self) { offset in
    shouldShowTitle = offset.y <= -32
}

// GOOD - only update when threshold crossed
.onPreferenceChange(ScrollOffsetKey.self) { offset in
    let shouldShow = offset.y <= -32
    if shouldShow != shouldShowTitle {
        shouldShowTitle = shouldShow
    }
}
```

---

## Passing Only Needed Values

Pass specific values to views, not entire model objects:

```swift
// GOOD - narrow dependency
struct ItemRow: View {
    let item: Item
    let themeColor: Color
    var body: some View {
        Text(item.name).foregroundStyle(themeColor)
    }
}

// AVOID - broad dependency
struct ItemRow: View {
    @Environment(AppModel.self) private var model
    let item: Item
    var body: some View {
        // Updates when ANY model property changes
        Text(item.name).foregroundStyle(model.theme.primaryColor)
    }
}
```

---

## Equatable Views

For views with expensive bodies, conform to `Equatable` with custom comparison:

```swift
struct ExpensiveView: View, Equatable {
    let data: SomeData

    static func == (lhs: Self, rhs: Self) -> Bool {
        lhs.data.id == rhs.data.id
    }

    var body: some View {
        // Expensive computation
    }
}

// Usage
ExpensiveView(data: data).equatable()
```

**Caution:** If you add new state or dependencies, update your `==` function.

---

## POD Views for Fast Diffing

**POD (Plain Old Data) views use `memcmp` for the fastest diffing.** A view is POD if it contains only simple value types and no property wrappers.

```swift
// POD view - fastest diffing (memcmp)
struct FastView: View {
    let title: String
    let count: Int
    var body: some View {
        Text("\(title): \(count)")
    }
}

// Non-POD view - slower diffing (reflection or custom equality)
struct SlowerView: View {
    let title: String
    @State private var isExpanded = false
    var body: some View {
        Text(title)
    }
}
```

### Advanced: POD Wrapper Pattern

Wrap expensive non-POD views in POD parents for fast outer comparison:

```swift
// POD wrapper - fast memcmp comparison
struct ExpensiveView: View {
    let value: Int
    var body: some View {
        ExpensiveViewInternal(value: value)
    }
}

// Internal view with state
private struct ExpensiveViewInternal: View {
    let value: Int
    @State private var item: Item?
    var body: some View {
        // Expensive rendering
    }
}
```

The POD parent uses `memcmp`. Only when `value` changes does the internal view get diffed.

---

## Lazy Loading

Use lazy containers for large collections:

```swift
// BAD - creates all views immediately
ScrollView {
    VStack {
        ForEach(items) { item in ExpensiveRow(item: item) }
    }
}

// GOOD - creates views on demand
ScrollView {
    LazyVStack {
        ForEach(items) { item in ExpensiveRow(item: item) }
    }
}
```

---

## Task Cancellation

Use `.task` for automatic cancellation when the view disappears:

```swift
List(data) { item in
    Text(item.name)
}
.task {
    data = await fetchData()
}
```

Use `.task(id:)` to restart when a value changes:

```swift
.task(id: selectedCategory) {
    data = await fetchItems(for: selectedCategory)
}
```

---

## Debugging View Updates

`Self._printChanges()` prints what caused `body` to be called.

```swift
#if DEBUG
var body: some View {
    let _ = Self._printChanges()
    // ... view content
}
#endif
```

> **Warning:** This is an undocumented internal API. It may break between Swift versions. **Always gate with `#if DEBUG`** and never ship to production.

---

## View Composition Rules

### Modifier Over Conditional

Prefer modifiers for state changes to maintain view identity:

```swift
// GOOD - preserves view identity, animates smoothly
SomeView().opacity(isVisible ? 1 : 0)

// AVOID - destroys and recreates view, loses state
if isVisible { SomeView() }
```

Use conditionals only for fundamentally different views (e.g., `DashboardView` vs `LoginView`).

### When to Extract vs Inline

| Situation | Approach |
|-----------|----------|
| Complex section, many views | Extract to separate `struct` |
| Small, simple (<10 lines) | `@ViewBuilder` function OK |
| Reusable container with slot | `@ViewBuilder let content: Content` |

### Why Separate Structs Win

```swift
// @ViewBuilder function re-executes on EVERY parent state change
@ViewBuilder func complexSection() -> some View { /* always runs */ }

// Separate struct - SwiftUI skips body when inputs unchanged
struct ComplexSection: View {
    var body: some View { /* skipped if nothing changed */ }
}
```

---

## Container View Pattern

### Use `@ViewBuilder let` Over Closures

```swift
// GOOD - view can be compared, skipped when unchanged
struct MyContainer<Content: View>: View {
    @ViewBuilder let content: Content
    var body: some View {
        VStack {
            Text("Header")
            content
        }
    }
}

// AVOID - closure prevents comparison
struct MyContainer<Content: View>: View {
    let content: () -> Content
    var body: some View {
        VStack {
            Text("Header")
            content()
        }
    }
}
```

---

## ZStack vs overlay/background

- **Decoration** (badge, border, shadow): Use `.overlay()` / `.background()`
- **Peer composition** (views jointly defining layout): Use `ZStack`

Key difference: `overlay`/`background` children inherit parent's proposed size. `ZStack` children participate independently in layout.

```swift
// GOOD - decoration
Button("Continue") { }
    .overlay(alignment: .trailing) {
        Image(systemName: "lock.fill").padding(.trailing, 8)
    }

// GOOD - background
HStack { /* content */ }
    .background { Capsule().strokeBorder(.blue, lineWidth: 2) }
```

---

## ForEach Identity and Stability

### Use Stable IDs

```swift
// GOOD - stable identity
ForEach(items) { item in
    ItemRow(item: item)
}

// BAD - indices change when items are added/removed
ForEach(items.indices, id: \.self) { index in
    ItemRow(item: items[index])
}
```

### Constant View Count Per Element

```swift
// BAD - varying view count confuses diffing
ForEach(items) { item in
    if item.hasImage {
        ImageRow(item: item)
    } else {
        TextRow(item: item)
    }
}

// GOOD - same structure, conditional content
ForEach(items) { item in
    ItemRow(item: item)  // Handles both cases internally
}
```

### Prefilter, Don't Inline Filter

```swift
// BAD - filtering inside ForEach
ForEach(items.filter { $0.isActive }) { item in
    ItemRow(item: item)  // Creates new array every body call
}

// GOOD - prefilter and store
let activeItems = items.filter { $0.isActive }
ForEach(activeItems) { item in
    ItemRow(item: item)
}
```

### Avoid AnyView in List Rows

`AnyView` prevents SwiftUI from performing type-specific diffing optimizations.

---

## Anti-Patterns

### Creating Objects in Body

```swift
// BAD - new formatter every body call
var body: some View {
    let formatter = DateFormatter()
    formatter.dateStyle = .long
    return Text(formatter.string(from: date))
}

// GOOD - static formatter
private static let dateFormatter: DateFormatter = {
    let f = DateFormatter()
    f.dateStyle = .long
    return f
}()

var body: some View {
    Text(Self.dateFormatter.string(from: date))
}
```

### Heavy Computation in Body

```swift
// BAD - sorts every body call
var body: some View {
    List(items.sorted { $0.name < $1.name }) { item in Text(item.name) }
}

// GOOD - compute once in onChange
@State private var sortedItems: [Item] = []
var body: some View {
    List(sortedItems) { item in Text(item.name) }
        .onChange(of: items) { _, newItems in
            sortedItems = newItems.sorted { $0.name < $1.name }
        }
}
```

### Unnecessary Derived State

```swift
// BAD - derived state stored separately
@State private var items: [Item] = []
@State private var itemCount: Int = 0  // Unnecessary!

// GOOD - compute derived values
@State private var items: [Item] = []
var itemCount: Int { items.count }
```
