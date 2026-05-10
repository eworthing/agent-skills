# contest-refactor Evaluation

**Date:** 2026-04-24
**Evaluator:** Claude (Opus 4.7) via skill-evaluator-1.0.0
**Skill version:** SKILL.md mtime 2026-04-20 (no explicit version field)
**Automated score:** 13/13 (100%)

---

## Automated Checks

```
📋 Skill Evaluation: contest-refactor
==================================================
Path: /Users/pl/.claude/skills/contest-refactor

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

Note: structural pass is hollow here. Skill is a single SKILL.md prompt-protocol — no scripts to lint, no creds to leak, no references to broken-link-check. The signal is in the manual rubric.

## Manual Assessment

| # | Criterion | Score | Notes |
|---|-----------|-------|-------|
| 1.1 | Completeness | 3/4 | Loop, scorecard, halts, guardrails covered. Step 0 discovers JS/Rust/Go/Python/Swift but Review Lenses are Apple-only — non-Swift codebases scored against Swift rules. |
| 1.2 | Correctness | 3/4 | Logic sound. Step 3.3 deletes `CURRENT_REVIEW.md` before restart → next loop has no prior scorecard for delta computation; only signal is git log of commit messages. |
| 1.3 | Appropriateness | 3/4 | Plain markdown protocol, zero deps, fits agent runtime. Lens/discovery mismatch above is the only awkwardness. |
| 2.1 | Fault Tolerance | 2/4 | Build break → revert + smaller scope. No envelope for infra failures (network, compiler crash, flaky test). Stagnation detector counts "no UP" but cannot distinguish flake from real stall. |
| 2.2 | Error Reporting | 3/4 | STATE flags clear. Evidence Rules require file:line citations. No structured schema for review sections. |
| 2.3 | Recoverability | 2/4 | Idempotent at loop boundaries. Mid-loop interrupt between commit and `CURRENT_REVIEW.md` deletion = ambiguous resume. No checkpoint file. |
| 3.1 | Token Cost | 3/4 | ~200 lines, mostly load-bearing. Lenses (~80 lines) + Output Format spec could move to `references/` for progressive load. |
| 3.2 | Execution Efficiency | 3/4 | Full build/test per loop is necessary for ground-truth scoring. No incremental option for large repos. |
| 4.1 | Learnability | 3/4 | Self-contained for fresh agent. Two ambiguities: how to compute Delta on loop 1 (no prior); where prior state lives after review deletion. |
| 4.2 | Consistency | 3/4 | STATE flags + phase numbering consistent. Scorecard "CANNOT increase without proof" rule lives as inline template comment, not in Scoring rules section. |
| 4.3 | Feedback Quality | 3/4 | STATE flags + structured review = good. No emoji/scannable summary on terminal between loops. |
| 4.4 | Error Prevention | 3/4 | Simplify Pressure Test, Blast Radius, files-NOT-to-touch list, no destructive git, no dep bumps. Strong rules. Relies entirely on agent compliance — no script enforces. |
| 5.1 | Discoverability | 3/4 | Description names slash command + triggers. No examples folder showing a real run for a fresh agent to anchor on. |
| 5.2 | Forgiveness | 3/4 | Commit-per-loop + no-squash + no destructive git ops = `git revert <sha>` always works. Solid. |
| 6.1 | Credential Handling | 4/4 | N/A. No secrets, no PII, none required. |
| 6.2 | Input Validation | 2/4 | Step 0 picks test command heuristically. No guard against discovering a 30-min CI target as the loop's test command. No bound on max loop count. |
| 6.3 | Data Safety | 3/4 | Guardrails block reset/force-push. Working-tree damage bounded by build-gate + revert. |
| 7.1 | Modularity | 3/4 | Phases + lenses sectioned. Could split lenses into references for reuse and per-stack variants. |
| 7.2 | Modifiability | 3/4 | New lens = append section. New halt state = touch multiple sections. |
| 7.3 | Testability | 1/4 | No fixtures, no example review.md output, no trace of a real run, no eval harness. Cannot validate the rubric without live invocation on a real repo. |
| 8.1 | Trigger Precision | 4/4 | Slash command + action words (autonomous, Actor-Critic, refactor loop) + explicit "Use when…" contexts. Low collision risk. |
| 8.2 | Progressive Disclosure | 2/4 | Single SKILL.md inline. No `references/` despite multiple disclosable sections (lenses, output format, scoring rubric). |
| 8.3 | Composability | 1/4 | Markdown-only output. STATE flag is in-band text. No JSON, no machine-readable scorecard. A wrapper agent must regex-parse. |
| 8.4 | Idempotency | 2/4 | Re-running from a clean state safe. Mid-loop re-entry undefined. Review-deletion-then-restart erases delta context. |
| 8.5 | Escape Hatches | 2/4 | No scope-to-dir flag, no max-loops cap, no force-lens, no dry-run. User abort is the only override. |
| | **TOTAL** | **67/100** | **Needs Work** — fix P0 + P1 before publishing. |

Verdict band per rubric: 60–69 = "Needs Work, fix P0+P1 before publishing."

## Priority Fixes

### P0 — Fix Before Publishing

1. **Adopt ICA architectural vocabulary as the only allowed terms in scorecards and findings.** Source: `/improve-codebase-architecture` `LANGUAGE.md`. Required terms: **module, interface, implementation, seam, adapter, depth, leverage, locality**. Reject "component / service / API / boundary" — overloaded, drift-prone. Add a "Vocabulary" section to SKILL.md and a one-line note to Evidence Rules. Without this, scorecard deltas across loops are noisy: same problem described two different ways looks like progress.

2. **Replace the "Bloat & Abstraction" core standard with three precise ICA tests:**
   - **Deletion test** — imagine deleting the module; does complexity vanish (it was a pass-through, delete it) or reappear across N callers (it was earning its keep, leave it)?
   - **Two-adapter rule** — does this seam have ≥2 real adapters? One adapter = hypothetical seam = indirection.
   - **Shallow module test** — is interface complexity ≥ implementation complexity?
   Each finding under this standard cites which test failed. Replaces today's vague "wrappers that exist only as architectural costume."

3. **Read `CONTEXT.md` and `docs/adr/` in Step 0 (Context Discovery).** Enumerate ADR titles + domain terms from CONTEXT.md if present. Findings that contradict an existing ADR must say so explicitly and justify reopening. Use domain vocabulary in evidence (e.g., "Order intake module" not "OrderHandler"). Currently the skill has no domain-vocabulary or prior-decision awareness — risks proposing changes that contradict load-bearing past decisions.

4. **Stop deleting `CURRENT_REVIEW.md` at Step 3.3.** Append previous review to `REVIEW_HISTORY.md`, then overwrite `CURRENT_REVIEW.md` next loop. Stagnation detector needs cross-loop scorecard comparison; today the only signal is grepping commit messages.

5. **Resolve lens / discovery mismatch.** Either (a) restrict Step 0 to Swift/Apple stacks and rename skill accordingly, or (b) add language-tagged lens references (`references/lens-rust.md`, `references/lens-python.md`) auto-selected by detected stack. Currently Rust code is silently scored against SwiftUI rules.

6. **Bound the loop.** Hard cap (default 10 loops, override via env var or first-line directive in `CURRENT_REVIEW.md`). Stagnation detector handles soft stall; hard cap handles runaway.

### P1 — Should Fix

7. **Sharpen the Simplify Pressure Test with concrete ICA pass criteria:** (i) deletion test passes for any module being removed; (ii) any new seam has ≥2 adapters planned (one prod + one test, not aspirational); (iii) tests after the refactor live at the new interface, not past it.

8. **Add "Replace, don't layer" rule to the Test Strategy / Regression Resistance lens.** Refactors that leave behind dead unit tests on shallow modules score lower. Forces deletion of waste tests, not accumulation. Old unit tests on shallow modules are waste once interface-level tests exist.

9. **Progressive disclosure.** Move Review Lenses (~80 lines), Output Format spec, and Scoring Rules into `references/`. Trim SKILL.md to ~80–120 lines: state machine + halting + ICA vocabulary + pointers. Saves agent context window.

10. **Machine-readable artifact.** Emit `CURRENT_REVIEW.json` alongside markdown: `{ state, scorecard: {...}, top_finding: {...}, backlog: [...], adr_conflicts: [...] }`. Lets `/loop` or wrapper agents parse without regex.

11. **Validate discovered test command.** Warn if estimated runtime > 5 min. Refuse `xcodebuild` on full app target without `--quick`-equivalent — generalize the BenchHype gate pattern. Step 0 currently picks heuristically with no runtime safeguard.

12. **Mid-loop checkpoint.** Write `LOOP_STATE.json` after each phase transition. On restart: if Step-3 incomplete, finish current loop, don't restart from Step 1.

13. **Document the scoring rule** "scorecard CANNOT increase without structural proof" in the Scoring section, not buried as an inline template comment.

14. **Add Dependency Category to each Coupling & Leakage finding.** ICA's four: in-process / local-substitutable / remote-owned (ports & adapters) / true external (mock). Forces the agent to pick a valid seam strategy instead of generic "extract a protocol."

### P2 — Nice to Have

15. **Example review** at `assets/example-review.md` — synthetic loop output anchored to ICA vocabulary, gives a fresh agent something to anchor format on.
16. **Fixture harness** — `scripts/dry-run.sh <repo>` walks protocol, stops before code edits, emits would-be review only.
17. **Lens registry** — `references/lenses.md` index so adding "Concurrency v2" or "Rust ownership" doesn't require touching SKILL.md.
18. **Cross-link to ICA.** Bottom of SKILL.md: "Architecture vocabulary and tests adopted from `/improve-codebase-architecture`. For deepening-only work without the rubric loop, invoke that skill directly." Prevents duplicating ICA's grilling-loop UX.

## Revision History

| Date | Score | Notes |
|------|-------|-------|
| 2026-04-24 | 67/100 | Baseline. Structural 100%, manual 67. Needs P0+P1 before publishing. ICA principles flagged for adoption. |
| 2026-05-09 | 89/100 | P0 #1-#6 + P1 #7, #9, #10, #11, #13, #14 + P2 #15, #16, #17, #18 shipped. Lens registry, ICA vocab, deletion/two-adapter/shallow tests, CONTEXT.md/ADR awareness in Step 0, REVIEW_HISTORY.md archive (no more delete), loop cap, CURRENT_REVIEW.json schema with 14 validation rules, Loop Isolation subagent boundary, Trust Model w/ payload-as-evidence-only, dry-run.sh preflight, example-review.md, build-failure carry-forward path, HALT_SUCCESS gating w/ accepted/queued residuals. SKILL.md trimmed 289→190 lines (34% reduction); Trust Model + Loop Isolation moved to references/trust-model.md; Unified Seam Policy moved to architecture-rubric.md. Verdict band: 80-89 = "Strong, ship-ready." |
| 2026-05-09 | ~91/100 | Added implementation reviewer subagent (references/implementation-reviewer.md, ~125 lines). Inspired by compound-engineering ce-code-review validator pattern, scoped down: one reviewer per loop instead of N personas + dedup pipeline. Three checks (reality / honesty / regression) on the diff before commit. Approve / reject / conditional verdict. Subagent-of-subagent (loop subagent spawns reviewer) for fresh-eyes value. Wired into SKILL.md Step 3 step 6 (between artifact gates and archive), output-format.md JSON schema (`implementation_review` field + rules #15 + #16), validation.md G15 (presence + reject↔loop_result coherence), Reference Load Matrix Step 3 row, See Also section. Reject path reverts code via `git checkout --`, commits review artifacts only, carries finding forward with reviewer reason. Score lift: 4.4 Error Prevention 3→4 (new gate enforces structural fitness beyond G1/G2 artifact-shape checks); 7.3 Testability stays 3 (still no eval harness against fixture repos). |
| 2026-05-09 | ~93/100 | Added halt subtypes + user-facing handoff (references/halt-handoff.md, ~150 lines) and Resume Detection pre-step (Step -1). Fixes two real-world gaps surfaced by user: (1) HALT_STAGNATION emitted with no plain-language explanation — user couldn't distinguish "structural wall / remaining is polish" from "loop oscillating on fake fixes" from "needs your decision". HALT_STAGNATION now requires `halt_subtype` ∈ {no_progress, oscillation, user_decision, no_backlog}; each subtype has a dedicated handoff template with a menu of next-step options. (2) No cleanup or re-validation on re-invocation — user had to manually prompt "run a fresh critic pass against current source" after commits landed past a halt. Step -1 now detects prior CURRENT_REVIEW.md state, computes drift via `git log <halt_sha>..HEAD`, auto-runs fresh Step-1 critic on drift, and either resumes (new findings), persists with re_validated_at_sha (same halt), or emits success. User flags `--reset` (archive + clear), `--cap N`, `--scope <dir>`, `--force-lens <name>` documented as escape hatches per Trust Model. Subagent return JSON gains `halt_subtype` + `halt_handoff_text`; output-format.md schema gains `halt_subtype` + `halt_handoff_text` + `re_validated_at_sha` + 3 validation rules (#17/#18/#19). Main agent contract updated: read `halt_handoff_text` aloud verbatim, do not paraphrase. Score lift: 4.3 Feedback Quality 3→4 (handoff = scannable user-facing message with menu); 8.5 Escape Hatches 3→4 (`--reset` / `--cap` / `--scope` / `--force-lens` flags now first-class). |
| 2026-05-09 | ~95/100 | Audit-driven plan execution (8 findings across 5 PRs), informed by 7-loop run on BenchHype + 3 Explore-agent audit + 5 rounds of /peer-plan-review copilot/gpt-5.4/high. **PR 1**: schema_version=2 baseline + cross-loop stable F-IDs via external `findings_registry.json` (created/persisted/committed; bootstrap from existing REVIEW_HISTORY.md) + cross-provider portability via new `references/provider-adapters.md` (Claude Code → claude-sonnet-4-6; Codex → gpt-5.4-mini; OpenCode → deepseek-v4-flash) + REVIEW_HISTORY.json formalization + new top-level fields (`provider`, `loop_model`, `loop_model_source`, `reviewer_model`, `reviewer_model_source`, `spawn_isolation`) + new gates G16/G18/G19 + Step -1 expanded (provider detection, registry bootstrap). **PR 2**: Unified Seam Policy canonical home in architecture-rubric.md (de-duplicated from 4 files); method.md compressed 108→89 lines. **PR 3**: Indirect Interface coverage carve-out (architecture-rubric.md § Replace, don't layer) + canonical Deepening Keywords + `interface_test_coverage_path` schema with `target_symbol` + new gate G17 + reviewer Check-2 verifies cited assertion references target_symbol AND distinguishes from no-op. **PR 4**: `halt_handoff` object schema (replaces flat `halt_handoff_text`) + structured `expected_actions[]` (HandoffAction with action_id/match_keywords/match_paths/match_kind ∈ all_of/any_of/no_drift_expected) + Step -1 step 4a (main agent matches commits against expected_actions) + step 4b (composes `why_halt_persists`) + `re_validation_context` schema + rule #18 update + #22 + trust-model.md HALT routing reads `halt_handoff.text` aloud verbatim. **PR 5**: Per-loop archive format compresses Builder Notes / Simplification Check / Discovery in REVIEW_HISTORY.md (.json keeps full fidelity). Token impact: ~−1790 per typical loop, ~−1650 per halt-with-drift loop, after ~5K bootstrap one-time. Cross-provider model defaults reduce dollar cost (Sonnet vs Opus inheritance ≈ 5× cheaper) without changing token counts. SKILL.md 226→273 lines (Step -1 expansion). New file `references/provider-adapters.md` (~155 lines). Plan file at `/Users/pl/.claude/plans/contest-refactor-skill-tidy-floyd.md`. |

## Re-Score Detail (2026-05-09)

| # | Criterion | 2026-04-24 | 2026-05-09 | Notes |
|---|-----------|------------|------------|-------|
| 1.1 | Completeness | 3 | 4 | Lens registry covers Apple/Rust/Go/Python/Node/JVM. P0 #5 done. |
| 1.2 | Correctness | 3 | 4 | REVIEW_HISTORY archive + build-failure carry-forward + HALT_SUCCESS gating. P0 #4 done. |
| 1.3 | Appropriateness | 3 | 4 | Loop Isolation ~300 token main-context budget. |
| 2.1 | Fault Tolerance | 2 | 3 | Build-failure path fully specified. No infra-failure envelope. |
| 2.2 | Error Reporting | 3 | 4 | JSON schema + 14 validation rules + G1-G14 gates. |
| 2.3 | Recoverability | 2 | 3 | Append-not-delete resolved old ambiguity. No mid-loop checkpoint (P1 #12 open). |
| 3.1 | Token Cost | 3 | 4 | SKILL.md 289→190 lines. Reference Load Matrix gates loads. |
| 3.2 | Execution Efficiency | 3 | 3 | Subagent isolation reduces main bloat. No incremental test option. |
| 4.1 | Learnability | 3 | 4 | Loop-1 delta + state location ambiguities resolved. Trust Model + Reference Load Matrix self-contained. |
| 4.2 | Consistency | 3 | 4 | Scoring rules promoted from inline comment to G4/G5/G6/G8 gates. |
| 4.3 | Feedback Quality | 3 | 3 | JSON adds terse summary. No emoji/scannable terminal summary. |
| 4.4 | Error Prevention | 3 | 3 | G1-G14 enforced via instruction; no script enforces gates. |
| 5.1 | Discoverability | 3 | 4 | example-review.md fixture added. P2 #15 done. |
| 5.2 | Forgiveness | 3 | 3 | Same — commit-per-loop + revert always works. |
| 6.1 | Credential Handling | 4 | 4 | N/A. |
| 6.2 | Input Validation | 2 | 3 | >5min runtime warn + xcodebuild full-app refuse + loop cap bound. P1 #11 + P0 #6 done. |
| 6.3 | Data Safety | 3 | 3 | Same. |
| 7.1 | Modularity | 3 | 4 | references/ split clean. P1 #9 done. |
| 7.2 | Modifiability | 3 | 4 | New lens = drop file + 1 row in lenses.md, no SKILL.md edit. |
| 7.3 | Testability | 1 | 3 | example-review.md + dry-run.sh + EVAL.md. No real-run trace, no eval harness. |
| 8.1 | Trigger Precision | 4 | 4 | Same. |
| 8.2 | Progressive Disclosure | 2 | 4 | Reference Load Matrix + 8 reference files + 190-line SKILL.md. |
| 8.3 | Composability | 1 | 4 | CURRENT_REVIEW.json schema + Loop Isolation routing JSON. P1 #10 done. |
| 8.4 | Idempotency | 2 | 3 | REVIEW_HISTORY.md preservation resolves prior ambiguity. Mid-loop re-entry still undefined. |
| 8.5 | Escape Hatches | 2 | 3 | Loop cap (env + directive) + dry-run + inline-mode bypass. No scope-to-dir, no force-lens. |
| | **TOTAL** | **67** | **89** | +22 points; Strong, ship-ready band. |

## Remaining Gaps (3/4 → 4/4 candidates)

Future iterations could push 89→95+ via:

- **3.2 Execution Efficiency** — incremental test option for large repos (e.g., changed-files-only mode for Step 1).
- **4.3 Feedback Quality** — emit one-line scannable terminal summary between loops (e.g., `loop 3/10 | F3 collapse-repository-theater | arch 8.0→8.5 UP | tests green | 47s`).
- **4.4 Error Prevention** — `scripts/check-gates.sh` that lints `CURRENT_REVIEW.json` against the 16 validation rules before commit. (Implementation reviewer added 2026-05-09 covers structural fitness; this gap is now about static schema-lint.)
- **2.3/8.4 Recoverability/Idempotency** — `LOOP_STATE.json` mid-loop checkpoint (P1 #12) so Step-3 interrupt resumes without restarting Step 1.
- **6.2/8.5 Input Validation/Escape Hatches** — `--scope <dir>` flag (loop only touches subset) + `--force-lens <name>` flag (override lens detection for monorepos).
- **7.3 Testability** — fixture repos under `assets/fixtures/{good,bad,medium}/` with expected scorecards; dry-run-on-fixture eval harness.
