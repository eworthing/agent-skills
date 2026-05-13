---
name: apple-tvos
author: eworthing
original-author: Antoine van der Lee (AvdLee)
source: https://github.com/AvdLee/SwiftUI-Agent-Skill
description: >-
  Definitive tvOS reference: focus engine, accessibility deltas, and
  design-regression checks for SwiftUI on Apple TV. Use when building or
  debugging tvOS focus behavior (settle delays on rapid card swiping,
  focus hover effect fighting custom `.animation()`, `.focusable()` on
  container wrappers blocking child focus, focus identity loss on POD
  rows after parent redraw, focus-driven scrolling failing because a
  `ScrollView` has no focusable children, picking between `.viewAligned`
  and `.paging`, verifying focus animations against Simulator vs Apple
  TV hardware divergence), applying tvOS accessibility patterns
  (`.onExitCommand` Menu button dismissal, destructive `confirmationDialog`
  / `alert` default focus ordering — severity-1 on tvOS, VoiceOver focus
  traversal), or auditing tvOS design regressions (modal focus
  containment leakage, manual focus reassertion anti-pattern via
  `DispatchQueue.main.asyncAfter`, glass-on-glass anti-pattern,
  `.buttonStyle(.plain)` focus-ring clipping, tvOS focus-traversal QA
  checklist). The authoritative community `swiftui-expert-skill` owns
  iOS/macOS depth; this skill owns tvOS deltas.
allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Bash
---

# Apple tvOS

## Scope

Owns three tvOS topic areas not covered by the authoritative community
`swiftui-expert-skill` (which is explicitly iOS/macOS):

| Topic | Reference |
|---|---|
| Focus engine (composition, identity, animation, scroll) | [references/focus-engine.md](references/focus-engine.md) |
| Accessibility deltas (Menu dismissal, destructive dialog focus, VoiceOver-on-tvOS) | [references/accessibility.md](references/accessibility.md) |
| Design regressions (modal containment, focus reassertion, glass-on-glass, button-style, QA checklist) | [references/design-regressions.md](references/design-regressions.md) |

## Sibling Skills

| Concern | Skill |
|---|---|
| General iOS/macOS SwiftUI (state, view structure, animation, scroll, perf, accessibility, Liquid Glass, Instruments) | `swiftui-expert-skill` (community) |
| Cross-platform conditionals (`#if os(tvOS)`, `editMode`, haptics, drag receiving) | `apple-multiplatform` |
| Design tokens (platform-branched motion springs, button tint) | `swiftui-design-tokens` |
| Drag-and-drop (tvOS gating) | `swiftui-drag-drop` |
| File export (tvOS gating) | `swiftui-file-export` |
| UI testing patterns + `AccessibilityMarkerView` + identifier conventions + tvOS XCUITest divergence | `xctest-ui-testing` |

## Headline Rules

### Focus Engine — [references/focus-engine.md](references/focus-engine.md)

1. **No `.focusable()` on container wrappers.** Focus stops at the
   outer view; children never receive focus.
2. **Pair focusable POD rows with parent `@FocusState`** to anchor focus
   identity against parent redraws.
3. **Scope custom `.animation()` to child content**, not the focusable
   element. Custom animation on the focusable view fights the built-in
   hover effect.
4. **Use token-based settle delay** for long focus-change animations to
   avoid noise during rapid swiping.
5. **`ScrollView` with no focusable children is unscrollable** on tvOS —
   scroll is focus-driven.
6. **Prefer `.scrollTargetBehavior(.viewAligned)` over `.paging`.**
7. **Verify focus animations on real Apple TV hardware** — Simulator
   does not replicate the hover curve.

### Accessibility — [references/accessibility.md](references/accessibility.md)

1. **Dismiss modals via `.onExitCommand`**, not Close buttons. Branch
   visible Close button with `#if !os(tvOS)`.
2. **Destructive `confirmationDialog` / `alert` declares Cancel first.**
   Severity-1 on tvOS — no pointer to override default focus.
3. **Never manually reassert focus** via
   `DispatchQueue.main.asyncAfter` — hijacks VoiceOver and Switch Control.
4. **Hide non-actionable focus helpers** (`Rectangle().fill(.clear)`)
   with `.accessibilityHidden(true)`, not `.accessibilityAddTraits(.isButton)`.

### Design Regressions — [references/design-regressions.md](references/design-regressions.md)

1. **Use `.fullScreenCover()` for tvOS modals**, not `.sheet()`. Sheet
   does not reliably trap focus on older tvOS.
2. **No glass-on-glass.** Glass button inside a glass-backed modal
   produces muddy double-blur. Use `.bordered` / `.borderedProminent`
   inside modals.
3. **No `.buttonStyle(.plain)` with custom styling on focusable views.**
   Loses automatic focus-ring management; rings clip against ScrollViews.
4. **Walk the tvOS QA checklist before merging:** toolbar traversal,
   default focus on entry, Menu-button dismiss path, no focus flicker.

## Review Checklist

### Focus
- [ ] No `.focusable()` on container views wrapping focusable children
- [ ] Focusable POD rows pair with parent `@FocusState` + `.focused(_:equals:)`
- [ ] Custom `.animation()` on focusable elements scoped to child content
- [ ] Long focus-change animations use token-based settle delay
- [ ] All `ScrollView` content contains focusable children
- [ ] `.viewAligned` preferred over `.paging`
- [ ] Focus animations verified on real Apple TV hardware

### Accessibility
- [ ] Modals dismiss via `.onExitCommand { dismiss() }`
- [ ] Visible Close buttons gated `#if !os(tvOS)`
- [ ] Destructive dialogs declare safe option (Cancel / Keep) first
- [ ] No manual `isFocused = true` from `DispatchQueue.main.asyncAfter`
- [ ] Zero-size focus helpers use `.accessibilityHidden(true)`

### Design Regressions
- [ ] tvOS modals use `.fullScreenCover()`, not `.sheet()`
- [ ] No glass button styles inside glass-backed modals
- [ ] No `.buttonStyle(.plain)` on focusable views with custom styling
- [ ] tvOS QA checklist walked before merging (toolbar, default focus, dismiss, no flicker)
- [ ] Focus containment verified: press right 5+ times inside modal, focus stays inside

## References

- [references/focus-engine.md](references/focus-engine.md) — Focus engine patterns: container `.focusable()` rule, POD + `@FocusState`, hover conflict, settle delay, focus-driven scroll, `.viewAligned` vs `.paging`, simulator vs hardware
- [references/accessibility.md](references/accessibility.md) — Menu dismissal, destructive dialog default focus (severity-1), cross-platform dismiss pattern, VoiceOver-on-tvOS rules
- [references/design-regressions.md](references/design-regressions.md) — Glass-on-glass anti-pattern, `.buttonStyle(.plain)` focus-ring issue, modal focus containment, manual focus reassertion anti-pattern, tvOS focus-traversal QA checklist
