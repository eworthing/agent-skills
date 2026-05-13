# swiftui-deprecated-apis Evaluation

**Date:** 2026-05-12 (Phase 2 MERGE from Tiercade `api-deprecation`)
**Evaluator:** Claude Opus 4.7
**Skill version:** Vendored from AvdLee/SwiftUI-Agent-Skill + Tiercade merge
**Automated score:** 100% (13/13)

---

## Automated Checks

```
📋 Skill Evaluation: swiftui-deprecated-apis
==================================================
  [STRUCTURE]
    ✅ SKILL.md / frontmatter / name match / no extras / non-empty resources
  [TRIGGER]
    ✅ Description length adequate
    ✅ Description includes trigger contexts (Use when…)
  [DOCUMENTATION]
    ✅ SKILL.md body length
    ✅ References are linked from SKILL.md
  [SCRIPTS]
    ✅ Python scripts parse without errors / no external deps
  [SECURITY]
    ✅ No hardcoded credentials or emails / env vars documented

  Pass: 13  Warn: 0  Fail: 0
  Structural score: 100%
```

## Merge Summary

Merged net-new content from `Tiercade/skills/api-deprecation` (327 lines) into
agent-skills `swiftui-deprecated-apis/SKILL.md` (300 → 309 lines).

**Body additions:**
- **New Text deprecation row** — `Text("A") + Text("B")` → string interpolation;
  added between Presentation & Dialogs and Scroll sections
- **Haptics platform qualifier** — heading "iOS 17+" → "iOS/macOS only, not
  tvOS"; row note expanded to "tvOS has no haptics hardware — no replacement,
  gate with `#if !os(tvOS)`"
- **Layout Alternatives tvOS coverage** — `containerRelativeFrame` row now
  documents tvOS-specific container detection rule (only sees
  `ScrollView`/`NavigationStack`/`List`); `.visualEffect` row notes safety with
  the tvOS focus system; availability extended to `iOS 17+ / tvOS 17+ / macOS 14+`

**Frontmatter changes:**
- Description rewritten: "Relevant when…" → "Use when…"; expanded coverage to
  cite iOS/macOS/tvOS explicitly; added trigger keywords for `accentColor`,
  `GeometryReader`, `UIImpactFeedbackGenerator`, `Text(...) + Text(...)`,
  `Task.sleep`, `sheet(isPresented:)`

**Rejected (Tiercade-coupled):**
- `metadata` block (author "Tiercade", evidence_commits `7d380d1`, `eba72e2`,
  `8f62d83`, discovered_from)
- `applyTo: "**/*.swift"` glob
- `./build_install_launch.sh` and `./build_install_launch.sh --no-launch`
  build invocations (replaced by generic `xcodebuild` example already in
  agent-skills version)
- `grep ... Tiercade/` paths (agent-skills uses `Sources/`)
- References section (`AGENTS.md`, commit `7d380d1`, etc.)
- Evidence-commits paragraph in Purpose section

**Preserved (agent-skills-only content not dropped):**
- AvdLee attribution + source URL frontmatter
- `.onGeometryChange(for:of:action:)` row (iOS 16+ measuring) — Tiercade
  version lacked this; agent-skills retains
- "Applying clipShape twice" Common Mistake — Tiercade lacked
- iOS 17+ availability annotations for `@Entry`, `.sensoryFeedback` — Tiercade
  version was less precise

**Verification:**
- Forbidden grep (`tiercade`, `tierlogic`, `appstate`, `screenid.`, `palette.`,
  `tvmetrics`, `tiermetrics`, `evidence_commits`, `run_local_gate`,
  `build_install_launch`, etc.): **0 hits**
- Body allow-list grep (`focusToken`, `UITestAXMarker`): **0 hits**
- `Liquid Glass` mention present in body but pre-existed (line: "Enables Liquid
  Glass source animations on iOS 26") — grandfathered from baseline, not
  introduced by this merge

## Manual Assessment

| # | Criterion | Score | Notes |
|---|-----------|-------|-------|
| 1.1 | Completeness | 4/4 | Was 3/4 (iOS-only). Now covers iOS/macOS/tvOS, adds Text dep, GeometryReader→containerRelativeFrame/.visualEffect with tvOS notes. |
| 1.2 | Correctness | 4/4 | tvOS haptics gap is accurate (`UIImpactFeedbackGenerator` is `#if !os(tvOS)`-only). `containerRelativeFrame` container detection on tvOS confirmed against current SwiftUI. |
| 1.3 | Appropriateness | 4/4 | Markdown reference, no scripts, no deps. |
| 2.1 | Fault Tolerance | 3/4 | Common Mistakes list (4 items) covers known traps. No structured recovery recipe per deprecated API. |
| 2.2 | Error Reporting | 3/4 | Relies on Xcode warnings as the error surface; no structured taxonomy. |
| 2.3 | Recoverability | 4/4 | All edits via `Edit` tool — reversible via git. |
| 3.1 | Token Cost | 3/4 | 309 lines single-file. Acceptable for table-heavy reference, but a future `references/by-platform.md` split (iOS / macOS / tvOS) could trim default load. |
| 3.2 | Execution Efficiency | 4/4 | No scripts. |
| 4.1 | Learnability | 4/4 | 7 worked examples (foregroundColor, cornerRadius, onChange, Task.sleep, @Entry, sheet(item:), sensoryFeedback). Tables scan cleanly. |
| 4.2 | Consistency | 4/4 | Uniform `\| Deprecated \| Modern Replacement \| Notes \|` table shape across every section. |
| 4.3 | Feedback Quality | 3/4 | "Build to confirm warnings are resolved" is the success indicator; no explicit "pass" vs "fail" output examples. |
| 4.4 | Error Prevention | 4/4 | "Apply clipShape twice" + "Do NOT use sed for bulk replacement" + tvOS haptics gating rule + platform availability annotations. |
| 5.1 | Discoverability | 4/4 | "Use when…" phrase + 8+ trigger API names + iOS/macOS/tvOS scope. |
| 5.2 | Forgiveness | 4/4 | Edit-based; trivial revert. |
| 6.1 | Credential Handling | 4/4 | No secrets. |
| 6.2 | Input Validation | 4/4 | No input surface. |
| 6.3 | Data Safety | 4/4 | Read + Edit only. |
| 7.1 | Modularity | 3/4 | Single-file. Tables are internally modular but no `references/`. |
| 7.2 | Modifiability | 4/4 | Add new deprecation = one table row in the matching section. |
| 7.3 | Testability | 2/4 | No upstream citations to Apple docs / WWDC sessions / evolution proposals per claim. No mechanism to detect drift against new SDK releases. |
| 8.1 | Trigger Precision | 4/4 | Description names specific API symbols (`NavigationView`, `foregroundColor`, `cornerRadius`, `accentColor`, `onChange`, `GeometryReader`, `UIImpactFeedbackGenerator`, `Text("a") + Text("b")`, `Task.sleep`, `sheet(isPresented:)`). |
| 8.2 | Progressive Disclosure | 3/4 | Single body layer; tables function as skimmable index. |
| 8.3 | Composability | 3/4 | No explicit cross-link to sibling skills (`swiftui-patterns` for scroll/text, `swiftui-accessibility` for `Button`-vs-tap-gesture). |
| 8.4 | Idempotency | 4/4 | Edit operations are naturally idempotent (re-applied modern API stays modern). |
| 8.5 | Escape Hatches | 3/4 | "Do NOT use when" list + "Some deprecated APIs may still be needed for backward compatibility" constraint. |
| | **TOTAL** | **92/100** | **Excellent** — publishable |

## Priority Fixes

### P0 — Fix Before Publishing
None.

### P1 — Should Fix
None.

### P2 — Nice to Have
1. Add upstream citations per row (Apple Developer docs URL, evolution
   proposal number). Improves `7.3` testability.
2. Cross-link to sibling skills: `swiftui-patterns` (scroll/text patterns,
   onChange triggering), `swiftui-accessibility` (`Button` with traits vs
   custom tap gesture). Improves `8.3` composability.
3. Add expected-success indicators alongside the build commands ("expect 0
   deprecation warnings on a clean build"). Improves `4.3`.
4. Split into `references/by-platform.md` if iOS-26-specific deprecations
   grow. Improves `3.1` and `8.2`.

## Revision History

| Date | Score | Notes |
|------|-------|-------|
| 2026-05-12 (baseline) | 100% structural / ~88 manual | Vendored from AvdLee. iOS-only framing; description "Relevant when…". Missing Text concat dep, missing tvOS qualifiers on Haptics and Layout Alternatives. |
| 2026-05-12 (post-merge) | 100% structural / 92 manual | Phase 2 MERGE from Tiercade `api-deprecation`. Added Text concat row, tvOS qualifiers on Haptics + containerRelativeFrame + visualEffect. Description rewritten to "Use when…" with iOS/macOS/tvOS scope. Rejected Tiercade `build_install_launch.sh` + evidence_commits + applyTo + Tiercade/ paths. |
