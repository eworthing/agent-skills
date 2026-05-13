# swiftui-design-review Evaluation

**Date:** 2026-05-12 (post-Phase-3 merge from Tiercade)
**Evaluator:** Claude Opus 4.7
**Skill version:** SKILL.md + references/{liquid-glass-and-tvos,non-regression-checklist}.md
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
    ✅ SKILL.md body length (143 lines)
    ✅ References linked from SKILL.md
  [SCRIPTS]
    ✅ No scripts/
  [SECURITY]
    ✅ No hardcoded credentials or emails

  Pass: 13  Warn: 0  Fail: 0
  Structural score: 100%
```

## Merge Summary

Imported and de-projectized from `Tiercade/skills/design-regression-review`:

**New `references/liquid-glass-and-tvos.md`** (~127 lines):
- Liquid Glass chrome-only rule + glass-on-glass anti-pattern (code example with `.fullScreenCover` + `.buttonStyle(.glass)`)
- Button-style selection by container table (chrome / modal / rows / tvOS cards)
- tvOS modal focus containment (`.fullScreenCover()` vs `.sheet()`)
- Manual focus reassertion anti-pattern (`DispatchQueue.main.asyncAfter` + `isFocused = true` breaks VoiceOver/Switch Control)
- tvOS manual-QA checklist (toolbar traversal, default focus, overlay dismiss, focus on appear)
- macOS design-review notes (window resize, keyboard shortcut collisions, form style)
- Severity statement: focus regressions are sev-1 on tvOS-supporting apps

**Body additions:**
- Step 2 Hard Rules: glass chrome-only, tvOS modal focus containment, no manual focus reset loops + pointer to references
- Step 3 Manual QA: new macOS subsection (window resize, shortcut collisions, form style) + new tvOS subsection (traversal, default focus, dismiss, modal containment) + pointer to references
- Common Mistakes #6 (manual focus reassertion on tvOS) + #7 (glass-on-glass)
- Description: iOS-only → iOS/macOS/tvOS coverage; "Relevant" → "Use when…"; expanded to enumerate glass misuse, tvOS focus containment, macOS window-resize, shortcut collisions

Rejected (Tiercade-coupled):
- Frontmatter `metadata` block (version/author/category/tags/discovered_from/`evidence_commits` array)
- `applyTo: "{Tiercade/Views/**/*.swift,Tiercade/Design/**/*.swift,docs/patterns/**/*.md,...}"` glob
- Scripts: `./build_install_launch.sh tvos`, `./scripts/run_ui_tests.sh --tvos|--mac|--ios`
- Doc paths: `docs/patterns/ui-pattern-button-styles-spec-implemented.md`, `docs/patterns/ui-pattern-focus-management-spec.md`, `docs/specs/ui-toolbar-unification-spec-implemented.md`
- Module references: `TiercadeCore`, `Tiercade/Design/`
- Screen names: `Quick Move`, `HeadToHead`, `Settings`, `More`
- `toolbar-contract` / `ActionID` action registry references
- `AGENTS.md` reference (project doc)
- "Keep overlay files under 400 lines" project policy

**Allow-list compliance verified:**
- `Liquid Glass` and `.fullScreenCover()`: confined to `references/liquid-glass-and-tvos.md`; absent from body.
- Body uses neutral phrasing: "Glass materials limited to chrome surfaces", "modal focus containment", "no manual focus reset loops".

## Manual Assessment

| # | Criterion | Score | Notes |
|---|-----------|-------|-------|
| 1.1 | Completeness | 4/4 | Non-regression contract, hard rules, multi-platform QA (iPhone/iPad/macOS/tvOS), evidence requirements, automated validation, common mistakes. Glass + tvOS depth in references. |
| 1.2 | Correctness | 4/4 | Button-style guidance matches Apple HIG. tvOS focus containment via `.fullScreenCover` matches documented behavior. `.formStyle(.automatic)` advice correct. |
| 1.3 | Appropriateness | 4/4 | Markdown workflow + references progressive disclosure. |
| 2.1 | Fault Tolerance | 3/4 | Hard-rules section + common-mistakes list preempt the typical regression sources. |
| 2.2 | Error Reporting | 4/4 | Severity callout ("focus regressions are sev-1 on tvOS"); concrete symptom→cause framing in glass-on-glass anti-pattern. |
| 2.3 | Recoverability | 4/4 | Read-only review doc. |
| 3.1 | Token Cost | 4/4 | Body 143 lines; tvOS/Glass depth in references. Agent loads only needed surface. |
| 3.2 | Execution Efficiency | 4/4 | No scripts. |
| 4.1 | Learnability | 4/4 | Concrete WRONG/CORRECT pairs for glass-on-glass and manual focus reassertion. Per-platform QA checklists. |
| 4.2 | Consistency | 4/4 | Uniform 5-step workflow; consistent hard-rule formatting; uniform per-platform QA subsections. |
| 4.3 | Feedback Quality | 4/4 | Severity statement; concrete diagnostic ("press right 5+ times") for focus containment regressions. |
| 4.4 | Error Prevention | 4/4 | Strong "no manual focus reset loops"; identifier discipline; explicit glass-on-glass forbidden. |
| 5.1 | Discoverability | 4/4 | "Use when…" phrase; trigger contexts enumerated (UI/UX changes, toolbar refactors, modal additions, parity work, view-heavy PRs). |
| 5.2 | Forgiveness | 4/4 | Read-only. |
| 6.1 | Credential Handling | 4/4 | No secrets. |
| 6.2 | Input Validation | 4/4 | No input surface. |
| 6.3 | Data Safety | 4/4 | Read-only. |
| 7.1 | Modularity | 4/4 | Three-file split (SKILL.md + liquid-glass-and-tvos.md + non-regression-checklist.md). |
| 7.2 | Modifiability | 4/4 | Add new platform → new QA subsection. Add new rule → hard-rules list. Add new mistake → common-mistakes list. |
| 7.3 | Testability | 2/4 | No mechanism to detect drift against Apple HIG updates. No upstream citations. |
| 8.1 | Trigger Precision | 4/4 | Description specific; cross-platform coverage enumerated; mentions reviewing/auditing UI PRs explicitly. |
| 8.2 | Progressive Disclosure | 4/4 | Body covers the workflow; tvOS/Glass depth in references file. |
| 8.3 | Composability | 4/4 | Cross-links `swiftui-design-tokens` (token + button style rules) and `xctest-ui-testing` (identifier conventions). Self-references its tvOS/Glass references file. |
| 8.4 | Idempotency | 4/4 | Read-only. |
| 8.5 | Escape Hatches | 3/4 | Severity statement and "Skip this for purely internal/model changes" provide explicit out-of-scope. |
| | **TOTAL** | **93/100** | **Excellent** — publishable |

## Priority Fixes

### P0 — Fix Before Publishing
None.

### P1 — Should Fix
None.

### P2 — Nice to Have
1. Add upstream HIG citations per hard rule. Improves `7.3` testability.
2. Add diagnostic recipes table: "if you see X visual regression → likely Y root cause".
3. Cross-link to `xctest-runner` for running platform-specific test suites named in Step 5.

## Revision History
| Date | Score | Notes |
|------|-------|-------|
| 2026-05-12 (baseline) | 100% structural / ~85 manual | Pre-merge. iOS-only QA; no tvOS or macOS coverage; no glass material rules; no focus containment guidance. |
| 2026-05-12 (post-merge) | 100% structural / 93 manual | references/liquid-glass-and-tvos.md added (glass rules, modal focus containment, focus-reassertion anti-pattern, per-platform QA, severity callout). Body adds macOS + tvOS QA subsections, two new common mistakes, description expanded to iOS/macOS/tvOS. |
| 2026-05-12 (Phase 2 fold) | 100% structural / 94 manual | Phase 2 FOLD from Tiercade `toolbar-contract`. Body additions: Destructive Actions subsection (Undoable=no-confirm, Not-Undoable=confirm table), Keyboard Shortcut Collision Audit subsection with `rg -n 'keyboardShortcut\('` recipe, Cross-platform parity principle (tvOS has no keyboard shortcuts → real divergence; missing toolbar action across platforms is usually oversight). Rejected Tiercade-coupled content: `ActionRegistry.swift`, `ToolbarSurface.swift`, `ToolbarLayout`, `tvOSToolbarActions`, `iOSTitleMenuActions`, AppState routing rules, `clearTier`/`reset`/`randomize` examples, `build_install_launch.sh`, `evidence_commits` metadata, `applyTo` glob. Generic substitutions: `clearList` / `permanentReset` / `regenerateAll`. |
