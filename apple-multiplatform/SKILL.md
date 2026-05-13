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
macOS, Mac Catalyst, and tvOS. Documents **what is portable and what is not**.
Captures the recurring compatibility patterns — `#if` guards, availability
tables, and platform gotchas — that cause one-platform build failures and
runtime divergence.

This skill does not prescribe a build script or CI workflow; the validation
step is "build every supported destination before merging" using whatever
invocation your project standardizes on (canonical `xcodebuild` examples
live in [`references/build-matrix.md`](references/build-matrix.md)).

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

This is a **functional** availability table — a "Yes" means the API both
compiles and behaves meaningfully on that platform. Apple's symbol-level
availability is sometimes broader than functional availability; where the
two diverge, this table follows what is useful in practice and the Notes
column explains the gap. Each row links to the canonical Apple Developer
documentation page for drift-checking against new SDKs.

| API | iOS | iPadOS | Catalyst | macOS | tvOS | Notes | Apple Docs |
|---|---|---|---|---|---|---|---|
| `TabView` style `.page` | Yes | Yes | Yes | **No** | Yes | Use `.automatic` on macOS | [PageTabViewStyle](https://developer.apple.com/documentation/swiftui/pagetabviewstyle) |
| `fullScreenCover` | Yes | Yes | Yes | **No** | Yes | Modifier is unavailable on macOS — use `.sheet` | [fullScreenCover](https://developer.apple.com/documentation/swiftui/view/fullscreencover(ispresented:ondismiss:content:)) |
| `@Environment(\.editMode)` | Yes | Yes | Yes | **No** | **No** (functional) | Symbol exists on tvOS per Apple docs but there is no edit interface — gate with `#if os(iOS)` to avoid dead code | [editMode](https://developer.apple.com/documentation/swiftui/environmentvalues/editmode) |
| `.topBarLeading` / `.topBarTrailing` | Yes | Yes | Yes | **No** | **No** | macOS / tvOS need different placements | [ToolbarItemPlacement](https://developer.apple.com/documentation/swiftui/toolbaritemplacement) |
| `glassEffect` modifier | iOS 26+ | iPadOS 26+ | Catalyst 26+ | macOS 26+ | tvOS 26+ | Liquid Glass — wrap with `if #available(iOS 26, *)` for older deployment targets | [glassEffect](https://developer.apple.com/documentation/swiftui/view/glasseffect(_:in:)) |
| Drag-and-drop **receiving** (`.onDrop`, `DropDelegate`) | Yes | Yes | Yes | Yes | **No** | tvOS has no pointer / touch drag source | [onDrop](https://developer.apple.com/documentation/swiftui/view/ondrop(of:istargeted:perform:)) |
| `UIImpactFeedbackGenerator` (haptics) | Yes | Yes | Yes | **No** (use `NSHapticFeedbackManager`) | **No** (no hardware) | Gate with `#if os(iOS)`, not `canImport(UIKit)` | [UIImpactFeedbackGenerator](https://developer.apple.com/documentation/uikit/uiimpactfeedbackgenerator) |
| `@CommandsBuilder` `ForEach` composition | n/a | n/a | n/a | **Fragile** | n/a | macOS commands — flatten via `Menu` for portability across SDK versions | [CommandsBuilder](https://developer.apple.com/documentation/swiftui/commandsbuilder) |
| `NavigationSplitView` | iOS 16+ | iPadOS 16+ | Catalyst 16+ | macOS 13+ | tvOS 16+ (adapts to single column) | macOS / Catalyst often need explicit `columnVisibility` of `.detailOnly` or `.all` | [NavigationSplitView](https://developer.apple.com/documentation/swiftui/navigationsplitview) |

When in doubt, check the Apple Developer "Availability" line in the symbol's
documentation — SwiftUI sometimes ships the **type** on a platform but the
**modifier or initializer** is unavailable, and sometimes the symbol exists
but the platform offers no UI affordance to drive it.

## Per-Platform Detail

Full gotcha catalogues live in the references files. Open the one that
matches the platform you are debugging.

- [`references/tvos.md`](references/tvos.md) — tvOS trap matrix (haptics, drag
  receiving, `editMode`, focus, pointer, Menu-button dismissal); inline + file-level
  guard patterns for `editMode`
- [`references/macos.md`](references/macos.md) — `TabView`, modal presentation,
  toolbar placement, `@CommandsBuilder` + `ForEach`, `NavigationSplitView`
  defaults, keyboard-shortcut collision audit, window resize-down, settings form
- [`references/catalyst.md`](references/catalyst.md) — `targetEnvironment(macCatalyst)`
  branching, window sizing, sidebar defaults, pointer-on-iOS, multi-window
  lifecycle
- [`references/ui-tests.md`](references/ui-tests.md) — `XCUICoordinate`,
  `NSToolbar`, `TabView .page` traversal, `XCUIRemote.menu`, drag-from-coordinate

## Common Failure Patterns

Quick-reference table. For per-error minimal repro + audit command + fix
snippet, see [`references/recovery.md`](references/recovery.md).

| Error message | Likely cause | Fix |
|---|---|---|
| `Cannot find 'X' in scope` on one platform only | Missing `#if` guard; symbol excluded from that platform | Add `#if os(...)` around the usage |
| `Value of type 'X' has no member 'Y'` on one platform | API exists on type but is unavailable on this platform | Branch the modifier per `#if os(...)` |
| `'private' modifier cannot be used in an extension` after split | Cross-file access | Promote to `internal` (or keep extension in same file) — see `swift-file-splitting` |
| Runtime crash on tvOS after `canImport(UIKit)` guard | UIKit imports but specific class is unavailable | Replace `canImport(UIKit)` with `os(iOS)` |
| `Ambiguous use of '...'` | Platform-specific overloads visible together | Add explicit type annotation or branch with `#if` |
| macOS-only `Static method 'page' requires ...` | `TabView.tabViewStyle(.page)` on macOS | Branch `tabViewStyle` per platform |
| Catalyst window collapses on launch | Missing `.defaultSize(...)` / scene config | Specify size — see `references/catalyst.md` |
| `.fullScreenCover` not found on macOS | Modifier is unavailable on macOS | Branch to `.sheet` on macOS |

## Cross-Platform Visibility After File Splits

`private` declarations are file-scoped. After moving a type or extension into
its own file, properties that compiled fine before may stop resolving — and the
failure can appear on **only one platform** because Swift's whole-module
optimization is platform-conditional. macOS often surfaces these faster than
tvOS.

For full guidance — what to extract, how to choose visibility levels, how to
verify after splitting — see the `swift-file-splitting` skill.

## Build Validation

Build every supported destination before merging. Canonical `xcodebuild`
invocations per platform, expected pass/fail stdout samples, and a CI wrapper
template live in [`references/build-matrix.md`](references/build-matrix.md).

## Static Audit

A static audit catches the five highest-frequency guard mistakes without
running a build:

```bash
./scripts/audit-platform-guards.sh path/to/your/swift/tree
```

Detects (script trap code → corresponding recovery-playbook entry):

| Script | Detects | Recovery |
|---|---|---|
| `T1` | `canImport(UIKit)` gating UIKit symbols that crash at runtime on tvOS | `E1`, `E4` |
| `T2` | `@Environment(\.editMode)` wrapped by bare `#if !os(tvOS)` (macOS also lacks the edit interface) | `E2` (analogous) |
| `T3` | `.tabViewStyle(.page)` without an `os(macOS)` branch | `E6` |
| `T4` | `.topBarLeading` / `.topBarTrailing` without an `os(macOS)` branch | `E2` |
| `T5` | `.fullScreenCover` without an `os(macOS)` branch | `E8` |

Exit code 0 = clean, 1 = at least one hit. Output format matches the
`APPLE-MP-FAIL <platform> <error-class> <file>:<line>: <message>` line shape
documented in `references/recovery.md`.

## Sibling Skills

- `swift-file-splitting` — visibility-preserving file extraction
- `swiftui-drag-drop` — drag-and-drop architecture, including tvOS gating
- `swiftui-design-tokens` — design tokens for spacing, typography, motion,
  button styling; macOS form style
- `apple-tvos` — tvOS focus engine, accessibility deltas (Menu-button dismissal,
  destructive dialog focus), and design regressions
- `xctest-ui-testing` — full XCTest testability checklist
- `swiftui-expert-skill` (community) — modern SwiftUI API surface
  (`references/latest-apis.md`, `references/macos-scenes.md`,
  `references/macos-views.md`, `references/macos-window-styling.md`)
- `swift-concurrency` (community) — async/await, actors, Sendable, Swift 6 migration

## Constraints

- Build failures on **any** supported destination block merge. macOS and
  Catalyst frequently surface issues tvOS misses; do not skip them.
- Prefer `#if os(...)` for API gating; reserve `#if canImport(...)` for the
  `import` statement itself.
- Re-evaluate guards after Swift / SDK upgrades — Apple occasionally extends
  API availability to additional platforms (which means stale `#if` branches
  become dead code). Apple-docs URLs in the availability matrix above are
  the audit anchors.
- When a behavior cannot be expressed on a platform at all, prefer a
  platform-specific subtype or per-file partition over deeply nested `#if`
  branches inside a shared view body.

## Escape Hatches

This skill defers to more specialized siblings when their scope overlaps:

- **tvOS focus engine, design regressions, accessibility deltas** → defer to
  `apple-tvos`. This skill covers tvOS compatibility *gating*; `apple-tvos`
  owns tvOS-specific behavior.
- **File extraction / visibility levels after split** → defer to
  `swift-file-splitting`. This skill notes the failure mode; the other owns
  the recipe.
- **XCTest testability conventions (root markers, accessibility IDs)** →
  defer to `xctest-ui-testing`. This skill covers cross-platform API
  divergence only.
- **Modern SwiftUI APIs, deprecation replacements, macOS scenes/views/window
  styling** → defer to `swiftui-expert-skill` references.
- **Project-specific build scripts** → if your project ships a wrapper
  (`./build_install_launch.sh`, etc.), prefer it over the generic
  `xcodebuild` invocations in `references/build-matrix.md`.

When this skill and a sibling disagree, the sibling wins for its specialty.
