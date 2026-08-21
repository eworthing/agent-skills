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

Description length: 846 chars / 107 words (Codex 1024 limit OK).

### anthropic-grade-optimizer scorecard (2026-07-03, target opus-4-7, Pass-1 mechanical)

`SCORE=100 GATE=PASS MUST_FIX=0 SHOULD_FIX=0 MAY_FIX=0` — "Anthropic-grade. Ship it." All 11 dimensions 100.0 (Clarity, Structure, Examples, Reasoning, Context, Model-fit, Agency, Self-check, Tools, Vision, Claude Code). Pass-2 (llm-judge) not run via API; qualitative duplication findings surfaced by a manual four-lens cross-audit (anthropic-grade-optimizer + skill-creator + writing-skills + writing-great-skills) and applied in the dedup pass below.

## Manual Assessment

| # | Criterion | Score | Notes |
|---|-----------|-------|-------|
| 1.1 | Completeness | 4/4 | Strong scope (12 refs + 6 workflows). Liquid Glass code examples and iPad multi-window patterns added 2026-05-17. |
| 1.2 | Correctness | 4/4 | Grounded in HIG/WWDC/Apple docs via source-architecture.md tier ranking. |
| 1.3 | Appropriateness | 4/4 | Trigger description (SKILL.md L3–17) is precise on iOS/iPadOS scope. |
| 2.1 | Fault Tolerance | 4/4 | Pure knowledge skill — no runtime failure surface. |
| 2.2 | Error Reporting | 4/4 | Failure conditions explicit in each workflow. |
| 2.3 | Recoverability | 4/4 | Non-destructive; critiques only. |
| 3.1 | Token Cost | 3/4 | ~4400 LOC total across refs+workflows after the 2026-08-21 dedup (−542 lines); SKILL.md lean at 161 lines. |
| 3.2 | Execution Efficiency | 4/4 | No external calls; decision tree at SKILL.md routes early, now with a fallback branch. |
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
| 7.3 | Testability | 4/4 | `evals/` ships 6 clean over-rejection guards + fixtures, re-verified 2026-08-21 against the deduped skill (20 with-skill runs, 10/10 consistent, zero over-rejection). The dirty four were cut after a measured cold baseline showed they tested the model, not the skill — see Open #2 resolution. Raised from 3/4: the suite now measures the one failure mode (over-rejection) the skill actually owns. |
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

2. ~~**The eval suite measured 0/10 RED (2026-08-04).**~~ **RESOLVED 2026-08-21: dirty four cut, clean six retained as over-rejection guards.** Re-measured after the dedup pass with n=2 with-skill runs per case (20 runs; the recorded 2026-08-04 cold baseline stands as the no-skill arm since fixtures are unchanged). With-skill runs were 10/10 internally consistent and passed all six clean guards — the escape hatch (eval 4), the scope words (eval 2), the topology-vs-container distinction (evals 0/3), and the artwork-frame distinction (eval 5) all held; no over-rejection anywhere. The dirty four remained non-discriminating (the cold baseline had already reproduced or exceeded every required finding without the skill), so they measured the model, not the guidance — cut, along with their fixtures. Eval 0's `expected_output` was corrected: both runs answered YES on the fixture's real full-width-push topology — correct per SKILL.md's own Tone Of Review — while never firing the guarded dashboard-grid rejection; the guard now names that distinction. Eval 5's was widened to permit AX-size column-width observations at non-blocking severity. Caveat: n=2 per case (the 2026-08-21 runs); consistency across all 20 makes the direction solid, no single cell is proven.

3. ~~**4 of 6 clean fixtures need hardening.**~~ **RESOLVED 2026-08-04.** Hardened and re-measured cold: evals 1 and 5 flipped YES→NO, evals 2 and 4 held NO with the previously-cited defects now absent from the rationale. 4/4 pass; all six clean fixtures now hold as over-rejection guards. Note the traps themselves always held — no agent ever took the intended bait, and eval 1 refused `.labelStyle(.iconOnly)` as a false positive by name in both runs.

4. **`Swift 6.2` in Target Baseline is unverified** against the Xcode 27 SDK. Left as-is rather than guessed during the 2026-08-04 version sweep.

## Revision History

| Date | Score | Notes |
|------|-------|-------|
| 2026-05-17 | 94/100 | Baseline — initial skill commit |
| 2026-05-17 | 95/100 | P1+P2 fixes: Liquid Glass examples, iPad multiwindow recipes, keyboard command set, design-tokens cross-link |
| 2026-05-17 | 95/100 | Add Stitch design-handoff workflow (9 new files: 1 workflow + 6 references + `data/stitch-negative-constraints.csv` + `templates/stitch-apple-native-brief.md`). SKILL.md routed via section anchors. Description compressed 948→846 chars (Codex headroom). House-rule labels applied. Paste-export fallback when no MCP tool found. Peer-reviewed by codex gpt-5.5 across 3 rounds. Structural 13/13 retained. |
| 2026-06-18 | 95/100 | `references/navigation-patterns.md`: added SDK 27 presentation/layout APIs harvested from Apple's Xcode 27 `swiftui-whats-new-27` skill — toolbar overflow/minimization (`visibilityPriority`, `ToolbarOverflowMenu`, `.topBarPinnedTrailing`, `toolbarMinimizeBehavior`, `toolbarVisibility(.statusBar)`), `swipeActionsContainer()` for swipe outside `List`, and data-driven `confirmationDialog(_:item:)`/`alert(_:item:)` as a presentation-choice guideline. Scoped strictly to design/layout/presentation — no state/dataflow content (that stays with the external `swiftui-expert-skill`; peer-review B1). Signatures verified against Xcode 27.0 (27A5194q); all snippets type-checked clean (`swiftc -typecheck -target arm64-apple-ios27.0`). Availability-gated. Structural 13/13 retained; manual held 95. |
| 2026-08-04 | 95/100 | Harden the 4 defective clean fixtures and re-measure. Fixes target exactly the defects the cold baseline named: `glass-toolbar` gained explicit 44pt targets and a `Toggle` + `.toggleStyle(.button)` so selected state reaches VoiceOver via `.isSelected` instead of a silently-changing label; `onboarding-hero` gained `@ScaledMetric(relativeTo: .largeTitle)` and a `ScrollView` + `.safeAreaInset` so the CTA cannot strand at AX3–AX5; `documented-custom-bar` gained a non-color selected state (`.symbolVariant`), `.accessibilityValue` so the score is announced rather than replaced, and a rewritten justification resting on the one constraint that survives scrutiny (no control over system tab-bar height from an in-flight `DragGesture`) after the baseline disproved two of the original three; `poster-carousel` dropped `lineLimit(2)` for `.fixedSize(horizontal: false, vertical: true)`. Re-run cold: **4/4 NO**, evals 1 and 5 flipped from YES. Four `expected_output` fields updated — they had come to describe code that no longer existed, the same stale-ground-truth trap as eval 9. **Lesson recorded: fixing loud defects surfaces quiet ones.** With the accessibility-parity failures gone, the eval-4 reviewer found a bug present since the fixture was written — the trailing `.overlay` score paints over the last section button and, `Text` being hit-testable, can swallow its taps. Replaced the overlay with an `HStack` sibling that reserves its own space, deleting the bug class rather than patching it with `.allowsHitTesting(false)`; that final edit is not itself re-measured. |
| 2026-08-04 | 95/100 | Four-lens re-audit (anthropic-grade-optimizer + skill-writer + skill-creator + writing-skills). Both mechanical gates were already clean (AGO 100/100, structural 13/13) and stayed clean, so every finding came from the qualitative lenses. **Two correctness bugs, same species — `SKILL.md` asserting something stricter or staler than the reference it routes to, which is internally consistent prose no regex can catch.** (1) Baseline retargeted 26→27 across 16 lines / 8 files; the worst site was `source-architecture.md`'s Demoted Claims block, which encoded the inversion *as an enforceable rule* (`Do not say: "macOS 27 is current"`), instructing the agent to correct a user who stated the truth. `SKILL.md`'s "27 is future-looking rumor" became a conditional keyed on an observable predicate, matching what `navigation-patterns.md` already did. Description trigger spans `26–27` to protect recall through the transition. (2) `Tone Of Review`'s blanket "Reject: `TabView` as the root container on iPad" was false — contradicted both Apple (`.tabViewStyle(.sidebarAdaptable)`, iPadOS 18+, WWDC24) and its own `ipad-layout.md:91` ("`TabView` can be correct on iPad"); rewritten to name the real defect (collection/detail stretched across a full-width `NavigationStack`) and `.sidebarAdaptable`/`TabSection` added to `ipad-layout.md`, where they appeared nowhere before. Structural: router single-sourced (SKILL.md 270→238; the three refs routed only by the flat lists were folded into the decision tree first to avoid orphaning), and `Always Apply`'s rejection bullet deleted after moving its one unique item (right-rail AI panels) into `Hard Rejections`. Added `evals/` — 10 agent-facing cases, 6 clean / 4 dirty, schema matched to `apple-multiplatform`. Cold baseline run: **0/10 RED** (see Open #2). `visual-audit` sibling annotated Tiercade-scoped. Manual held at 95: the correctness fixes restore a score 1.2 was already claiming, and the eval suite does not yet earn a Testability raise. |
| 2026-07-03 | 95/100 | Dedup/polish pass from a four-lens audit (anthropic-grade-optimizer Pass-1 100/100 + skill-creator + writing-skills + writing-great-skills). SKILL.md 299→270 lines: merged duplicate `Source Use Policy` + `Evidence Discipline` into one section (deep tiers stay in `source-architecture.md`); trimmed `When To Use` to a scope-boundary pointer (triggers now single-sourced in the `description`); removed two `Always Apply` bullets duplicating Default Workflow steps 4/11. Added `## Contents` TOC to the 10 references ≥250 lines (canonical AR-CC-S21 >100 deviated to ≥250 on writing-great-skills no-op grounds; 7 mid-band refs left TOC-less by documented choice). Preserved by design: Hard Rejections negative list (correct prohibition form), description keyword-variants (trigger surface), version pinning, zero coercive emphasis. Plan peer-reviewed by codex gpt-5.4-mini xhigh across 3 rounds (2 REVISE → APPROVED). Structural 13/13 retained. |
| 2026-08-21 | 95/100 | Single-source dedup pass from a writing-for-agents + skill-writer + skill-creator three-lens audit. −542/+122 lines across 19 files; SKILL.md 238→161. Each duplicated meaning reduced to one authoritative home: container decision tree → `navigation-patterns.md` (7 copies deleted; gains Content Containers branch); rejection inventory → `anti-web-smells.md` as severity-tiered list, CSV folded in and `data/` deleted (no script consumed it); spacing scale → `visual-hierarchy.md` (two conflicting tables deleted); critique workflow drops rubric/template copies; `stitch-handoff-format.md` becomes spec-only; Rule 1, tone pairs, reductionist definition, sheet-vs-inspector each single-sourced. Router hardened: fallback route added (router-without-default hard stop); description trigger renames collapsed 846→797 chars (26–27 scope, "what's wrong", "Apple-native look and feel" kept; the 2026-07-03 keyword-variant preservation is consciously reversed on new evidence — the 0/10 RED baseline showed the variants were not earning recall, and each always-loaded word spends context every turn; prohibition *form* preserved); Always Apply 15→3; Target Baseline → pins only; Stitch source-ranking disclosed to its workflow; severity vocab unified; *web gravity* coined and reused; Tiercade-scoped `visual-audit` row removed; `source-architecture.md` pruned (AGENTS.md-dup section, stale CSV schema, dead dirs). evals.json: dirty four cut (non-discriminating per measured baseline), clean six retained as over-rejection guards and re-verified with n=2 with-skill runs (20 runs, 10/10 consistent, zero over-rejection); eval 0/5 expected_outputs corrected. Structural 15/15 retained (evaluator now reports 15 checks vs 13 recorded earlier — checker version drift, not a regression). Reversals of prior recorded decisions are called out above; carried gaps unchanged (Swift 6.2 unverified, worked-example critiques open). |
