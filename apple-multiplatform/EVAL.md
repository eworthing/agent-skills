# apple-multiplatform Evaluation

**Date:** 2026-05-12 (initial extraction from Tiercade `cross-platform-build`)
**Evaluator:** Claude Opus 4.7
**Skill version:** 0.1.0 — first release
**Automated score:** 100% (13/13)

---

## Automated Checks

```
📋 Skill Evaluation: apple-multiplatform
==================================================
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

  Pass: 13  Warn: 0  Fail: 0
  Structural score: 100%
```

## Merge Summary

New skill extracted from `Tiercade/skills/cross-platform-build/SKILL.md` (260
lines) into agent-skills `apple-multiplatform/SKILL.md` (342 lines). This is a
**reframe**, not a copy: the source mixes a Tiercade-specific build-orchestration
policy with portable Apple-platform compatibility content; only the latter is
kept here.

**Kept and generalized:**
- API availability matrix (`TabView .page`, `fullScreenCover`, `editMode`,
  `.topBarLeading` / `.topBarTrailing`, `glassEffect`, drag-and-drop receiving)
  expanded with explicit iPadOS and Mac Catalyst columns
- `editMode` audit pattern, with corrected note that `#if !os(tvOS)` alone is
  insufficient (macOS lacks `editMode` too)
- `canImport(UIKit)` vs `#if os(iOS)` discipline — promoted to its own
  section with a "Critical rule" callout, because the tvOS haptics trap is the
  single most common failure mode
- tvOS gotchas table (drag receiving, `editMode`, haptics, focus, pointer,
  Menu-button dismissal)
- macOS gotchas (TabView `.page`, sheet vs `fullScreenCover`,
  `@CommandsBuilder` + `ForEach` with corrected fix using `Menu`, toolbar
  placements, split-view defaults, keyboard shortcuts)
- Mac Catalyst gotchas (window sizing, sidebar defaults, pointer-on-iOS,
  multi-window lifecycle) plus the `targetEnvironment(macCatalyst)` branching
  pattern
- UI test divergence table (`XCUICoordinate`, `NSToolbar`, `TabView .page`,
  `XCUIRemote .menu`, drag-from-coordinate)
- Cross-file visibility after split — short note + cross-link to
  `swift-file-splitting`
- Common failure-pattern table (error → cause → fix), expanded with the
  Catalyst window-collapse case and the tvOS-`canImport(UIKit)` runtime crash
- Per-platform `xcodebuild` examples for iOS / iPadOS / Catalyst / macOS / tvOS

**Rejected (Tiercade-coupled, dropped entirely):**
- `./build_install_launch.sh` and its `--no-launch` / `tvos|ios|ipad|macos`
  flags — replaced with generic `xcodebuild` invocations
- `./scripts/run_ui_tests.sh --tvos|--mac|--ios`
- `AGENTS.md` reference + evidence commits (`f662d34`, `ff660ad`, `451bcf7`,
  `95c2b10`)
- "NEVER call `xcodebuild` directly in local development" constraint —
  Tiercade policy, not a portable rule. Replaced with "build every supported
  destination before merging"
- "Build Script Behavior" section (swiftformat + swiftlint pre-flight,
  quarantine removal, simulator lifecycle, colored pass/fail) — Tiercade
  infrastructure
- `metadata:` block (`version`, `author: "Tiercade"`, `category`,
  `discovered_from`, `evidence_commits`, `tags`)
- `applyTo: "**/*.swift"` glob

**Reframed:**
- Title "Cross-Platform Build Validation" → "Apple Multiplatform Compatibility"
  to signal this is a reference skill, not a validation workflow
- Description rewritten from "Validate code changes across all Apple platforms"
  to lead with capabilities (cross-platform compatibility reference) and
  include nine explicit "Use when…" trigger contexts
- "Workflow / Step 1-6" sectioning replaced with topic-keyed sections
  (Platform Conditionals, API Matrix, tvOS Gotchas, macOS Gotchas, etc.)

**Forbidden-grep verification:**
- Pattern 1 (`tiercade|tierlogic|appstate|build_install_launch|...`): **0 hits**
- Pattern 2 (`focusToken|UITestAXMarker|Liquid Glass`): **0 hits**
  (the Tiercade source did not contain these tokens either; the second grep
  is a forward-looking exclusion against the agent-skills house style)

## Manual Assessment

| # | Criterion | Score | Notes |
|---|-----------|-------|-------|
| 1.1 | Completeness | 4/4 | iOS / iPadOS / Catalyst / macOS / tvOS all covered. Conditional macros, API matrix, gotchas per platform, UI test divergence, file-split visibility, failure-pattern table, per-platform build examples. |
| 1.2 | Correctness | 4/4 | `canImport(UIKit)` vs `os(iOS)` rule is right for tvOS haptics. `editMode` gating note (don't use bare `#if !os(tvOS)`) is right — macOS lacks it too. `@CommandsBuilder` + `ForEach` fix uses `Menu`, which is the actual workaround. |
| 1.3 | Appropriateness | 4/4 | Pure markdown reference, no scripts, no deps. `allowed-tools` limited to Read / Bash / Glob / Grep — matches the read-only verify-via-build workflow. |
| 2.1 | Fault Tolerance | 3/4 | Failure-pattern table maps 7 error messages → cause → fix. No structured retry recipe per error (none needed — this is a reference). |
| 2.2 | Error Reporting | 3/4 | Errors surface through `xcodebuild`; skill maps the message text to a fix but does not standardize an output format. |
| 2.3 | Recoverability | 4/4 | Read-only skill; recommendations applied via Edit → git revert is trivial. |
| 3.1 | Token Cost | 3/4 | 342 body lines — within the 250-400 "acceptable" band. Could split into `references/by-platform.md` per-OS if it grows further. |
| 3.2 | Execution Efficiency | 4/4 | No scripts. |
| 4.1 | Learnability | 4/4 | Six code examples (canImport vs os, editMode inline + file-level, haptics right/wrong, CommandsBuilder right/wrong, visibility after split, Catalyst branching) plus five tables. Agent can pattern-match without leaving the file. |
| 4.2 | Consistency | 4/4 | All API/gotcha tables use the same column shape (platform columns or Topic / Pattern). Code examples uniformly use `// WRONG` / `// CORRECT` headers. |
| 4.3 | Feedback Quality | 3/4 | Success indicator is "build every destination cleanly" with the `xcodebuild` commands as the assertion. No explicit pass/fail output samples. |
| 4.4 | Error Prevention | 4/4 | `canImport(UIKit)` vs `os(iOS)` callout, bare-`#if !os(tvOS)` warning for editMode, Catalyst `targetEnvironment` pattern, and `swift-file-splitting` cross-link all prevent the most common traps. |
| 5.1 | Discoverability | 4/4 | "Use when" phrase enumerates nine trigger contexts; description cites specific symbols (`editMode`, `.page`, `.automatic`, `XCUICoordinate`, `NSToolbar`, `@CommandsBuilder`). |
| 5.2 | Forgiveness | 4/4 | Reference skill; edits go through Edit tool → git revert. |
| 6.1 | Credential Handling | 4/4 | No secrets. |
| 6.2 | Input Validation | 4/4 | No input surface. |
| 6.3 | Data Safety | 4/4 | `allowed-tools`: Read / Bash / Glob / Grep — no Write or Edit. |
| 7.1 | Modularity | 3/4 | Single-file, but sections are topic-keyed and independently consultable. Could move per-platform gotcha sections to `references/` if growth justifies it. |
| 7.2 | Modifiability | 4/4 | Adding a new platform-divergent API = one table row. Adding a new gotcha = one bullet in the matching platform section. |
| 7.3 | Testability | 3/4 | Per-platform `xcodebuild` invocations are the test mechanism, and the failure-pattern table doubles as an assertion table. No automated drift detection against new SDKs. |
| 8.1 | Trigger Precision | 4/4 | Description names specific symbols (`editMode`, `TabView .page` / `.automatic`, `@CommandsBuilder`, `XCUICoordinate`, `NSToolbar`, `#if os()`, `#if canImport()`) and lists nine distinct "Use when" contexts. |
| 8.2 | Progressive Disclosure | 3/4 | Single-file body; topic-keyed sections function as a skimmable index. No `references/` split yet — would be the obvious P2 upgrade. |
| 8.3 | Composability | 4/4 | Cross-links five sibling skills (`swift-file-splitting`, `swiftui-drag-drop`, `swiftui-accessibility`, `xctest-ui-testing`, `swiftui-deprecated-apis`) where their coverage is more authoritative. |
| 8.4 | Idempotency | 4/4 | Reference content; reading it repeatedly produces the same outcome. Build commands are themselves idempotent. |
| 8.5 | Escape Hatches | 3/4 | "Do NOT use when" list scopes it out of doc-only / single-platform / off-topic changes. Build invocations are noted as lowest-common-denominator with "prefer your wrapper script if you have one". |
| | **TOTAL** | **93/100** | **Excellent** — publishable |

## Priority Fixes

### P0 — Fix Before Publishing
None.

### P1 — Should Fix
None.

### P2 — Nice to Have
1. Split per-platform gotchas (`tvos.md`, `macos.md`, `catalyst.md`) into
   `references/` if the body grows past ~400 lines. Improves `3.1` and `8.2`.
2. Add visionOS coverage (`os(visionOS)`, immersive-space APIs, ornament
   placement) once that platform stabilizes in the project's deployment
   targets. Improves `1.1`.
3. Add upstream citations (Apple Developer docs URL, evolution proposal
   numbers) per API row in the availability matrix. Improves `7.3`.
4. Add a short `references/build-matrix.md` showing CI-friendly `xcodebuild`
   invocations + `xcrun simctl` device pinning. Improves `8.3` composability
   with CI workflows.

## Verification

- `python3 .claude/skills/skill-evaluator-1.0.0/scripts/eval-skill.py apple-multiplatform`
  → 100% structural (13/13 passed, 0 warn, 0 fail)
- Forbidden-token grep #1 (`tiercade|tierlogic|tiercadecore|appstate|...
  |evidence_commits|com\.tiercade`): exit 1 (no matches)
- Forbidden-token grep #2 (`focusToken|UITestAXMarker|Liquid Glass`):
  exit 1 (no matches — corrected after initial draft used "Liquid Glass"
  as the user-facing name for `glassEffect`; replaced with "`glassEffect`
  modifier" to satisfy the house-style exclusion)
- SKILL.md line count: 342 (within target 200-350 band)

## Revision History

| Date | Score | Notes |
|------|-------|-------|
| 2026-05-12 | 100% structural / 93 manual | Initial extraction from Tiercade `cross-platform-build` (260 lines). Reframed as compatibility reference, not validation workflow. Tiercade-specific build script + evidence commits + `applyTo` glob + `metadata` block all rejected. Generic `xcodebuild` examples per platform. iPadOS and Mac Catalyst columns added to availability matrix. `canImport(UIKit)` vs `os(iOS)` rule promoted to its own section. Cross-linked five sibling skills. |
