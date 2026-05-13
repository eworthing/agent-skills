---
name: swiftui-accessibility
author: eworthing
original-author: Antoine van der Lee (AvdLee)
source: https://github.com/AvdLee/SwiftUI-Agent-Skill
description: >-
  SwiftUI accessibility deltas for iOS, macOS, and tvOS: typed-enum
  identifier-as-API-contract pattern, cross-platform
  `AccessibilityMarkerView` (UIKit + AppKit) for root-marker overlays,
  destructive confirmation dialog focus ordering, and tvOS Menu-button
  dismissal. Use when wiring or renaming `accessibilityIdentifier`
  values that UI tests depend on, attaching root markers to modal
  containers without violating the leaf-only identifier rule, building
  destructive `confirmationDialog` / `alert` cases where default focus
  ordering must protect against accidental data loss (severity-1 on
  tvOS), or implementing Menu-button dismissal for modals on tvOS.
  Generic VoiceOver / traits / Dynamic Type guidance lives in the
  authoritative `swiftui-expert-skill` (`references/accessibility-patterns.md`).
allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Bash
---

# SwiftUI Accessibility Deltas

## Scope

Project-specific accessibility patterns that augment the authoritative
`swiftui-expert-skill` (`references/accessibility-patterns.md`). This
skill owns four deltas:

1. **Identifier-as-API-contract** — typed-enum pattern, rename order
2. **`AccessibilityMarkerView`** — cross-platform UIKit + AppKit marker
3. **Destructive dialog focus ordering** — severity-1 on tvOS
4. **tvOS Menu-button dismissal** — see [references/tvos.md](references/tvos.md)

For generic VoiceOver, traits, labels, Dynamic Type, Reduce Motion, and
custom actions guidance, defer to
`swiftui-expert-skill` `references/accessibility-patterns.md`.

| Concern | Skill |
|---|---|
| General VoiceOver / labels / traits / Dynamic Type / reduce motion | `swiftui-expert-skill` (`references/accessibility-patterns.md`) |
| tvOS focus engine (hover conflict, settle delay, focus-driven scroll) | `swiftui-tvos-focus` |
| UI testing patterns and root-marker discovery | `xctest-ui-testing` |
| Design review (modal focus containment, glass-on-glass) | `swiftui-design-review` |
| Cross-platform conditionals (`#if os(tvOS)`, haptics) | `apple-multiplatform` |

## 1. Identifiers as a Stable API Contract

Accessibility identifiers are an API contract between the app and the UI
test target. Renaming an identifier is an API migration, not a
refactor. Wrong order produces a test-suite outage between the two
commits.

### Rename Order

1. Update test code (and any testability documentation) to reference the
   new identifier value **first**.
2. Update the view's `.accessibilityIdentifier(...)` to the new value
   **second**.

### Typed-Enum Single Source of Truth

Use a typed enum shared between app and test targets. Never inline raw
identifier strings in either side — inline strings drift the moment one
side renames and the other does not.

```swift
// Shared between app and test targets
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

// View
Button("Save") { save() }
    .accessibilityIdentifier(ScreenIdentifiers.MyScreen.primaryAction)

// Test
app.buttons[ScreenIdentifiers.MyScreen.primaryAction].tap()
```

Naming rules:

- Root identifiers end in `_Root` (paired with the marker pattern below).
- Component identifiers follow `<Screen>_<Component>` — gives every test
  target a stable prefix to grep when a screen is renamed.
- Avoid identifiers that include user data (`"Item_\(item.name)"`). Use
  the stable id (`"Item_\(item.id)"`).

### Identifier Placement: Leaves Only

Adding `.accessibilityIdentifier()` to a container with
`.accessibilityElement(children: .contain)` makes the identifier
unreliable for UI testing — the identifier conflicts with the child
element tree.

```swift
// WRONG — identifier on container
VStack {
    Text("Label")
    Button("Action") { }
}
.accessibilityElement(children: .contain)
.accessibilityIdentifier("myContainer")  // VIOLATION

// CORRECT — identifier on leaf, marker overlay for the container
VStack {
    Text("Label")
    Button("Action") { }
        .accessibilityIdentifier("myButton")
}
.accessibilityElement(children: .contain)
.overlay(alignment: .topLeading) {
    AccessibilityMarkerView(identifier: "MyScreen_Root")
        .frame(width: 1, height: 1)
}
```

## 2. `AccessibilityMarkerView` — Cross-Platform Root Marker

The plain SwiftUI `Color.clear` marker pattern works on iOS but is
**unreliable on macOS** — `Color.clear` overlays do not always reach
the AppKit accessibility tree. UIKit and AppKit native views reliably
expose identifiers across all three platforms.

```swift
#if canImport(UIKit)
import UIKit

struct AccessibilityMarkerView: UIViewRepresentable {
    let identifier: String

    func makeUIView(context: Context) -> UIView {
        let v = UIView()
        v.isAccessibilityElement = true
        v.accessibilityIdentifier = identifier
        v.isUserInteractionEnabled = false
        return v
    }

    func updateUIView(_ uiView: UIView, context: Context) {
        uiView.accessibilityIdentifier = identifier
    }
}
#elseif canImport(AppKit)
import AppKit

struct AccessibilityMarkerView: NSViewRepresentable {
    let identifier: String

    final class MarkerView: NSView {
        let identifier: String
        init(identifier: String) {
            self.identifier = identifier
            super.init(frame: .zero)
            setAccessibilityIdentifier(identifier)
            setAccessibilityElement(true)
        }
        required init?(coder: NSCoder) { nil }
    }

    func makeNSView(context: Context) -> NSView {
        MarkerView(identifier: identifier)
    }

    func updateNSView(_ nsView: NSView, context: Context) {}
}
#endif
```

Apply as a 1×1 overlay on the container that needs a root identifier:

```swift
.overlay(alignment: .topLeading) {
    AccessibilityMarkerView(identifier: "Settings_Root")
        .frame(width: 1, height: 1)
}
```

UI tests then `waitForExistence` on `app.otherElements["Settings_Root"]`
to reliably detect modal presentation.

## 3. Destructive Confirmation Dialog Focus Ordering

`confirmationDialog` / `alert` initial focus follows declaration order.
On tvOS this is **severity-1** — there is no pointer to override
default focus, so a destructive button declared first is one Select
press away from accidental data loss. On iOS / macOS the same pattern
is good practice; on tvOS it is mandatory.

```swift
// CORRECT — safe option declared first, gets default focus
.confirmationDialog("Delete All Items?", isPresented: $showDeleteConfirm) {
    Button("Cancel", role: .cancel) { }
    Button("Delete All", role: .destructive) { deleteAll() }
} message: {
    Text("This cannot be undone.")
}
```

### Button Ordering Matrix

| Dialog type | First button (default focus) | Second button |
|---|---|---|
| Destructive | Cancel / Keep | Delete / Remove |
| Confirmation | Cancel / No | Confirm / Yes |
| Discard changes | Keep Editing | Discard |

## 4. tvOS Menu-Button Dismissal

Full reference: [references/tvos.md](references/tvos.md).

On tvOS the canonical modal dismissal is the Siri Remote Menu button,
surfaced via `.onExitCommand`. Do not place a visible Close button on
tvOS — it clutters the layout and can break focus traversal. Use a
cross-platform branch when sharing modal content:

```swift
ModalContent()
    .onExitCommand { dismiss() }           // tvOS Menu button (no-op on iOS/macOS)
#if !os(tvOS)
    .overlay(alignment: .topTrailing) {
        Button("Close") { dismiss() }
            .accessibilityIdentifier(ScreenIdentifiers.MyScreen.close)
    }
#endif
```

## Review Checklist

### Identifier API
- [ ] All identifier strings come from a shared typed-enum source of truth (no inline literals in views or tests)
- [ ] Identifier renames updated in tests **before** views
- [ ] No `.accessibilityIdentifier()` on containers with `.accessibilityElement(children: .contain)`
- [ ] Root markers attached via `AccessibilityMarkerView`, not `Color.clear`
- [ ] No user data in identifiers (`item.id`, not `item.name`)

### Destructive Dialogs
- [ ] Destructive `confirmationDialog` / `alert` declares safe button first
- [ ] tvOS destructive dialogs verified on hardware (default focus = safe option)

### tvOS
- [ ] Modals use `.onExitCommand { dismiss() }` for Menu-button dismissal
- [ ] Close buttons gated `#if !os(tvOS)` on cross-platform modals
- [ ] Focus helpers (zero-size tap targets) marked `.accessibilityHidden(true)`, not `.isButton`
- [ ] No manual `isFocused = true` from `DispatchQueue.main.asyncAfter` (hijacks VoiceOver / Switch Control)

## References

- [references/tvos.md](references/tvos.md) — Menu-button dismissal, focus traversal rules, VoiceOver on tvOS, identifier naming convention, focus-helper anti-patterns
