# swiftdata-persistence Evaluation

**Date:** 2026-05-12
**Evaluator:** Claude Opus 4.7 (1M context)
**Skill version:** iOS-26/27 currency + concurrency correction + dedup/split pass
**Automated score:** 100% (13/13 structural checks)

---

## Merge Summary

Extracted the portable SwiftData patterns from
`/Users/Shared/git/Tiercade/skills/swiftdata-persistence/SKILL.md` (290 lines,
Tiercade-coupled) into a generic skill at
`/Users/Shared/git/agent-skills/swiftdata-persistence/` (321 lines, portable).

Generalizations applied:

- `TierListEntity` / `TierItemEntity` / `TierListSource` → `BundledItemEntity` / `ChildEntity` / `BundledSource`
- `BundledProjects.swift` / `prefillBundledProjectsIfNeeded` → `bundledItems` / `prefillBundledItemsIfNeeded`
- `makeBundledTierListEntity(from:)` → `makeEntity(from:)`
- `Logger.persistence` → generic `Logger()`
- `~/Library/Containers/com.tiercade.Tiercade/...` → `~/Library/Containers/<your.bundle.id>/...`
- `TiercadeApp.swift` → `YourApp.swift`

Removed:

- Tiercade frontmatter fields (`applyTo`, `metadata:` block, `evidence_commits`, `author: "Tiercade Team"`)
- "Related Documentation" block of `docs/specs/data-*-spec-implemented.md` links
- "Key Files" table pointing at `State/AppState+*.swift`
- Historical Dec-2024 bug callout (kept the *symptom* and *root cause* — dropped the company-specific incident metadata)

Additions over source:

- "Do NOT Use For" section delimiting scope (Apple `VersionedSchema`, CloudKit, user-content)
- Safer-default delete-app-data command (`simctl uninstall <device> <bundle-id>`) before the destructive broad `rm -rf`, with warning that the broad form wipes every other simulator app's data
- Explicit `@MainActor` annotations on every persistence-mutating example
- "Use typed errors" constraint expanded into an actionable note

## Automated Checks

```
📋 Skill Evaluation: swiftdata-persistence
==================================================
Path: /Users/Shared/git/agent-skills/swiftdata-persistence

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

## Verification

Forbidden-content greps (must return no matches):

```
$ grep -irE "(tiercade|tierlogic|tiercadecore|appstate|screenid|palette\.[a-z]|tvmetrics|\
tiermetrics|modelresolver|projectvalidation|stagingstate|finalize[Cc]hange|\
build_install_launch|run_local_gate|run_ui_tests|sync_skills|init_skill|\
tiercade-schema|evidence_commits|com\.tiercade)" swiftdata-persistence/SKILL.md
(no matches)

$ grep -E "(focusToken|UITestAXMarker|Liquid Glass)" swiftdata-persistence/SKILL.md
(no matches)
```

Line counts:
- `SKILL.md` — 417 lines (17 frontmatter + 400 body; split at the ~400 house threshold)
- `references/migrations.md` — 198 lines; `references/modern-apis.md` — 160 lines

## Manual Assessment

Pure documentation/reference skill (no scripts). Now three-tier: `SKILL.md` + two `references/` files. Script-bound criteria scored against reference-skill expectations (idempotent reads, no exec surface).

| # | Criterion | Score | Notes |
|---|-----------|-------|-------|
| 1.1 | Completeness | 4/4 | Headline gotcha, 3 migration patterns, container setup, context injection, `FetchDescriptor` + `@Query` patterns, concurrency (main vs `ModelActor`), cascade-delete, debugging, typed errors, and a version-anchored availability table. `VersionedSchema` + `SchemaMigrationPlan` walkthrough and the iOS 18–27 surface now covered in `references/`. CloudKit stays out of scope by design. |
| 1.2 | Correctness | 4/4 | `@Model`, `@Relationship(deleteRule: .cascade)`, `#Predicate`, `SortDescriptor`, `FetchDescriptor.fetchLimit`, `.modelContainer(_:)`, `@Environment(\.modelContext)`, `modelContext.hasChanges` all match Apple's current SwiftData API. `simctl uninstall` syntax verified. |
| 1.3 | Appropriateness | 4/4 | Markdown reference, zero deps, right tool for codifying gotchas. |
| 2.1 | Fault Tolerance | 3/4 | Examples wrap `try modelContext.save()` in do/catch; auto-save swallows throw and logs. Migration examples handle `try modelContext.fetch` failure. No retry semantics (N/A for doc). |
| 2.2 | Error Reporting | 3/4 | Constraint section calls out typed errors. Examples log via `Logger().error(...)`. No own error surface. |
| 2.3 | Recoverability | 4/4 | Re-reading idempotent. All three migration patterns are idempotent across launches. |
| 3.1 | Token Cost | 4/4 | Body held at 400 lines by splitting the gated migration variants and the iOS 18–27 API patterns into `references/`. Fetching (`FetchDescriptor` + `@Query`) kept co-located inline where it earns its place. |
| 3.2 | Execution Efficiency | 4/4 | No scripts, no overhead. |
| 4.1 | Learnability | 4/4 | Self-sufficient. Headline gotcha leads with symptom set ("images show placeholders…") matching real bug-report language. WRONG/CORRECT framing in delete-and-regenerate, version-based, and hash-based comparisons. |
| 4.2 | Consistency | 4/4 | Uniform code-fence style, uniform `@MainActor` annotation across mutating examples, uniform Swift syntax, uniform section headers. |
| 4.3 | Feedback Quality | 3/4 | N/A for doc. Debugging checklist provides ordered diagnostic steps. |
| 4.4 | Error Prevention | 4/4 | Explicit "Never use for user-created content" callouts on each migration pattern. Destructive `rm -rf` paired with safer `simctl uninstall` alternative + warning. `@MainActor` on every mutation example. |
| 5.1 | Discoverability | 4/4 | Lead-with-the-gotcha structure. "When to Use" + "Do NOT Use For" + scoped headers make navigation obvious. |
| 5.2 | Forgiveness | 4/4 | Read-only artifact. Destructive shell command paired with narrowly-scoped alternative. |
| 6.1 | Credential Handling | 4/4 | No secrets, no scripts. |
| 6.2 | Input Validation | 4/4 | No input surface. |
| 6.3 | Data Safety | 4/4 | Read-only doc. Migration patterns explicitly flag data-loss risk on user content. Wipe-command section orders safe → destructive. |
| 7.1 | Modularity | 4/4 | Three-tier: `SKILL.md` core + `references/migrations.md` + `references/modern-apis.md`, each single-topic and linked from a `## References` section. |
| 7.2 | Modifiability | 4/4 | New migration pattern → append to "Seed-Data Migration Patterns" section. New fetch pattern → append to "FetchDescriptor Patterns". No tight coupling. |
| 7.3 | Testability | 3/4 | Availability table links each API to its Apple doc page and carries a `Last verified: 2026-07-04` stamp; every version floor was checked against live DocC (e.g. `ResultsObserver`/`HistoryObserver` iOS 27 beta, `#Unique`/`#Index` iOS 18). Drift is now detectable by re-walking the linked pages. No automated harness (repo-wide F-005). |
| 8.1 | Trigger Precision | 4/4 | "Use when…" includes specific symptom strings ("images-show-placeholder-after-upgrade", "data not showing", "stale entity") plus API names. Low false-positive risk. |
| 8.2 | Progressive Disclosure | 4/4 | 3 levels: description → `SKILL.md` core → two `references/` files. Only the migration and modern-API branches pull in the heavy reference; the always-loaded core stays at 400 lines. |
| 8.3 | Composability | 4/4 | `## Sibling Skills — Defer When` hands off actor mechanics → `swift-concurrency`, `@Query` view-perf → `swiftui-expert-skill`, platform gating → `apple-multiplatform`, with no defer-loop back to `swiftui-native-ux` (which already names this skill as owner). |
| 8.4 | Idempotency | 4/4 | Read-only artifact. |
| 8.5 | Escape Hatches | 3/4 | Doc lists three migration strategies (delete-regen, version-gated, hash-gated) — agent picks per dataset shape. |
| | **TOTAL** | **97/100** | **Excellent** — publish confidently |

## Priority Fixes

### P0 — Fix Before Publishing
None. No blockers.

### P1 — Should Fix
None. All structural checks pass; description meets trigger-precision requirements with specific symptom strings.

### P2 — Nice to Have

All four prior P2 items are now addressed:

1. ✅ `references/migrations.md` created (gated seed variants + user-content schema migration).
2. ✅ Apple doc links added inline and across the availability table; `Last verified` stamp added.
3. ✅ `VersionedSchema` + `SchemaMigrationPlan` walkthrough added to `references/migrations.md`.
4. ✅ `@Query` patterns (static filter/sort + dynamic-predicate-in-`init`) added inline.

Remaining (repo-wide, non-blocking):

- **F-005 eval-harness** — no automated drift check against the live SwiftData API (deferred repo-wide). The `Last verified` stamp + per-row doc links are the manual mitigation.

## Revision History
| Date | Score | Notes |
|------|-------|-------|
| 2026-05-12 | 91/100 | Baseline — extracted portable patterns from Tiercade-coupled skill. Auto-eval 100%. Forbidden-token grep clean. |
| 2026-06-03 | ~92/100 | Anthropic-grade pass: typed-error referent + `deleteItem` do/catch (resolves typed-error self-contradiction), terminology anchor, example-imports note, dropped trivial "Basic" fetch. F-005 eval-harness deferred (repo-wide). |
| 2026-07-04 | 97/100 | iOS-26/27 currency + concurrency correction + dedup/split (Opus 4.8). Corrected the outdated "@MainActor-only mutation" rule to name `ModelActor` (verified iOS 17 protocol); added a version-anchored availability table (floors verified against live DocC — `#Unique`/`#Index`/history/`DataStore` iOS 18, model inheritance iOS 26, `ResultsObserver`/`HistoryObserver` iOS 27 beta); added `@Query` patterns + `## Sibling Skills`; collapsed 5×/3×/2× duplication to single source of truth; split gated seed variants + a new `VersionedSchema`/`SchemaMigrationPlan` walkthrough into `references/migrations.md` and the iOS 18–27 surface into `references/modern-apis.md` (fixes the undefined-helper bug); tightened `allowed-tools` to `Read, Bash, Glob`. Closes P2 #1–4. |
