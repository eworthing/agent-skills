# swiftui-accessibility Evaluation

**Date:** 2026-05-12 (post-Phase-3 merge from Tiercade)
**Evaluator:** Claude Opus 4.7
**Skill version:** SKILL.md + references/tvos.md
**Automated score:** 100% (13/13)

---

## Automated Checks

```
  [STRUCTURE]
    ✅ SKILL.md / frontmatter / name match / non-empty references
  [TRIGGER]
    ✅ Description length adequate
    ✅ Description includes trigger contexts (Use when…)
  [DOCUMENTATION]
    ✅ SKILL.md body length (337 lines)
    ✅ References linked from SKILL.md
  [SCRIPTS]
    ✅ No scripts/
  [SECURITY]
    ✅ No hardcoded credentials or emails

  Pass: 13  Warn: 0  Fail: 0
  Structural score: 100%
```

## Merge Summary

Imported and de-projectized from `Tiercade/skills/accessibility-compliance`:

**New `references/tvos.md`** (~139 lines):
- Modal dismissal via Menu button (`.onExitCommand`) — no Close buttons on tvOS
- Cross-platform dismiss pattern: `.onExitCommand` always-on + Close button `#if !os(tvOS)`
- VoiceOver-on-tvOS implications: focus traversal vs touch, no manual focus reassertion, no `.accessibilityAddTraits(.isButton)` on focus helpers
- Destructive dialog default-focus severity statement (sev-1 on tvOS)
- **Identifier naming convention** (generic): `ScreenIdentifiers` typed-enum pattern, `<Screen>_Root` suffix rule, `<Screen>_<Component>` per-component pattern, stable-id rule (no user data in identifiers)
- Cross-references: `xctest-ui-testing` (AccessibilityMarkerView code), `swiftui-design-review` (modal focus containment)

**Body additions/edits:**
- Description: "Relevant when…" → "Use when…"; expanded from 33 → 67 words; iOS-only → iOS/macOS/tvOS; explicit triggers for Menu-button dismissal, typed-enum identifier naming, destructive-dialog default focus
- Purpose section: iOS-only → iOS/macOS/tvOS coverage; pointer to references/tvos.md
- Hidden marker view section: cross-link to `xctest-ui-testing`'s `AccessibilityMarkerView` for cross-platform reliability; pointer to references for identifier naming convention
- Modal Dimmer Pattern: explicit Close button guarded by `#if !os(tvOS)`; pointer to tvOS dismissal pattern
- Confirmation Dialog Safe Default Focus: tvOS severity callout (sev-1, no pointer override, one Select press away)

Rejected (Tiercade-coupled):
- Frontmatter `metadata` block (version/author "Tiercade"/category/tags/discovered_from)
- `evidence_commits` array (`e1167b4`, `45c598d`, `dcc9553`, `940bb8b`) + body commit-hash citations
- `applyTo: "**/*.swift"` glob
- `Tiercade/` paths in audit `rg` commands
- `import TiercadeCore`, `ScreenID.headToHead`, `ScreenID.analysis` (replaced with generic `ScreenIdentifiers.MyScreen`)
- `UITestAXMarkerView` exact name (replaced with `AccessibilityMarkerView`, defined in `xctest-ui-testing`)
- `app.tierColors`, `app.tierOrder`, `app.lockedTiers`, `app.displayLabel`, `app.moveItemLeft`/`Right` project state
- `tier.label`, `tier.items.count` Tiercade-specific accessor (target already uses generic `category`)
- `AGENTS.md`, `docs/testing/testability-contract.md` doc paths
- `.swiftlint.yml` reference (project config)

**Allow-list compliance verified:**
- `focusToken`, `UITestAXMarker`, `Liquid Glass`: absent from SKILL.md body.
- `UITestAXMarker` was not introduced (already generalized as `AccessibilityMarkerView` in `xctest-ui-testing`).

## Manual Assessment

| # | Criterion | Score | Notes |
|---|-----------|-------|-------|
| 1.1 | Completeness | 4/4 | Identifier rules (leaf-only), button-vs-tap-gesture, icon-button labels, decorative images, modal dimmers (with tvOS branch), focus-helper hiding, custom actions, reduce motion, voice control labels, semantic labels, manual VoiceOver test, confirmation dialogs (with tvOS severity), toast announcements + live regions. tvOS dismissal + identifier naming in references. |
| 1.2 | Correctness | 4/4 | `.onExitCommand` is the documented tvOS dismissal API. `Button(_:systemImage:action:)` initializer is current SwiftUI. `AccessibilityNotification.Announcement` matches iOS 17+ API. Default-focus-on-first-button accurately describes `confirmationDialog`. |
| 1.3 | Appropriateness | 4/4 | Markdown reference + references progressive disclosure. |
| 2.1 | Fault Tolerance | 3/4 | Anti-pattern blocks for every category; decision tree for removing container identifiers. |
| 2.2 | Error Reporting | 4/4 | Severity callout on tvOS destructive default focus. Symptom→cause framing in identifier-on-container anti-pattern. |
| 2.3 | Recoverability | 4/4 | Read-only doc. |
| 3.1 | Token Cost | 4/4 | SKILL.md 337 lines; tvOS depth in references/tvos.md. Agent loads only the needed depth. |
| 3.2 | Execution Efficiency | 4/4 | No scripts. |
| 4.1 | Learnability | 4/4 | Concrete BEST/ACCEPTABLE/WRONG pairs for icon buttons; CORRECT/WRONG pairs for every pattern. Toast example complete. |
| 4.2 | Consistency | 4/4 | Uniform code-fence + WRONG/CORRECT structure across sections. |
| 4.3 | Feedback Quality | 4/4 | Multiple severity callouts (tvOS data-loss, identifier-on-container). Decision tree for identifier removal. |
| 4.4 | Error Prevention | 4/4 | Strong "NEVER" rules; explicit "no manual focus reassertion" + "no `.isButton` trait on focus helpers". |
| 5.1 | Discoverability | 4/4 | "Use when…" phrase; trigger contexts enumerated; iOS/macOS/tvOS explicit. |
| 5.2 | Forgiveness | 4/4 | Read-only. |
| 6.1 | Credential Handling | 4/4 | No secrets. |
| 6.2 | Input Validation | 4/4 | No input surface. |
| 6.3 | Data Safety | 4/4 | Read-only. |
| 7.1 | Modularity | 4/4 | Two-file split (SKILL.md + tvos.md). Each topic has its own home. |
| 7.2 | Modifiability | 4/4 | Add new pattern → new subsection. Add new tvOS rule → references file. |
| 7.3 | Testability | 2/4 | No mechanism to detect drift against Apple Accessibility API releases. No source-link citations. |
| 8.1 | Trigger Precision | 4/4 | Description specific; cross-platform; mentions Menu-button dismissal, typed-enum naming, dialog focus safety explicitly. |
| 8.2 | Progressive Disclosure | 4/4 | Body covers common-path patterns; tvOS focus-engine specifics in references. |
| 8.3 | Composability | 4/4 | Cross-links `xctest-ui-testing` (AccessibilityMarkerView, identifier conventions), `swiftui-design-review` (focus containment). |
| 8.4 | Idempotency | 4/4 | Read-only. |
| 8.5 | Escape Hatches | 3/4 | "Skip this for non-UI code / containers / cosmetic changes" out-of-scope statement; ACCEPTABLE-vs-BEST framing for manual `.accessibilityLabel` shows when to relax the initializer rule. |
| | **TOTAL** | **93/100** | **Excellent** — publishable |

## Priority Fixes

### P0 — Fix Before Publishing
None.

### P1 — Should Fix
None.

### P2 — Nice to Have
1. Add upstream Apple Accessibility / HIG citations per pattern. Improves `7.3` testability.
2. Add diagnostic recipes table (symptom → likely a11y misuse).
3. Cross-link to `swiftui-design-tokens`'s reduce-motion section for fuller motion-token coverage.

## Revision History
| Date | Score | Notes |
|------|-------|-------|
| 2026-05-12 (baseline) | 92% structural / ~85 manual | Pre-merge. 1 description warning (Relevant when → Use when). iOS-only framing; no references/. No tvOS dismissal, no identifier naming convention, no tvOS severity callouts. |
| 2026-05-12 (post-merge) | 100% structural / 93 manual | references/tvos.md added (.onExitCommand, typed-enum naming, focus-traversal rules, severity statement). Body fixed description, added tvOS dimmer branch and severity callouts, cross-linked AccessibilityMarkerView from xctest-ui-testing. |
