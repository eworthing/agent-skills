# swiftui-drag-drop Evaluation

**Date:** 2026-05-12
**Evaluator:** Claude (Opus 4.7, 1M context)
**Skill version:** 1.0.0 (initial)
**Automated score:** 100% (13/13 structural checks)

---

## Automated Checks

```
📋 Skill Evaluation: swiftui-drag-drop
==================================================
Path: /Users/Shared/git/agent-skills/swiftui-drag-drop

  [STRUCTURE]
    ✅ SKILL.md exists
    ✅ SKILL.md has valid frontmatter
    ✅ Skill name matches directory
    ✅ No extraneous files
    ✅ Resource directories are non-empty

  [TRIGGER]
    ✅ Description length adequate
    ✅ Description includes trigger contexts

  [DOCUMENTATION]
    ✅ SKILL.md body length
    ✅ References are linked from SKILL.md

  [SCRIPTS]
    ✅ Python scripts parse without errors
    ✅ Scripts use no external dependencies

  [SECURITY]
    ✅ No hardcoded credentials or emails
    ✅ Environment variables documented

==================================================
  ✅ Pass: 13  ⚠️  Warn: 0  ❌ Fail: 0
  Structural score: 100% (13/13 checks passed)
```

## Manual Assessment

| # | Criterion | Score | Notes |
|---|-----------|-------|-------|
| 1.1 | Completeness | 4/4 | Covers DropDelegate vs `.onDrop`, priority routing, NSItemProvider lifecycle, payload extraction across providers, Chrome/Safari/Firefox UTType matrix, view-attachment pitfalls, tvOS gating, undo, debugging — all common operations + edge cases for the receiving side of SwiftUI drag-drop. |
| 1.2 | Correctness | 4/4 | All rules cross-checked against Apple `DropDelegate` semantics and Tiercade's production code: `validateDrop` for suppression, async work after `performDrop` returns `true`, `@MainActor` hop in loader completion, `.contentShape(.rect)` on `Button` wrapper. Sample code compiles structurally. |
| 1.3 | Appropriateness | 4/4 | Zero external deps, pure SwiftUI / UTType / NSItemProvider. Follows Apple platform conventions; uses `@Observable` for the router (modern Swift 5.9+). |
| 2.1 | Fault Tolerance | 3/4 | Explicitly addresses partial failure modes (silent ignored drops, ghost drops, browser-specific provider gaps) and prescribes recovery (HTML parser fallback, multi-tier extractor). No retry logic, but drops don't need it. |
| 2.2 | Error Reporting | 3/4 | "Debugging Drop Types" section gives an actionable `print` snippet with three concrete diagnoses (empty, `dyn.…`, html-only). Could add a richer logger, but the technique is enough for a fresh agent to diagnose. |
| 2.3 | Recoverability | 3/4 | Undo Semantics section calls out atomic finalize for multi-item drops. Re-running a drop is naturally idempotent at the API level; cannot score 4 because there is no checkpoint mechanism, which is N/A for drops. |
| 3.1 | Token Cost | 3/4 | 342 lines — slightly over the <250 ideal for a single SKILL.md, but justified: code skeletons (priority chain, extractor enum, view wrapper) load-bear and would lose value if split into a reference file for a 1-file skill. No fat to trim without removing concrete examples. |
| 3.2 | Execution Efficiency | 4/4 | No scripts to run. The documented patterns themselves are efficient (kick off `Task` once in `performDrop`, no polling, no double-loads). |
| 4.1 | Learnability | 4/4 | A fresh agent can implement a multi-target drop system from this file alone: includes router model, three `DropDelegate` examples at different priority tiers, view wrapper, platform gate, and debug snippet. |
| 4.2 | Consistency | 4/4 | Uniform code style throughout, consistent UTType naming, consistent priority-suppression idiom across all three delegate examples. |
| 4.3 | Feedback Quality | 3/4 | Documents what successful and silently-ignored drops look like, with concrete debug technique. No JSON mode (N/A — this is documentation, not a CLI). |
| 4.4 | Error Prevention | 4/4 | "Constraints" section lists hard rules; "Do NOT Use For" section prevents misapplication (tvOS, `Transferable` collisions, AppKit pasteboard). Suppression-in-`validateDrop` rule explicitly warns against the most common bug. |
| 5.1 | Discoverability | 4/4 | Description leads with capabilities, then lists 13+ specific trigger contexts (DropDelegate, onDrop, NSItemProvider, UTType, drop priority, drop handler conflicts, payload extraction, multi-provider drops, Chrome image drag, etc.). Section headings are scannable. |
| 5.2 | Forgiveness | 3/4 | Undo Semantics covers atomic undo groups for multi-item creates and notes single-step undo for replaces. The skill prescribes safe defaults but cannot enforce them. |
| 6.1 | Credential Handling | 4/4 | No secrets, no PII, no committed credentials. |
| 6.2 | Input Validation | 4/4 | Documents that `validateDrop` must be the gate, including rejection of internal-move UTTypes in background handlers. Treats `NSItemProvider` data as untrusted (caller validates types before consuming). |
| 6.3 | Data Safety | 4/4 | Drop receiving is non-destructive by definition. Multi-item create wrapped in one undo group. |
| 7.1 | Modularity | 4/4 | Sample code separates the router (`DropRouter`), delegates (`ItemDropDelegate`, etc.), extractor (`DropPayloadExtractor`), and view wrapper. Each is independently swappable. |
| 7.2 | Modifiability | 4/4 | Adding a new payload tier is a single change in the extractor priority list. Adding a new drop target is copy-modify of a `DropDelegate` skeleton + one router field. |
| 7.3 | Testability | 4/4 | Extractor is explicitly pure (`[NSItemProvider] -> DroppedPayload?`), making it unit-testable without a UI host. Delegates depend only on the router model, which is mockable. |
| 8.1 | Trigger Precision | 4/4 | "Use when…" phrase present; description enumerates concrete triggers spanning API names (DropDelegate, onDrop, NSItemProvider, UTType), problem phrases ("drop handler conflicts", "wrong handler catches drop"), and domain terms (Chrome image drag, multi-provider drops). Specific enough to avoid false positives against `Transferable`/`.dropDestination` workflows. |
| 8.2 | Progressive Disclosure | 3/4 | Two-level disclosure: description → SKILL.md. No references/ directory; the source skill is small enough (342 lines) that splitting would hurt rather than help. Acceptable for skill size. |
| 8.3 | Composability | 3/4 | Pairs cleanly with `swiftui-expert-skill` (view identity via `references/view-structure.md` + `performance-patterns.md`), `swiftui-accessibility` (drop-target labels), and `ios-security-hardening` (validating dropped URLs). Output is human-readable documentation, not machine-parsed. |
| 8.4 | Idempotency | 4/4 | Re-reading the skill yields the same guidance. Documented patterns are themselves idempotent (returning `true` from `performDrop` then doing async work; rejecting in `validateDrop` is side-effect-free). |
| 8.5 | Escape Hatches | 3/4 | Skill explicitly identifies "Do NOT Use For" cases and points to `Transferable` / `.dropDestination(for:)` as the simpler alternative when caller controls both sides. No flags (N/A — documentation skill). |
| | **TOTAL** | **92/100** | |

## Priority Fixes

### P0 — Fix Before Publishing
None.

### P1 — Should Fix
None. 92/100 with no failing structural checks is publish-ready.

### P2 — Nice to Have
1. If the skill grows beyond ~400 lines, split the Chrome compatibility table and the payload extractor priority list into `references/payload-extraction.md` and link from SKILL.md, recovering one point on 3.1 Token Cost and 8.2 Progressive Disclosure.
2. Add a `references/troubleshooting.md` cataloging more "wrong handler catches drop" diagnoses (would raise 2.2 Error Reporting and 4.3 Feedback Quality).

---

## Merge Summary

This skill was extracted from `Tiercade/skills/drag-drop/SKILL.md` (272
lines, Tiercade-coupled).

**Kept (generalized):**

- DropDelegate vs `.onDrop` decision criteria.
- Drop priority architecture across overlapping handlers, with the rule
  that suppression must live in `validateDrop` not `performDrop`.
- Three `DropDelegate` skeletons at different priority tiers (leaf,
  mid, fallback), renamed to generic `ItemDropDelegate`,
  `BinDropDelegate`/row, and background.
- `DropPayloadExtractor` concept — multi-provider extraction with a
  documented priority list of UTTypes.
- Chrome / Safari / Firefox image-drag UTType reliability matrix,
  including the rule to parse `public.html` before `public.tiff`.
- Apple NSItemProvider lifecycle rules (load inside `performDrop`,
  return `true` immediately, `@MainActor` hop in completion handlers).
- "Don't attach `.onDrop` to `Button`" wrapper pattern with
  `.contentShape(.rect)` and `.allowsHitTesting(false)` overlay.
- Platform gating (`#if !os(tvOS)`).
- Debug technique (`providers.flatMap(\.registeredTypeIdentifiers)`).
- Undo semantics for atomic multi-item creates.

**Rejected (Tiercade-coupled):**

- `TiercadeItemIDPayload`, `TiercadeDropTypes`, `com.tiercade.item-id`
  UTType, `tiercade-schema`.
- `appState.imageDropTargetItemId`, `appState.tierDropTargetId`,
  `app.overlays.*`, `finalizeChange`, `updateItem` — replaced with a
  generic `DropRouter` model.
- Class names `CardDropDelegate`, `TierRowDropDelegate`,
  `StagingDrawerDropDelegate` — replaced with `ItemDropDelegate`,
  `BinDropDelegate`, generic background delegate.
- "Phased Implementation" section (Tiercade-specific rollout history).
- "Sorted View Restrictions" section (Tiercade SavedView feature).
- "Staging Drawer Drop Target" section (Tiercade UI surface).
- All `Tiercade/...` file paths and `docs/specs/...` references.
- `metadata:` block, `evidence_commits`, `applyTo` glob.

**Judgment calls:**

- Kept all three priority-tier delegate examples even though they
  expand the file to 342 lines. A single example would not demonstrate
  the suppression contract; the value of this skill is precisely the
  multi-handler routing, which requires showing at least two tiers
  communicating through a shared router.
- Added a "Do NOT Use For" section pointing users to `Transferable` /
  `.dropDestination(for:)` for in-app model drops — the source skill
  did not address this distinction and it is a common confusion.
- Added a browser column for Firefox in the compatibility table based
  on Apple's documented UTType conformance; Tiercade's table only
  covered Chrome.

---

## Verification

**Forbidden-grep on Tiercade-coupled terms** (from
`/Users/Shared/git/agent-skills`):

```
grep -irE "(tiercade|tierlogic|tiercadecore|appstate|screenid|palette\.[a-z]|tvmetrics|tiermetrics|modelresolver|projectvalidation|stagingstate|finalize[Cc]hange|build_install_launch|run_local_gate|run_ui_tests|sync_skills|init_skill|tiercade-schema|evidence_commits|launchtiercade|com\.tiercade)" swiftui-drag-drop/SKILL.md
```

Result: no matches (exit 1).

**Phase 3 allow-list grep on references-only terms:**

```
grep -E "(focusToken|UITestAXMarker|Liquid Glass)" swiftui-drag-drop/SKILL.md
```

Result: no matches (exit 1).

**Automated structural eval:**

```
python3 .claude/skills/skill-evaluator-1.0.0/scripts/eval-skill.py swiftui-drag-drop
```

Result: 100% (13/13 pass, 0 warn, 0 fail).

---

## Revision History

| Date | Score | Notes |
|------|-------|-------|
| 2026-05-12 | 92/100 | Baseline — extracted from `Tiercade/skills/drag-drop/SKILL.md`, generalized for the agent-skills repo. |
