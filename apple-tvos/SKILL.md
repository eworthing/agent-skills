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

## Rule Index

| ID | Rule | Severity |
|---|---|---|
| tvOS-F01 | No `.focusable()` on container wrappers | 1 |
| tvOS-F02 | Pair focusable POD rows with parent `@FocusState` | 1 |
| tvOS-F03 | Scope custom `.animation()` to child content, not focusable view | 2 |
| tvOS-F04 | Use token-based settle delay for focus-driven animations | 2 |
| tvOS-F05 | `ScrollView` needs focusable children to be scrollable | 1 |
| tvOS-F06 | Prefer `.scrollTargetBehavior(.viewAligned)` over `.paging` | 3 |
| tvOS-F07 | Verify focus animations on real Apple TV hardware | 2 |
| tvOS-A01 | Dismiss modals via `.onExitCommand`, not visible Close button | 2 |
| tvOS-A02 | Destructive `confirmationDialog`/`alert` declares Cancel first | 1 |
| tvOS-A03 | Never manually reassert focus via `DispatchQueue.main.asyncAfter` | 1 |
| tvOS-A04 | Hide non-actionable focus helpers with `.accessibilityHidden(true)` | 2 |
| tvOS-D01 | Use `.fullScreenCover()` for tvOS modals, not `.sheet()` | 1 |
| tvOS-D02 | No glass-on-glass (glass button inside glass-backed modal) | 2 |
| tvOS-D03 | No `.buttonStyle(.plain)` with custom styling on focusable views | 2 |
| tvOS-D04 | Walk tvOS QA checklist before merging | 2 |

Severity 1 = data loss or focus break; 2 = UX regression; 3 = polish.

## Headline Rules

Each rule includes a **Bypass / N/A** note for shared-code or
non-tvOS-supporting contexts.

### Focus Engine — [references/focus-engine.md](references/focus-engine.md)

**tvOS-F01.** No `.focusable()` on container wrappers. Focus stops at the
outer view; children never receive focus.
*Bypass / N/A:* Containers that intentionally act as a single focusable
unit (e.g., a card cluster behaving as one logical button). Use a real
`Button` instead.

**tvOS-F02.** Pair focusable POD rows with parent `@FocusState` to
anchor focus identity against parent redraws.
*Bypass / N/A:* Rows that are not POD (already hold `@State` /
`@Observable`) — SwiftUI tracks identity via the property wrapper.

**tvOS-F03.** Scope custom `.animation()` to child content, not the
focusable element. Custom animation on the focusable view fights the
built-in hover effect.
*Bypass / N/A:* `.animation(nil, ...)` to explicitly disable, or
animations on `@FocusState`-driven properties handled by the system.

**tvOS-F04.** Use token-based settle delay for long focus-change
animations to avoid noise during rapid swiping.
*Bypass / N/A:* Cheap, idempotent focus reactions (e.g., a color tint
change) that cancel cleanly without visible thrash.

**tvOS-F05.** `ScrollView` with no focusable children is unscrollable —
scroll is focus-driven on tvOS.
*Bypass / N/A:* Code branched `#if !os(tvOS)` for iOS-only content;
single-screen content that fits without scrolling.

**tvOS-F06.** Prefer `.scrollTargetBehavior(.viewAligned)` over
`.paging`.
*Bypass / N/A:* True full-screen pager UX (onboarding, slideshow) where
page boundaries are part of the design intent.

**tvOS-F07.** Verify focus animations on real Apple TV hardware —
Simulator does not replicate the hover curve.
*Bypass / N/A:* Animations that do not interact with focus (data-driven
content transitions). Still smoke-test once on hardware before shipping.

### Accessibility — [references/accessibility.md](references/accessibility.md)

**tvOS-A01.** Dismiss modals via `.onExitCommand`, not Close buttons.
Branch visible Close button with `#if !os(tvOS)`.
*Bypass / N/A:* Modals on iOS / iPadOS / macOS in shared code —
`.onExitCommand` also triggers on macOS Escape key (tvOS 13+, macOS
10.15+), no-op on iOS / iPadOS.

**tvOS-A02 (severity-1).** Destructive `confirmationDialog` / `alert`
declares Cancel first. tvOS focus engine puts default focus on first
declared button.
*Bypass / N/A:* Non-destructive confirmations where either choice is
safe. Never bypass for destructive (`role: .destructive`) actions.

**tvOS-A03 (severity-1).** Never manually reassert focus via
`DispatchQueue.main.asyncAfter` — hijacks VoiceOver and Switch Control.
*Bypass / N/A:* None. Use focus containment (`.fullScreenCover()`,
scoped `@FocusState`) instead.

**tvOS-A04.** Hide non-actionable focus helpers
(`Rectangle().fill(.clear)`) with `.accessibilityHidden(true)`, not
`.accessibilityAddTraits(.isButton)`.
*Bypass / N/A:* Helpers that are genuinely actionable (run code on
Select) — model them as a real `Button`.

### Design Regressions — [references/design-regressions.md](references/design-regressions.md)

**tvOS-D01.** Use `.fullScreenCover()` for tvOS modals, not `.sheet()`.
`.sheet()` focus containment is not reliable on tvOS; assume it leaks
unless verified on hardware for the specific tvOS deployment target.
*Bypass / N/A:* Non-modal pop-overs handled separately; cross-platform
code can use `.sheet()` on iOS branches and `.fullScreenCover()` on
tvOS.

**tvOS-D02.** No glass-on-glass. Glass button (`.buttonStyle(.glass)` /
`.glassProminent`) inside a glass-backed modal or chrome surface
produces muddy double-blur. Use `.bordered` / `.borderedProminent`
inside modal content.
*Bypass / N/A:* Glass surfaces on toolbar / nav bar / tab bar chrome
where the foreground itself is not glass.

**tvOS-D03.** No `.buttonStyle(.plain)` with custom styling on focusable
views. Loses automatic focus-ring management; rings clip against
`ScrollView` containers.
*Bypass / N/A:* Non-focusable content rows (e.g., a row that's never
the focus target — display only) can use `.plain` safely.

**tvOS-D04.** Walk the tvOS QA checklist before merging — toolbar
traversal, default focus on entry, Menu-button dismiss path, no focus
flicker.
*Bypass / N/A:* PRs that touch zero tvOS-rendered code (e.g., backend
data layer; iOS-only feature gated `#if !os(tvOS)`).

## Review Checklist

### Focus
- [ ] tvOS-F01 — No `.focusable()` on container views wrapping focusable children
- [ ] tvOS-F02 — Focusable POD rows pair with parent `@FocusState` + `.focused(_:equals:)`
- [ ] tvOS-F03 — Custom `.animation()` on focusable elements scoped to child content
- [ ] tvOS-F04 — Long focus-change animations use token-based settle delay
- [ ] tvOS-F05 — All `ScrollView` content contains focusable children
- [ ] tvOS-F06 — `.viewAligned` preferred over `.paging`
- [ ] tvOS-F07 — Focus animations verified on real Apple TV hardware

### Accessibility
- [ ] tvOS-A01 — Modals dismiss via `.onExitCommand { dismiss() }`; visible Close buttons gated `#if !os(tvOS)`
- [ ] tvOS-A02 — Destructive dialogs declare safe option (Cancel / Keep) first
- [ ] tvOS-A03 — No manual `isFocused = true` from `DispatchQueue.main.asyncAfter`
- [ ] tvOS-A04 — Zero-size focus helpers use `.accessibilityHidden(true)`

### Design Regressions
- [ ] tvOS-D01 — tvOS modals use `.fullScreenCover()`, not `.sheet()`
- [ ] tvOS-D02 — No glass button styles inside glass-backed modals
- [ ] tvOS-D03 — No `.buttonStyle(.plain)` on focusable views with custom styling
- [ ] tvOS-D04 — tvOS QA checklist walked before merging (toolbar, default focus, dismiss, no flicker)
- [ ] Focus containment verified: press right 5+ times inside modal, focus stays inside (covered by tvOS-D01)

## References

- [references/focus-engine.md](references/focus-engine.md) — Focus engine patterns: container `.focusable()` rule, POD + `@FocusState`, hover conflict, settle delay, focus-driven scroll, `.viewAligned` vs `.paging`, simulator vs hardware
- [references/accessibility.md](references/accessibility.md) — Menu dismissal, destructive dialog default focus (severity-1), cross-platform dismiss pattern, VoiceOver-on-tvOS rules
- [references/design-regressions.md](references/design-regressions.md) — Glass-on-glass anti-pattern, `.buttonStyle(.plain)` focus-ring issue, modal focus containment, manual focus reassertion anti-pattern, tvOS focus-traversal QA checklist
