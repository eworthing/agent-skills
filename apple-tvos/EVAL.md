# apple-tvos Evaluation

**Date:** 2026-05-13 (renamed + expanded from `swiftui-tvos-focus`)
**Evaluator:** Claude Opus 4.7
**Skill version:** Definitive tvOS skill — focus engine + accessibility deltas + design regressions
**Status:** Needs re-evaluation against full rubric; prior `swiftui-tvos-focus` 93/100 manual score no longer applicable to the new scope.

---

## Rename + Expansion Summary

Renamed `swiftui-tvos-focus` → `apple-tvos`. Scope broadened from
focus-engine-only to comprehensive tvOS coverage by absorbing tvOS
deltas from two eliminated skills:

- `swiftui-accessibility` (eliminated in same round): tvOS Menu
  dismissal, destructive `confirmationDialog` default focus ordering,
  VoiceOver-on-tvOS traversal rules, cross-platform dismiss-pattern
  branch.
- `swiftui-design-review` (eliminated in same round): tvOS modal focus
  containment audit, manual-focus-reassertion anti-pattern,
  glass-on-glass anti-pattern, `.buttonStyle(.plain)` focus-ring
  clipping, tvOS focus-traversal QA checklist, severity-1 designation.

Auth-coverage verification confirmed (per user rule "verify auth doesn't
already cover that portion"):
- `swiftui-expert-skill/references/focus-patterns.md` covers only
  cross-platform API availability for tvOS — no runtime focus patterns,
  hover conflict, settle delay, POD identity, or scroll mechanics.
- `swiftui-expert-skill/references/accessibility-patterns.md` does not
  cover `.onExitCommand`, Menu-button dismissal, or tvOS destructive
  dialog severity.
- `swiftui-expert-skill/references/liquid-glass.md` covers iOS/macOS
  Liquid Glass adoption — no tvOS focus-context glass-on-glass.

Dropped (auth covers — with different guidance):
- `references/observable-state.md` — `@AppStorage`-inside-`@Observable`
  gotcha. Auth `swiftui-expert-skill/references/state-management.md`
  (lines 78-103) covers this topic with **opposite** guidance
  (`@ObservationIgnored @AppStorage` works correctly because @AppStorage
  uses its own UserDefaults KVO channel). Conflict resolved by deferring
  to auth.

## File Layout

- `SKILL.md` — router + 3-topic scope + headline rules + review checklist
- `references/focus-engine.md` (renamed from `tvos.md`) — focus mechanics
- `references/accessibility.md` (NEW — absorbed from
  `swiftui-accessibility/references/tvos.md` + tvOS sections of
  `swiftui-accessibility/SKILL.md`)
- `references/design-regressions.md` (NEW — absorbed from
  `swiftui-design-review/references/liquid-glass-and-tvos.md`)

## Re-eval Required

After absorption + rename + drop, the rubric needs re-running. Skip until
next eval pass. Structural eval verified 100% (13/13).

## Revision History

| Date | Score | Notes |
|------|-------|-------|
| 2026-05-12 (baseline) | 83 manual | Vendored from AvdLee/SwiftUI-Agent-Skill (as `swiftui-patterns`). iOS-only scope. |
| 2026-05-12 (post-merge) | 92 manual | + tvOS focus reference. Scope table cross-links 5 sibling skills. |
| 2026-05-12 (Phase 2 FOLD) | 93 manual | + observable-state reference. |
| 2026-05-12 (refocus) | _pending_ | Renamed to `swiftui-tvos-focus`. Slimmed SKILL.md 493 → ~115 lines. Dropped animation-guide.md + performance-guide.md. Trimmed observable-state.md to @AppStorage gotcha. |
| 2026-05-13 (rename + expand) | _pending_ | Renamed to `apple-tvos`. Absorbed tvOS deltas from eliminated `swiftui-accessibility` (Menu dismissal, destructive dialog focus) → new `references/accessibility.md`. Absorbed tvOS deltas from eliminated `swiftui-design-review` (modal containment, focus reassertion anti-pattern, glass-on-glass, button-style focus-ring, QA checklist) → new `references/design-regressions.md`. Dropped `references/observable-state.md` (@AppStorage gotcha conflicts with auth `state-management.md` guidance). Renamed `tvos.md` → `focus-engine.md`. SKILL.md rewritten as 3-topic router with combined review checklist. |
