# apple-tvos Evaluation

**Date:** 2026-05-13 (P1 lift: rule IDs + bypass contexts + eval fixtures + context7 corrections)
**Evaluator:** Claude Opus 4.7
**Skill version:** Definitive tvOS skill — focus engine + accessibility deltas + design regressions
**Automated score:** 13/13 (100%)
**Manual score:** **96/100**

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

## Manual Assessment

Doc-only skill (no scripts). Criteria normally tied to runtime
(2.1–2.3, 3.2, 6.2–6.3, 7.3, 8.3–8.5) scored in spirit — guidance
quality and idempotency of doc reads — per skill-evaluator-1.0.0
precedent.

| # | Criterion | Score | Notes |
|---|-----------|-------|-------|
| 1.1 | Completeness | 4/4 | Three topic areas covered: focus engine (composition, hover, settle, scroll, simulator), accessibility (Menu dismissal, destructive-dialog focus, VoiceOver), design regressions (modal containment, focus reassertion, glass-on-glass, button-style, QA checklist). Sibling-skill table delegates the rest cleanly. |
| 1.2 | Correctness | 4/4 | Patterns match Apple guidance; wrong/right code pairs concrete. Severity-1 designation accurate for destructive-dialog default focus on tvOS. |
| 1.3 | Appropriateness | 4/4 | Zero deps, portable Markdown, follows agent-skills repo conventions (YAML frontmatter, "Use when…" trigger, sibling-skill table, references/ progressive disclosure). |
| 2.1 | Fault Tolerance | 4/4 | Guidance teaches resilience: settle-delay debounce token, POD + `@FocusState` identity anchor, focus-containment alternative to manual reassertion. |
| 2.2 | Error Reporting | 3/4 | Severity-1 designation surfaces UX-failure cost. No structured "diagnostic" output (doc-only). Could lift to 4 with a single-screen "tvOS gotcha decision tree" / glossary at top of SKILL.md. |
| 2.3 | Recoverability | 4/4 | Reads idempotent. Manual-focus-reassertion anti-pattern + containment alternative explicitly cover the "regression appeared, what now?" recovery path. |
| 3.1 | Token Cost | 3/4 | SKILL.md 204 lines after rule index + bypass contexts (was 129, target <150 for 4/4). 150–250 band = 3/4. References 188 + 112 + 174 lines split by topic; agent loads only relevant one. Lift to 4: extract rule index + bypass table to `references/rules.md` and link from SKILL.md. |
| 3.2 | Execution Efficiency | 4/4 | Progressive disclosure via 3-level hierarchy (description → SKILL.md router → topic reference). |
| 4.1 | Learnability | 4/4 | Headline Rules section in SKILL.md is self-contained for 80% of cases; references reachable when a rule needs more depth. Code pairs labeled WRONG / CORRECT. |
| 4.2 | Consistency | 4/4 | Same structure across all 3 reference files: wrong/right code, mitigation paragraph, cross-refs section. Same severity vocabulary. |
| 4.3 | Feedback Quality | 4/4 | Numbered rule index in SKILL.md (`tvOS-F01..F07`, `tvOS-A01..A04`, `tvOS-D01..D04`) with severity column. Review checklist cites IDs. References section headers anchored on rule IDs. |
| 4.4 | Error Prevention | 4/4 | Button-style selection matrix, dialog button-ordering matrix, review checklist all prevent the most common tvOS mistakes proactively. |
| 5.1 | Discoverability | 4/4 | Description 134 words with ~15 specific scenarios. SKILL.md has scope table + sibling table + headline rules + review checklist. Internal cross-refs explicit. |
| 5.2 | Forgiveness | 4/4 | Anti-pattern (manual focus reassertion) flagged with named alternative (focus containment via `.fullScreenCover()` + scoped `@FocusState`). |
| 6.1 | Credential Handling | 4/4 | None present. |
| 6.2 | Input Validation | 4/4 | Doc-only — no inputs. |
| 6.3 | Data Safety | 4/4 | Doc-only — no writes. |
| 7.1 | Modularity | 4/4 | SKILL.md = pure router. Three topic references map 1:1 to three topic areas. |
| 7.2 | Modifiability | 4/4 | Adding a new tvOS topic = new reference file + scope-table row + headline-rules section + review-checklist block. Pattern obvious from existing 3. |
| 7.3 | Testability | 3/4 | `evals/evals.json` with 6 fixtures (5 violation cases + 1 clean) covering 7 of 13 testable rule IDs (F01, F05, A01, A02, A03, D01, D03). Lift to 4: add fixtures for F02, F03, F04, F06, A04, D02 (F07 + D04 not source-evaluable). |
| 8.1 | Trigger Precision | 4/4 | Description has 6+ specific scenarios per topic, "Use when…" phrase, scope-vs-auth boundary explicit ("authoritative community `swiftui-expert-skill` owns iOS/macOS depth"). |
| 8.2 | Progressive Disclosure | 4/4 | Three levels: description → SKILL.md (router, 129 lines) → 3 topic references (focus-engine, accessibility, design-regressions). |
| 8.3 | Composability | 3/4 | Cross-refs into 5 sibling skills make composition explicit. No machine-readable rule index (e.g. JSON) for agents to ingest. Doc-only skills can reasonably stop at 3. |
| 8.4 | Idempotency | 4/4 | Doc reads idempotent. |
| 8.5 | Escape Hatches | 4/4 | Each headline rule in SKILL.md has an explicit *Bypass / N/A* line covering shared-code carve-outs, non-tvOS-supporting apps, and version-specific exemptions. tvOS-A02 / tvOS-A03 explicitly marked "no bypass" for severity-1 cases. |
| **TOTAL** | | **96/100** | Excellent band (≥ 90). Three P1 lifts: 4.3 +1, 7.3 +1, 8.5 +1 (= +3). Side-effect loss: 3.1 Token Cost 4→3 (SKILL.md 129→204 lines). Net: +2. |

## Priority Fixes

### P1 — Shipped (2026-05-13)

1. **4.3 Feedback Quality 3→4.** ✅ Numbered rule index `tvOS-F01..F07`, `tvOS-A01..A04`, `tvOS-D01..D04` with severity column. Review checklist + reference headers cite IDs.
2. **7.3 Testability 2→3.** ✅ `evals/evals.json` with 6 fixtures (5 violation + 1 clean), covering F01, F05, A01, A02, A03, D01, D03.
3. **8.5 Escape Hatches 3→4.** ✅ Per-rule *Bypass / N/A* lines. Severity-1 rules (tvOS-A02, tvOS-A03) marked "no bypass".

### Bonus correction (context7-driven)

- **`.onExitCommand` cross-platform claim.** Was: "no-op on iOS/macOS". Now: "tvOS 13+ AND macOS 10.15+; triggers on Escape on macOS; no-op on iOS / iPadOS / visionOS." Per Apple SwiftUI docs (`/websites/developer_apple_swiftui`).
- **`.glassBackgroundEffect()` in glass-on-glass example.** Was used in a tvOS code sample; modifier is **visionOS-only**. Rewrote the example to use chrome glass surfaces (`.toolbar` + `.buttonStyle(.glass)`) and `.fullScreenCover` content with `.borderedProminent` for tvOS.

### P1 — Remaining (lifts 97 → 99)

4. **7.3 Testability 3→4.** Add fixtures for tvOS-F02 (POD without `@FocusState`), tvOS-F03 (custom `.animation()` on focusable view), tvOS-F04 (no settle delay), tvOS-F06 (`.paging` over `.viewAligned`), tvOS-A04 (`.accessibilityAddTraits(.isButton)` on Rectangle), tvOS-D02 (glass-on-glass). tvOS-F07 + tvOS-D04 are procedural; not source-evaluable.

### P2 — Nice to Have

5. **2.2 Error Reporting 3→4.** "tvOS Gotcha Decision Tree" at top of SKILL.md: "Symptom → reference → rule ID."
6. **8.3 Composability 3→4.** Generate `evals/rules.json` (machine-readable rule index: id, area, summary, severity, reference-path).
7. **`.sheet()` focus-leak version specificity.** Reworded as "assume leak unless verified on hardware for the specific deployment target" — still not a hard version threshold. Apple does not publish reliability matrix; live verification is the standard.
8. **Frontmatter `version: 1.0.0`** field.

## Revision History

| Date | Score | Notes |
|------|-------|-------|
| 2026-05-12 (baseline) | 83 manual | Vendored from AvdLee/SwiftUI-Agent-Skill (as `swiftui-patterns`). iOS-only scope. |
| 2026-05-12 (post-merge) | 92 manual | + tvOS focus reference. Scope table cross-links 5 sibling skills. |
| 2026-05-12 (Phase 2 FOLD) | 93 manual | + observable-state reference. |
| 2026-05-12 (refocus) | _pending_ | Renamed to `swiftui-tvos-focus`. Slimmed SKILL.md 493 → ~115 lines. Dropped animation-guide.md + performance-guide.md. Trimmed observable-state.md to @AppStorage gotcha. |
| 2026-05-13 (rename + expand) | _pending_ | Renamed to `apple-tvos`. Absorbed tvOS deltas from eliminated `swiftui-accessibility` (Menu dismissal, destructive dialog focus) → new `references/accessibility.md`. Absorbed tvOS deltas from eliminated `swiftui-design-review` (modal containment, focus reassertion anti-pattern, glass-on-glass, button-style focus-ring, QA checklist) → new `references/design-regressions.md`. Dropped `references/observable-state.md` (@AppStorage gotcha conflicts with auth `state-management.md` guidance). Renamed `tvos.md` → `focus-engine.md`. SKILL.md rewritten as 3-topic router with combined review checklist. |
| 2026-05-13 (re-score) | 94/100 | Full-rubric re-evaluation after rename + expand. Excellent band reached. Strengths: Completeness 4, scope discipline 4 (sibling-skill table + auth deferral), token cost 4 (SKILL.md 129 lines), trigger precision 4 (134-word description with 15+ scenarios). Gaps: 7.3 Testability 2 (no eval fixtures), 4.3 Feedback Quality 3 (no rule-ID index), 8.5 Escape Hatches 3 (no per-rule N/A contexts), 8.3 Composability 3 (no machine-readable rule index), 2.2 Error Reporting 3 (no decision tree). |
| 2026-05-13 (P1 lift) | 96/100 | Three P1 gaps shipped: 4.3 Feedback Quality 3→4 (rule index `tvOS-F01..F07`, `tvOS-A01..A04`, `tvOS-D01..D04` with severity column; review checklist + reference headers cite IDs), 7.3 Testability 2→3 (`evals/evals.json` with 6 fixtures covering 7 of 13 testable rule IDs, including 1 clean fixture as false-positive check), 8.5 Escape Hatches 3→4 (per-rule *Bypass / N/A* lines; severity-1 A02 / A03 marked "no bypass"). Side-effect loss: 3.1 Token Cost 4→3 (SKILL.md 129→204 lines). Net: +2. Context7-driven corrections: `.onExitCommand` cross-platform claim fixed (macOS Escape, not no-op); `.glassBackgroundEffect()` removed from glass-on-glass tvOS example (visionOS-only modifier). |
