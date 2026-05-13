# swiftui-patterns Evaluation

**Date:** 2026-05-12 (post-Phase-3 merge from Tiercade + P1 fixes)
**Evaluator:** Claude Opus 4.7
**Skill version:** Vendored from AvdLee/SwiftUI-Agent-Skill + Tiercade tvOS merge
**Automated score:** 100% (13/13)

---

## Automated Checks

```
📋 Skill Evaluation: swiftui-patterns
==================================================
  [STRUCTURE]
    ✅ SKILL.md / frontmatter / name match / non-empty references
  [TRIGGER]
    ✅ Description length adequate (69 words)
    ✅ Description includes trigger contexts (Use when…)
  [DOCUMENTATION]
    ✅ SKILL.md body length (493 lines)
    ✅ References linked from SKILL.md
  [SCRIPTS]
    ✅ No scripts/
  [SECURITY]
    ✅ No hardcoded credentials or emails

  Pass: 13  Warn: 0  Fail: 0
  Structural score: 100%
```

File layout:
- `SKILL.md` — 493 lines (scope + decision rules + checklists + tvOS pointers)
- `references/animation-guide.md` — 605 lines (transitions, Animatable, phase/keyframe, transactions, completion)
- `references/performance-guide.md` — 425 lines (POD, equatable, ForEach, anti-patterns, composition)
- `references/tvos.md` — 186 lines (focus-driven scrolling, focus hover conflict, focusToken settle delay, POD + `@FocusState`, container-`.focusable()` rule, simulator caveat)

## Merge Summary

Merged from `Tiercade/skills/swiftui-patterns` + addressed pre-existing P1 list.

**New `references/tvos.md`** (186 lines):
- Composition: no `.focusable()` on container wrappers
- POD + `@FocusState` pairing to prevent focus identity loss
- Animation: focus hover conflict + mitigation (scope to inner content)
- Animation: token-based focus settle delay (`focusToken` counter) for long-running focus-change animations
- Simulator-vs-hardware caveat
- Scroll: focus-driven scrolling (no focusable = unscrollable)
- Scroll: `.viewAligned` over `.paging` on tvOS
- Cross-references to sibling tvOS reference files (xctest-ui-testing, design-review, accessibility, design-tokens)

**Body additions:**
- New "Scope" section at top: declares ownership (composition / identity / diffing / animation / scroll / text / tvOS focus) and table of scope boundaries with 5 sibling skills
- tvOS one-line pointers at end of Composition, Performance, Animation, Scroll sections — each redirects to `references/tvos.md` for depth
- tvOS items added to Review Checklist (composition, animation, scroll)
- New references row in References section

**P1 fixes (from prior 83/100 baseline):**
- **Description**: "Relevant when…" → "Use when…"; expanded 32 → 69 words; tvOS coverage made explicit; trigger contexts enumerated (POD diffing, focus hover, settle delay, focus-driven scroll)
- **Modernized `ScrollViewReader`**: new code now uses `.scrollPosition(id:)` (iOS 17+); `ScrollViewReader` kept as pre-17 fallback with explicit annotation
- **Modernized downsample**: `UIScreen.main.scale` (deprecated since iOS 16) replaced with `displayScale` parameter sourced from `@Environment(\.displayScale)`; call-site example added
- **Scope-boundary cross-link**: explicit table maps adjacent concerns to sibling skills (`swiftui-expert-skill`, `swiftui-deprecated-apis`, `swiftui-design-tokens`, `swiftui-accessibility`, `xctest-ui-testing`)

Rejected (Tiercade-coupled):
- Frontmatter `metadata` block (version 1.2.0, "Tiercade Team", category/tags)
- `applyTo: "Tiercade/Views/**/*.swift"` glob
- "Tiercade is tvOS-first" preamble framing
- `CardView.swift` line-number reference (`already used in CardView.swift line ~130`)
- `TierStatistic` model type used in narrow-state example
- `image-import` skill cross-reference
- Tiercade Cross-References table (pointed at `state-management`, `api-deprecation`, `tvos-navigation`, `ui-component-test-setup` which don't exist in agent-skills; replaced with the actual agent-skills equivalents)

**Allow-list compliance verified:**
- `focusToken` confined to `references/tvos.md`; absent from SKILL.md body.
- Body uses neutral phrasing: "token-based settle delay", "focus hover conflict".

## Manual Assessment

| # | Criterion | Score | Notes |
|---|-----------|-------|-------|
| 1.1 | Completeness | 4/4 | Was 3/4 (iOS-only). Now adds tvOS focus engine via references: focus-driven scrolling, hover conflict, settle delay, POD + `@FocusState`, container-`.focusable()` rule. macOS-tilted text content unchanged but explicitly scoped via new Scope section. |
| 1.2 | Correctness | 4/4 | Was 3/4. `ScrollViewReader` claim modernized — `.scrollPosition(id:)` annotated as preferred on iOS 17+, `ScrollViewReader` retained for pre-17 with explicit framing. `UIScreen.main.scale` replaced by `displayScale` parameter sourced from `@Environment(\.displayScale)` (post-iOS-16 supported approach). `@Animatable` macro availability still un-versioned (acceptable since it's name-stable across releases). |
| 1.3 | Appropriateness | 4/4 | Markdown reference, no deps. |
| 2.1 | Fault Tolerance | 3/4 | Anti-pattern lists still present; new tvOS reference adds mitigation patterns (token-based settle delay) which is a higher-confidence fault-tolerance pattern. |
| 2.2 | Error Reporting | 3/4 | "Missing animatableData = silent failure" callout retained. Could still add more diagnostic recipes. |
| 2.3 | Recoverability | 4/4 | Read-only. |
| 3.1 | Token Cost | 3/4 | Was 2/4 (391 lines well over target). Body grew to 493 (under 500 threshold) by adding tvOS one-line pointers + Scope section, but tvOS depth offloaded entirely to references. Net: agent loads only the surface it needs; tvOS code is fetched only when relevant. |
| 3.2 | Execution Efficiency | 4/4 | No scripts. |
| 4.1 | Learnability | 4/4 | GOOD/BAD pairs throughout. New Scope table is a learnability win: agent immediately sees what's in/out of scope. |
| 4.2 | Consistency | 4/4 | Uniform framing maintained. New tvOS pointers all follow same "tvOS:" prefix + reference link pattern. |
| 4.3 | Feedback Quality | 3/4 | Decision trees and tables preserved. tvOS section adds symptom→pattern mapping (focus jitter → scope to child). |
| 4.4 | Error Prevention | 4/4 | Strong: deprecated-form warnings, `#if DEBUG` gate, tvOS container-focusable rule explicit. |
| 5.1 | Discoverability | 4/4 | Was 3/4. "Use when…" phrase now present; trigger contexts include tvOS-specific terms. Scope-boundary table resolves prior overlap-with-`swiftui-expert-skill` concern. |
| 5.2 | Forgiveness | 4/4 | Read-only. |
| 6.1 | Credential Handling | 4/4 | No secrets. |
| 6.2 | Input Validation | 4/4 | No input surface. |
| 6.3 | Data Safety | 4/4 | Read-only. |
| 7.1 | Modularity | 4/4 | Was 3/4. Three reference files now (animation, performance, tvos). tvOS content has a dedicated home; no duplication risk. |
| 7.2 | Modifiability | 4/4 | Was 3/4. Adding a new tvOS pattern → references/tvos.md only. Adding a new top-level pattern still requires SKILL.md edit but the Scope table makes the structural decision explicit. |
| 7.3 | Testability | 2/4 | Still no mechanism to detect drift against live SwiftUI behavior. No per-claim citations. Improvement available in P2 (link to WWDC sessions, evolution proposals). |
| 8.1 | Trigger Precision | 4/4 | Was 3/4. "Use when…" present; trigger contexts now name tvOS-specific symptoms ("focus hover conflicts", "focus settle delays", "focus-driven scroll"). Scope-boundary table resolves overlap with `swiftui-expert-skill`. |
| 8.2 | Progressive Disclosure | 3/4 | Was 2/4. SKILL.md still ~493 lines but now the middle layer is genuinely intermediate: it owns decision rules + brief examples, and the three references files own depth. tvOS code (the biggest delta) lives only in references. |
| 8.3 | Composability | 4/4 | Was 3/4. Explicit Scope table cross-links 5 sibling skills; tvOS reference cross-links 4 sibling tvOS reference files. |
| 8.4 | Idempotency | 4/4 | Read-only. |
| 8.5 | Escape Hatches | 3/4 | `Self._printChanges()` acknowledged as undocumented; deprecated forms named explicitly; pre-17 `ScrollViewReader` retained as explicit escape hatch for older deployment targets. |
| | **TOTAL** | **92/100** | **Excellent** — publishable |

## Priority Fixes

### P0 — Fix Before Publishing
None.

### P1 — Should Fix
None. All prior P1 fixes landed.

### P2 — Nice to Have
1. Add per-iOS-version availability table for scattered `(iOS 17+)` annotations.
2. Add upstream citations: `@Animatable` macro → Swift evolution proposal; `_printChanges` → WWDC session; `.scrollPosition(id:)` → Apple docs. Improves `7.3` testability.
3. Add accessibility-pattern pointers cross-linked to `swiftui-accessibility` skill.
4. Add macOS variant section or rename to clarify iOS/tvOS bias of some content (Navigation Configuration still references `.navigationBarTitleDisplayMode` which is iOS-only).
5. Add a "when to break the rule" section per category.
6. Add diagnostic recipes table (symptom → likely root cause → pattern to apply).

## Revision History
| Date | Score | Notes |
|------|-------|-------|
| 2026-05-12 (baseline) | 92% structural / 83 manual | Vendored from AvdLee. Auto-eval 1 warn (Relevant when → Use when). Main drags: iOS-only scope, two stale-API examples, no tvOS, 391-line body duplicated references. |
| 2026-05-12 (post-merge) | 100% structural / 92 manual | references/tvos.md added (focus-driven scrolling, hover conflict, focusToken settle delay, POD+@FocusState, container-focusable rule, simulator caveat). Body adds Scope table with 5-sibling cross-links, four tvOS one-line pointers, three checklist additions. P1 fixes landed: description "Use when…", ScrollViewReader → .scrollPosition(id:) on iOS 17+, UIScreen.main.scale → @Environment(\.displayScale). |
