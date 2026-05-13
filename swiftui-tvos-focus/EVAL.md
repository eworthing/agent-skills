# swiftui-tvos-focus Evaluation

**Date:** 2026-05-12 (refocus after authoritative `swiftui-expert-skill` adoption)
**Evaluator:** Claude Opus 4.7
**Skill version:** Refocus of repo `swiftui-patterns` → tvOS focus engine + one cross-platform state gotcha
**Status:** Needs re-evaluation against full rubric; prior 93/100 manual score no longer applicable to the new scope.

---

## Refocus Summary

Renamed `swiftui-patterns` → `swiftui-tvos-focus`. Repo `swiftui-patterns`
duplicated general SwiftUI guidance now owned by authoritative
[`swiftui-expert-skill`](https://github.com/AvdLee/SwiftUI-Agent-Skill)
(`references/state-management.md`, `view-structure.md`,
`performance-patterns.md`, `animation-*.md`, `scroll-patterns.md`,
`list-patterns.md`, `text-patterns.md`, `focus-patterns.md`). This
skill is now scoped to:

1. **tvOS focus-engine deltas** — patterns auth's `focus-patterns.md` does not cover at depth.
2. **`@AppStorage`-inside-`@Observable` silent-failure gotcha** — unique enough to repeat outside the general state reference.

## Dropped Files

- `references/animation-guide.md` (605 lines) — auth `references/animation-basics.md` + `animation-transitions.md` + `animation-advanced.md` cover this surface.
- `references/performance-guide.md` (425 lines) — auth `references/performance-patterns.md` covers POD, equatable, ForEach identity, anti-patterns, composition.

## Retained Files

- `SKILL.md` — slimmed from 493 → ~100 lines. Owns scope table, 7-rule tvOS focus checklist, `@AppStorage` gotcha summary, cross-references.
- `references/tvos.md` — focus engine patterns (composition, POD + `@FocusState`, hover conflict, settle delay, focus-driven scroll, `.viewAligned` vs `.paging`, simulator vs hardware).
- `references/observable-state.md` — trimmed to `@AppStorage`-inside-`@Observable` gotcha only; cross-links auth `references/state-management.md` for general state-container shape, `@Bindable`, mutation routing, undo snapshots, error surfacing.

## Dropped Content (now in auth)

- View composition (`@ViewBuilder let` over closures, modifier-over-conditional, extraction rules, ZStack vs overlay) → auth `view-structure.md`
- POD views + general performance rules, `Self._printChanges()` → auth `performance-patterns.md`
- Animation decision tree, transforms over layout, `withAnimation` completion, `@Animatable` macro → auth `animation-basics.md` + `animation-advanced.md`
- Scroll threshold gating, `.scrollPosition(id:)`, `.visualEffect`, scroll target behavior → auth `scroll-patterns.md`
- `Text(value, format:)`, `localizedStandardContains`, `Label`, `.onGeometryChange` → auth `text-patterns.md` + `layout-best-practices.md`
- Image downsampling → auth `image-optimization.md`
- Navigation title display mode → auth `latest-apis.md` / `sheet-navigation-patterns.md`
- `@Observable` + `@MainActor` + `final class` container shape, `@Bindable`, mutation routing, undo snapshot, error surfacing, typed-error taxonomy → auth `state-management.md`

## Re-eval Required

The original 93/100 score reflected the broader `swiftui-patterns` scope.
After the refocus, the skill is tighter but narrower; the rubric needs
re-running against the new SKILL.md body. Skip until next eval pass.

## Revision History

| Date | Score | Notes |
|------|-------|-------|
| 2026-05-12 (baseline) | 83 manual | Vendored from AvdLee/SwiftUI-Agent-Skill. iOS-only scope. |
| 2026-05-12 (post-merge) | 92 manual | + tvOS focus reference (focus-driven scrolling, hover conflict, settle delay, POD + `@FocusState`, container-focusable rule, simulator caveat). Scope table cross-links 5 sibling skills. |
| 2026-05-12 (Phase 2 FOLD) | 93 manual | + observable-state reference (`@Observable` + `@MainActor` + `final class`, `@Bindable`, mutation routing, undo snapshot, error surfacing, typed-error taxonomy, `@AppStorage`-in-`@Observable` gotcha). |
| 2026-05-12 (refocus) | _pending_ | Renamed `swiftui-patterns` → `swiftui-tvos-focus`. Dropped `animation-guide.md`, `performance-guide.md`. Slimmed `SKILL.md` 493 → ~100 lines. Trimmed `observable-state.md` to the `@AppStorage`-in-`@Observable` gotcha only. Defers general SwiftUI to authoritative `swiftui-expert-skill`. |
