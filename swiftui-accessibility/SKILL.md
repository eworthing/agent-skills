---
name: swiftui-accessibility
author: eworthing
original-author: Antoine van der Lee (AvdLee)
source: https://github.com/AvdLee/SwiftUI-Agent-Skill
description: >-
  Ensures accessible, VoiceOver-friendly interactive SwiftUI UI on iOS,
  macOS, and tvOS with correct identifiers, labels, traits, and focus
  behavior. Use when adding or changing buttons, toggles, forms, sheets,
  or screens, fixing accessibility / VoiceOver / a11y /
  accessibilityIdentifier issues, applying tvOS Menu-button dismissal,
  setting up typed-enum identifier naming for UI tests, or ensuring safe
  default focus on destructive confirmation dialogs.
allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Bash
---

# Accessibility Compliance

## Purpose

Ensures VoiceOver compatibility, proper accessibility semantics, and
correct identifier placement for iOS, macOS, and tvOS apps. For tvOS
focus-engine specifics (Menu-button dismissal, focus traversal rules,
typed-enum identifier naming convention) see
[references/tvos.md](references/tvos.md).

## When to Use This Skill

- Adding interactive UI elements or custom controls
- Adding accessibility identifiers for UI testing
- User says "fix a11y", "VoiceOver support", "accessibility audit"
- Code review flags accessibility concerns

## Workflow

### Step 1: Audit Accessibility Patterns

```bash
# Find potential violations
rg '\.accessibilityIdentifier\(|\.accessibilityLabel\(|\.accessibilityHint\(' --glob '*.swift'

# Find tap gestures that should be buttons
rg '\.onTapGesture' --glob '*.swift'

# Find containers that use .contain
rg 'accessibilityElement\(children:\s*\.contain\)' --glob '*.swift'
```

### Step 2: Apply Correct Patterns

#### Identifier Placement Rule

Apply identifiers to LEAF elements only. Adding `.accessibilityIdentifier()` to a container with `.accessibilityElement(children: .contain)` causes the identifier to conflict with the child element tree, making it unreliable for UI testing.

```swift
// WRONG - identifier on container
VStack {
    Text("Label")
    Button("Action") { }
}
.accessibilityElement(children: .contain)
.accessibilityIdentifier("myContainer")  // VIOLATION

// CORRECT - identifier on leaf element
VStack {
    Text("Label")
    Button("Action") { }
        .accessibilityIdentifier("myButton")
}
.accessibilityElement(children: .contain)
```

#### Decision Tree: Removing an Identifier from a Container

When you find an `.accessibilityIdentifier()` on a container with `.contain`:

1. **Check UI tests** — does any test reference this identifier?
2. **If yes** — replace with a hidden marker view overlay (see below)
3. **If no** — simply remove the identifier

The hidden marker view pattern provides a reliable, zero-size accessibility element for UI test discovery without interfering with the container's child semantics:

```swift
// Hidden marker view for UI test discovery
VStack { /* content */ }
    .accessibilityElement(children: .contain)
    .overlay(alignment: .topLeading) {
        Color.clear
            .frame(width: 1, height: 1)
            .accessibilityElement()
            .accessibilityIdentifier("MyScreen_Root")
            .accessibilityHidden(true)  // Hidden from VoiceOver but visible to XCUITest
    }
```

For cross-platform reliability (the `Color.clear` overlay is occasionally
unreliable on macOS), use the `AccessibilityMarkerView` pattern from the
`xctest-ui-testing` skill — it provides concrete UIKit and AppKit
implementations of a zero-size accessibility marker. Identifier naming
convention (typed-enum, `<Screen>_Root` suffix) is in
[references/tvos.md](references/tvos.md).

#### Button vs Tap Gesture

Buttons provide built-in accessibility traits. Using `.onTapGesture` on non-button elements makes them invisible to VoiceOver as interactive controls.

```swift
// WRONG - tap gesture on non-button
Text("Click me")
    .onTapGesture { action() }

// CORRECT - use Button for actionable content
Button("Click me") { action() }
    .buttonStyle(.plain)
```

#### Icon Buttons Must Include Text

Buttons with image labels must always include text for VoiceOver, even if invisible.
Prefer the Button initializer that natively includes a text label:

```swift
// BEST - text label built into initializer (VoiceOver reads "Add Item")
Button("Add Item", systemImage: "plus", action: addItem)

// ACCEPTABLE - manual label
Button { addItem() } label: {
    Image(systemName: "plus")
}
.accessibilityLabel("Add Item")

// WRONG - no text label at all
Button { addItem() } label: {
    Image(systemName: "plus")
}
```

The same applies to `Menu`: use `Menu("Options", systemImage: "ellipsis.circle") { }`
rather than an image-only label.

#### Decorative Images

For images that are purely decorative, use `Image(decorative:)` instead of adding `accessibilityHidden()` after the fact:

```swift
// BEST - decorative initializer (automatically hidden from VoiceOver)
Image(decorative: "backgroundPattern")

// ACCEPTABLE - manual hiding
Image("backgroundPattern")
    .accessibilityHidden(true)
```

#### Modal Dimmer Pattern

```swift
// WRONG - backdrop is an accessibility button
Color.black.opacity(0.5)
    .accessibilityAddTraits(.isButton)
    .accessibilityLabel("Close")

// CORRECT - backdrop is hidden from VoiceOver, explicit close button provided
Color.clear
    .background(.regularMaterial)
    .ignoresSafeArea()
    .accessibilityHidden(true)

#if !os(tvOS)
Button("Close") { dismiss() }
    .accessibilityIdentifier("CloseButton")
#endif
```

On tvOS, dismiss via the Menu button (`.onExitCommand { dismiss() }`)
instead of an explicit Close button — see
[references/tvos.md](references/tvos.md).

#### Focus Management Tap Areas

```swift
// WRONG - button trait on focus helper
Rectangle()
    .fill(.clear)
    .accessibilityAddTraits(.isButton)
    .onTapGesture { focusItem() }

// CORRECT - hide non-actionable focus helpers
Rectangle()
    .fill(.clear)
    .accessibilityHidden(true)
    .onTapGesture { focusItem() }
```

### Step 3: VoiceOver Custom Actions

Use `.accessibilityActions { }` to expose custom actions for VoiceOver users:

```swift
// CORRECT - closure syntax with ViewBuilder
ItemView(item: item)
    .accessibilityActions {
        Button("Move Up") { moveItemUp(item.id) }
        Button("Move Down") { moveItemDown(item.id) }
        Button("Delete") { deleteItem(item.id) }
    }

// WRONG - passing view directly (syntax error)
.accessibilityActions(myActionsView)  // Error: expects closure
```

**Key point:** The `.accessibilityActions { }` modifier requires a ViewBuilder closure
containing Buttons, not a view passed as a parameter.

### Step 4: Reduce Motion

Respect the `accessibilityReduceMotion` environment value. When enabled, replace
motion-based animations with opacity fades or remove them entirely:

```swift
@Environment(\.accessibilityReduceMotion) var reduceMotion

SomeView()
    .animation(reduceMotion ? nil : .spring, value: isExpanded)
    .opacity(reduceMotion && !isVisible ? 0 : 1)
```

### Step 5: Voice Control Input Labels

Use `.accessibilityInputLabels()` for buttons with complex or frequently changing labels:

```swift
Button("\(category.label) (\(category.items.count) items)") { selectCategory() }
    .accessibilityInputLabels(["Select category", category.label])
```

### Step 6: Semantic Labels

Provide meaningful labels for custom controls:

```swift
Button {
    toggleFavorite()
} label: {
    Image(systemName: isFavorite ? "star.fill" : "star")
}
.accessibilityLabel(isFavorite ? "Remove from favorites" : "Add to favorites")
.accessibilityIdentifier("FavoriteButton")
```

### Step 7: Manual VoiceOver Testing

1. Enable VoiceOver (triple-click side button on iOS)
2. Navigate through the interface
3. Verify announcements are meaningful
4. Ensure all interactive elements are reachable
5. Check focus order makes sense

## Confirmation Dialog Accessibility

### Safe Default Focus

Destructive confirmation dialogs should have the safe option (Cancel/Keep) focused by default to prevent accidental data loss. On tvOS this is severity-1 — the focus engine puts initial focus on the first button in declaration order, and there is no pointer to override it. Declaring a destructive button first puts data one Select press away.

```swift
// CORRECT - Cancel is default focused (appears first)
.confirmationDialog("Delete All Items?", isPresented: $showDeleteConfirm) {
    Button("Cancel", role: .cancel) { }
    Button("Delete All", role: .destructive) { deleteAll() }
} message: {
    Text("This cannot be undone.")
}
```

### Button Ordering Patterns

| Dialog Type | First Button (Default Focus) | Second Button |
|-------------|------------------------------|---------------|
| Destructive | Cancel / Keep | Delete / Remove |
| Confirmation | Cancel / No | Confirm / Yes |
| Discard changes | Keep Editing | Discard |

## Toast & Notification Accessibility

### Screen Reader Announcements

Toasts must announce their content to VoiceOver users:

```swift
struct ToastView: View {
    let message: String

    var body: some View {
        HStack {
            Image(systemName: "checkmark.circle.fill")
            Text(message)
        }
        .accessibilityElement(children: .combine)
        .accessibilityLabel(message)
        .accessibilityAddTraits(.updatesFrequently)
    }
}
```

### Live Region Announcements (iOS 17+)

```swift
.onChange(of: toastMessage) { _, newMessage in
    if let message = newMessage {
        AccessibilityNotification.Announcement(message).post()
    }
}
```

### Toast Accessibility Requirements

| Requirement | Implementation |
|-------------|----------------|
| Auto-announce on appear | `AccessibilityNotification.Announcement` |
| Pausable by VoiceOver | Don't auto-dismiss while VoiceOver reading |
| Readable content | `.accessibilityLabel` with full message |
| Non-blocking | Toast should not trap focus or block navigation |

## Common Mistakes to Avoid

1. **Identifier on container** — Never add `.accessibilityIdentifier()` to elements with `.accessibilityElement(children: .contain)`
2. **Button trait on non-buttons** — Dimmers and tap helpers should use `.accessibilityHidden(true)`
3. **Missing labels on icon-only buttons** — Use `Button("Label", systemImage:, action:)` initializer
4. **Duplicate announcements** — One close mechanism is enough
5. **Tap gesture instead of Button** — Always prefer `Button` for actionable content
6. **`Image("name")` for decorative images** — Use `Image(decorative:)` instead
7. **Ignoring Reduce Motion** — Gate animations with `accessibilityReduceMotion`
