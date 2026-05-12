# swiftui-patterns Evaluation

**Date:** 2026-05-12
**Evaluator:** Claude Opus 4.7
**Skill version:** Vendored from AvdLee/SwiftUI-Agent-Skill (commit b22265f)
**Automated score:** 92% (12/13, 1 warning)

---

## Automated Checks

```
📋 Skill Evaluation: swiftui-patterns
==================================================
Path: /Users/Shared/git/agent-skills/swiftui-patterns

  [STRUCTURE]
    ✅ SKILL.md exists
    ✅ SKILL.md has valid frontmatter
    ✅ Skill name matches directory
    ✅ No extraneous files
    ✅ Resource directories are non-empty

  [TRIGGER]
    ✅ Description length adequate (32 words)
    ⚠️  Description includes trigger contexts
       No trigger phrases found — add 'Use when...' to improve activation

  [DOCUMENTATION]
    ✅ SKILL.md body length (391 lines)
    ✅ References are linked from SKILL.md

  [SCRIPTS]
    ✅ No scripts/ directory
    ✅ Scripts use no external dependencies

  [SECURITY]
    ✅ No hardcoded credentials or emails
    ✅ Environment variables documented

==================================================
  ✅ Pass: 12  ⚠️  Warn: 1  ❌ Fail: 0
  Structural score: 92% (12/13 checks passed)
```

File layout:
- `SKILL.md` — 391 lines (overview + decision rules + checklists)
- `references/animation-guide.md` — 606 lines (transitions, Animatable, phase/keyframe, transactions, completion)
- `references/performance-guide.md` — 425 lines (POD, equatable, ForEach, anti-patterns, composition)

## Manual Assessment

Pure documentation skill (no scripts). Script-bound criteria scored against reference-skill expectations (read-only, no exec surface).

| # | Criterion | Score | Notes |
|---|-----------|-------|-------|
| 1.1 | Completeness | 3/4 | Covers composition, performance, animation, scroll, text, image downsampling, navigation. Missing: macOS/iPadOS/visionOS variants (skill is iOS-tilted — uses `UIScreen.main.scale`, `UIImage`, `.navigationBarTitleDisplayMode`). No accessibility patterns (DynamicType, VoiceOver). No focus-state / keyboard patterns. |
| 1.2 | Correctness | 3/4 | Most claims verified against Apple docs and current SwiftUI behavior. `@ViewBuilder let Content` over closure claim is accurate (closure-stored-as-value comparability). `Self._printChanges()` correctly gated with `#if DEBUG`. `@Animatable` macro (Swift 6/iOS 18+) noted but no minimum-version gate stated. **Caveat:** `ScrollViewReader` recommended as default for programmatic scrolling — Apple deprecates this in favor of `.scrollPosition(id:)` on iOS 17+; skill mentions neither the deprecation nor the modern API. `kCGImageSourceShouldCache: false` in `downsample` is correct but `UIScreen.main` is deprecated since iOS 16 (use trait collection). |
| 1.3 | Appropriateness | 4/4 | Markdown reference, no deps. Right tool for codifying SwiftUI rendering invariants. |
| 2.1 | Fault Tolerance | 3/4 | No retries (N/A doc). Anti-pattern lists exist but no "what to do if a pattern conflicts" guidance. |
| 2.2 | Error Reporting | 3/4 | "Missing `animatableData` = silent failure" callout is exemplary. More such failure-mode callouts (e.g., transition outside `withAnimation`, `if` destroying identity) would lift this to 4. |
| 2.3 | Recoverability | 4/4 | Re-reading idempotent. |
| 3.1 | Token Cost | 2/4 | **SKILL.md 391 lines is well over the ~150-line target.** Body inlines complete code examples for POD views, decision trees, scroll gating, etc. that duplicate content in the two reference files. Sibling skills (`swift-linting` at 54, `swift-file-splitting`) cut SKILL.md to a thin index for this reason. |
| 3.2 | Execution Efficiency | 4/4 | No scripts, no overhead. |
| 4.1 | Learnability | 4/4 | GOOD/BAD pairs with annotations, decision trees for animation, extraction-rules table. Agent can act without loading references for common cases. |
| 4.2 | Consistency | 4/4 | Uniform GOOD/BAD / WRONG/CORRECT framing, uniform tables, consistent header depth. |
| 4.3 | Feedback Quality | 3/4 | Decision trees and tables map situation→pattern. No diagnostic recipes ("if you see X symptom, look for Y"). |
| 4.4 | Error Prevention | 4/4 | Strong: explicit "deprecated form" warnings on `.animation(_:)`, explicit `#if DEBUG` gate on `_printChanges`, explicit "animation outside conditional" rule for transitions. |
| 5.1 | Discoverability | 3/4 | Description tags scope ("composition, identity, list, grid, animation, scroll-performance"). Missing literal "Use when…" phrase — auto-eval flags this. Adjacent skill `swiftui-expert-skill` overlaps; no scope-boundary cross-link. |
| 5.2 | Forgiveness | 4/4 | Read-only artifact. |
| 6.1 | Credential Handling | 4/4 | No secrets, no scripts. |
| 6.2 | Input Validation | 4/4 | No input surface. |
| 6.3 | Data Safety | 4/4 | Read-only. |
| 7.1 | Modularity | 3/4 | Two reference files (animation, performance) — clean topic split. But SKILL.md duplicates substantial portions of both (POD-view example, ZStack-vs-overlay rules, modifier-vs-conditional rule appear in SKILL.md AND performance-guide.md). |
| 7.2 | Modifiability | 3/4 | Adding a new animation pattern is clear (append to animation-guide.md). Adding a new top-level topic (e.g., accessibility) requires editing SKILL.md table-of-contents + new reference. Duplication risk: change a rule and miss the SKILL.md copy. |
| 7.3 | Testability | 2/4 | No way to detect drift against live SwiftUI behavior. Claims about `@Animatable` macro version availability, deprecated APIs (`.animation(_:)` no-value, `ScrollViewReader`), `UIScreen.main.scale` could rot silently. No source links for verification (AvdLee upstream credited in frontmatter but no per-claim citations). |
| 8.1 | Trigger Precision | 3/4 | "Relevant when…" instead of "Use when…" — slightly weaker pattern, auto-eval flags it. Trigger contexts are specific ("janky scrolling, re-rendering, view-identity problems") which is good. Overlap with `swiftui-expert-skill` unmentioned. |
| 8.2 | Progressive Disclosure | 2/4 | Three levels exist (description → SKILL.md → references) but the middle layer is too thick (391 lines) and duplicates layer 3. Agent reads more than needed on most invocations. |
| 8.3 | Composability | 3/4 | Doc-only; composes with `swift-linting`, `swift-file-splitting`, `swiftui-expert-skill` implicitly. No explicit cross-link to sibling skills. |
| 8.4 | Idempotency | 4/4 | Read-only. |
| 8.5 | Escape Hatches | 3/4 | Acknowledges `Self._printChanges()` as undocumented, names deprecated forms explicitly. No "when to break these rules" section (e.g., when `if/else` IS the right call beyond the one-line example). |
| | **TOTAL** | **83/100** | **Good** — publishable, with known P1 gaps |

## Priority Fixes

### P0 — Fix Before Publishing
None. No blockers.

### P1 — Should Fix
1. **Trigger phrase**: change description from "Relevant when…" to "Use when…" — closes auto-eval warning and matches sibling-skill convention. One-line frontmatter edit.
2. **Split SKILL.md into a thin index** (target ~100–150 lines). Move full code examples for POD views, scroll-gating, animation decision tree, image downsampling, navigation, and the review checklist into references. Keep SKILL.md as: scope + decision rules (one-line each) + links. Pattern proven on `swift-linting` (54 lines, 91/100).
3. **Add scope-boundary cross-link** to `swiftui-expert-skill` — clarify which skill owns what (this one: composition/perf/animation patterns; expert skill: state management / view composition / macOS APIs / Liquid Glass). Mirror the swift-linting ↔ swift-file-splitting cross-link.
4. **Modernize two stale claims**:
   - `ScrollViewReader` example should note `.scrollPosition(id:)` (iOS 17+) as preferred for new code.
   - `UIScreen.main.scale` in `downsample` is deprecated since iOS 16; reference current trait-collection / window-scene approach.

### P2 — Nice to Have
1. Add per-iOS-version availability table (which patterns are iOS 17+, 18+, Swift 6+). Centralizing this beats the current scattered `(iOS 17+)` annotations.
2. Add upstream citations: link `@Animatable` macro to Swift evolution proposal; link `_printChanges` mention to WWDC sessions where Apple discusses it. Improves `7.3` testability and `1.2` verifiability.
3. Add accessibility patterns (DynamicType, VoiceOver labels, focus management) — closes a `1.1` gap and matches the "performance and identity correctness" remit.
4. Add macOS variant section or rename skill to `swiftui-ios-patterns` — current content is iOS-tilted (`UIScreen`, `UIImage`, `.navigationBarTitleDisplayMode`).
5. Add a "when to break the rule" section per category (e.g., when `if/else` over modifier is actually correct beyond `DashboardView` vs `LoginView`).

## Revision History
| Date | Score | Notes |
|------|-------|-------|
| 2026-05-12 | 83/100 | Baseline. Vendored from AvdLee. Auto-eval 92% (1 warn: trigger phrase). Main drags: 391-line SKILL.md (token-cost, progressive disclosure), iOS-only scope, two stale-API examples. |
