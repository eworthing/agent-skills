---
name: apple-multiplatform
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

## Contents

- [Purpose](#purpose)
- [When to Use This Skill](#when-to-use-this-skill)
- [Platform Conditionals: `canImport` vs `os(...)`](#platform-conditionals-canimport-vs-os)
- [SwiftUI API Availability Matrix](#swiftui-api-availability-matrix)
- [Per-Platform Detail](#per-platform-detail)
- [Common Failure Patterns](#common-failure-patterns)
- [Cross-Platform Visibility After File Splits](#cross-platform-visibility-after-file-splits)
- [Narrowing a Guard Is a Behaviour Change](#narrowing-a-guard-is-a-behaviour-change)
- [Build Validation](#build-validation)
- [Static Audit](#static-audit)
- [Sibling Skills](#sibling-skills)
- [Constraints](#constraints)
- [Escape Hatches](#escape-hatches)

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
  tvOS, less commonly iPad / Mac Catalyst)
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
Mac Catalyst specifically:

```swift
#if targetEnvironment(macCatalyst)
// Catalyst-only behavior
#elseif os(iOS)
// Pure iOS / iPadOS (non-Catalyst)
#endif
```

## SwiftUI API Availability Matrix

In the matrix and code comments below, **"Catalyst" is shorthand for
"Mac Catalyst"** (the full term used in prose). Both refer to the same
platform — `os(iOS)` AND `targetEnvironment(macCatalyst)`.

This is a **functional** availability table — a "Yes" means the API both
compiles and behaves meaningfully on that platform. Apple's symbol-level
availability is sometimes broader than functional availability; where the
two diverge, this table follows what is useful in practice and the Notes
column explains the gap. Each row links to the canonical Apple Developer
documentation page for drift-checking against new SDKs.

The 27-cycle rows below were verified against the 27 **beta** SDK docs (floors
may shift before GA); existing rows unchanged this pass. Last verified: 2026-07-04.

| API | iOS | iPadOS | Catalyst | macOS | tvOS | Notes | Apple Docs |
|---|---|---|---|---|---|---|---|
| `TabView` style `.page` | Yes | Yes | Yes | **No** | Yes | Use `.automatic` on macOS | [PageTabViewStyle](https://developer.apple.com/documentation/swiftui/pagetabviewstyle) |
| `fullScreenCover` | Yes | Yes | Yes | **No** | Yes | Modifier is unavailable on macOS — use `.sheet` | [fullScreenCover](https://developer.apple.com/documentation/swiftui/view/fullscreencover(ispresented:ondismiss:content:)) |
| `@Environment(\.editMode)` | Yes | Yes | Yes | **No** | **No** (functional) | Symbol exists on tvOS per Apple docs but there is no edit interface — gate with `#if os(iOS)` to avoid dead code | [editMode](https://developer.apple.com/documentation/swiftui/environmentvalues/editmode) |
| `.topBarLeading` / `.topBarTrailing` | Yes | Yes | Yes | **No** | **No** (functional) | macOS needs a different placement (hard compile error). Symbol exists on tvOS (14+) per Apple docs and compiles, but there is no top-bar chrome — gate with `#if os(iOS)` to avoid dead code | [ToolbarItemPlacement](https://developer.apple.com/documentation/swiftui/toolbaritemplacement) |
| `.topBarPinnedTrailing` placement + `ToolbarOverflowMenu` | 27+ | 27+ | 27+ | **No** | **No** | New in the 27 SDKs (beta; also visionOS 27) — **absent on macOS/tvOS**; use existing placements there. Sibling 27 toolbar APIs `toolbarMinimizeBehavior` / `visibilityPriority(_:)` **are** cross-platform | [topBarPinnedTrailing](https://developer.apple.com/documentation/swiftui/toolbaritemplacement/topbarpinnedtrailing) |
| `glassEffect` modifier | iOS 26+ | iPadOS 26+ | Catalyst 26+ | macOS 26+ | tvOS 26+ | Liquid Glass — wrap with `if #available(iOS 26, *)` for older deployment targets. On the 27 SDKs the `UIDesignRequiresCompatibility` opt-out is ignored (iOS/iPadOS/Catalyst/macOS/tvOS 27), so Liquid Glass is mandatory on all five | [glassEffect](https://developer.apple.com/documentation/swiftui/view/glasseffect(_:in:)) |
| Drag-and-drop **receiving** (`.onDrop`, `DropDelegate`) | Yes | Yes | Yes | Yes | **No** | tvOS has no pointer / touch drag source | [onDrop](https://developer.apple.com/documentation/swiftui/view/ondrop(of:istargeted:perform:)) |
| Reorderable containers (`.reorderable()`, `.reorderContainer(for:isEnabled:move:)`) | 27+ | 27+ | 27+ | 27+ | **No** | New in the 27 SDKs (beta; also visionOS/watchOS 27). tvOS is **not** in the availability list — gate with `#if !os(tvOS)`, same family as drag-receiving | [reorderable()](https://developer.apple.com/documentation/swiftui/dynamicviewcontent/reorderable()) |
| `UIImpactFeedbackGenerator` (haptics) | Yes | Yes | Yes | **No** (use `NSHapticFeedbackManager`) | **No** (no hardware) | Gate with `#if os(iOS)`, not `canImport(UIKit)` | [UIImpactFeedbackGenerator](https://developer.apple.com/documentation/uikit/uiimpactfeedbackgenerator) |
| `@CommandsBuilder` `ForEach` composition | n/a | n/a | n/a | **Fragile** | n/a | macOS commands — flatten via `Menu` for portability across SDK versions | [CommandsBuilder](https://developer.apple.com/documentation/swiftui/commandsbuilder) |
| `NavigationSplitView` | iOS 16+ | iPadOS 16+ | Catalyst 16+ | macOS 13+ | tvOS 16+ (adapts to single column) | macOS / Catalyst often need explicit `columnVisibility` of `.detailOnly` or `.all` | [NavigationSplitView](https://developer.apple.com/documentation/swiftui/navigationsplitview) |

When in doubt, check the Apple Developer "Availability" line in the symbol's
documentation — SwiftUI sometimes ships the **type** on a platform but the
**modifier or initializer** is unavailable, and sometimes the symbol exists
but the platform offers no UI affordance to drive it.

**Not divergence — all-platform 27-SDK changes** (migration, not gating): `@State`
expands via the [`State()`](https://developer.apple.com/documentation/swiftui/state)
macro under Xcode 27; `ReferenceFileDocument` is deprecated for new `ReadableDocument` / `WritableDocument` (27.0);
[`navigationBarLeading`](https://developer.apple.com/documentation/swiftui/toolbaritemplacement/navigationbarleading) / `navigationBarTrailing`
are deprecated 27.0 in favour of `topBarLeading` / `topBarTrailing` (same availability — iOS/iPadOS/Catalyst/tvOS/visionOS, no macOS —
so this is a rename, not a re-gate). Defer to `swiftui-expert-skill`.

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
| Mac Catalyst window collapses on launch | Missing `.defaultSize(...)` / scene config | Specify size — see `references/catalyst.md` |
| `.fullScreenCover` not found on macOS | Modifier is unavailable on macOS | Branch to `.sheet` on macOS |

## Cross-Platform Visibility After File Splits

`private` declarations are file-scoped. After moving a type or extension into
its own file, properties that compiled fine before may stop resolving — and the
failure can appear on **only one platform** because Swift's whole-module
optimization is platform-conditional. macOS often surfaces these faster than
tvOS.

For full guidance — what to extract, how to choose visibility levels, how to
verify after splitting — see the `swift-file-splitting` skill.

## Narrowing a Guard Is a Behaviour Change

Widening a guard adds a platform; **narrowing one removes code from a platform.**
Widening only risks a build failure, which the build catches. Narrowing risks
silent feature loss, which it does not — the build is green either way, so
"all platforms compile" is no evidence the change was safe.

The trap is reading a matrix **No** and narrowing an existing guard to match. The
matrix answers *"does it compile / behave there?"*; narrowing asserts the
stronger *"nothing on that platform depends on this."*

> **A guard tells you where code compiles. It never tells you whether anything
> drives it.** A dead-code claim is a claim about the whole program.

Before removing a platform from a guard:

1. **Find the producer.** For state channels — `@Environment` keys above all —
   search the whole tree for what *supplies* the value, not just what reads it.
   An app can own a key Apple ships no UI for, making every reader on that
   platform live. Worked example: [`references/tvos.md`](references/tvos.md)
   § *When tvOS `editMode` is NOT dead*.
2. **Never conclude absence from a truncated search.** `rg … | head` supports
   "X exists", never "nothing does X" — a negative needs the *whole* result set.
   A producer missed in a truncated grep's tail is exactly how a correct guard
   gets narrowed into a bug.
3. **"No affordance" ≠ "no symbol".** *No edit interface on tvOS* is a design
   fact you may override; *no `editMode` on tvOS* would be a compile error. Only
   the second forces a guard.

## Build Validation

Build every supported destination before merging. Canonical `xcodebuild`
invocations per platform, expected pass/fail stdout samples, and a CI wrapper
template live in [`references/build-matrix.md`](references/build-matrix.md).

## Static Audit

A static audit catches the highest-frequency guard mistakes without running a
build:

```bash
./scripts/audit-platform-guards.py path/to/your/swift/tree   # needs python3
```

It tracks the `#if` guard stack and reports a symbol **only when the stack proves
the line is compiled for the offending platform** (comments stripped). That is
the whole design: `#if os(tvOS)` excludes macOS *without naming it*, so a
file-scoped "does `os(macOS)` appear here?" grep flags every correctly guarded
tvOS-only file — an earlier grep-based version scored **19/19 false positives**
against a shipping 4-platform app.

Build-break checks (trap code → recovery-playbook entry) — these set exit 1:

| Script | Detects | Recovery |
|---|---|---|
| `T1` | Haptics / `UIPasteboard` on a **tvOS-compiled** line — the `canImport(UIKit)` trap | `E1`, `E4` |
| `T1b` | `.onDrop` / `DropDelegate` on a **tvOS-compiled** line (SwiftUI, not UIKit — no tvOS) | `E1` (analogous) |
| `T2` | `@Environment(\.editMode)` on a **macOS-compiled** line | `E2` (analogous) |
| `T3` | `.tabViewStyle(.page)` on a **macOS-compiled** line | `E6` |
| `T4` | `.topBarLeading` / `.topBarTrailing` on a **macOS-compiled** line | `E2` |
| `T5` | `.fullScreenCover` on a **macOS-compiled** line | `E8` |

Dead-code checks — informational, emitted as `APPLE-MP-INFO`, and they **do not
affect the exit code**, so they are safe in a CI gate:

| Script | Detects |
|---|---|
| `D1` | `editMode` compiles on tvOS **and nothing in the tree injects it** — dead code |
| `D2` | `.topBar*` compiles on tvOS — symbol exists (tvOS 14+), but no top-bar chrome |

`D1` is suppressed tree-wide when any tvOS-compiled line injects `\.editMode` —
an app may own that channel, and then its tvOS readers are live. See
[`references/tvos.md`](references/tvos.md) § *When tvOS `editMode` is NOT dead*.

Exit code 0 = no build-break hits, 1 = at least one, 2 = usage error. Output
matches the `APPLE-MP-FAIL <platform> <error-class> <file>:<line>: <message>`
shape documented in `references/recovery.md`.

Fixtures live in `tests/fixtures/`, run via `./scripts/run-tests.sh`. The
`clean-*` cases are load-bearing: each is a real false positive a previous
version produced. A fixture with none of the audited symbols passes vacuously —
every `clean-*` here contains the symbol and guards it correctly.

### Guards may not be in this file

Platform code is routinely factored into sibling files (`Foo+tvOS.swift`) or
custom `ViewModifier`s, so **file-scoped greps under-report**. A view can look
like it is missing its `.onExitCommand` or its `#if` while the guard lives one
file over. Resolve the guard stack for the line, or read the sibling — do not
grep a single file and conclude.

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
  Mac Catalyst frequently surface issues tvOS misses; do not skip them.
- Prefer `#if os(...)` for API gating; reserve `#if canImport(...)` for the
  `import` statement itself.
- Re-evaluate guards after Swift / SDK upgrades — Apple occasionally extends
  API availability to additional platforms (which means stale `#if` branches
  become dead code). Apple-docs URLs in the availability matrix above are
  the audit anchors.
- **Narrowing a guard needs a producer search, not just a matrix row.** A
  matrix **No** justifies *adding* a guard; it never by itself justifies
  *removing* a platform from an existing one. Find what drives the code first —
  see *Narrowing a Guard Is a Behaviour Change*.
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
