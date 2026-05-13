---
name: swiftui-patterns
author: eworthing
original-author: Antoine van der Lee (AvdLee)
source: https://github.com/AvdLee/SwiftUI-Agent-Skill
description: >-
  Applies SwiftUI composition, identity, list, grid, animation, scroll,
  text-formatting, observable-state, and tvOS-focus performance patterns
  across iOS, macOS, and tvOS. Use when building or restructuring SwiftUI
  views, reusable containers, lists, grids, or animations, diagnosing
  janky scrolling, re-rendering, or view-identity problems, optimizing
  POD diffing, wiring `@Observable` / `@Bindable` state containers,
  routing view binding to observable state, fixing `@AppStorage` view
  updates not firing inside `@Observable` classes, handling tvOS focus
  hover conflicts or focus settle delays, or wiring focus-driven scroll
  behavior.
allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Bash
---

# SwiftUI Patterns

## Scope

This skill owns SwiftUI **rendering invariants** — composition, identity,
diffing performance, animation mechanics, scroll handling, text
formatting, and tvOS focus-engine caveats.

For adjacent concerns use the appropriate sibling skill:

| Concern | Skill |
|---|---|
| App-level state architecture, store-of-stores composition | `swiftui-expert-skill` |
| Deprecated SwiftUI APIs (`foregroundColor`, `cornerRadius`, `NavigationView`, old `onChange`) | `swiftui-deprecated-apis` |
| Design tokens (colors, spacing, motion tokens, button styles) | `swiftui-design-tokens` |
| Accessibility identifiers, VoiceOver, focus dismissal | `swiftui-accessibility` |
| UI testing patterns and accessibility-marker views | `xctest-ui-testing` |

tvOS-specific composition, animation, and scroll patterns (focus hover
conflict, focus settle delay, focus-driven scrolling, POD + `@FocusState`)
are documented in [references/tvos.md](references/tvos.md).

## View Composition & Container Patterns

### `@ViewBuilder let` Over Closures (Critical)

The single most important performance pattern for reusable container views.
SwiftUI compares view inputs to decide whether to skip `body` re-evaluation. Closures
(`() -> Content`) are **never comparable** — SwiftUI must always re-evaluate. A
`@ViewBuilder let content: Content` stores the *built view tree* as a concrete value
that SwiftUI can compare and skip.

```swift
// GOOD — comparable, skippable
struct Card<Content: View>: View {
    let title: String
    @ViewBuilder let content: Content

    var body: some View {
        VStack {
            Text(title)
            content
        }
    }
}

// BAD — closure forces re-render on every parent update
struct Card<Content: View>: View {
    let title: String
    let content: () -> Content

    var body: some View {
        VStack {
            Text(title)
            content()
        }
    }
}
```

The call site syntax is identical — `Card(title: "X") { Text("Y") }`. The difference
is in how Swift resolves the trailing closure: `@ViewBuilder let` evaluates at
construction and stores the result; `() -> Content` stores the closure itself.

**When you see a generic container with `() -> Content`, change it to `@ViewBuilder let content: Content`.**

### Modifier Over Conditional

Prefer ternary/modifier over `if/else` branching to preserve structural identity:

```swift
// GOOD — same view, ternary preserves identity, animates smoothly
SomeView()
    .opacity(isVisible ? 1 : 0)

// AVOID — _ConditionalContent destroys identity, breaks animations
if isVisible { SomeView() } else { SomeView().opacity(0) }
```

Use `if/else` only for fundamentally different views (`DashboardView` vs `LoginView`).
For insertion/removal with transitions, use single-branch `if` inside an always-present
parent (e.g., `.overlay { if condition { badge } }`).

### Extraction Rules

| Situation | Approach |
|-----------|----------|
| Complex section, many views | Extract to separate `struct` (enables skip) |
| Small, simple section (<10 lines) | `@ViewBuilder` function is OK |
| Reusable container with slot | `@ViewBuilder let content: Content` |
| Computed property returning views | Extract to struct instead (avoids re-evaluation) |

Keep logic out of view body — extract button actions to methods.

### ZStack vs overlay/background

- **Decoration** (badge, border, shadow): `.overlay()` / `.background()` — child inherits parent size
- **Peer composition** (views jointly defining layout): `ZStack` — children participate independently

**tvOS:** never apply `.focusable()` to a container wrapping focusable
children — it blocks focus from reaching them. See
[references/tvos.md](references/tvos.md).

---

## Observable State

For `@Observable` + `@MainActor` + `final class` state containers, `@Bindable`
view binding, mutation routing through methods, undo-snapshot capture, and
error surfacing — and the silent-failure gotcha with **`@AppStorage` inside
`@Observable`** — see [references/observable-state.md](references/observable-state.md).

---

## Performance

For the complete reference with code examples and anti-patterns, see:
[references/performance-guide.md](references/performance-guide.md)

### POD Views (Plain Old Data)

Views with only simple value types and no property wrappers use `memcmp` for the fastest
possible diffing — a single memory comparison instead of field-by-field equality checks.

```swift
// POD view — memcmp fast path
struct StatCard: View {
    let title: String
    let percentage: Double
    let count: Int

    var body: some View {
        VStack {
            Text(title)
            Text(percentage, format: .percent.precision(.fractionLength(1)))
        }
    }
}

// Non-POD — slower diffing (property wrapper prevents memcmp)
struct StatCard: View {
    let title: String
    @State private var isExpanded = false
    // ...
}
```

**Making views POD-eligible:**
1. Pass only needed primitive values, not entire model objects
2. Use `@ViewBuilder let content: Content` instead of closures
3. Keep `@State`/`@FocusState` in parent views when possible

**tvOS:** POD focusable rows can lose focus identity on parent redraw.
Pair them with `@FocusState` + `.focused(_:equals:)` in the parent —
details in [references/tvos.md](references/tvos.md).

### Key Rules

1. **Narrow state scope** — Pass only needed values, not entire model objects. A view
   taking `percentage: Double` only invalidates when that value changes; a view taking
   the whole model invalidates when *any* property changes.
2. **Gate hot paths** — Only update state when crossing thresholds in scroll/geometry handlers.
   Compare before writing: `if shouldShow != showTitle { showTitle = shouldShow }`
3. **Extract subviews** — Separate `struct` views can be skipped when inputs don't change.
   `@ViewBuilder` functions re-execute on every parent state change.
4. **No object creation in body** — Static formatters, precomputed values.
5. **Lazy containers** — `LazyVStack`/`LazyHStack` for large collections.
6. **`@State` as cache** — `@State` can store expensive non-observable objects (e.g. `CIContext`)
   for persistence across redraws without observation overhead.

### Verifying Performance Fixes

Use `Self._printChanges()` to confirm which views re-render and why:

```swift
#if DEBUG
var body: some View {
    let _ = Self._printChanges()
    // ... rest of body
}
#endif
```

**This is an undocumented internal API.** Always gate with `#if DEBUG` — never ship.

---

## Animation Patterns

For the complete animation reference with code examples, decision trees, and advanced
patterns (phase/keyframe animations, Animatable protocol, transitions), see:
[references/animation-guide.md](references/animation-guide.md)

### Decision Tree

1. **State-driven, scoped to specific properties?** `.animation(_:value:)` (implicit)
2. **Event-driven (button tap, gesture)?** `withAnimation(.spring) { }` (explicit)
3. **Multi-step sequence returning to start?** `PhaseAnimator` (iOS 17+)
4. **Precise timing with multiple tracks?** `KeyframeAnimator` (iOS 17+)
5. **View insertion/removal?** `.transition()` with animation context **outside** the conditional
6. **Sequential chained animations?** `withAnimation(completionCriteria:completion:)` (iOS 17+)

### Core Rules

- **Always** use `.animation(_:value:)` with value parameter — the no-value form is deprecated
- **Place** animation modifiers **after** the properties they animate
- **Prefer** transforms (`offset`, `scaleEffect`, `rotationEffect`) over layout changes
  (`frame`, `padding`) — transforms are GPU-accelerated
- **Scope** animations narrowly to affected subviews
- **Use** `.animation(nil, value:)` to exclude specific properties from animation
- **Use `@Animatable` macro** instead of manual `animatableData` — it synthesizes
  conformance automatically. Mark non-animatable properties with `@AnimatableIgnored`
- **Chain sequential animations** with `withAnimation` completion closures (iOS 17+, not delays):
  ```swift
  withAnimation(.spring, completionCriteria: .logicallyComplete) {
      scale = 2
  } completion: {
      withAnimation(.spring) { scale = 1 }
  }
  ```

**tvOS:** custom `.animation()` on focusable elements can fight the
built-in focus hover effect, causing jitter; scope animation to inner
content instead. For long-running animations on focus change (thumbnail
playback, detail loads), use the token-based settle-delay pattern in
[references/tvos.md](references/tvos.md). The tvOS Simulator does not
replicate focus animations faithfully — verify on hardware.

---

## Scroll Patterns

### Scroll Threshold Gating

When reacting to scroll position, transform to the type you actually need in
`.onScrollGeometryChange` rather than reading raw `CGFloat` and guarding downstream.
This reduces callback frequency at the framework level:

```swift
// BEST — transform to Bool; onChange only fires at threshold crossings
.onScrollGeometryChange(for: Bool.self) { geo in
    geo.contentOffset.y > 50
} onChange: { _, shouldShow in
    if shouldShow != showStickyHeader {
        showStickyHeader = shouldShow
    }
}

// BAD — unguarded write on every frame causes jank
.onScrollGeometryChange(for: CGFloat.self) { geo in
    geo.contentOffset.y
} onChange: { _, offset in
    showStickyHeader = offset > 50  // Fires 60-120x/sec!
}
```

### Programmatic Scrolling

For new code on iOS 17+ / tvOS 17+ / macOS 14+, prefer
`.scrollPosition(id:)` over `ScrollViewReader`. It's the modern,
declarative replacement:

```swift
@State private var scrolledID: Item.ID?

ScrollView {
    LazyVStack {
        ForEach(items) { item in
            ItemRow(item: item).id(item.id)
        }
    }
    .scrollTargetLayout()
}
.scrollPosition(id: $scrolledID)
.onChange(of: items.count) { _, _ in
    if let last = items.last?.id {
        withAnimation { scrolledID = last }
    }
}
```

For pre-17 deployment, `ScrollViewReader` is still supported:

```swift
ScrollViewReader { proxy in
    ScrollView {
        LazyVStack {
            ForEach(items) { item in
                ItemRow(item: item).id(item.id)
            }
            Color.clear.frame(height: 1).id("bottom")
        }
    }
    .onChange(of: items.count) { _, _ in
        withAnimation { proxy.scrollTo("bottom", anchor: .bottom) }
    }
}
```

### Scroll Target Behavior (iOS 17+)

| Behavior | Use Case |
|----------|----------|
| `.scrollTargetBehavior(.paging)` | Full-page snapping |
| `.scrollTargetBehavior(.viewAligned)` | Snap to individual items |

Combine with `.scrollTargetLayout()` on the inner stack and
`containerRelativeFrame()` (also iOS 17+) for full-width pages.

**tvOS:** scrolling is **focus-driven** — a `ScrollView` with no
focusable children is unscrollable. Prefer `.viewAligned` over `.paging`;
full-page jumps on a 1920x1080 display feel jarring. Details and a
fix-it pattern are in [references/tvos.md](references/tvos.md).

### `.visualEffect` (iOS 17+)

Apply position-based visual changes (parallax, opacity fade) without layout side effects.
Unlike `GeometryReader`, this doesn't affect layout — it only applies visual transforms:

```swift
ItemCard(item: item)
    .visualEffect { content, geometry in
        let frame = geometry.frame(in: .scrollView)
        return content.opacity(1 + min(0, frame.minY) / 200)
    }
```

---

## Text Formatting

### `Text(value, format:)` Over `String(format:)`

Always prefer `Text(value, format:)` — it's localization-aware, avoids creating a new
`String` allocation on every body evaluation, and supports accessibility formatting:

```swift
// GOOD — localized, no allocation per render
Text(value, format: .number.precision(.fractionLength(2)))
Text(price, format: .currency(code: "USD"))
Text(ratio, format: .percent.precision(.fractionLength(1)))
Text(date, format: .dateTime.day().month().year())

// AVOID — new String allocation per render, not localization-aware
Text(String(format: "%.1f%%", ratio))
```

### Localized String Operations

| Operation | Modern API |
|-----------|-----------|
| User search filtering | `string.localizedStandardContains(query)` |
| Locale-aware sorting | `strings.sorted { $0.localizedStandardCompare($1) == .orderedAscending }` |
| Case-insensitive check | `string.localizedCaseInsensitiveContains(query)` |

### Label Over HStack

```swift
// GOOD
Label("Settings", systemImage: "gear")

// AVOID
HStack { Image(systemName: "gear"); Text("Settings") }
```

### Text Measurement (iOS 16+)

Use `.onGeometryChange(for:of:action:)` instead of `GeometryReader` for measuring text.
It fires only when the transformed value changes, avoiding unnecessary updates:

```swift
Text(text)
    .onGeometryChange(for: CGFloat.self) { geometry in
        geometry.size.height
    } action: { newValue in
        textHeight = newValue
    }
```

---

## Image Downsampling

For performance-sensitive contexts (scrollable lists, grids), decode and downsample off
the main thread using `CGImageSourceCreateThumbnailAtIndex`:

```swift
actor ImageProcessor {
    /// Caller passes a `displayScale` — usually
    /// `@Environment(\.displayScale)` read in the SwiftUI view that
    /// requests the thumbnail. Avoid `UIScreen.main.scale` (deprecated
    /// since iOS 16 — does not handle multi-window scenes correctly).
    func downsample(data: Data, to targetSize: CGSize, displayScale: CGFloat) -> UIImage? {
        guard let source = CGImageSourceCreateWithData(data as CFData, nil) else {
            return nil
        }
        let maxDim = max(targetSize.width, targetSize.height) * displayScale
        let options: [CFString: Any] = [
            kCGImageSourceThumbnailMaxPixelSize: maxDim,
            kCGImageSourceCreateThumbnailFromImageAlways: true,
            kCGImageSourceCreateThumbnailWithTransform: true,
            kCGImageSourceShouldCache: false
        ]
        guard let cgImage = CGImageSourceCreateThumbnailAtIndex(source, 0, options as CFDictionary) else {
            return nil
        }
        return UIImage(cgImage: cgImage)
    }
}

// Call site
struct ThumbnailView: View {
    @Environment(\.displayScale) private var displayScale
    // ...
    .task { image = await processor.downsample(data: data, to: size, displayScale: displayScale) }
}
```

---

## Navigation Configuration

### Always Use Inline Title Display Mode

Every `.navigationTitle(...)` must be paired with `.navigationBarTitleDisplayMode(.inline)`.
The default large title mode wastes significant vertical space, especially on screens with
toolbars and search bars.

```swift
// GOOD — compact, consistent
.navigationTitle("Library")
.navigationBarTitleDisplayMode(.inline)

// BAD — large title wastes vertical space
.navigationTitle("Library")
```

**When adding `.navigationTitle` to any view, always add `.navigationBarTitleDisplayMode(.inline)` immediately after.**

---

## Review Checklist

### Navigation
- [ ] Every `.navigationTitle(...)` paired with `.navigationBarTitleDisplayMode(.inline)`

### View Composition & Performance
- [ ] Container views use `@ViewBuilder let content: Content` (not closures)
- [ ] Views pass only needed primitive values (not entire model objects)
- [ ] Frequently-rendered views are POD-eligible (simple values, no property wrappers)
- [ ] Complex sections extracted to separate structs (enables skip)
- [ ] Modifiers over conditionals for state changes (preserves identity)
- [ ] State updates gated by value comparison in hot paths
- [ ] Large lists use `LazyVStack`/`LazyHStack`
- [ ] `Self._printChanges()` gated with `#if DEBUG` if present
- [ ] **tvOS:** Focusable POD rows use `@FocusState` binding for stable focus
- [ ] **tvOS:** No `.focusable()` on container wrappers

### Animation
- [ ] Using `.animation(_:value:)` with value parameter (not deprecated form)
- [ ] `withAnimation` for event-driven animations
- [ ] Transitions paired with animation context **outside** conditional
- [ ] Transforms preferred over layout changes for animated properties
- [ ] **tvOS:** No custom `.animation()` fighting focus hover — scope to children
- [ ] **tvOS:** Long-running focus-change animations use token-based settle delay

### Scroll
- [ ] New code uses `.scrollPosition(id:)` (iOS 17+); `ScrollViewReader` for older targets
- [ ] **tvOS:** All scrollable content contains focusable children
- [ ] **tvOS:** Prefer `.viewAligned` over `.paging` for smoother navigation

### Text
- [ ] Using `Text(value, format:)` not `String(format:)`
- [ ] Using `localizedStandardContains()` for user search

## References

- [references/animation-guide.md](references/animation-guide.md) — Animation mechanics, transitions, Animatable, phase/keyframe animators
- [references/performance-guide.md](references/performance-guide.md) — POD views, equatable views, view composition, anti-patterns
- [references/observable-state.md](references/observable-state.md) — `@Observable` + `@MainActor` containers, `@Bindable`, mutation routing, undo snapshots, error surfacing, typed-error taxonomy, **`@AppStorage`-in-`@Observable` silent-failure gotcha**
- [references/tvos.md](references/tvos.md) — tvOS focus engine patterns: focus-driven scrolling, focus hover conflict, settle delay, POD + `@FocusState`, container-`.focusable()` caveats
