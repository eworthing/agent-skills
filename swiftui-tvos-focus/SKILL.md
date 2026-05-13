---
name: swiftui-tvos-focus
author: eworthing
original-author: Antoine van der Lee (AvdLee)
source: https://github.com/AvdLee/SwiftUI-Agent-Skill
description: >-
  SwiftUI tvOS focus-engine patterns plus the cross-platform
  `@AppStorage`-inside-`@Observable` silent-failure gotcha. Use when
  building or debugging tvOS focus behavior — focus settle delays on
  rapid card swiping, focus hover effect fighting custom `.animation()`,
  `.focusable()` on container wrappers blocking child focus, focus
  identity loss on POD rows after parent redraw, focus-driven scrolling
  failing because a `ScrollView` has no focusable children, picking
  between `.viewAligned` and `.paging` on tvOS, verifying focus
  animations against tvOS Simulator vs Apple TV hardware divergence, or
  diagnosing stale views when `@AppStorage` is declared inside an
  `@Observable` class.
allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Bash
---

# SwiftUI tvOS Focus

## Scope

tvOS-specific deltas to the SwiftUI rendering model, plus one
cross-platform state-container gotcha unique enough to repeat. General
SwiftUI patterns (composition, animation mechanics, scroll, performance,
state-container shape) live in the authoritative `swiftui-expert-skill`.

| Concern | Skill |
|---|---|
| General SwiftUI state, view composition, animation, scroll, focus, performance | `swiftui-expert-skill` |
| Deprecated SwiftUI APIs (`foregroundColor`, old `onChange`, `NavigationView`) | `swiftui-expert-skill` (`references/latest-apis.md`) |
| Cross-platform conditionals (`#if os(tvOS)`, `editMode`, haptics) | `apple-multiplatform` |
| Accessibility identifiers, VoiceOver, Menu-button dismissal | `swiftui-accessibility` |
| UI test patterns and `AccessibilityMarkerView` | `xctest-ui-testing` |
| Design review (modal containment, glass-on-glass, keyboard collisions) | `swiftui-design-review` |
| Design tokens (motion springs, button styles, modal sizing) | `swiftui-design-tokens` |
| Drag-and-drop (gated for tvOS) | `swiftui-drag-drop` |

## tvOS Focus Engine

Full reference: [references/tvos.md](references/tvos.md). Hard rules:

1. **No `.focusable()` on container wrappers.** Focus stops at the
   outer view. Apply `.focusable()` only to leaf views. A container
   wrapping focusable children that itself becomes `.focusable()`
   blocks the focus engine from reaching the children.
2. **Pair focusable POD rows with parent `@FocusState`.** Pure POD
   views get `memcmp` fast-path diffing, but on tvOS that same identity
   can change on parent redraw — the focus engine then sees a "new"
   element and may move focus elsewhere. Use
   `@FocusState` + `.focused(_:equals:)` in the parent to anchor focus
   identity independent of POD identity.
3. **Scope custom `.animation()` to child content, not the focusable
   element.** The built-in focus hover effect (~200 ms perspective lift
   + specular shine) runs on every focusable view; a custom animation
   on the same view fights it and produces jitter on hardware.
4. **Use a token-based settle delay for long focus-change animations.**
   Without it, rapid swiping starts and immediately cancels animations
   on every passed-over card. Increment a token on each `isFocused`
   change and only run the animation if the token still matches when
   the delay elapses.
5. **`ScrollView` with no focusable children is unscrollable on tvOS.**
   tvOS scroll is focus-driven — focus moves off-screen, the framework
   scrolls. Plain `Text` in a `ScrollView` produces a static view.
6. **Prefer `.scrollTargetBehavior(.viewAligned)` over `.paging` on
   tvOS.** Full-page jumps on 1920×1080 feel jarring; view-aligned
   matches the platform's focus-to-focus navigation expectations.
7. **Verify focus animations on real Apple TV hardware.** The tvOS
   Simulator does not replicate the hover curve, perspective lift, or
   specular shine. Declaring an animation issue "fixed" without
   hardware verification is unsafe.

## Observable State: `@AppStorage` Inside `@Observable`

Full reference: [references/observable-state.md](references/observable-state.md).

`@AppStorage` does **not** participate in the Observation framework. On
a property of an `@Observable` class it reads/writes `UserDefaults`
correctly, but **SwiftUI views observing that class will never re-render
when the value changes** — even with `@ObservationIgnored`. No warning.
The view simply stays stale.

```swift
// WRONG — views never re-render when `appearance` changes
@Observable
final class Settings {
    @AppStorage("appearance") var appearance: String = "system"
}
```

```swift
// CORRECT — plain stored property + didSet syncs to UserDefaults.
// Observation tracks reads/writes; views update.
@Observable
final class Settings {
    var appearance: String =
        UserDefaults.standard.string(forKey: "appearance") ?? "system" {
        didSet { UserDefaults.standard.set(appearance, forKey: "appearance") }
    }
}
```

`@AppStorage` is safe **directly on a SwiftUI `View`** — only the
`@Observable`-class case breaks.

## Review Checklist

- [ ] No `.focusable()` on container views wrapping focusable children
- [ ] Focusable POD rows pair with parent `@FocusState` + `.focused(_:equals:)`
- [ ] Custom `.animation()` on focusable elements scoped to child content
- [ ] Long focus-change animations use token-based settle delay
- [ ] All `ScrollView` content on tvOS contains focusable children
- [ ] `.viewAligned` preferred over `.paging` on tvOS
- [ ] Focus animations verified on real Apple TV hardware
- [ ] No `@AppStorage` on properties of `@Observable` classes

## References

- [references/tvos.md](references/tvos.md) — Focus engine patterns: container `.focusable()`, POD + `@FocusState`, hover conflict, settle delay, focus-driven scrolling, `.viewAligned` vs `.paging`, simulator vs hardware
- [references/observable-state.md](references/observable-state.md) — `@AppStorage` inside `@Observable` silent-failure gotcha
