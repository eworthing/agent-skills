---
name: xctest-ui-testing
author: eworthing
description: >-
  Writes and debugs XCTest UI automation for iOS, macOS, and tvOS apps. Covers
  accessibility identifiers, root-marker patterns for modal detection, wait-for-element
  strategies, drag-and-drop tests, sheet/alert testing, macOS activation/window-pinning
  helpers, platform divergence handling, and the new-component testability checklist.
  Use when writing or debugging UI tests, investigating flaky or timing-sensitive
  failures, wiring accessibility identifiers, introducing a new modal/sheet/overlay/screen
  that needs test coverage, or working on cross-platform XCUITest infrastructure.
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - Glob
  - Grep
---

# UI Testing Skill

## Overview

XCTest UI automation patterns for iOS (iPhone + iPad). Covers accessibility
identifiers, wait-for-element strategies, and common pitfalls.

## When to Use

- Writing new UI tests
- Debugging test failures or flaky tests
- Adding accessibility identifiers to views
- Understanding XCUITest patterns on iOS
- Introducing a new modal, sheet, overlay, or screen that needs test coverage

## Running Tests

Use `xcodebuild test` or your project's test script:

```bash
# Run all UI tests
xcodebuild test -scheme YourApp -destination 'platform=iOS Simulator,name=iPhone 16'

# Run a specific test class
xcodebuild test -scheme YourApp -destination 'platform=iOS Simulator,name=iPhone 16' \
  -only-testing:YourAppUITests/SomeTestClass

# Run a specific test method
xcodebuild test -scheme YourApp -destination 'platform=iOS Simulator,name=iPhone 16' \
  -only-testing:YourAppUITests/SomeTestClass/testSpecificMethod
```

## Deterministic UI Test Launch

UI tests should launch with specific arguments to enable deterministic behavior:

```swift
let app = XCUIApplication()
app.launchArguments.append("-uiTest")  // Enables deterministic test data
app.launch()
```

You can also pass arguments to present specific screens directly, avoiding
flaky navigation steps:

```swift
app.launchArguments.append(contentsOf: ["-uiTestPresent", "someScreen"])
```

Handle these in your app's startup code to route directly to the target screen.

## Accessibility Identifier Conventions

### General Rules

1. Identifiers belong on **leaf** elements (buttons, fields, labels), not containers
2. Never assign `.accessibilityIdentifier()` to a parent with `.accessibilityElement(children: .contain)` -- the identifier won't propagate correctly
3. Use a consistent naming pattern: `ComponentName_ElementName`

### Root Markers for Modals

To reliably detect whether a modal or overlay is presented, place a small
invisible marker view with a known identifier:

```swift
.overlay(alignment: .topLeading) {
    Color.clear
        .frame(width: 1, height: 1)
        .accessibilityIdentifier("MyModal_Root")
}
```

This approach works because:
- The 1x1 frame doesn't affect layout
- The identifier is always in the accessibility tree when the view is presented
- Tests can use `waitForExistence` on this marker for reliable timing

If plain SwiftUI accessibility doesn't surface reliably (especially on macOS,
where `Color.clear` markers don't always reach the AppKit accessibility tree),
wrap a platform-native view in a `UIViewRepresentable` /
`NSViewRepresentable`:

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
    func makeNSView(context: Context) -> NSView { MarkerView(identifier: identifier) }
    func updateNSView(_ nsView: NSView, context: Context) {}
}
#endif
```

Use it as the marker overlay:

```swift
.overlay(alignment: .topLeading) {
    AccessibilityMarkerView(identifier: "MyModal_Root")
        .frame(width: 1, height: 1)
}
```

UIKit/AppKit native views reliably expose identifiers to the accessibility tree
across all three platforms; `Color.clear` does not.

## Test Patterns

### Wait for Element

The most important pattern in UI testing -- never assume elements are
immediately available:

```swift
func waitForElement(_ element: XCUIElement, timeout: TimeInterval = 5) {
    XCTAssertTrue(element.waitForExistence(timeout: timeout),
                  "Element \(element) did not appear within \(timeout)s")
}
```

### Tap and Wait for Result

```swift
let button = app.buttons["SubmitButton"]
button.tap()

let confirmation = app.staticTexts["ConfirmationLabel"]
XCTAssertTrue(confirmation.waitForExistence(timeout: 5))
```

### Drag and Drop

```swift
let sourceItem = app.buttons["Card_abc123"]
let targetArea = app.otherElements["DropTarget_A"]
sourceItem.press(forDuration: 0.5, thenDragTo: targetArea)
```

### Sheet and Modal Testing

```swift
// Trigger sheet presentation
app.buttons["ShowSettings"].tap()

// Wait for sheet root marker
let sheetRoot = app.otherElements["Settings_Root"]
XCTAssertTrue(sheetRoot.waitForExistence(timeout: 5))

// Interact with sheet content
app.switches["DarkModeToggle"].tap()

// Dismiss (swipe down or tap close)
app.buttons["Settings_Close"].tap()

// Verify dismissal
XCTAssertFalse(sheetRoot.waitForExistence(timeout: 2))
```

### Confirmation Dialog Testing

```swift
// Trigger destructive action
app.buttons["DeleteButton"].tap()

// Wait for alert
let alert = app.alerts.firstMatch
XCTAssertTrue(alert.waitForExistence(timeout: 5))

// Verify alert content and confirm
XCTAssertTrue(alert.staticTexts["Are you sure?"].exists)
alert.buttons["Delete"].tap()
```

### Sheet Detent Testing (iOS 16+)

When testing sheets with `.presentationDetents()`, verify behavior at
different detent sizes by checking element visibility.

## macOS-Specific Patterns

### Ensure App Is Frontmost Before Events

XCUITest on macOS sends keyboard and click events to whatever window has key
status. If your app isn't frontmost, events go to the wrong window (Xcode,
the simulator, Finder) and fail silently. **Always** activate the app before
keyboard or click events. Use escalating strategies — `XCUIApplication.activate()`
alone is not reliable on every macOS release:

```swift
import AppKit
import XCTest

func ensureAppIsFrontmost(_ app: XCUIApplication,
                          bundleIdentifier: String,
                          timeout: TimeInterval = 5) {
    // 1. XCUIApplication.activate() — works most of the time
    app.activate()

    let deadline = Date().addingTimeInterval(timeout)
    while Date() < deadline {
        if NSWorkspace.shared.frontmostApplication?.bundleIdentifier == bundleIdentifier {
            return
        }
        // 2. NSRunningApplication direct activation
        if let running = NSRunningApplication.runningApplications(
                            withBundleIdentifier: bundleIdentifier
                        ).first {
            running.activate(options: [.activateIgnoringOtherApps])
        }
        Thread.sleep(forTimeInterval: 0.1)
    }
    // 3. Last resort: AppleScript / Dock click (project-specific helper)
}
```

Call this immediately after `app.launch()` and before any `typeKey`, `tap()`,
or coordinate-based action.

### Pin Window Size for Stable Coordinates

Coordinate-based tests (drag, click-at-position) on macOS are sensitive to
window size. Pin a known size in `-uiTest` mode:

```swift
#if os(macOS)
import AppKit

@MainActor
func pinTestWindowSize() {
    guard ProcessInfo.processInfo.arguments.contains("-uiTest"),
          let window = NSApplication.shared.windows.first else {
        return
    }
    window.setContentSize(NSSize(width: 1280, height: 800))
    window.styleMask.remove(.resizable)
    window.center()
}
```

Call from your app's first scene/window after launch. Tests then reason in a
fixed coordinate space regardless of the developer's display resolution.

### Toolbar / Keyboard Reliability

- SwiftUI toolbar backed by `NSToolbar` does **not** expose individual toolbar
  items reliably to the accessibility tree. Prefer menu items / keyboard
  shortcuts for toolbar actions in tests.
- `typeKey` can be unreliable across macOS releases — prefer menu bar
  navigation (`app.menuBars.menuItems["Action Name"].click()`) when available.
- Always call `ensureAppIsFrontmost(_:bundleIdentifier:)` before any
  keyboard-based interaction.

## Platform Divergences Matrix

Cross-platform XCUITest exposes the same `XCUIApplication` API, but the
underlying interaction model differs.

| Feature | iOS | tvOS | macOS |
|---------|-----|------|-------|
| Toolbar buttons | Direct accessibility identifier | Via focus navigation | `NSToolbar`-backed; often not exposed — use menu bar |
| Modal dismissal | Tap close / swipe down | `XCUIRemote.shared.press(.menu)` | Tap close / `typeKey(.escape, ...)` |
| Drag & drop | `press(forDuration:thenDragTo:)` | Not supported | `press(forDuration:thenDragTo:)` (window-pinned) |
| Keyboard | `typeText` / `typeKey` | Limited | `typeKey` + frontmost activation required |
| Activation | Not applicable | Not applicable | **Required before every event burst** |
| Coordinate stability | Layout-driven | Layout-driven | **Pin window size in `-uiTest`** |
| Focus assertions | N/A | `element.hasFocus` | N/A |

For tvOS-specific patterns (Siri Remote, focus assertions, focus reachability
audits, modal focus containment), see
[references/tvos.md](references/tvos.md).

## Critical Gotchas

### LazyVStack Hides Accessibility Elements

LazyVStack only instantiates visible items, so off-screen items won't
appear in the accessibility tree. This is the most common cause of
"element not found" failures in scrollable lists.

```swift
// Problem: elements not discoverable in tests
LazyVStack {
    ForEach(items) { item in
        ItemView(item: item)
            .accessibilityIdentifier("Item_\(item.id)")
    }
}

// Solution: use VStack in test mode so all items are instantiated
let isUITest = ProcessInfo.processInfo.arguments.contains("-uiTest")

if isUITest {
    VStack { content }  // All items instantiated for tests
} else {
    LazyVStack { content }  // Performance in production
}
```

### Duplicate Accessibility Identifiers

Without `.combine`, child elements get separate accessibility entries,
causing duplicate identifiers:

```swift
// Problem: creates duplicate Card_ identifiers
Button { ... } label: {
    VStack {
        Image(...)
        Text(...)
    }
}
.accessibilityIdentifier("Card_\(item.id)")

// Solution: combine children first
Button { ... } label: { ... }
    .accessibilityElement(children: .combine)
    .accessibilityIdentifier("Card_\(item.id)")
```

### Modifier Order Matters

Accessibility modifiers must be applied in this order to work correctly:

```swift
.accessibilityElement(children: .combine)  // 1. Combine children
.accessibilityIdentifier("Card_\(id)")     // 2. Set identifier
.accessibilityLabel(item.name ?? "")       // 3. Set label
.accessibilityAddTraits(.isButton)         // 4. Add traits
```

Reversing the order (e.g., setting identifier before combine) can cause
the identifier to be lost.

## Debugging Tips

### Element Not Found

```swift
// Print the full accessibility tree to find what's available
print(app.debugDescription)
```

### Flaky Tests

Common causes:
1. Missing `waitForExistence` — element not yet rendered
2. Animation in progress — use `waitForExistence` after taps that trigger animations
3. Keyboard blocking elements — dismiss keyboard first: `app.keyboards.buttons["Return"].tap()`
4. Stale element references — re-query after navigation changes

## New Component Checklist

When adding a new modal, sheet, overlay, or screen, follow the 8-step
testability checklist before merging. See
[references/new-component-checklist.md](references/new-component-checklist.md)
for the full checklist (cross-checking presentations vs markers,
TestIdentifiers enum, direct-launch support, dialog/detent tests,
`.xcodeproj` integration, and cross-platform verification).

## Constraints

- Apply identifiers to leaf elements only (buttons, fields, text)
- Never use LazyVStack for content that needs UI testing without a test-mode fallback
- Keep individual tests under 15 seconds to prevent timeouts
- Use `waitForExistence` instead of `Thread.sleep` for timing
- Use existing identifier naming patterns in the project for consistency
