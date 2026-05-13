# tvOS UI Testing Patterns

XCUITest patterns specific to tvOS. tvOS is focus-driven (no touch, no
direct tap), so test interaction goes through `XCUIRemote` and focus
assertions rather than coordinate tapping.

## Siri Remote API

```swift
// Direction
XCUIRemote.shared.press(.up)
XCUIRemote.shared.press(.down)
XCUIRemote.shared.press(.left)
XCUIRemote.shared.press(.right)

// Selection / activation
XCUIRemote.shared.press(.select)

// Dismissal (back / menu)
XCUIRemote.shared.press(.menu)

// Playback / siri (rarely needed in UI tests)
XCUIRemote.shared.press(.playPause)
```

`.menu` is the canonical dismissal — tvOS modals close with the back press,
NOT with a close button tap.

## Focus Assertions

```swift
let card = app.buttons["Card_abc123"]
XCTAssertTrue(card.waitForExistence(timeout: 5))
XCTAssertTrue(card.hasFocus, "Card should be focused after Down navigation")
```

`hasFocus` is the authoritative tvOS focus check. It is more reliable than
querying focus state via accessibility-tree traversal.

## Focus Navigation Pattern

```swift
// Move focus from toolbar into content grid
XCUIRemote.shared.press(.down)
let firstCard = app.descendants(matching: .button).element(boundBy: 0)
XCTAssertTrue(firstCard.waitForExistence(timeout: 3))
XCTAssertTrue(firstCard.hasFocus)
```

Avoid manual `lastFocus` storage / restore loops in your app — tvOS's focus
system handles this. Tests fail when they assume focus state is
deterministic across navigation; instead, assert on `hasFocus` after each
remote press.

## Modal Focus Containment

When presenting a modal on tvOS, focus must be **trapped** inside the modal
until dismissed. Test that focus cannot escape:

```swift
// Open modal
XCUIRemote.shared.press(.select)
let modalRoot = app.otherElements["SettingsModal_Root"]
XCTAssertTrue(modalRoot.waitForExistence(timeout: 5))

// Try to escape by pressing right repeatedly
for _ in 0..<5 {
    XCUIRemote.shared.press(.right)
}

// Focus should still be inside the modal
let outsideElement = app.buttons["BackgroundElement"]
XCTAssertFalse(outsideElement.hasFocus,
               "Focus escaped from modal — containment broken")
```

Use `.fullScreenCover()` instead of `.sheet()` on tvOS when you need focus
containment that survives Siri Remote navigation. `.sheet()` on tvOS does
not reliably trap focus in older OS versions.

## Focus Settle Delay

After a remote press that triggers a layout change or animation, focus may
take 1-2 frames to settle on the new element. Use `waitForExistence` paired
with `hasFocus` rather than asserting immediately:

```swift
XCUIRemote.shared.press(.down)

// Wait for focus to settle
let predicate = NSPredicate(format: "hasFocus == true")
let expectation = expectation(for: predicate, evaluatedWith: targetElement)
wait(for: [expectation], timeout: 2.0)
```

For state-driven UI (focus-driven sticky headers, focus-driven scroll
position), the app side typically tracks focus via a token that updates on
focus change. Tests should drive interactions through the remote and assert
on resulting accessibility tree state, not on internal focus tokens.

## Focus Reachability Audit Pattern

A focus reachability audit is a separate test suite that verifies every
focusable element in a region can be reached from the region's entry point
via remote navigation alone (no programmatic focus assignment).

```swift
final class FocusReachabilityAuditTests: XCTestCase {
    @MainActor
    func testAllToolbarItemsReachableFromContentEntry() throws {
        let app = XCUIApplication()
        app.launchArguments.append(contentsOf: ["-uiTest"])
        app.launch()

        // Enter region
        let firstCard = app.buttons.element(boundBy: 0)
        XCTAssertTrue(firstCard.waitForExistence(timeout: 5))
        XCTAssertTrue(firstCard.hasFocus)

        // Navigate up to toolbar
        XCUIRemote.shared.press(.up)

        // Walk every toolbar item
        let toolbarIDs = ["Action_New", "Action_Edit", "Action_Settings"]
        for id in toolbarIDs {
            let element = app.buttons[id]
            XCTAssertTrue(element.waitForExistence(timeout: 2))

            // Find direction to navigate; this is project-specific
            // (depends on toolbar layout)
            navigateToFocus(on: element, in: app)
            XCTAssertTrue(element.hasFocus, "\(id) should be reachable")
        }
    }
}

final class FocusTransitionAndContainmentTests: XCTestCase {
    // Tests modal containment, region-to-region focus transitions, etc.
}
```

Run these as a separate test class (not mixed into your interaction tests)
so reachability regressions are isolated from interaction regressions.

## Layout Caveats

- **`LazyVStack` hides off-screen focusable elements** from the
  accessibility tree, breaking focus-walking tests. In `-uiTest` mode,
  prefer `VStack` (or a conditional based on `-uiTest` argument).
- **Hover conflicts**: `.hoverEffect()` modifiers can interfere with focus
  on tvOS in some OS versions. If focus tests fail intermittently on a view
  with hover effects, try removing the hover modifier in test mode.
- **POD views with `@FocusState`**: views become non-POD when they hold
  `@FocusState`, breaking the SwiftUI POD diffing fast path. If a view's
  re-render performance suffers under focus, extract `@FocusState` into a
  small wrapper view and let the inner content stay POD.

## Determining tvOS Window / Scene

tvOS has a single full-screen window per app. Coordinate-based tests are
rarely useful — prefer identifier-based or focus-based assertions. If you
need to know the window for accessibility-tree dumps:

```swift
print(app.descendants(matching: .any).debugDescription)
```

## Test Class Naming Convention

Group focus tests by purpose:

- `FocusReachabilityAuditTests` — every focusable element reachable
- `FocusTransitionAndContainmentTests` — region transitions, modal trap
- `FocusInteractionTests` — actual user-flow tests using remote

Naming separation lets you run reachability/audit suites on CI without
running long interaction flows, and lets you ship a "focus audit" job that
gates UI changes.
