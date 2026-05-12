---
name: xctest-ui-testing
author: eworthing
description: >-
  Writes and debugs XCTest UI automation for BenchHype screens and flows. Relevant
  when adding UI tests, investigating flaky or timing-sensitive UI failures, wiring
  accessibility identifiers to support UI automation, or introducing a new modal,
  sheet, overlay, or screen that should be covered by UI tests from the start.
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

If plain SwiftUI accessibility doesn't surface reliably, wrap a UIKit
view (UIViewRepresentable) with the identifier set on the native UIView.

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

## Adding Test Files to Xcode Project

New UI test files must be added to the Xcode project to compile and run.
Unlike SwiftPM where files are auto-discovered, `.xcodeproj` requires
explicit file references in `project.pbxproj`.

For each new test file, add entries to:
1. **PBXBuildFile** section
2. **PBXFileReference** section
3. **UITests PBXGroup** children
4. **UITests PBXSourcesBuildPhase** files

Generate UUIDs for the file reference and build file entries:
```bash
uuidgen | tr -d '-' | cut -c1-24  # FileRef UUID
uuidgen | tr -d '-' | cut -c1-24  # BuildFile UUID
```

Verify the file is included:
```bash
xcodebuild test -scheme YourApp -list | grep YourNewTestClass
```

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

When adding a new modal, sheet, overlay, or screen, follow this checklist to ensure
it is testable from the start.

### 1. Cross-Check Presentations vs Root Markers

After adding or changing a `.sheet` or `.fullScreenCover`, verify that
each destination view has a root marker (see "Root Markers for Modals" above).

```bash
# Find all presentation sites
rg '\.sheet\(|\.fullScreenCover\(' --glob '*.swift' YourApp/Views -n
```

### 2. Create a TestIdentifiers Enum

In your UI test target, create a section for the component's identifiers.
This gives tests a single source of truth:

```swift
// MARK: - MyComponent

enum MyComponent {
    static let root = "MyComponent_Root"
    static let close = "MyComponent_Close"
    static let tabPrefix = "MyComponent_Tab_"
    static let searchField = "MyComponent_SearchField"
}
```

### 3. Add Direct Launch Support (Optional but Recommended)

Enable launching the app directly to this screen for faster, more
reliable tests:

```swift
// In your app's launch argument handling
if ProcessInfo.processInfo.arguments.contains("-uiTestPresent") {
    if let screenArg = /* parse the argument */ {
        switch screenArg {
        case "myComponent":
            // Navigate directly to MyComponent
        }
    }
}
```

### 4. Update Testability Documentation

Document the new identifiers in your project's testability docs:

```markdown
**MyComponent (modal)**

- `MyComponent_Root` (root marker)
- `MyComponent_Close` (close button)
- `MyComponent_Tab_<Name>` (tab buttons)
- `MyComponent_SearchField` (search input)
```

### 5. Add Confirmation Dialog Tests (if applicable)

If your component uses `.alert()` or `.confirmationDialog()`:

```swift
@MainActor
func testMyComponentShowsConfirmationDialog() throws {
    let app = XCUIApplication()
    app.launchArguments.append(contentsOf: ["-uiTest", "-uiTestPresent", "myComponent"])
    app.launch()

    app.buttons[TestIdentifiers.MyComponent.deleteButton].tap()

    let alert = app.alerts.firstMatch
    XCTAssertTrue(alert.waitForExistence(timeout: 5))
    XCTAssertTrue(alert.buttons["Cancel"].exists)
}
```

### 6. Add Sheet Detent Tests (if using detents)

If your component uses `.presentationDetents()`:

```swift
@MainActor
func testMyComponentSheetDetents() throws {
    let app = XCUIApplication()
    app.launchArguments.append(contentsOf: ["-uiTest"])
    app.launch()

    app.buttons["ShowMyComponent"].tap()

    let root = app.otherElements[TestIdentifiers.MyComponent.root]
    XCTAssertTrue(root.waitForExistence(timeout: 5))
}
```

### 7. Add Test Files to Xcode Project

If you created new `.swift` test files, add them to the Xcode project.
See "Adding Test Files to Xcode Project" above for the required
`project.pbxproj` entries.

## Constraints

- Apply identifiers to leaf elements only (buttons, fields, text)
- Never use LazyVStack for content that needs UI testing without a test-mode fallback
- Keep individual tests under 15 seconds to prevent timeouts
- Use `waitForExistence` instead of `Thread.sleep` for timing
- Use existing identifier naming patterns in the project for consistency
