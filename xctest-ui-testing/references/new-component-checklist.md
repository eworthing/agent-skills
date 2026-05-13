# New Component Testability Checklist

When adding a new modal, sheet, overlay, or screen, follow this checklist to
ensure it's testable from the start. Skipping any step typically results in
flaky or unreachable tests that pass locally but fail in CI.

## 1. Cross-Check Presentations vs Root Markers

After adding or changing a `.sheet` or `.fullScreenCover`, verify that each
destination view has a root marker (see "Root Markers for Modals" in
[SKILL.md](../SKILL.md)).

```bash
# Find all presentation sites
rg '\.sheet\(|\.fullScreenCover\(' --glob '*.swift' YourApp/Views -n
```

For each presentation site, confirm the destination view has an overlay-mounted
`AccessibilityMarkerView` (or equivalent) with a `*_Root` identifier.

## 2. Create a TestIdentifiers Enum

In your UI test target, define identifiers in a single namespaced enum so
tests have a single source of truth (and refactors that rename identifiers
fail loudly rather than at runtime):

```swift
// MARK: - MyComponent

enum MyComponent {
    static let root = "MyComponent_Root"
    static let close = "MyComponent_Close"
    static let tabPrefix = "MyComponent_Tab_"
    static let searchField = "MyComponent_SearchField"
}
```

The enum is the API contract between view and test. Both sides import it;
neither side inlines the raw string. Renaming an identifier is then an
API migration with a defined order: update the enum case + test
references first, update the view's `.accessibilityIdentifier(...)` use
second. Doing it in the opposite order produces a window where tests
can't find the element and CI fails on a green diff.

## 3. Add Direct Launch Support (Recommended)

Enable launching the app directly to this screen for faster, more reliable
tests. Without this, every test for the component must navigate from the
launch screen, which is slow and flaky:

```swift
// In your app's launch argument handling
if ProcessInfo.processInfo.arguments.contains("-uiTestPresent") {
    if let screenArg = /* parse the argument from launchArguments */ {
        switch screenArg {
        case "myComponent":
            // Navigate directly to MyComponent
        default:
            break
        }
    }
}
```

Use the convention `-uiTestPresent <screen-name>` so existing tests
follow the same pattern. Document the new screen identifier in your test
docs.

## 4. Update Testability Documentation

Document the new identifiers so tests don't reference stale or fictional IDs:

```markdown
**MyComponent (modal)**

- `MyComponent_Root` (root marker)
- `MyComponent_Close` (close button)
- `MyComponent_Tab_<Name>` (tab buttons)
- `MyComponent_SearchField` (search input)
```

## 5. Add Confirmation Dialog Tests (if applicable)

If your component uses `.alert()` or `.confirmationDialog()`, write a
specific test that exercises the dialog. Dialogs are a common source of test
flake because they may attach to a different window or scene:

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

## 6. Add Sheet Detent Tests (if using detents)

If your component uses `.presentationDetents()`, test behavior at each
detent. Coordinate-based tests for sheets at small detents are particularly
fragile — prefer identifier-based assertions:

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

## 7. Add Test Files to Xcode Project

If you created new `.swift` test files, add them to the Xcode project so
they actually compile and run. Unlike SwiftPM where files are
auto-discovered, `.xcodeproj` requires explicit file references in
`project.pbxproj`.

For each new test file, add entries to:

1. **PBXBuildFile** section
2. **PBXFileReference** section
3. **UITests PBXGroup** children
4. **UITests PBXSourcesBuildPhase** files

Generate stable 24-character UUIDs for the FileRef and BuildFile entries:

```bash
uuidgen | tr -d '-' | cut -c1-24  # FileRef UUID
uuidgen | tr -d '-' | cut -c1-24  # BuildFile UUID
```

Verify the file is included after editing:

```bash
xcodebuild test -scheme YourApp -list | grep YourNewTestClass
```

If the test class doesn't appear, one of the four `project.pbxproj` entries
is wrong. Most common mistake: adding to PBXFileReference but not to the
UITests target's PBXSourcesBuildPhase.

## 8. Run the Full Cross-Platform Test Pass

Before merging, run tests on every platform you support:

```bash
# iOS (replace destination as appropriate)
xcodebuild test -scheme YourApp -destination 'platform=iOS Simulator,name=iPhone 16'

# macOS
xcodebuild test -scheme YourApp -destination 'platform=macOS'

# tvOS (if applicable)
xcodebuild test -scheme YourApp -destination 'platform=tvOS Simulator,name=Apple TV'
```

Per-platform divergences (see [SKILL.md](../SKILL.md)'s "Platform
Divergences Matrix") often mean a test that passes on iOS fails silently on
macOS until you actually run it there.
