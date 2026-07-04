# macOS UI Testing Patterns

## Contents

- Ensure App Is Frontmost Before Events
- Pin Window Size for Stable Coordinates
- Toolbar / Keyboard Reliability

> Reference for the parent `xctest-ui-testing` skill. See the SKILL.md
> *Platform Divergences Matrix* for the cross-platform summary.

XCUITest on macOS diverges from iOS in three ways that cause silent failures:
events target the key window (so the app must be frontmost), coordinate-based
actions depend on window size, and `NSToolbar`-backed toolbars don't expose
their items reliably to the accessibility tree.

## Ensure App Is Frontmost Before Events

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

## Pin Window Size for Stable Coordinates

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

## Toolbar / Keyboard Reliability

- SwiftUI toolbar backed by `NSToolbar` does **not** expose individual toolbar
  items reliably to the accessibility tree. Prefer menu items / keyboard
  shortcuts for toolbar actions in tests.
- `typeKey` can be unreliable across macOS releases — prefer menu bar
  navigation (`app.menuBars.menuItems["Action Name"].click()`) when available.
- Always call `ensureAppIsFrontmost(_:bundleIdentifier:)` before any
  keyboard-based interaction.
