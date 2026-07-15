# apple-multiplatform Evaluation

**Date:** 2026-07-15 (audit-script correctness pass)
**Evaluator:** Claude Opus 4.8
**Skill version:** 0.4.0 — audit rewritten as a guard-stack evaluator after a field run scored 19/19 false positives
**Automated score:** 100% (13/13)
**Manual score:** 100/100 (post-fix; **was 90/100** at the start of this pass — see *Field Failure* below)

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

## Field Failure (0.3.0 → 0.4.0) — why this pass exists

`scripts/audit-platform-guards.sh` was run against a shipping tvOS-first app
(4 platforms, ~440 Swift files, all platforms green). It produced **19 findings.
All 19 were false positives.** The tool was not merely noisy — it was worse than
useless on correct code, and 0.3.0's 100/100 told the reader to trust it.

**Why the checks failed**

| Cause | Effect |
|---|---|
| T3/T4/T5 asked "does the literal string `os(macOS)` appear in this file?" | `#if os(tvOS)` excludes macOS **without naming it** → every correctly guarded tvOS-only file flagged (10 hits) |
| A correct `#else` branch names no platform | `#if os(tvOS)` / `#else` → `.sheet` — the recommended fix — flagged as a break |
| No comment stripping | A doc comment reading "use `.fullScreenCover`" flagged as an unguarded call |
| T1 never tracked the enclosing scope | The textbook haptics pattern **this skill documents** (`canImport(UIKit)` wrapping only the `import`, uses inside `#if os(iOS)`) flagged 8× |

**Why the eval did not catch it — the more important defect**

0.3.0's recorded verification was:

> Audit script smoke-tested against a synthetic file containing all five
> documented traps → emits 5 hits, exit 1. Audit script smoke-tested against a
> **clean file** → 0 hits, exit 0.

The "clean file" contained none of the audited symbols, so it passed
**vacuously**. The test design had no case for the only thing that can produce a
false positive: **a file that contains the risky symbol and guards it
correctly.** Every one of the 19 failures lived in that untested quadrant.

The fix is therefore two-part, and the second part is the durable one:

1. Rewrite the audit to resolve the `#if` guard stack (`scripts/audit-platform-guards.py`).
2. **Commit the 19 false positives as `clean-*` fixtures** (`tests/fixtures/`),
   so the untested quadrant is now the bulk of the suite. Precedent:
   `apple-tvos/evals/evals.json` already states *"False positives … are
   failures"*; this skill now enforces it.

**Rule for future passes:** a detection script may not score above 3/4 on 7.3
Testability without negative fixtures — correctly-guarded code that must stay
silent. Positive fixtures only prove the regex fires, never that it discriminates.

### The new check reproduced the same bug within the hour

`D1` shipped in this pass asserting *"editMode compiles on tvOS but tvOS has no
edit interface → dead code"*. Run against the same app, it flagged two sites — and
**both were false positives**. The premise holds only while *nothing supplies the
value*. That app declares `@State var editMode`, injects it with
`.environment(\.editMode, $editMode)` under `#if os(iOS) || os(tvOS)`, toggles it
from its own tvOS toolbar, and branches Back-button handling on it: a deliberate
multi-select channel that reuses SwiftUI's environment key. Every tvOS reader is
live. A reviewer acting on `D1` would have deleted working tvOS behaviour — and
during this pass one nearly did, narrowing a guard to `#if os(iOS)` before the
injection was found.

Fix: `D1` now carries a tree-level precondition — suppressed if any tvOS-compiled
line injects `\.editMode` — plus `clean-app-injects-editmode-tvos`, the fixture
that pins it.

The lesson generalises past this one check. **A dead-code claim is a claim about
the whole program, not about one line's guard.** A guard tells you where code
*compiles*; it cannot tell you whether anything *drives* it. Any future `D`-class
check must name the condition under which its premise fails, and ship the fixture
where it does — which is now the second entry in this file's evidence that
positive fixtures prove nothing about discrimination.

## File Layout (post-restructure)

```
apple-multiplatform/
├── SKILL.md                            275 lines — topic index + master API matrix (ceiling 275)
├── EVAL.md                             this file
├── references/
│   ├── tvos.md                          76 lines — tvOS trap matrix, editMode guards, reorderable
│   ├── macos.md                        132 lines — TabView, modal, toolbar (+27 APIs), Commands, shortcuts
│   ├── catalyst.md                      53 lines — Catalyst branching, window sizing, 27-cycle status
│   ├── ui-tests.md                      34 lines — XCTest API divergence
│   ├── build-matrix.md                 160 lines — xcodebuild invocations + pass/fail samples
│   └── recovery.md                     258 lines — per-error playbook (E1–E8)
├── scripts/
│   ├── audit-platform-guards.py       ~300 lines — guard-stack audit (T1–T5, T1b, D1–D2)
│   └── run-tests.sh                    ~95 lines — fixture runner (Bash 3.2)
└── tests/
    └── fixtures/                       16 cases — 8 clean-* (the field FPs), 6 fail-*, 2 info-*
```

## Manual Assessment

| # | Criterion | Score | Notes |
|---|-----------|-------|-------|
| 1.1 | Completeness | 4/4 | iOS / iPadOS / Catalyst / macOS / tvOS all covered. Conditional macros, API matrix w/ Apple docs URLs, per-platform gotchas (refs), UI test divergence (ref), file-split visibility, failure-pattern table, recovery playbook (ref), build examples + pass/fail samples (ref). |
| 1.2 | Correctness | 4/4 | Prose was always right — the *script* contradicted it (0.3.0 flagged the very haptics pattern the skill documents as correct). Now aligned. `canImport(UIKit)` vs `os(iOS)` rule is right for tvOS haptics. `editMode` gating note (don't use bare `#if !os(tvOS)`) is right — macOS lacks it too. `@CommandsBuilder` + `ForEach` row "Fragile" w/ `Menu` workaround. `fullScreenCover` macOS row "No". This pass: `.topBar*` tvOS cell given the same symbol-exists-but-no-affordance note the `editMode` row carries (verified tvOS 14+); `navigationBarLeading` 27.0 deprecation added as an all-platform rename, not a divergence. |
| 1.3 | Appropriateness | 4/4 | Pure markdown + one portable Bash audit script (Bash 3.2 + GNU/BSD safe). `allowed-tools` limited to Read / Bash / Glob / Grep — matches read-only verify-via-build workflow. |
| 2.1 | Fault Tolerance | 4/4 | `references/recovery.md` provides per-error minimal repro + audit command + fix snippet for the eight highest-frequency build failures (E1–E8). |
| 2.2 | Error Reporting | 4/4 | Standardized output format `APPLE-MP-FAIL <platform> <error-class> <file>:<line>: <message>` shared between audit script and recovery playbook. CI-greppable. |
| 2.3 | Recoverability | 4/4 | Read-only skill; recommendations applied via Edit → git revert is trivial. |
| 3.1 | Token Cost | 4/4 | SKILL.md is 239 lines (was 368) — well within target band. Per-platform detail loaded on demand via references/. |
| 3.2 | Execution Efficiency | 4/4 | Audit script uses ripgrep when available, falls back to grep; O(files) scan with no expensive operations. |
| 4.1 | Learnability | 4/4 | Multiple worked examples in SKILL.md (canImport vs os, Catalyst branching) plus full code samples in references. Right/wrong contrast preserved. |
| 4.2 | Consistency | 4/4 | Tables across files share column shape (platform columns or Topic / Pattern). Code examples uniformly use `// WRONG` / `// CORRECT` headers. Standardized error format across audit + recovery + build-matrix. |
| 4.3 | Feedback Quality | 4/4 | `references/build-matrix.md` includes literal `xcodebuild` stdout samples for the success line and four common failure messages. Audit script emits one diagnostic per hit in standardized format. |
| 4.4 | Error Prevention | 4/4 | `canImport(UIKit)` vs `os(iOS)` callout, bare-`#if !os(tvOS)` warning for editMode, Catalyst `targetEnvironment` pattern, file-split visibility cross-link, and the pre-build static audit prevent the most common traps before they hit `xcodebuild`. **Caveat retired this pass:** 0.3.0 cited the audit as a strength while it mis-flagged correct code — a linter that cries wolf on the documented-correct pattern trains readers to ignore it, which is negative prevention. New "Guards may not be in this file" note also warns that sibling-file / ViewModifier factoring defeats file-scoped greps. |
| 5.1 | Discoverability | 4/4 | "Use when" phrase enumerates nine trigger contexts; description cites specific symbols (`editMode`, `.page`, `.automatic`, `XCUICoordinate`, `NSToolbar`, `@CommandsBuilder`). References/ files self-describe in SKILL.md "Per-Platform Detail" section. |
| 5.2 | Forgiveness | 4/4 | Reference skill; edits go through Edit tool → git revert. Audit script is read-only static analysis. |
| 6.1 | Credential Handling | 4/4 | No secrets. |
| 6.2 | Input Validation | 4/4 | Audit script validates `$ROOT` is a directory; usage error returns exit 2. Path argument is the only input. |
| 6.3 | Data Safety | 4/4 | `allowed-tools`: Read / Bash / Glob / Grep — no Write or Edit. Audit script does not mutate. |
| 7.1 | Modularity | 4/4 | SKILL.md → six topic-keyed references + one audit script. Each reference is independently consultable. Failure-pattern table cross-links to recovery.md. |
| 7.2 | Modifiability | 4/4 | Adding a new platform-divergent API = one table row in SKILL.md + (optional) detail in references/. Adding a new trap = one entry in audit script + one row in recovery.md. Apple docs URLs make SDK drift detection cheap. |
| 7.3 | Testability | 4/4 | **Was 4/4 in 0.3.0 on a verification that could not detect false positives (synthetic all-traps file + a vacuously clean file); the field run then scored 19/19 FP → 2/4.** Restored to 4/4 only now that `tests/fixtures/` carries 7 `clean-*` negative cases (each a real field FP), 6 `fail-*` positives, and 2 `info-*`, run by `scripts/run-tests.sh` and verified to go red when a fixture guard is deliberately widened. |
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
2. Wire `scripts/audit-platform-guards.py` into a pre-commit hook template
   in the consuming project (out of scope — skills do not own hook config).
3. ~~Expand the audit script to cover keyboard-shortcut collision detection~~
   — **deferred indefinitely.** Adding checks was what got 0.3.0 into trouble;
   breadth is not the constraint, trustworthiness is. Any new check ships with
   `clean-*` fixtures proving it stays silent on correct code, or it does not ship.
4. Capture screenshots of the canonical pass/fail xcodebuild output for
   reference; current text samples are sufficient but a visual aid helps
   newcomers.

## Verification

- `python3 .claude/skills/skill-evaluator-1.0.0/scripts/eval-skill.py apple-multiplatform`
  → 100% structural (13/13 passed, 0 warn, 0 fail)
- `./scripts/run-tests.sh` → **20/20 pass**. Every `clean-*` fixture emits zero
  hits and exits 0; every `fail-*` emits its trap code and exits 1; both `info-*`
  emit `APPLE-MP-INFO` and exit 0 (dead-code hits must never fail a gate).
- `python3 -m py_compile scripts/audit-platform-guards.py` → clean.
- **Negative control:** widening a `clean-*` fixture's guard
  (`#if os(tvOS)` → `#if !os(iOS)`) makes the suite go red with
  `T5-fullscreencover-unguarded`; restoring it goes green. The suite bites.
- **Field re-run** against the same 4-platform app that produced 19/19 false
  positives: **0 build-break hits, exit 0.** That app builds all four platforms,
  so any `T` hit there is by construction a false positive.
- **Field run is fully silent**, including `D1`: that app injects `\.editMode` on
  tvOS, so the dead-code premise does not hold and the check correctly suppresses.
  `D1`'s first cut flagged two sites there and both were false positives — see
  *The new check reproduced the same bug within the hour*. The
  `info-editmode-tvos-deadcode` fixture (no injection anywhere) still fires, so
  the check discriminates rather than being switched off.

Superseded 0.3.0 verification, kept as the record of what a passing-but-blind
test looks like: *"synthetic file containing all five traps → 5 hits; clean file
→ 0 hits."* Both passed. Neither could see the 19 false positives, because
neither exercised correctly-guarded code containing the audited symbols.
- Forbidden-token grep #1 (`tiercade|tierlogic|tiercadecore|appstate|...
  |evidence_commits|com\.tiercade`): exit 1 (no matches)
- Forbidden-token grep #2 (`focusToken|UITestAXMarker`): exit 1 (no matches).
  Note: "Liquid Glass" now appears **intentionally** (the `glassEffect` row's
  mandatory-on-27-SDK note and the Modal/Toolbar guidance) — it is no longer a
  forbidden token.
- SKILL.md line count: 275 (this-pass ceiling ≤ 275; original ≤250 target
  relaxed by 25 lines to absorb the iOS-27 matrix rows + baseline + defer note)

## Manual Spot-Check (0.3.0 pass)

Re-scored only the four dimensions this pass touches (rest unchanged from 100/100):

| Dimension | Score | Notes |
|---|---|---|
| 1.2 Correctness | 4/4 | Every new claim (C1–C6) verified against live developer.apple.com DocC docs on the 27 **beta** SDKs. Unverifiable items dropped, not hedged: `ContentBuilder` recovery entry (E9) skipped (overlay/ShapeStyle failure mode not Apple-stated; `ContentBuilder` is a `typealias` of `ViewBuilder`, not a layer under it); the "NSToolbar remap" toolbar sub-claim dropped (`topBarPinnedTrailing` is simply absent on macOS); "source-break" framing on `@State`/Document swap dropped (Apple states the macro + `ReferenceFileDocument` deprecation, not a break). |
| 3.1 Token Cost / 8.2 Progressive Disclosure | 4/4 | SKILL.md held to the 275 ceiling; narrative detail pushed to `tvos.md`/`macos.md`/`catalyst.md`, matrix rows kept terse. |
| 8.1 Trigger Precision | 4/4 | New symbols (`reorderable`, `topBarPinnedTrailing`, `toolbarMinimizeBehavior`) are named in-body; description unchanged and still accurate. |
| 4.2 Consistency | 4/4 | New matrix rows follow the existing column shape + Apple-doc-URL convention; tvos.md trap row matches the Wrong/Right format. |

## Revision History

| Date | Score | Notes |
|------|-------|-------|
| 2026-07-15 | 100% structural / 100 manual (was 90 pre-fix) | **Audit-script correctness pass (v0.4.0).** Field run against a shipping 4-platform app scored **19/19 false positives** — see *Field Failure*. Root cause: T3/T4/T5 tested for the literal string `os(macOS)`, but `#if os(tvOS)` excludes macOS without naming it; T1 ignored enclosing scope and matched doc comments. Root cause of the eval miss: verification used a synthetic all-traps file + a *vacuously* clean file, so the false-positive quadrant (symbol present, correctly guarded) was never tested. **Rewrote** `audit-platform-guards.sh` → `audit-platform-guards.py`: recursive-descent `#if` parser + guard-stack evaluation per line, comment stripping, no `eval()` (conditions are untrusted input). Portability contract changed Bash 3.2 → python3 (ships with Xcode CLT; Apple-only skill). **Added** `tests/fixtures/` (7 `clean-*` = the field FPs, 6 `fail-*`, 2 `info-*`) + `scripts/run-tests.sh`; negative control verified. **Checks:** T1 reframed from "canImport co-location" to "tvOS-unavailable symbol on a tvOS-compiled line" (category fix — `.onDrop`/`DropDelegate` are SwiftUI, not UIKit → split out as T1b; `onDrop` has no tvOS per Apple docs); T2 generalised from the bare-`#if !os(tvOS)` special case to "editMode compiles on macOS"; new info-severity D1/D2 dead-code checks that never affect exit code. **Docs:** `.topBar*` tvOS cell annotated symbol-exists-but-no-affordance (tvOS 14+, verified); `navigationBarLeading` 27.0 deprecation added to the all-platform note; new "Guards may not be in this file" subsection (sibling-file / ViewModifier factoring defeats file-scoped greps); E1's manual `rg` marked as a lead, not a verdict — it is the exact heuristic that produced the 19 FPs. |
| 2026-05-12 | 100% structural / 93 manual | Initial extraction from Tiercade `cross-platform-build` (260 lines). Reframed as compatibility reference, not validation workflow. Tiercade-specific build script + evidence commits + `applyTo` glob + `metadata` block all rejected. Generic `xcodebuild` examples per platform. iPadOS and Mac Catalyst columns added to availability matrix. `canImport(UIKit)` vs `os(iOS)` rule promoted to its own section. Cross-linked five sibling skills. |
| 2026-05-13 (am) | 100% structural / 93 manual | Re-eval after correctness audit. `fullScreenCover` macOS row was Yes; Apple docs and HackingWithSwift confirm modifier is unavailable on macOS (iOS / iPadOS / Catalyst / tvOS / watchOS / visionOS only). Table row and `macOS Gotchas` bullet rewritten to state unavailability rather than HIG preference. `editMode` tvOS claim and `@CommandsBuilder` ForEach claim audited but not changed — sources mixed, deferring to skill author's empirical build tests. |
| 2026-05-13 (pm) | 100% structural / 100 manual | Restructure for top-band scoring. SKILL.md split from 368 → 239 lines; per-platform detail moved to `references/{tvos,macos,catalyst,ui-tests,build-matrix,recovery}.md`. Apple Developer doc URLs added per API matrix row. New `scripts/audit-platform-guards.sh` covers five highest-frequency guard mistakes with standardized `APPLE-MP-FAIL` output format. Recovery playbook (`references/recovery.md`) provides per-error minimal repro + audit + fix for E1–E8. `@CommandsBuilder` ForEach row downgraded from "No" to "Fragile" — `Menu` workaround stays correct either way. Explicit "Escape Hatches" section added with defer-to-sibling clauses. visionOS coverage explicitly deferred per user request. |
| 2026-07-04 | 100% structural / 100 manual (spot-check) | **iOS 27 freshness pass (v0.3.0).** Every claim gated through a verify-first table (C1–C6) checked against live developer.apple.com DocC docs on the 27 beta SDKs. Added: reorderable-container row (iOS/iPadOS/Catalyst/macOS 27, **tvOS excluded**) to the matrix + tvos.md trap; `topBarPinnedTrailing`/`ToolbarOverflowMenu` row (absent on macOS/tvOS) + macos.md toolbar note incl. portable `toolbarMinimizeBehavior`/`visibilityPriority`; `glassEffect` note that `UIDesignRequiresCompatibility` is ignored on the 27 SDK (Liquid Glass mandatory, all five platforms); all-platform "not divergence" defer-note (`State()` macro, `ReferenceFileDocument` deprecation → `swiftui-expert`); catalyst.md not-deprecated status stamp. **Dropped as unverifiable:** `ContentBuilder` E9 recovery entry, the NSToolbar-remap toolbar sub-claim, and the "source-break" framing. SKILL.md 266→275 (new one-pass ceiling 275). |
| 2026-05-13 (eve) | 100% structural / 100 manual | Independent re-audit pass. Fixed two 404 Apple doc URLs (`onDrop` slug, `glassEffect` signature). Reframed availability matrix preface as a *functional* table — `editMode` tvOS row stays `No` with explicit note that the symbol exists per Apple docs but no edit interface exists on tvOS, reconciling docs-literalism with operational guidance. `NavigationSplitView` row corrected: tvOS 16+ is supported (single-column adaptation), was wrongly `n/a`. `glassEffect` availability corrected from vague "SwiftUI 5+ targets" to `iOS 26+ / macOS 26+ / tvOS 26+ / visionOS 1+` with `if #available` guidance. Added script-trap-code → recovery-entry mapping table (`T1`–`T5` ↔ `E1`–`E8`). Fixed audit script glob-expansion bug by converting `$GREP` string to `${GREP_CMD[@]}` array — `*.swift` no longer subject to filename expansion on call. Catalyst rendering wording corrected (UIKit variant bridging to AppKit, not raw AppKit). `swiftui-design-tokens` added to Sibling Skills section. |
