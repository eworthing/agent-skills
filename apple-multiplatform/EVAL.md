# apple-multiplatform Evaluation

**Date:** 2026-05-13 (post-restructure)
**Evaluator:** Claude Opus 4.7
**Skill version:** 0.2.0 — references/ + audit script + escape hatches
**Automated score:** 100% (13/13)
**Manual score:** 100/100

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

## File Layout (post-restructure)

```
apple-multiplatform/
├── SKILL.md                            239 lines — topic index + master API matrix
├── EVAL.md                             this file
├── references/
│   ├── tvos.md                          72 lines — tvOS trap matrix, editMode guards
│   ├── macos.md                        112 lines — TabView, modal, toolbar, Commands, shortcuts
│   ├── catalyst.md                      48 lines — Catalyst branching, window sizing
│   ├── ui-tests.md                      34 lines — XCTest API divergence
│   ├── build-matrix.md                 152 lines — xcodebuild invocations + pass/fail samples
│   └── recovery.md                     246 lines — per-error playbook (E1–E8)
└── scripts/
    └── audit-platform-guards.sh        150 lines — static audit (T1–T5)
```

## Manual Assessment

| # | Criterion | Score | Notes |
|---|-----------|-------|-------|
| 1.1 | Completeness | 4/4 | iOS / iPadOS / Catalyst / macOS / tvOS all covered. Conditional macros, API matrix w/ Apple docs URLs, per-platform gotchas (refs), UI test divergence (ref), file-split visibility, failure-pattern table, recovery playbook (ref), build examples + pass/fail samples (ref). |
| 1.2 | Correctness | 4/4 | `canImport(UIKit)` vs `os(iOS)` rule is right for tvOS haptics. `editMode` gating note (don't use bare `#if !os(tvOS)`) is right — macOS lacks it too. `@CommandsBuilder` + `ForEach` row downgraded to "Fragile" w/ `Menu` workaround. `fullScreenCover` macOS row corrected to "No". |
| 1.3 | Appropriateness | 4/4 | Pure markdown + one portable Bash audit script (Bash 3.2 + GNU/BSD safe). `allowed-tools` limited to Read / Bash / Glob / Grep — matches read-only verify-via-build workflow. |
| 2.1 | Fault Tolerance | 4/4 | `references/recovery.md` provides per-error minimal repro + audit command + fix snippet for the eight highest-frequency build failures (E1–E8). |
| 2.2 | Error Reporting | 4/4 | Standardized output format `APPLE-MP-FAIL <platform> <error-class> <file>:<line>: <message>` shared between audit script and recovery playbook. CI-greppable. |
| 2.3 | Recoverability | 4/4 | Read-only skill; recommendations applied via Edit → git revert is trivial. |
| 3.1 | Token Cost | 4/4 | SKILL.md is 239 lines (was 368) — well within target band. Per-platform detail loaded on demand via references/. |
| 3.2 | Execution Efficiency | 4/4 | Audit script uses ripgrep when available, falls back to grep; O(files) scan with no expensive operations. |
| 4.1 | Learnability | 4/4 | Multiple worked examples in SKILL.md (canImport vs os, Catalyst branching) plus full code samples in references. Right/wrong contrast preserved. |
| 4.2 | Consistency | 4/4 | Tables across files share column shape (platform columns or Topic / Pattern). Code examples uniformly use `// WRONG` / `// CORRECT` headers. Standardized error format across audit + recovery + build-matrix. |
| 4.3 | Feedback Quality | 4/4 | `references/build-matrix.md` includes literal `xcodebuild` stdout samples for the success line and four common failure messages. Audit script emits one diagnostic per hit in standardized format. |
| 4.4 | Error Prevention | 4/4 | `canImport(UIKit)` vs `os(iOS)` callout, bare-`#if !os(tvOS)` warning for editMode, Catalyst `targetEnvironment` pattern, file-split visibility cross-link, and pre-build static audit script all prevent the most common traps before they hit `xcodebuild`. |
| 5.1 | Discoverability | 4/4 | "Use when" phrase enumerates nine trigger contexts; description cites specific symbols (`editMode`, `.page`, `.automatic`, `XCUICoordinate`, `NSToolbar`, `@CommandsBuilder`). References/ files self-describe in SKILL.md "Per-Platform Detail" section. |
| 5.2 | Forgiveness | 4/4 | Reference skill; edits go through Edit tool → git revert. Audit script is read-only static analysis. |
| 6.1 | Credential Handling | 4/4 | No secrets. |
| 6.2 | Input Validation | 4/4 | Audit script validates `$ROOT` is a directory; usage error returns exit 2. Path argument is the only input. |
| 6.3 | Data Safety | 4/4 | `allowed-tools`: Read / Bash / Glob / Grep — no Write or Edit. Audit script does not mutate. |
| 7.1 | Modularity | 4/4 | SKILL.md → six topic-keyed references + one audit script. Each reference is independently consultable. Failure-pattern table cross-links to recovery.md. |
| 7.2 | Modifiability | 4/4 | Adding a new platform-divergent API = one table row in SKILL.md + (optional) detail in references/. Adding a new trap = one entry in audit script + one row in recovery.md. Apple docs URLs make SDK drift detection cheap. |
| 7.3 | Testability | 4/4 | `scripts/audit-platform-guards.sh` provides automated drift detection for the five highest-frequency guard mistakes. Per-platform `xcodebuild` invocations are the test mechanism, and the recovery playbook doubles as an assertion table. Apple Developer URLs per matrix row enable manual SDK-drift checks. |
| 8.1 | Trigger Precision | 4/4 | Description names specific symbols (`editMode`, `TabView .page` / `.automatic`, `@CommandsBuilder`, `XCUICoordinate`, `NSToolbar`, `#if os()`, `#if canImport()`) and lists nine distinct "Use when" contexts. |
| 8.2 | Progressive Disclosure | 4/4 | SKILL.md (topic index, master matrix, summary tables) → references/ (per-platform detail, build matrix, recovery playbook) → script (static audit). Three-tier progression. |
| 8.3 | Composability | 4/4 | Cross-links six sibling skills (`swift-file-splitting`, `swiftui-drag-drop`, `apple-tvos`, `xctest-ui-testing`, `swiftui-expert-skill`, `swift-concurrency`) where their coverage is more authoritative. Audit script output format is CI-grep-compatible. |
| 8.4 | Idempotency | 4/4 | Reference content; reading it repeatedly produces the same outcome. Build commands are themselves idempotent. Audit script is a pure read scan. |
| 8.5 | Escape Hatches | 4/4 | "Do NOT use when" list scopes it out of doc-only / single-platform / off-topic changes. Build invocations are noted as lowest-common-denominator with "prefer your wrapper script if you have one". **New "Escape Hatches" section** explicitly defers to `apple-tvos` / `swift-file-splitting` / `xctest-ui-testing` / `swiftui-expert-skill` / project wrapper scripts when scopes overlap. |
| | **TOTAL** | **100/100** | **Perfect** — publishable. |

## Priority Fixes

### P0 — Fix Before Publishing
None.

### P1 — Should Fix
None.

### P2 — Nice to Have
1. Add visionOS row to the availability matrix when the project targets it
   (explicitly deferred for this round per user request).
2. Wire `scripts/audit-platform-guards.sh` into a pre-commit hook template
   in the consuming project (out of scope — skills do not own hook config).
3. Expand the audit script to cover keyboard-shortcut collision detection
   (currently a manual `rg` invocation in `references/macos.md`).
4. Capture screenshots of the canonical pass/fail xcodebuild output for
   reference; current text samples are sufficient but a visual aid helps
   newcomers.

## Verification

- `python3 .claude/skills/skill-evaluator-1.0.0/scripts/eval-skill.py apple-multiplatform`
  → 100% structural (13/13 passed, 0 warn, 0 fail)
- Audit script smoke-tested against a synthetic file containing all five
  documented traps → emits 5 hits in standardized format, exit code 1
- Audit script smoke-tested against a clean file → "No platform-guard
  issues found.", exit code 0
- Forbidden-token grep #1 (`tiercade|tierlogic|tiercadecore|appstate|...
  |evidence_commits|com\.tiercade`): exit 1 (no matches)
- Forbidden-token grep #2 (`focusToken|UITestAXMarker|Liquid Glass`):
  exit 1 (no matches)
- SKILL.md line count: 239 (target ≤ 250)

## Revision History

| Date | Score | Notes |
|------|-------|-------|
| 2026-05-12 | 100% structural / 93 manual | Initial extraction from Tiercade `cross-platform-build` (260 lines). Reframed as compatibility reference, not validation workflow. Tiercade-specific build script + evidence commits + `applyTo` glob + `metadata` block all rejected. Generic `xcodebuild` examples per platform. iPadOS and Mac Catalyst columns added to availability matrix. `canImport(UIKit)` vs `os(iOS)` rule promoted to its own section. Cross-linked five sibling skills. |
| 2026-05-13 (am) | 100% structural / 93 manual | Re-eval after correctness audit. `fullScreenCover` macOS row was Yes; Apple docs and HackingWithSwift confirm modifier is unavailable on macOS (iOS / iPadOS / Catalyst / tvOS / watchOS / visionOS only). Table row and `macOS Gotchas` bullet rewritten to state unavailability rather than HIG preference. `editMode` tvOS claim and `@CommandsBuilder` ForEach claim audited but not changed — sources mixed, deferring to skill author's empirical build tests. |
| 2026-05-13 (pm) | 100% structural / 100 manual | Restructure for top-band scoring. SKILL.md split from 368 → 239 lines; per-platform detail moved to `references/{tvos,macos,catalyst,ui-tests,build-matrix,recovery}.md`. Apple Developer doc URLs added per API matrix row. New `scripts/audit-platform-guards.sh` covers five highest-frequency guard mistakes with standardized `APPLE-MP-FAIL` output format. Recovery playbook (`references/recovery.md`) provides per-error minimal repro + audit + fix for E1–E8. `@CommandsBuilder` ForEach row downgraded from "No" to "Fragile" — `Menu` workaround stays correct either way. Explicit "Escape Hatches" section added with defer-to-sibling clauses. visionOS coverage explicitly deferred per user request. |
| 2026-05-13 (eve) | 100% structural / 100 manual | Independent re-audit pass. Fixed two 404 Apple doc URLs (`onDrop` slug, `glassEffect` signature). Reframed availability matrix preface as a *functional* table — `editMode` tvOS row stays `No` with explicit note that the symbol exists per Apple docs but no edit interface exists on tvOS, reconciling docs-literalism with operational guidance. `NavigationSplitView` row corrected: tvOS 16+ is supported (single-column adaptation), was wrongly `n/a`. `glassEffect` availability corrected from vague "SwiftUI 5+ targets" to `iOS 26+ / macOS 26+ / tvOS 26+ / visionOS 1+` with `if #available` guidance. Added script-trap-code → recovery-entry mapping table (`T1`–`T5` ↔ `E1`–`E8`). Fixed audit script glob-expansion bug by converting `$GREP` string to `${GREP_CMD[@]}` array — `*.swift` no longer subject to filename expansion on call. Catalyst rendering wording corrected (UIKit variant bridging to AppKit, not raw AppKit). `swiftui-design-tokens` added to Sibling Skills section. |
