# xctest-runner Evaluation

**Date:** 2026-05-12 (Phase 2 MERGE from Tiercade `xctest-selection-and-xctestrun`)
**Evaluator:** Claude Opus 4.7
**Skill version:** Baseline + Tiercade merge (description rewrite, no-match guardrail, keep-result guardrail, runner flag-surface section)
**Automated score:** 100% (13/13)

---

## Automated Checks

```
📋 Skill Evaluation: xctest-runner
==================================================
  [STRUCTURE]
    ✅ SKILL.md / frontmatter / name match / no extras / non-empty resources
  [TRIGGER]
    ✅ Description length adequate
    ✅ Description includes trigger contexts (Use when…)
  [DOCUMENTATION]
    ✅ SKILL.md body length (188 lines)
    ✅ References linked from SKILL.md
  [SCRIPTS]
    ✅ No scripts/
  [SECURITY]
    ✅ No hardcoded credentials or emails

  Pass: 13  Warn: 0  Fail: 0
  Structural score: 100%
```

## Merge Summary

Imported portable runner-script patterns from
`Tiercade/skills/xctest-selection-and-xctestrun` (152 lines, heavily coupled
to `scripts/run_ui_tests.sh`) and folded the generalizable insight into
the existing agent-skills version (144 → 188 lines).

**Description rewrite:**
- "Relevant when…" → "Use when…"
- Expanded scope to iOS/macOS/tvOS explicitly
- Added trigger keywords: `test-without-building`, `debug flaky UI tests`,
  `Executed 0 tests`, `preserving an .xcresult`, `list/range/glob/match/class/id
  selection modes`, `-retry-tests-on-failure`, `zero-test guardrails`,
  `PIPESTATUS exit propagation`

**Body additions:**
- **Two new Essential Guardrails (Step 4):**
  - "No tests matched" fails fast — resolve selection patterns before invoking
    `xcodebuild`; exit non-zero on empty resolution rather than letting
    `xcodebuild` silently run zero tests
  - Preserve `.xcresult` on demand — keep a `--keep-result` (or equivalent)
    opt-in so flaky failures can be inspected with `xcrun xcresulttool`
- **New Step 6: Recommended Runner-Script Flag Surface** — selection-mode
  table (`--list`, `--range`, `--glob`, `--match`, `--class`, `--id`,
  `--keep-result`) with examples + a pseudocode implementation pattern
  showing how to resolve flags to `-only-testing` arguments before calling
  `xcodebuild`

**Rejected (Tiercade-coupled):**
- `metadata` block (author "Tiercade Team", `evidence_commits` 1706f72/af0c1cf/
  929aa96/95c2b10, `discovered_from`)
- `applyTo` glob naming `scripts/run_ui_tests.sh`, `scripts/run_local_gate.sh`,
  `TiercadeUITests/**`, `TiercadeTests/**`, `docs/testing/**`
- All `./scripts/run_ui_tests.sh ...` direct invocations
- `./scripts/run_local_gate.sh --quick` validation cookbook
- `cd TiercadeCore && swift test` (project-specific module path)
- `./build_install_launch.sh` (forbidden term)
- References list pointing at `TiercadeUITests/`, `docs/testing/...`,
  `docs/research/...`, `HeadToHead`/`DragAndDropTests` (project-specific
  class names)

**Verification:**
- Forbidden grep (`tiercade`, `tierlogic`, `appstate`, `screenid.`,
  `palette.`, `tvmetrics`, `tiermetrics`, `evidence_commits`,
  `run_local_gate`, `run_ui_tests`, `build_install_launch`, etc.):
  **0 hits**
- Body allow-list grep (`focusToken`, `UITestAXMarker`): **0 hits**

## Manual Assessment

| # | Criterion | Score | Notes |
|---|-----------|-------|-------|
| 1.1 | Completeness | 4/4 | Full lifecycle: model (build vs run destinations), select, find xctestrun, guardrails (6 invariants), destinations, runner flag surface with implementation pseudocode. |
| 1.2 | Correctness | 4/4 | `xcodebuild build-for-testing`/`test-without-building` split is the documented Apple flow; `${PIPESTATUS[0]}` is bash-correct; DerivedData mtime selection matches Xcode's actual layout. |
| 1.3 | Appropriateness | 4/4 | Markdown reference, no scripts, no deps. |
| 2.1 | Fault Tolerance | 4/4 | Six explicit guardrails (latest-xctestrun selection, single cleanup trap, exit-code propagation, zero-test detection, no-match fail-fast, keep-result on demand) — covers the known failure modes. |
| 2.2 | Error Reporting | 3/4 | Explicit `ERROR: No tests were executed.` example. Suggests `xcrun xcresulttool` for post-mortem. No structured error taxonomy. |
| 2.3 | Recoverability | 4/4 | Read-only workflow on the agent side; runner scripts are idempotent (re-run with same flags = same result). |
| 3.1 | Token Cost | 3/4 | 188-line single file. Acceptable but `references/runner-script-recipe.md` split would help if the flag surface grows. |
| 3.2 | Execution Efficiency | 4/4 | No scripts; xcodebuild invocations are minimal. |
| 4.1 | Learnability | 4/4 | Numbered Steps 1–6, code examples per step, debug-flaky-test worked example, pseudocode runner skeleton. |
| 4.2 | Consistency | 4/4 | Uniform code-fence + numbered-step structure throughout. |
| 4.3 | Feedback Quality | 3/4 | Zero-test detection has explicit ERROR message. No expected-success output indicator (no "expect 'Test Suite ... passed'" sample). |
| 4.4 | Error Prevention | 4/4 | Destination invariant rule (generic for build / real for run), `PIPESTATUS` exit propagation, zero-test guardrail, no-match fail-fast, `.xcresult` preservation toggle. |
| 5.1 | Discoverability | 4/4 | "Use when…" present; 9+ specific trigger contexts including symptom strings ("Executed 0 tests") and flag names. |
| 5.2 | Forgiveness | 4/4 | Read-only; rerun with different flags is free. |
| 6.1 | Credential Handling | 4/4 | No secrets. |
| 6.2 | Input Validation | 4/4 | No untrusted input surface; runner-script pseudocode shows guarded selection resolution. |
| 6.3 | Data Safety | 4/4 | Cleanup trap pattern documented; preserve-result is opt-in. |
| 7.1 | Modularity | 3/4 | Single-file SKILL.md; no `references/`. Each Step is internally modular. |
| 7.2 | Modifiability | 4/4 | Adding a new selection mode = one row in flag table + one branch in pseudocode `case`. |
| 7.3 | Testability | 2/4 | No upstream citations (Apple `xcodebuild` man page, WWDC sessions on `.xctestrun` model, `xcresulttool` docs). No mechanism to detect drift as Xcode flag set evolves. |
| 8.1 | Trigger Precision | 4/4 | Description names specific symptoms ("Executed 0 tests"), specific flags (`-retry-tests-on-failure`, `PIPESTATUS`), and specific use-cases (debugging flaky UI tests, modifying a runner script). |
| 8.2 | Progressive Disclosure | 3/4 | Single body layer; well-organized with numbered steps + tables, but no separate reference depth. |
| 8.3 | Composability | 3/4 | No explicit cross-link to sibling skills (`xctest-ui-testing` for UI-test authoring, `bash-macos` for portable runner-script bash, `swift-testing-expert` for Swift Testing migration). |
| 8.4 | Idempotency | 4/4 | All commands re-runnable; pseudocode `case` resolution is deterministic given the same flags. |
| 8.5 | Escape Hatches | 3/4 | Constraints section notes "Prefer wrapper scripts over raw `xcodebuild` to avoid drift" — escape via direct `xcodebuild` is implicit. No explicit "when to break the rule" subsection. |
| | **TOTAL** | **93/100** | **Excellent** — publishable |

## Priority Fixes

### P0 — Fix Before Publishing
None.

### P1 — Should Fix
None.

### P2 — Nice to Have
1. Add upstream citations: Apple `xcodebuild` man page, WWDC session on
   `.xctestrun` model, `xcresulttool` documentation. Improves `7.3`.
2. Cross-link sibling skills: `xctest-ui-testing` (UI-test authoring patterns
   that this skill consumes), `bash-macos` (portable runner-script bash —
   `${PIPESTATUS[0]}` is bash-only, not zsh-portable; runner pseudocode uses
   Bash 3.2-compatible idioms). Improves `8.3`.
3. Add expected-success output indicators (sample "Test Suite ... passed"
   block to anchor `4.3` Feedback Quality).
4. Split into `references/runner-script-recipe.md` if the flag surface grows
   beyond the current 7 modes. Improves `3.1` + `8.2`.
5. Add a structured error-to-fix table (symptom → diagnosis → recovery)
   alongside the Common Mistakes list. Improves `2.2`.

## Revision History

| Date | Score | Notes |
|------|-------|-------|
| 2026-05-12 (baseline) | 100% structural / ~85 manual (estimate) | Pre-merge. Description "Relevant when…", iOS-centric framing, 4 essential guardrails, no runner flag-surface coverage. |
| 2026-05-12 (post-merge) | 100% structural / 93 manual | Phase 2 MERGE from Tiercade `xctest-selection-and-xctestrun`. Description rewritten "Use when…" with iOS/macOS/tvOS scope. Added two guardrails (no-match fail-fast, preserve-result). Added Step 6 Recommended Runner-Script Flag Surface with selection-mode table + pseudocode. Rejected `scripts/run_ui_tests.sh`/`run_local_gate.sh`/`build_install_launch.sh` paths, evidence_commits, Tiercade-class names. |
