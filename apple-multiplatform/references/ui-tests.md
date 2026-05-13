# UI Test API Divergence

XCTest spans iOS / iPadOS / Mac Catalyst / macOS / tvOS but exposes different
surfaces. See `xctest-ui-testing` for the full root-marker + accessibility-ID
testability checklist; this file captures only the cross-platform divergence.

## Divergence Matrix

| API / Symbol | Issue | Workaround |
|---|---|---|
| `XCUICoordinate.coordinate(withNormalizedOffset:)` | Unavailable on tvOS | Gate test helper with `#if !os(tvOS)`; use focus-based traversal on tvOS |
| `NSToolbar` items (macOS) | Accessibility IDs frequently fail to propagate to `XCUIElement` queries | Query by label, role, or attach IDs to embedded SwiftUI controls inside the toolbar item, not the toolbar item itself |
| `TabView .page` traversal | Style unavailable on macOS — no swipe-between-pages affordance | Use `.automatic` style and assert via sidebar tab selection |
| `XCUIRemote.shared.press(.menu)` | tvOS-only API | Wrap with `#if os(tvOS)`; do not call from shared helpers |
| Drag-from-coordinate gestures | Only meaningful on iOS / iPadOS / macOS | Skip drag tests on tvOS with `XCTSkipIf(...)` or `#if !os(tvOS)` |

## Shared Helper Pattern

```swift
// Test helper file — gates per platform
func tapElementAtNormalizedOffset(_ element: XCUIElement, x: CGFloat, y: CGFloat) throws {
    #if os(tvOS)
    throw XCTSkip("Coordinate-based tap not available on tvOS — use focus traversal")
    #else
    let coord = element.coordinate(withNormalizedOffset: CGVector(dx: x, dy: y))
    coord.tap()
    #endif
}
```

## Related Skills

- `xctest-ui-testing` — full XCTest testability checklist, root markers, accessibility ID conventions
- `apple-tvos` — `references/accessibility.md` for tvOS focus traversal patterns
