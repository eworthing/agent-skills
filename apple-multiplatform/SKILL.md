---
name: apple-multiplatform
author: eworthing
description: >-
  Cross-platform Apple SwiftUI compatibility reference for iOS, iPadOS, macOS,
  Mac Catalyst, and tvOS. Use when adding platform-conditional code, debugging
  "Cannot find 'X' in scope" or "Value of type has no member" errors that only
  reproduce on one platform, choosing between `#if os()` and `#if canImport()`,
  gating `editMode` / drag-and-drop receiving / haptics for tvOS, picking
  between `.page` and `.automatic` TabView style on macOS, handling Mac
  Catalyst sidebar and window-sizing defaults, working with `@CommandsBuilder`
  and toolbar placement, or fixing UI test API divergence across
  `XCUICoordinate`, `NSToolbar`, and `TabView .page`.
allowed-tools:
  - Read
  - Bash
  - Glob
  - Grep
---

# Apple Multiplatform Compatibility

## Purpose

Reference for SwiftUI and Apple-framework API differences across iOS, iPadOS,
macOS, Mac Catalyst, and tvOS. Captures the recurring compatibility patterns —
`#if` guards, availability tables, and platform gotchas — that cause one-platform
build failures and runtime divergence.

This skill documents **what is portable and what is not**. It does not prescribe
a build script or CI workflow; the validation step is "build every supported
destination before merging" using whatever invocation your project standardizes
on (generic `xcodebuild` examples are included below).

## When to Use This Skill

Use when:
- Adding or auditing `#if os(...)` / `#if canImport(...)` guards in Swift code
- Debugging an error that only reproduces on one platform (commonly macOS or
  tvOS, less commonly iPad/Catalyst)
- Choosing between `os(...)` and `canImport(...)` for a new conditional
- Gating `editMode`, drag-and-drop receiving, or haptics for tvOS
- Picking SwiftUI styles whose availability differs across platforms
  (`TabView .page`, `.fullScreenCover`, toolbar placements)
- Working with `@CommandsBuilder` (macOS menus) and discovering `ForEach`
  doesn't compose
- Writing UI tests that call platform-divergent XCTest APIs
  (`XCUICoordinate.coordinate(withNormalizedOffset:)`, `NSToolbar` accessibility
  IDs, `TabView .page` traversal)
- Reviewing a PR before merge to spot missing platform conditionals

Do NOT use when:
- The change is documentation- or comment-only
- Only one platform is supported by the target — no conditionals needed
- The question is about Swift Concurrency, accessibility, or design tokens
  (use `swift-concurrency`, `apple-tvos` for tvOS-specific deltas,
  `swiftui-design-tokens`)

## Platform Conditionals: `canImport` vs `os(...)`

These two macros answer different questions. Use both, deliberately.

| Macro | Question it answers | Use for |
|---|---|---|
| `#if canImport(Framework)` | Is this framework linkable on the current platform? | Conditional `import` statements (UIKit, AppKit) |
| `#if os(Platform)` | Is this code being compiled for that specific OS? | Behavior or API gating where framework presence is insufficient |

**Critical rule:** `canImport(UIKit)` succeeds on iOS, iPadOS, Mac Catalyst, **and
tvOS** — but many UIKit APIs are unavailable on tvOS at the symbol level. For
API gating (vs framework gating), prefer `#if os(iOS)` / `#if os(tvOS)`.

```swift
// Framework-level: gates the import itself
#if canImport(UIKit)
import UIKit
#endif

#if canImport(AppKit)
import AppKit
#endif

// OS-level: gates platform-specific behavior
#if os(tvOS)
// tvOS-specific code (no touch, focus-driven)
#elseif os(iOS)
// iOS / iPadOS / Catalyst code
#elseif os(macOS)
// macOS code (AppKit-backed SwiftUI)
#endif
```

Mac Catalyst is `os(iOS)` AND `targetEnvironment(macCatalyst)`. To branch
Catalyst specifically:

```swift
#if targetEnvironment(macCatalyst)
// Catalyst-only behavior
#elseif os(iOS)
// Pure iOS / iPadOS (non-Catalyst)
#endif
```

## SwiftUI API Availability Matrix

| API | iOS | iPadOS | Catalyst | macOS | tvOS | Notes |
|---|---|---|---|---|---|---|
| `TabView` style `.page` | Yes | Yes | Yes | **No** | Yes | Use `.automatic` on macOS |
| `fullScreenCover` | Yes | Yes | Yes | Yes | Yes | Prefer `.sheet` on macOS for HIG fit |
| `@Environment(\.editMode)` | Yes | Yes | Yes | **No** | **No** | iOS / iPadOS / Catalyst only |
| `.topBarLeading` / `.topBarTrailing` | Yes | Yes | Yes | **No** | **No** | macOS / tvOS need different placements |
| `glassEffect` modifier | Yes | Yes | Yes | Yes | Yes | Available across SwiftUI 5+ targets |
| Drag-and-drop **receiving** (`.onDrop`, `DropDelegate`) | Yes | Yes | Yes | Yes | **No** | tvOS has no pointer / touch drag source |
| `UIImpactFeedbackGenerator` (haptics) | Yes | Yes | Yes | **No** (use `NSHapticFeedbackManager`) | **No** (no hardware) | Gate with `#if os(iOS)`, not `canImport(UIKit)` |
| `@CommandsBuilder` `ForEach` composition | n/a | n/a | n/a | **No** | n/a | macOS commands require explicit calls |
| `NavigationSplitView` sidebar visibility default | Auto | Auto | Auto | Visible | n/a | macOS / Catalyst often need explicit `.detailOnly` or `.all` defaults |

When in doubt, check the Apple Developer "Availability" line in the symbol's
documentation — SwiftUI sometimes ships the **type** on a platform but the
**modifier or initializer** is unavailable.

## editMode Platform Pattern

`@Environment(\.editMode)` exists only on iOS-family platforms. Both styles
below are correct; pick one consistently per file:

```swift
// Inline guard — keeps the property only on iOS
struct ItemList: View {
    #if os(iOS)
    @Environment(\.editMode) private var editMode
    #endif

    var body: some View { /* ... */ }
}
```

```swift
// File-level guard — entire view is iOS-only
#if !os(tvOS) && !os(macOS)
struct ItemList: View {
    @Environment(\.editMode) private var editMode  // safe: file excludes tvOS + macOS
    var body: some View { /* ... */ }
}
#endif
```

**Audit checklist** when a file references `editMode`:
1. File-level `#if os(iOS)` or `#if !os(tvOS) && !os(macOS)` wraps the type, **or**
2. Inline `#if os(iOS)` wraps the `@Environment` declaration AND every read site

Watch out for `#if !os(tvOS)` alone — that still compiles `editMode` on macOS,
where it does not exist.

## tvOS Gotchas

tvOS imports `UIKit` (so `canImport(UIKit)` is true) but disallows a long list
of UIKit APIs at the symbol level. Always prefer `#if os(...)` for API gating.

| Topic | Pattern |
|---|---|
| Drag-and-drop receiving | Wrap `.onDrop`, `DropDelegate`, `NSItemProvider` extraction in `#if !os(tvOS)` |
| `editMode` | Wrap with `#if os(iOS)` (see above) |
| Haptics | `UIImpactFeedbackGenerator` and friends require `#if os(iOS)` — `canImport(UIKit)` is **not** sufficient |
| Focus | Use `.focusSection()`, `.focusable()`, `.onMoveCommand`, `.focused($state)` instead of touch / hover |
| Pointer | No mouse / trackpad APIs; gate cursor + hover modifiers |
| `Menu` button dismissal | Press the Menu button (`UIPressType.menu`) — see `apple-tvos` `references/accessibility.md` for the standard `.onExitCommand` dismissal handler |

Example — haptics gating done right:

```swift
// WRONG — compiles on tvOS, crashes at runtime
#if canImport(UIKit)
UIImpactFeedbackGenerator(style: .medium).impactOccurred()
#endif

// CORRECT — symbol is excluded from tvOS at compile time
#if os(iOS)
UIImpactFeedbackGenerator(style: .medium).impactOccurred()
#endif
```

## macOS Gotchas

macOS SwiftUI is AppKit-backed; many iOS-shaped APIs are unavailable or behave
differently.

- **`TabView` style** — `.page` is unavailable. Use `.automatic` (sidebar tabs)
  or design a different navigation surface.
- **Modal presentation** — prefer `.sheet` over `.fullScreenCover` for HIG
  conformance; `.fullScreenCover` compiles but feels foreign on macOS.
- **Toolbar placement** — `.topBarLeading` / `.topBarTrailing` do not exist.
  Use `.navigation`, `.primaryAction`, `.automatic`, or `.principal`. Map
  per platform if needed.
- **`@CommandsBuilder` does not accept `ForEach`.** Result builders for menus
  must use explicit, statically-known children:

```swift
// WRONG — does not compile inside Commands
.commands {
    CommandGroup(after: .newItem) {
        ForEach(recentItems) { item in
            Button(item.title) { open(item) }
        }
    }
}

// CORRECT — flatten the list or use a `Menu` instead
.commands {
    CommandGroup(after: .newItem) {
        Menu("Recent") {
            ForEach(recentItems) { item in
                Button(item.title) { open(item) }
            }
        }
    }
}
```

- **`NavigationSplitView` defaults** — sidebar visibility heuristic differs;
  often set `columnVisibility` explicitly on macOS.
- **Keyboard shortcuts** — modifiers map differently; `Cmd` is canonical, not
  Ctrl.
- **Keyboard shortcut collision audit** — after adding or changing any
  `.keyboardShortcut(...)` modifier, audit the codebase for collisions
  across every surface that can register a shortcut (Commands, toolbar
  buttons, menu items, focused-view modifiers):
  ```bash
  rg -n 'keyboardShortcut\(' YourApp
  ```
  If two actions bind the same key combination, resolve it in the Commands
  layer (where shortcut ownership is centralized) or by changing the
  shortcut on one of the colliding actions. A duplicate binding produces
  silent non-determinism — whichever view installs its modifier later
  wins, and the loser fails silently. Also verify no collision with
  system shortcuts (`Cmd+W`, `Cmd+Q`, `Cmd+,`, `Cmd+H`).
- **Window resize-down stability** — drag the window to its minimum
  width. Critical toolbar actions must remain visible (no truncation to
  overflow menus for primary actions).
- **Settings form style** — use `.formStyle(.automatic)` (see
  `swiftui-design-tokens`). Forcing `.grouped` produces an iOS-looking
  dialog on macOS that feels foreign.

## Mac Catalyst Gotchas

Catalyst inherits the iOS API surface but renders through AppKit. Things that
work on iPad regularly diverge here:

- **Window sizing** — initial window size and resize behavior differ; set
  `.defaultSize(...)` and verify under live resize.
- **Sidebar defaults** — `NavigationSplitView` may default to a different
  column visibility than on iPad; set explicitly.
- **Touch vs pointer** — pointer events arrive even though `os(iOS)` is true.
- **App lifecycle** — multiple-window scenarios behave more like macOS than
  iPad; test scene reuse and state restoration.

When a behavior is Catalyst-specific (not pure iOS), branch with
`#if targetEnvironment(macCatalyst)` as shown above.

## UI Test API Divergence

XCTest itself spans the platforms but exposes different surfaces.

| API / Symbol | Issue | Workaround |
|---|---|---|
| `XCUICoordinate.coordinate(withNormalizedOffset:)` | Unavailable on tvOS | Gate test helper with `#if !os(tvOS)`; use focus-based traversal on tvOS |
| `NSToolbar` items (macOS) | Accessibility IDs frequently fail to propagate to `XCUIElement` queries | Query by label, role, or attach IDs to embedded SwiftUI controls inside the toolbar item, not the toolbar item itself |
| `TabView .page` traversal | Style unavailable on macOS — no swipe-between-pages affordance | Use `.automatic` style and assert via sidebar tab selection |
| `XCUIRemote.shared.press(.menu)` | tvOS-only API | Wrap with `#if os(tvOS)`; do not call from shared helpers |
| Drag-from-coordinate gestures | Only meaningful on iOS / iPadOS / macOS | Skip drag tests on tvOS with `XCTSkipIf(...)` or `#if !os(tvOS)` |

See the `xctest-ui-testing` skill for the full root-marker + accessibility-ID
testability checklist; this section captures only the cross-platform divergence.

## Cross-Platform Visibility After File Splits

`private` declarations are file-scoped. After moving a type or extension into
its own file, properties that compiled fine before may stop resolving — and the
failure can appear on **only one platform** because Swift's whole-module
optimization is platform-conditional. macOS often surfaces these faster than
tvOS.

```swift
// File A (before split)
struct Model {
    private var helper = Helper()  // accessed from extension in same file
}
extension Model { func use() { helper.doThing() } }   // fine

// After extracting the extension to File B:
//    File B fails to find `helper` on macOS first, then tvOS
//    Fix:
struct Model {
    internal var helper = Helper()   // or `fileprivate` only if extension stays in File A
}
```

For full guidance — what to extract, how to choose visibility levels, how to
verify after splitting — see the `swift-file-splitting` skill.

## Common Failure Patterns

| Error message | Likely cause | Fix |
|---|---|---|
| `Cannot find 'X' in scope` on one platform only | Missing `#if` guard; symbol excluded from that platform | Add `#if os(...)` around the usage, or move to a per-platform file |
| `Value of type 'X' has no member 'Y'` on one platform | API exists on type but is unavailable on this platform (e.g. `.topBarLeading`) | Branch the modifier per `#if os(...)` |
| `'private' modifier cannot be used in an extension` after split | Cross-file access | Promote to `internal` (or keep extension in same file) |
| Runtime crash on tvOS after `canImport(UIKit)` guard | UIKit imports but specific class is unavailable (haptics, drag) | Replace `canImport(UIKit)` with `os(iOS)` |
| `Ambiguous use of '...'` | Platform-specific overloads visible together | Add explicit type annotation or branch with `#if` |
| macOS-only "Static method 'page' requires ..." | `TabView.tabViewStyle(.page)` on macOS | Branch `tabViewStyle` per platform |
| Catalyst window collapses on launch | Missing `.defaultSize(...)` / scene config | Specify size and verify resize |

## Per-Platform Build Examples

Build every supported destination before merging. The exact invocation depends
on your project's scheme; the destinations below are the canonical ones:

```bash
# iOS Simulator (latest)
xcodebuild build -scheme YourScheme \
  -destination 'generic/platform=iOS Simulator'

# iPadOS — same SDK as iOS, but verify on an iPad device class
xcodebuild build -scheme YourScheme \
  -destination 'platform=iOS Simulator,name=iPad Pro (12.9-inch) (6th generation)'

# Mac Catalyst
xcodebuild build -scheme YourScheme \
  -destination 'platform=macOS,variant=Mac Catalyst'

# macOS (native)
xcodebuild build -scheme YourScheme \
  -destination 'platform=macOS'

# tvOS Simulator
xcodebuild build -scheme YourScheme \
  -destination 'generic/platform=tvOS Simulator'
```

For projects with multiple schemes (app, widget extension, watch companion),
build each scheme against each destination it claims to support. If your
project ships a wrapper script, prefer it — these `xcodebuild` invocations are
the lowest-common-denominator equivalents.

## Sibling Skills

- `swift-file-splitting` — visibility-preserving file extraction
- `swiftui-drag-drop` — drag-and-drop architecture, including tvOS gating
- `apple-tvos` — tvOS focus engine, accessibility deltas (Menu-button dismissal, destructive dialog focus), and design regressions
- `xctest-ui-testing` — full XCTest testability checklist
- `swiftui-expert-skill` — modern SwiftUI API surface, including deprecated-API replacements (`references/latest-apis.md`)

## Constraints

- Build failures on **any** supported destination block merge. macOS and
  Catalyst frequently surface issues tvOS misses; do not skip them.
- Prefer `#if os(...)` for API gating; reserve `#if canImport(...)` for the
  `import` statement itself.
- Re-evaluate guards after Swift / SDK upgrades — Apple occasionally extends
  API availability to additional platforms (which means stale `#if` branches
  become dead code).
- When a behavior cannot be expressed on a platform at all, prefer a
  platform-specific subtype or per-file partition over deeply nested `#if`
  branches inside a shared view body.
