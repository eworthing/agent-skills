# xctest-ui-testing Evaluation

**Date:** 2026-05-12 (post-Phase-3 merge from Tiercade)
**Evaluator:** Claude Opus 4.7
**Skill version:** SKILL.md + references/{tvos,new-component-checklist}.md
**Automated score:** 100% (13/13)

---

## Automated Checks

```
  [STRUCTURE]
    ✅ SKILL.md exists / frontmatter / name match / non-empty references
  [TRIGGER]
    ✅ Description length adequate (74 words)
    ✅ Description includes trigger contexts (Use when…)
  [DOCUMENTATION]
    ✅ SKILL.md body length (412 lines — split achieved)
    ✅ References are linked from SKILL.md
  [SCRIPTS]
    ✅ No scripts/
  [SECURITY]
    ✅ No hardcoded credentials or emails

  Pass: 13  Warn: 0  Fail: 0
  Structural score: 100%
```

## Merge Summary

Imported and de-projectized from `Tiercade/skills/ui-testing`:

**New body content:**
- **Concrete `AccessibilityMarkerView`** UIKit + AppKit code (renamed from Tiercade's `UITestAXMarkerView` — generic name)
- **macOS-Specific Patterns** section: `ensureAppIsFrontmost(_:bundleIdentifier:)` helper with escalating strategies (XCUIApplication.activate → NSRunningApplication.activate), window-pinning function `pinTestWindowSize()` for stable coordinates, toolbar/keyboard reliability notes
- **Platform Divergences Matrix**: iOS / tvOS / macOS comparison across toolbar, modals, drag/drop, keyboard, activation, coordinate stability, focus

**New `references/tvos.md`** (~210 lines): tvOS focus testing patterns — `XCUIRemote` API, `hasFocus` assertions, focus settle delay, focus reachability audit test class pattern (`FocusReachabilityAuditTests`/`FocusTransitionAndContainmentTests`), modal focus containment, layout caveats (LazyVStack, hover, POD + @FocusState).

**Extracted `references/new-component-checklist.md`** (~140 lines): the 8-step new-component testability checklist that was inlined in body. Brought SKILL.md from 530 → 412 lines.

Rejected (Tiercade-coupled):
- Frontmatter `metadata` block, `applyTo: "{TiercadeUITests/**}"` glob
- 35-screen Tiercade-specific `-uiTestPresent` enum list
- `./scripts/run_ui_tests.sh` flag set (belongs in `xctest-runner` if migrated later)
- `TiercadeUITests`, `TiercadeCore`, `ScreenID`, `OverlayRootMarker` references
- `Tiercade.xcodeproj` UUID examples (`6EF0B1012E78F0B0008EABCD`)
- Tiercade macOS shortcuts (Cmd+1..9, Opt+Cmd+arrow)
- `TVMoreSheet`/`TVSortPicker` UI component names
- `docs/testing/...` doc paths
- Body-coupled rename: `UITestAXMarkerView` → `AccessibilityMarkerView`

Also fixed while editing:
- Description: "for BenchHype screens" → "for iOS, macOS, and tvOS apps"; "Relevant when…" → "Use when…"; word count 53 → 74

## Manual Assessment

| # | Criterion | Score | Notes |
|---|-----------|-------|-------|
| 1.1 | Completeness | 4/4 | Covers launch args, accessibility identifiers, root markers (concrete code now), wait-for-element, drag/drop, sheet/alert, sheet detents, LazyVStack/duplicate-ID/modifier-order gotchas, macOS activation/window pinning, platform divergence matrix, debugging, new-component checklist (refs), tvOS focus (refs). Comprehensive. |
| 1.2 | Correctness | 4/4 | XCUITest APIs accurate; NSWorkspace frontmost check correct; tvOS focus patterns match XCUIRemote API. macOS activation escalating strategies match documented Apple behavior. |
| 1.3 | Appropriateness | 4/4 | Markdown reference + references progressive disclosure. |
| 2.1 | Fault Tolerance | 3/4 | Strong gotcha section + debugging tips. No retry semantics (N/A doc). |
| 2.2 | Error Reporting | 3/4 | Identifies common failure modes (element not found, flaky tests, frontmost activation). Could add "if you see X assertion failure" diagnostic recipes. |
| 2.3 | Recoverability | 4/4 | Read-only. |
| 3.1 | Token Cost | 4/4 | SKILL.md 412 lines (under 500 threshold); two references files split out. Agent loads only needed depth. |
| 3.2 | Execution Efficiency | 4/4 | No scripts. |
| 4.1 | Learnability | 4/4 | Concrete code examples for every pattern (root markers, activation, window pinning, etc.). New checklist is step-by-step. |
| 4.2 | Consistency | 4/4 | Uniform code-fence style; problem→solution pairs; identical pattern across sections. |
| 4.3 | Feedback Quality | 3/4 | Flaky-test triage section names specific causes (4 common). Platform matrix maps symptom → cause. |
| 4.4 | Error Prevention | 4/4 | Multiple "Always do X" / "Never do Y" rules: activation required, identifier on leaf only, modifier order matters, no Thread.sleep, 15s test cap. |
| 5.1 | Discoverability | 4/4 | "Use when…" phrase; trigger contexts enumerated; description names every covered topic. |
| 5.2 | Forgiveness | 4/4 | Read-only. |
| 6.1 | Credential Handling | 4/4 | No secrets. |
| 6.2 | Input Validation | 4/4 | No input surface. |
| 6.3 | Data Safety | 4/4 | Read-only. |
| 7.1 | Modularity | 4/4 | Three-file split (SKILL.md + tvos.md + new-component-checklist.md). Each topic has its own home. |
| 7.2 | Modifiability | 4/4 | Add new platform pattern → matrix row + section. Add new gotcha → Critical Gotchas section. Checklist updates → references file. |
| 7.3 | Testability | 2/4 | No mechanism to detect drift against XCUITest API changes or Apple platform releases. No source-link citations to Apple docs. |
| 8.1 | Trigger Precision | 4/4 | Description specific; trigger phrase present. iOS/macOS/tvOS coverage made explicit. |
| 8.2 | Progressive Disclosure | 4/4 | Body covers common path; tvOS-specific lives in references/tvos.md; new-component depth in references/new-component-checklist.md. |
| 8.3 | Composability | 3/4 | Cross-links to references/tvos.md and references/new-component-checklist.md. Could cross-link to `xctest-runner` for selective execution. |
| 8.4 | Idempotency | 4/4 | Read-only. |
| 8.5 | Escape Hatches | 3/4 | Documents test-mode conditional patterns (`-uiTest`); `Thread.sleep` discouraged but not banned in macOS activation polling loop. |
| | **TOTAL** | **92/100** | **Excellent** — publishable |

## Priority Fixes

### P0 — Fix Before Publishing
None.

### P1 — Should Fix
None. Description, BenchHype mention, macOS gaps, tvOS coverage all landed.

### P2 — Nice to Have
1. Cross-link to `xctest-runner` skill (selective test execution).
2. Add upstream citations to Apple XCTest UI Testing documentation per major pattern. Improves `7.3` testability (claims become traceable).
3. Diagnostic recipes table (symptom → likely cause → fix) for `4.3`.

## Revision History
| Date | Score | Notes |
|------|-------|-------|
| 2026-05-12 (baseline) | 92% structural / ~88 manual | Pre-merge. 1 description warning (Relevant when → Use when). Description coupled to "BenchHype". |
| 2026-05-12 (post-merge) | 100% structural / 92 manual | macOS activation/window-pin patterns, AccessibilityMarkerView code, platform matrix, tvOS references/, checklist references/. Description de-projectized + reworded. |
| 2026-05-12 (Phase 2 merge) | 100% structural / 93 manual | Phase 2 MERGE from Tiercade `ui-component-test-setup`. Added Focus Audit Registries section to references/tvos.md (~115 lines): FocusInventory registry pattern (per-screen expected-focusable-elements enum decoupled from test assertions), FocusContainmentRules registry pattern (central set of modals that must trap focus), Coverage Validation Gate concept (CI step asserting registry membership matches test-suite coverage), Sweep-Based Reachability Helper pattern (generic `performDetailedSweep(maxPressesPerDirection:directions:)` returning `(reachedElements, sweepPath)`). Rejected Tiercade-coupled content: `TiercadeCore/...ScreenID.swift`, `Tiercade/State/AppState+UITests.swift`, `TiercadeUITests/Helpers/*`, `TVMoreSheet.swift`, `./build_install_launch.sh`, `./scripts/run_ui_tests.sh`, `./scripts/run_local_gate.sh`, `./scripts/validate_test_coverage.sh`, `./scripts/visual_audit/run_visual_audit.sh`, `com.tiercade.app`, `launchTiercade(arguments:)` helper, `metadata` block, Tiercade-specific class names (`HeadToHead`, `DragAndDropTests`). |
