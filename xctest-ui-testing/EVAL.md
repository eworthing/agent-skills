# xctest-ui-testing Evaluation

**Date:** 2026-07-04 (accessibility-audit pass)
**Evaluator:** Claude Opus 4.8
**Skill version:** SKILL.md + references/{tvos,macos,new-component-checklist,runner,accessibility-audit}.md
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
    ✅ SKILL.md body length (448 lines — macOS patterns externalized to
       references/macos.md, symmetric with references/tvos.md)
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
| 4.3 | Feedback Quality | 4/4 | Flaky-test triage names specific causes; platform matrix maps symptom → cause; Judging-Failures visual-layout row now points contrast/hit-target/clipped-text/description defects at the exact instrument (`performAccessibilityAudit`) instead of a dead end. |
| 4.4 | Error Prevention | 4/4 | Multiple "Always do X" / "Never do Y" rules: activation required, identifier on leaf only, modifier order matters, no Thread.sleep, 15s test cap. |
| 5.1 | Discoverability | 4/4 | "Use when…" phrase; trigger contexts enumerated; description names every covered topic. |
| 5.2 | Forgiveness | 4/4 | Read-only. |
| 6.1 | Credential Handling | 4/4 | No secrets. |
| 6.2 | Input Validation | 4/4 | No input surface. |
| 6.3 | Data Safety | 4/4 | Read-only. |
| 7.1 | Modularity | 4/4 | SKILL.md + five references (tvos, macos, accessibility-audit, runner, new-component-checklist). Each topic has its own home. |
| 7.2 | Modifiability | 4/4 | Add new platform pattern → matrix row + section. Add new gotcha → Critical Gotchas section. Checklist updates → references file. |
| 7.3 | Testability | 3/4 | `references/accessibility-audit.md` now carries cited Apple-doc Sources (audit method + audit-type enum), verified live against the iOS 27 DocC, making those claims drift-checkable. Broader per-pattern citation across all files deliberately deferred (validator-facing, no behavioral signal in testing). |
| 8.1 | Trigger Precision | 4/4 | Description specific; trigger phrase present. iOS/macOS/tvOS coverage made explicit. |
| 8.2 | Progressive Disclosure | 4/4 | Body covers the cross-platform common path; platform-specific depth externalized (references/{tvos,macos}.md); accessibility-audit, runner, and new-component depth each in their own reference. |
| 8.3 | Composability | 3/4 | Cross-links to references/tvos.md and references/new-component-checklist.md. Could cross-link to `xctest-runner` for selective execution. |
| 8.4 | Idempotency | 4/4 | Read-only. |
| 8.5 | Escape Hatches | 3/4 | Documents test-mode conditional patterns (`-uiTest`); `Thread.sleep` discouraged but not banned in macOS activation polling loop. |
| | **TOTAL** | **94/100** | **Excellent** — publishable |

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
| 2026-05-12 (Phase 2 fold) | 100% structural / 94 manual | Phase 2 FOLD from Tiercade `toolbar-contract`. Body addition: "Identifiers Are a Stable API Contract" subsection under Accessibility Identifier Conventions — frames identifier renames as API migration (update tests + docs first, change view's `.accessibilityIdentifier(...)` second), enforces typed-enum SSOT (`TestIdentifiers` / `ActionID`) and bans inline raw identifier strings in tests OR views. references/new-component-checklist.md step 2 augmented with same API-migration framing. Rejected Tiercade-coupled content: `ActionRegistry.swift`, `ToolbarSurface.swift`, `docs/testing/testability-contract.md`, AppState routing rules, specific `ActionID` cases (`clearTier`, `reset`, `randomize`), `build_install_launch.sh`, `evidence_commits` metadata, `applyTo` glob. |
| 2026-06-03 (doctrine pass) | 100% structural / manual unchanged; anthropic-grade-optimizer 93 (A) | `anthropic-grade-optimizer` audit (target opus-4-7): Pass-1 mechanical 0 findings; Pass-2 surfaced two D-CC items, both fixed. Added `## Contents` TOC to all three reference files (runner.md / tvos.md / new-component-checklist.md), each >100 lines (AR-CC-S21). Softened residual ALL-CAPS emphasis to sentence case where the reasoning was already stated — `FIRST`/`SECOND`/`OR` in SKILL.md, `NOT` in references/tvos.md (AR-CC-S09). Gate passed, voice drift 0; re-audit expected ~100. |
| 2026-07-04 (macOS externalization) | 100% structural / 94 manual | Moved `## macOS-Specific Patterns` (activation escalation, window pinning, `NSToolbar`/keyboard reliability) to new `references/macos.md`, symmetric with the already-external `references/tvos.md` — SKILL body carries the cross-platform common path, platform-specific depth lives in references. Left a 6-line summary + pointer in SKILL.md and a Sibling-Skills row. Reclaimed the body-length soft-cap headroom the audit pass consumed: body 512→448, restoring structural 100% (13/13) without cutting any content. Real progressive-disclosure improvement (8.2), not validator-hardening. |
| 2026-07-04 (accessibility audit + RED-verified misdirection fix) | 92% structural (1 body-length WARN) / 94 manual | Added automated accessibility auditing. New `references/accessibility-audit.md`: `performAccessibilityAudit` one-call pattern, 10-case `XCUIAccessibilityAuditType` table, `issueHandler` suppression semantics (return `true` suppresses a triaged issue / `false` fails), per-platform relevance (tvOS: `.hitRegion`/`.dynamicType` moot), dedicated audit-class CI gating, cited Apple-doc Sources. Tight SKILL `## Accessibility Auditing` section, Platform Divergences matrix row, checklist step-8 audit line, description trigger clause. **Key fix (RED-verified):** amended the Judging-Failures visual-layout row — agents were citing its "XCUITest sees structure not pixels" line to *skip* the audit and wrongly conclude contrast is uncheckable. RED baseline: weak-cue "accessibility problems" task → 1/1 missed the audit + made the false claim; strong-cue tasks naming contrast/hit-target → 3/3 already found it (an inline API tutorial would have been a no-op — the value is the misdirection fix, not teaching the call). GREEN: same weak-cue task on the patched skill → 2/2 now reach for `performAccessibilityAudit` and cite the new guidance. Signature verified against live Apple DocC (iOS 17+/macOS 14+/tvOS 17+, Xcode 16.3+); not compiled (skills repo has no app project). Currency sweep found no deprecations/new APIs (verified `waitForExistence`, `press(forDuration:thenDragTo:)`, `XCTExpectFailure` live). Approved scope narrowed from "broad" to this sharp core after RED collapsed the rest: broad citation campaign + `XCTExpectFailure` deliberately NOT taken (validator-facing, no behavioral signal). Body 495→512 (WARN accepted: real coverage growth with depth externalized; cutting existing patterns to flip a soft cap would be validator-hardening). |
| 2026-06-18 (Xcode 27 verify heuristics) | 100% structural / 92 manual | Debugging Tips gained three subsections harvested from Apple's Xcode 27 `device-interaction` skill, adapted to scripted XCUITest: **Settle Before Asserting** (gate first interaction on a readiness root marker, not `sleep`), **Retry: Diagnose, Don't Mask** (treat pass-on-retry as a flake signal; preserve first-failure `XCTAttachment`; ban silent retry loops — peer-review N3), and **Judging Failures: Real Bug vs Transient** (functional/visual/transient/unexpected-exit/expected-behavior taxonomy). XCTest→Swift Testing migration content deliberately NOT taken (owned by external `swift-testing-expert`; this skill defers unit-test framework). `launchArguments` skipped (already covered). Substantive APIs (`app.state`, `XCTAttachment(screenshot:)`, `add`, `isHittable`, `addUIInterruptionMonitor`) type-checked clean vs iOS 27 simulator SDK. Manual held 92. |
