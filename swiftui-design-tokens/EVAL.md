# swiftui-design-tokens Evaluation

**Date:** 2026-05-12 (post-Phase-3 merge from Tiercade)
**Evaluator:** Claude Opus 4.7
**Skill version:** SKILL.md + references/{motion-tokens,token-values}.md
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
    ✅ SKILL.md body length (348 lines)
    ✅ References linked from SKILL.md
  [SCRIPTS]
    ✅ No scripts/
  [SECURITY]
    ✅ No hardcoded credentials or emails

  Pass: 13  Warn: 0  Fail: 0
  Structural score: 100%
```

## Merge Summary

Imported and de-projectized from `Tiercade/skills/design-tokens`:

**New `references/motion-tokens.md`** (~120 lines): full spring token
catalog (`spring`, `lift`, `drop`, platform-branched `focusSpring`),
reduce-motion alternatives (`liftReduced`, `dropReduced`), per-interaction
selection guide table (drag pickup, drag drop, focus change, overlay
appear, chip/row toggle, modal present → normal vs reduce-motion token),
anti-patterns section. tvOS `.bouncy()` and iOS/macOS `.spring()` focus
springs split via `#if os(tvOS)`. Pointer added from body Motion section.

**New body sections:**
- **Form Styling (macOS)**: `.formStyle(.automatic)` + `.scenePadding()`
  with rationale (Apple Settings doc convention, platform-tracking).
- **Modal Sizing**: generic `ScaledDimensions` token example with
  modal-frame application + magic-number anti-pattern.

**Description fix:** "Relevant when…" → "Use when…"; expanded 41 → 65
words; explicit trigger contexts for motion tokens, reduce-motion,
button styles, macOS form styling, modal sizing.

Rejected (Tiercade-coupled):
- Frontmatter `applyTo: "{Tiercade/Design/*.swift,**/*Style*.swift}"` glob
- Frontmatter `metadata` block (version/author "Tiercade Team"/category/tags)
- File references: `TVMetrics.swift`, `VibrantDesign.swift`, `TierTheme.swift`
- `Palette.tierColor(tierId, from: app.tierColors)` example
  (target already uses generic `Palette.categoryColor`)
- `TierRowView(tier:app:)` example
- `docs/patterns/ui-pattern-button-styles-spec-implemented.md` doc paths
- Glass-on-glass anti-pattern → originally deferred to `swiftui-design-review`; that skill was eliminated 2026-05-13. Generic Liquid Glass adoption lives in auth `swiftui-expert-skill` `references/liquid-glass.md`; tvOS focus-context glass-on-glass lives in `apple-tvos` `references/design-regressions.md`.
  so Liquid Glass content consolidates there and stays out of this skill's body

## Manual Assessment

| # | Criterion | Score | Notes |
|---|-----------|-------|-------|
| 1.1 | Completeness | 4/4 | Palette (dynamic + category), Metrics (8pt grid), TypeScale (with Dynamic Type), Motion (timed + spring + platform-specific focus + reduce-motion via references), Button Styles (context table), Modal Backgrounds, Form Styling (macOS), Modal Sizing, View Modifiers, audit recipe, exemptions. Comprehensive coverage. |
| 1.2 | Correctness | 4/4 | `.formStyle(.automatic)` + `.scenePadding()` match Apple's Settings sample. `.bouncy()` API correct for tvOS 17+. `Palette.categoryColor` fallback chain accurate. `@ScaledMetric` syntax correct. |
| 1.3 | Appropriateness | 4/4 | Markdown reference + references progressive disclosure. |
| 2.1 | Fault Tolerance | 3/4 | Reduce-motion alternatives prevent silent accessibility failure. Audit recipe + exemptions section preempt false-positive flags. |
| 2.2 | Error Reporting | 3/4 | "WRONG/CORRECT" pairs on Motion anti-patterns and Modal Sizing. Doesn't enumerate runtime failure modes (N/A — tokens are compile-time). |
| 2.3 | Recoverability | 4/4 | Read-only doc artifact. |
| 3.1 | Token Cost | 4/4 | SKILL.md 348 lines; motion catalog offloaded to references/motion-tokens.md. Agent loads only the depth it needs. |
| 3.2 | Execution Efficiency | 4/4 | No scripts. |
| 4.1 | Learnability | 4/4 | Concrete example for every token category; selection-guide table for motion. |
| 4.2 | Consistency | 4/4 | Uniform code-fence style; uniform WRONG/CORRECT pairs; tables for context-based selection. |
| 4.3 | Feedback Quality | 4/4 | Anti-pattern blocks named for each token type. Diagnostic Recipes table maps symptoms → causes → fixes (10 patterns). |
| 4.4 | Error Prevention | 4/4 | Strong "NEVER hardcode" rules; reduce-motion column explicitly forbidden to use springs. |
| 5.1 | Discoverability | 4/4 | "Use when…" phrase; trigger contexts enumerated; description names every covered topic. |
| 5.2 | Forgiveness | 4/4 | Read-only. |
| 6.1 | Credential Handling | 4/4 | No secrets. |
| 6.2 | Input Validation | 4/4 | No input surface. |
| 6.3 | Data Safety | 4/4 | Read-only. |
| 7.1 | Modularity | 4/4 | Three-file split (SKILL.md + motion-tokens.md + token-values.md). Each topic has its own home. |
| 7.2 | Modifiability | 4/4 | Add new motion token → references row + selection-guide row. Add new modifier → View Modifiers section. |
| 7.3 | Testability | 3/4 | Apple HIG citations present (Motion, FormStyle, scenePadding, Spring, bouncy). Diagnostic Recipes table provides manual verification path. No automated Swift syntax validation yet. |
| 8.1 | Trigger Precision | 4/4 | Description specific; trigger phrase present; iOS/macOS/tvOS coverage explicit. |
| 8.2 | Progressive Disclosure | 4/4 | Body covers common path; spring catalog + selection guide in references/motion-tokens.md; raw values in references/token-values.md. |
| 8.3 | Composability | 3/4 | Cross-links `swiftui-expert-skill` (deprecated API replacements via `references/latest-apis.md`; animation mechanics via `animation-*.md`; generic Liquid Glass via `liquid-glass.md`) and `apple-tvos` (tvOS focus-animation caveats; tvOS-context glass-on-glass). |
| 8.4 | Idempotency | 4/4 | Read-only. |
| 8.5 | Escape Hatches | 3/4 | Exemptions section documents acceptable hardcoded values (user-selectable presets, color computations). |
| | **TOTAL** | **94/100** | **Excellent** — publishable |

## Priority Fixes

### P0 — Fix Before Publishing
None.

### P1 — Should Fix
None.

### P2 — Nice to Have
1. ~~Cross-link `swiftui-design-review` once that skill lands Liquid Glass content~~ — design-review eliminated 2026-05-13; Liquid Glass coverage now lives in auth `swiftui-expert-skill` `references/liquid-glass.md` (generic) and `apple-tvos` `references/design-regressions.md` (tvOS focus context). Cross-links updated.
2. ~~Add upstream Apple HIG/Settings sample citations to Form Styling and Spring Animations sections.~~ — Done 2026-05-13. Added HIG Motion link, Spring/bouncy API docs, FormStyle/scenePadding API refs.
3. ~~Add diagnostic recipes table (symptom → likely token misuse) for `4.3`.~~ — Done 2026-05-13. Added 10-pattern Diagnostic Recipes section.

## Revision History
| Date | Score | Notes |
|------|-------|-------|
| 2026-05-12 (baseline) | 92% structural / ~85 manual | Pre-merge. 1 description warning (Relevant when → Use when). Motion section limited to fast/standard/spring + one reduce-motion line. No Form Styling or Modal Sizing sections. |
| 2026-05-12 (post-merge) | 100% structural / 92 manual | references/motion-tokens.md added (springs, reduce-motion, selection guide, platform branching). macOS Form Styling + Modal Sizing sections added to body. Description de-projectized and expanded. |
| 2026-05-13 (P2 fixes) | 100% structural / 94 manual | Added Apple HIG citations to Motion and Form Styling sections (HIG Motion, Spring/bouncy/FormStyle/scenePadding API docs). Added 10-pattern Diagnostic Recipes table mapping symptoms → causes → fixes. 4.3 Feedback Quality: 3→4. 7.3 Testability: 2→3. |
