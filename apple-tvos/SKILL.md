---
name: apple-tvos
author: eworthing
original-author: Antoine van der Lee (AvdLee)
source: https://github.com/AvdLee/SwiftUI-Agent-Skill
description: >-
  Definitive tvOS reference for SwiftUI on Apple TV: focus engine,
  accessibility deltas, and design-regression checks. Use when building
  or debugging tvOS focus behavior (settle delays, `.focusable()`
  container blocking children, focus identity loss across redraws,
  `ScrollView` with no focusable children, `.viewAligned` vs `.paging`,
  Simulator vs hardware divergence), applying tvOS accessibility patterns
  (`.onExitCommand` Menu dismissal, destructive `confirmationDialog` /
  `alert` default focus — severity-1 on tvOS, VoiceOver traversal), or
  auditing tvOS design regressions (modal focus containment leakage,
  manual focus reassertion, glass-on-glass, `.buttonStyle(.plain)`
  focus-ring clipping). The community `swiftui-expert-skill` owns
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

Full rule index + per-rule *Bypass / N/A* contexts:
**[references/rules.md](references/rules.md)** (machine-readable:
[evals/rules.json](evals/rules.json)).

Severity 1 = data loss or focus break; 2 = UX regression; 3 = polish.

### Focus Engine — [references/focus-engine.md](references/focus-engine.md)

- **tvOS-F01 (1).** No `.focusable()` on container wrappers.
- **tvOS-F02 (1).** Pair focusable POD rows with parent `@FocusState`.
- **tvOS-F03 (2).** Scope custom `.animation()` to child content.
- **tvOS-F04 (2).** Token-based settle delay for focus-driven animations.
- **tvOS-F05 (1).** `ScrollView` needs focusable children to be scrollable.
- **tvOS-F06 (3).** Prefer `.viewAligned` over `.paging`.
- **tvOS-F07 (2).** Verify focus animations on real Apple TV hardware.

### Accessibility — [references/accessibility.md](references/accessibility.md)

- **tvOS-A01 (2).** Dismiss modals via `.onExitCommand`; gate visible Close button `#if !os(tvOS)`.
- **tvOS-A02 (1).** Destructive `confirmationDialog`/`alert` declares Cancel first.
- **tvOS-A03 (1).** Never manually reassert focus via `DispatchQueue.main.asyncAfter`.
- **tvOS-A04 (2).** Hide non-actionable focus helpers with `.accessibilityHidden(true)`.

### Design Regressions — [references/design-regressions.md](references/design-regressions.md)

- **tvOS-D01 (1).** Use `.fullScreenCover()` for tvOS modals, not `.sheet()`.
- **tvOS-D02 (2).** No glass-on-glass.
- **tvOS-D03 (2).** No `.buttonStyle(.plain)` with custom styling on focusable views.
- **tvOS-D04 (2).** Walk tvOS QA checklist before merging.

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

- [references/rules.md](references/rules.md) — Full rule index + per-rule *Bypass / N/A* contexts (source of truth)
- [references/focus-engine.md](references/focus-engine.md) — Focus engine patterns: container `.focusable()` rule, POD + `@FocusState`, hover conflict, settle delay, focus-driven scroll, `.viewAligned` vs `.paging`, simulator vs hardware
- [references/accessibility.md](references/accessibility.md) — Menu dismissal, destructive dialog default focus (severity-1), cross-platform dismiss pattern, VoiceOver-on-tvOS rules
- [references/design-regressions.md](references/design-regressions.md) — Glass-on-glass anti-pattern, `.buttonStyle(.plain)` focus-ring issue, modal focus containment, manual focus reassertion anti-pattern, tvOS focus-traversal QA checklist
- [evals/rules.json](evals/rules.json) — Machine-readable rule index for agent ingestion
