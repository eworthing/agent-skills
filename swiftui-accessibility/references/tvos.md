# tvOS Accessibility Patterns

tvOS replaces touch with the Siri Remote's focus engine. That changes
several accessibility patterns: there is no Close button to tap, modal
dismissal happens via the Menu button, and identifier conventions need to
be stable across regions for both VoiceOver and UI-test navigation.

## Modal Dismissal: Menu Button, Not Close Button

On iOS and macOS, modals usually carry an explicit Close / Cancel button.
On tvOS, the canonical dismissal is the **Menu button** on the Siri
Remote, surfaced in code via `.onExitCommand`.

```swift
// CORRECT on tvOS — Menu button dismisses; no visible Close button
.fullScreenCover(isPresented: $showModal) {
    SettingsContent()
        .onExitCommand { showModal = false }
}

// WRONG on tvOS — Close buttons clutter the layout and confuse focus
.fullScreenCover(isPresented: $showModal) {
    SettingsContent()
        .toolbar {
            Button("Close") { showModal = false }  // unfocusable on tvOS in some layouts
        }
}
```

If a modal needs an explicit dismiss action visible on tvOS (e.g., a
confirmation step), make it a real focusable element inside the modal,
not chrome.

## Cross-Platform Dismiss Pattern

For shared modal content across iOS/macOS/tvOS, branch the close affordance:

```swift
ModalContent()
    .onExitCommand { dismiss() }           // tvOS Menu button
#if !os(tvOS)
    .overlay(alignment: .topTrailing) {
        Button("Close") { dismiss() }
            .accessibilityIdentifier("MyScreen_CloseButton")
    }
#endif
```

`.onExitCommand` is a no-op on iOS/macOS, so it's safe to apply on every
platform — but the visible Close button must be `#if !os(tvOS)`.

## VoiceOver on tvOS

VoiceOver on tvOS uses focus traversal, not direct touch. Implications:

- **Focus order matters more.** VoiceOver reads elements in focus order
  (driven by `.focusable()` and `@FocusState`), not visual order. Verify
  that the focus path covers every readable element.
- **Don't manually reassert focus.** Setting `isFocused = true` from
  `DispatchQueue.main.asyncAfter` hijacks events VoiceOver and Switch
  Control expect to handle themselves. Use focus containment (modals via
  `.fullScreenCover()`, scoped `@FocusState`) instead.
- **No `.accessibilityAddTraits(.isButton)` on focus helpers.** A
  zero-size `Rectangle().fill(.clear)` used purely to capture focus
  should be `.accessibilityHidden(true)`. Otherwise VoiceOver will
  announce a spurious "Button" with no label.

## Destructive Dialog Default Focus

Destructive `confirmationDialog` / `alert` cases on tvOS are severity-1
when wrong: the focus engine places initial focus on the first button in
declaration order, so a destructive button declared first is one Select
press away from accidental data loss.

```swift
// CORRECT on tvOS — Cancel declared first, gets default focus
.confirmationDialog("Delete All?", isPresented: $confirm) {
    Button("Cancel", role: .cancel) { }
    Button("Delete All", role: .destructive) { delete() }
} message: {
    Text("This cannot be undone.")
}
```

The same rule is good practice on iOS/macOS, but on tvOS it is enforced
by the physical interaction model — there is no pointer to override the
default focus.

## Identifier Naming Convention

Even on a single-platform app, drifting identifier names will break UI
tests across refactors. Adopt a typed-enum pattern so the test target and
app target share a single source of truth:

```swift
// In a small file shared between app and test targets
enum ScreenIdentifiers {
    enum MyScreen {
        static let root = "MyScreen_Root"
        static let close = "MyScreen_CloseButton"
        static let primaryAction = "MyScreen_PrimaryAction"
    }

    enum Settings {
        static let root = "Settings_Root"
        static let appearanceToggle = "Settings_AppearanceToggle"
    }
}
```

Apply them via the constants, not string literals:

```swift
Button("Save") { save() }
    .accessibilityIdentifier(ScreenIdentifiers.MyScreen.primaryAction)
```

Naming rules:

- Root identifiers end in `_Root` (paired with the marker pattern from
  the `xctest-ui-testing` skill).
- Component identifiers follow `<Screen>_<Component>` — that gives every
  test target a stable prefix to grep when a screen is renamed.
- Avoid identifiers that include user data (`"Item_\(item.name)"`). Use
  the stable id (`"Item_\(item.id)"`).

For the cross-platform marker view used to attach a root identifier to a
container without violating the leaf-only identifier rule, see the
`AccessibilityMarkerView` code in the `xctest-ui-testing` skill — UIKit
and AppKit implementations are provided there.

## tvOS Focus Settle / Modal Containment

For tvOS-specific focus settle delays, modal focus containment
verification, and `.fullScreenCover` vs `.sheet` differences, see the
`xctest-ui-testing` skill's `references/tvos.md` and the
`swiftui-design-review` skill's `references/liquid-glass-and-tvos.md`.
This file covers the accessibility-layer rules; those cover the
UI-testing and design-review angles on the same focus system.
