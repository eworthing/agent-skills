# swiftui-native-ux Evaluation

**Date:** 2026-05-17
**Evaluator:** Claude (Opus 4.7)
**Skill version:** initial commit on main
**Automated score:** 100% (13/13 structural checks)

---

## Automated Checks

```
[STRUCTURE]      5/5
[TRIGGER]        2/2
[DOCUMENTATION]  2/2
[SCRIPTS]        2/2
[SECURITY]       2/2
Pass: 13  Warn: 0  Fail: 0
Structural score: 100%
```

Description length: 948 chars / 123 words (Codex 1024 limit OK).

## Manual Assessment

| # | Criterion | Score | Notes |
|---|-----------|-------|-------|
| 1.1 | Completeness | 4/4 | Strong scope (12 refs + 6 workflows). Liquid Glass code examples and iPad multi-window patterns added 2026-05-17. |
| 1.2 | Correctness | 4/4 | Grounded in HIG/WWDC/Apple docs via source-architecture.md tier ranking. |
| 1.3 | Appropriateness | 4/4 | Trigger description (SKILL.md L3–17) is precise on iOS/iPadOS scope. |
| 2.1 | Fault Tolerance | 4/4 | Pure knowledge skill — no runtime failure surface. |
| 2.2 | Error Reporting | 4/4 | Failure conditions explicit in each workflow. |
| 2.3 | Recoverability | 4/4 | Non-destructive; critiques only. |
| 3.1 | Token Cost | 3/4 | ~4900 LOC total across refs+workflows; agent must load selectively via SKILL.md L32–42 decision tree. SKILL.md itself is lean (244 lines). |
| 3.2 | Execution Efficiency | 4/4 | No external calls; decision tree at SKILL.md L32–42 routes early. |
| 4.1 | Learnability | 4/4 | Quick-start decision tree + "When to Use" + workflow list. |
| 4.2 | Consistency | 4/4 | Unified vocab across refs/workflows. |
| 4.3 | Feedback Quality | 3/4 | Critique rubric + expert lenses are strong, but no worked-example critiques ship as reference. |
| 4.4 | Error Prevention | 4/4 | anti-web-smells.md flags generative-AI silhouettes early. |
| 5.1 | Discoverability | 4/4 | Examples + "When to Use" in SKILL.md. |
| 5.2 | Forgiveness | 4/4 | Knowledge-only; no state mutation. |
| 6.1 | Credential Handling | 4/4 | No secrets. |
| 6.2 | Input Validation | 4/4 | No user input requiring validation. |
| 6.3 | Data Safety | 4/4 | No data mutation. |
| 7.1 | Modularity | 4/4 | SKILL.md → references → workflows separation. |
| 7.2 | Modifiability | 4/4 | source-architecture.md templates extension. |
| 7.3 | Testability | 3/4 | Rules testable in principle; no formal test suite. |
| 8.1 | Trigger Precision | 4/4 | Tight Apple-only scope, explicit web rejection. |
| 8.2 | Progressive Disclosure | 4/4 | 4 disclosure tiers (SKILL → refs → workflows → expert lenses). |
| 8.3 | Composability | 3/4 | Prose output, not structured JSON for chaining. |
| 8.4 | Idempotency | 4/4 | Re-running critique always safe. |
| 8.5 | Escape Hatches | 3/4 | "Prefer native" rules largely non-overridable (intentional). |
| | **TOTAL** | **95/100** | Excellent — publish-ready. |

## Priority Fixes

### P0 — Fix Before Publishing

_None._ Skill is publish-ready.

### P1 — Should Fix

_All P1 issues resolved 2026-05-17._

1. ~~Liquid Glass code examples~~ — `references/liquid-glass.md` now has 4 worked examples using iOS 26 `.glassEffect()` API (toolbar capsule, map overlay, tab bar, anti-pattern), with cross-link to `swiftui-expert-skill` `references/liquid-glass.md` for full API surface.
2. ~~iPad multi-window patterns~~ — `references/ipad-layout.md` Multiwindow section expanded with `WindowGroup(for:)`, `@SceneStorage`, scene-isolated `NavigationSplitView`, and pitfalls (singleton view-model leakage, `@AppStorage` misuse).

### P2 — Nice to Have

_All P2 issues resolved 2026-05-17._

1. ~~iPad keyboard/trackpad coverage~~ — `ipad-layout.md` Keyboard Support section now includes Common Command Set table (⌘N/⌘S/⌘W/⌘F/⌘R + `.defaultAction`/`.cancelAction`/`.delete`), Split-Pane Navigation pattern using `List(selection:)`, and `Commands` menu-bar integration (`SidebarCommands`, `InspectorCommands`).
2. ~~Token reuse cross-link~~ — `workflows/generate-new-screen.md` Step 2 now defers color/spacing/typography/motion to `swiftui-design-tokens` when project tokens exist.

### Open

1. **Worked-example critiques.** No reference critiquing real screenshots/code ships with the skill. Adding `references/critique-examples.md` with 2–3 before/after critiques would raise 4.3 Feedback Quality to 4/4.

## Revision History

| Date | Score | Notes |
|------|-------|-------|
| 2026-05-17 | 94/100 | Baseline — initial skill commit |
| 2026-05-17 | 95/100 | P1+P2 fixes: Liquid Glass examples, iPad multiwindow recipes, keyboard command set, design-tokens cross-link |
| 2026-05-17 | 95/100 | Add Stitch design-handoff workflow (9 new files: 1 workflow + 6 references + `data/stitch-negative-constraints.csv` + `templates/stitch-apple-native-brief.md`). SKILL.md routed via section anchors. Description compressed 948→846 chars (Codex headroom). House-rule labels applied. Paste-export fallback when no MCP tool found. Peer-reviewed by codex gpt-5.5 across 3 rounds. Structural 13/13 retained. |
| 2026-06-18 | 95/100 | `references/navigation-patterns.md`: added SDK 27 presentation/layout APIs harvested from Apple's Xcode 27 `swiftui-whats-new-27` skill — toolbar overflow/minimization (`visibilityPriority`, `ToolbarOverflowMenu`, `.topBarPinnedTrailing`, `toolbarMinimizeBehavior`, `toolbarVisibility(.statusBar)`), `swipeActionsContainer()` for swipe outside `List`, and data-driven `confirmationDialog(_:item:)`/`alert(_:item:)` as a presentation-choice guideline. Scoped strictly to design/layout/presentation — no state/dataflow content (that stays with the external `swiftui-expert-skill`; peer-review B1). Signatures verified against Xcode 27.0 (27A5194q); all snippets type-checked clean (`swiftc -typecheck -target arm64-apple-ios27.0`). Availability-gated. Structural 13/13 retained; manual held 95. |
