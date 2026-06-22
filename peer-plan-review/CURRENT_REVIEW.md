<!-- loop_cap: 10 -->

### Discovery (first loop only)

- **Scope / working root:** `/Users/Shared/git/agent-skills/peer-plan-review/` (invoked as `/contest-refactor <this path>`). The contest is scoped to this skill directory. Commits land in the enclosing `agent-skills` git repo; committed paths appear under `peer-plan-review/`.
- **Source roots (in-scope, refactorable):**
  - `scripts/run_review.py` (746 LoC) — primary orchestrator: arg parsing, per-provider CLI command build, two-attempt resume/fresh loop, per-run Codex `CODEX_HOME` isolation, signal handling, subprocess capture, output/metadata extraction, self-check, model validation. The function `run_review()` alone spans lines 201–612 (~411 LoC).
  - `scripts/check_web_search.py` (348 LoC) — per-provider web-search capability probe.
  - `scripts/ppr_paths.py` (25 LoC) — thin CLI wrapper re-exporting `_common.session.paths`.
  - `scripts/tests/*.py` (7 files) + `scripts/test_run_review.py` (16-LoC unittest discovery shim).
- **OFF-LIMITS (do NOT edit):** `scripts/_common/**` is a **vendored** tree (see `scripts/_common/VENDORED_FROM`). Source of truth is repo-root `common/common/`, synced via `common/scripts/sync_common.py`; CI + pre-commit run `sync_common.py --check` requiring byte-identical vendored copies. Any change to `_common` behavior belongs in `common/` (out of scope: shared with `quorum-review`, blast radius beyond this skill). Findings may *cite* `_common` as a consumed dependency; refactors must not modify it.
- **Test command (CANONICAL):** `cd /Users/Shared/git/agent-skills/peer-plan-review && python3 -m pytest scripts/tests/`
  - **Ground-truth state at Step 0: RED — 116 passed, 2 failed** (deterministic).
  - Failing: `scripts/tests/test_execution_paths.py::TestRunReviewExecution::test_run_review_codex_accepts_last_message_file_without_json_stdout` and `::test_run_review_codex_stale_events_do_not_mask_empty_current_output`.
  - Root cause: `scripts/tests/_helpers.py::make_args()` (lines 66–82) hard-codes a parallel copy of the CLI arg names and was not updated when `run_review.py` added `--codex-home-manifest` (parse_args line 108–114, dest `codex_home_manifest`). `run_review.py:306` reads `args.codex_home_manifest`; the helper's `Namespace` omits it → `AttributeError`. **Production CLI is unaffected** (argparse supplies the `None` default); the defect is duplicated-authority-over-the-args-contract in the test helper.
- **Lint command:** `python3 -m ruff check scripts/run_review.py scripts/check_web_search.py scripts/ppr_paths.py scripts/tests/` (ruff 0.15.6 available; config in repo-root `pyproject.toml`: line-length 100, py311, rule sets E/F/I/UP/B/SIM/RUF/PTH/YTT, E501 ignored). Do not lint `scripts/_common/` (vendored).
- **Build command:** n/a (pure Python, stdlib-only; no compile step).
- **ADRs found:** none (`docs/adr/` absent).
- **Domain terms (CONTEXT.md):** none (no `CONTEXT.md`). Project vocabulary from `SKILL.md` / `README.md`: reviewer/provider (codex, gemini, claude, copilot, opencode, `agy`/Antigravity), review round, resume (request-not-guarantee, auto-fallback to fresh), session/session-file, per-run Codex home isolation, `PROVIDERS` registry, adversarial vs standard stance, model normalization / alias fuzzy-suggest, metadata extraction, web-search probe, `--self-check`, `--list-models`, `--summary-file`.
- **Selected lens:** Generic (Python).
- **Loaded lenses:** `["lens-generic.md", "lens-security.md"]`.
- **Churn (top, 6 mo, peer-plan-review/, excl. `_common/`):** `SKILL.md` (3), `references/antigravity.md` (3), `references/adapter-cli.md` (3), `EVAL.md` (3), `scripts/test_run_review.py` (2), `scripts/run_review.py` (2). Low, stable churn — no high-churn-without-abstraction leaky-seam signal.
- **Provider:** `claude_code` (CLAUDECODE=1). Loop Isolation available (Agent subagent per loop). `loop_model: claude-sonnet-4-6` (source: default), `reviewer_model: claude-sonnet-4-6` (source: default). `spawn_isolation: subagent`.
- **working_tree_dirty_paths:** `[]` (clean at Step 0).
- **test_scope:** `full`. **test_filter:** `null`.
- **Existing quality baseline:** `EVAL.md` records 98/100 (skill-evaluator rubric, 2026-06-14). Note: that rubric ≠ this contest's architecture rubric; treat as context, not a score. `EVAL.md` also claims "118 passed" — currently stale (suite is red, see above) and the README's documented test command (`pytest test_run_review.py test_web_search.py`) points at renamed files (doc-rot; later-loop credibility candidate, not part of the build-failure loop).

### Loop Counter
Loop 4 of 10 (cap)

### System Flag
[STATE: CONTINUE]

---

## Contest Verdict
Good app, but not top-tier yet

Tests are green (119 passed). Production lint is clean: `ruff check scripts/run_review.py` now exits 0 (was 3 violations: PTH108 + I001 + RUF100). Loop 4 resolved F-004 via a minimal 3-item fix: removed stale `# noqa: F401` annotation, applied import sorting via ruff `--fix`, and replaced `os.unlink(agy_log_path)` with `Path(agy_log_path).unlink()`. The remaining contest-grade drag is `run_review()` at ~405 LoC with no sub-function structure — the primary lever for architecture and simplicity dimensions.

## Scorecard (1-10)

- **Architecture quality:** 7 | SAME | `run_review.py` orchestrates cleanly via `_common` (DAG enforced by import direction, no cycles). Seams are honest: provider behavior lives in `_common.providers.PROVIDERS`; dispatch logic in `run_review()`. No costume layers. But `run_review()` spans ~405 LoC without sub-module boundaries — provider-specific setup, subprocess management, output extraction, and session persistence are a single flat function body. Structural proof (unchanged): `run_review.py:339` (`PROVIDERS[reviewer]["build_cmd"](build_args, session_id)` — registry dispatch); `run_review.py:25-69` (clean import DAG).
- **State management and runtime ownership:** 8 | SAME | `_active_proc` at `run_review.py:187` is module-level, written only by `run_review()` (line 375, line 598), read by `_signal_handler()` (line 192). Single-writer; idiomatic for signal handler communication in Python. Local state machine (`use_resume`, `fallback_used`, `session_id`) scoped to the function. No multi-writer hazards.
- **Domain modeling:** 7 | SAME | CLI adapter domain is thin by design; `PROVIDERS` registry (from `_common`) is the core model. No impossible-state hazard at the schema level. `REVIEWER_ALIASES` dict (`run_review.py:73`) and the normalization at `parse_args():121-122` are clean. Residual: no discriminated type for provider-specific output — accepted as residual (CLI adapter thin-by-design).
- **Data flow and dependency design:** 8 | SAME | Clean DAG: `run_review.py` → `_common.*`. Re-exports at `run_review.py:58-69` (with `# noqa: F401 — re-exports` for `_common.providers`) make `mock.patch("run_review.X")` paths stable. The `_common.metadata.extractors` names (`_codex_session_files`, `_parse_codex_session_id`, `_extract_opencode_metadata_via_export`) are now imported without noqa since they ARE used in-module. The `extract_metadata` / `extract_text_from_output` seam at `run_review.py:516–527` shows temporal coupling mitigated by pre-reading content at `run_review.py:501–510`; commenting explains it.
- **Framework / platform best practices:** 6.5 | UP | **Structural proof:** `python3 -m ruff check scripts/run_review.py` → `All checks passed!` (was: exit 1 with PTH108 at :605, I001 at :27, RUF100 at :36). Production module now has zero ruff violations. Residual: test-file violations (E401 + I001 + RUF100 on stdlib import lines; F405 from star imports in `_helpers.py`) remain as pre-existing infrastructure debt. These are test-only; production code is clean.
- **Concurrency and runtime safety:** 8 | SAME | Single-threaded Python. Signal handling saves/restores prior handlers in try/finally (`run_review.py:322–325`, `run_review.py:598–602`). No threading races. `subprocess.Popen` with `communicate()` blocks correctly. Gemini and agy temp cleanup in finally block. `Path(agy_log_path).unlink()` inside `contextlib.suppress(OSError)` is behaviorally identical to the prior `os.unlink(agy_log_path)`.
- **Code simplicity and clarity:** 6 | SAME | `run_review()` at ~405 LoC with no named sub-functions is the primary complexity hit. The function interleaves provider-specific environment setup, subprocess dispatch and retry, metadata extraction, and session persistence as a single flat function body. Loop 4 change is purely cosmetic (import order, noqa removal, os→Path); simplicity score unchanged.
- **Test strategy and regression resistance:** 7.5 | SAME | `TestArgContract.test_make_args_keys_match_parse_args_dests` guards the arg-contract. 119 tests green. No structural change to test strategy this loop (only production code cosmetics changed). Remaining gap: `make_args()` dict still manually maintained (guarded by sync test, but two-step edit required on arg changes). Deepening candidate: derive `make_args()` from `parse_args([])` directly.
- **Overall implementation credibility:** 8 | UP | **Structural proof:** F-004 resolved — production module passes ruff with zero violations. The orchestrator-registry pattern, signal safety, and session isolation are all well-tested. Remaining credibility drag: `run_review()` 405-LoC flat body (no sub-function navigation); `make_args()` dict still manually maintained (guarded but two-step). Moved from 7.5: cleaner signal is production-grade lint cleanliness.

## Authority Map

- **Concern:** CLI arg contract
  - **Owner:** `run_review.py:parse_args()` (argparse definition, dest names, defaults)
  - **Allowed writers:** `run_review.py:parse_args()` only
  - **Observers / readers:** `run_review.run_review()` (production), `scripts/tests/_helpers.py:make_args()` (test surrogate — manually maintained, guarded by sync test)
  - **Persistence seam:** none
  - **Async mutation entry points:** none
  - **Verdict:** Split and ambiguous — two sources of truth for arg-name set; `make_args()` can still drift (requires two-step edit), though drift is detected immediately by `TestArgContract.test_make_args_keys_match_parse_args_dests`.

- **Concern:** Active subprocess handle
  - **Owner:** module-level `_active_proc` at `run_review.py:187`
  - **Allowed writers:** `run_review.run_review()` (sets at :375, clears at :598)
  - **Observers / readers:** `_signal_handler()` (reads at :192)
  - **Persistence seam:** none
  - **Async mutation entry points:** SIGTERM / SIGINT via signal handler
  - **Verdict:** Single and clear — one writer, one reader, idiomatic Python signal-handler pattern

- **Concern:** Session state
  - **Owner:** session JSON file (written by `save_session()` from `_common.session`)
  - **Allowed writers:** `run_review.run_review()` via `save_session()` at :579
  - **Observers / readers:** `run_review.run_review()` via `load_session()` at :213; tests read the file post-run
  - **Persistence seam:** JSON file at `args.session_file`
  - **Async mutation entry points:** none
  - **Verdict:** Single and clear — serialized via file; run_review() is the sole writer per execution

## Strengths That Matter

- `run_review.py` cleanly delegates all provider-specific logic to `_common.providers.PROVIDERS`: command construction, cap flags, effort maps, session ID extraction. The orchestrator doesn't branch on provider internals — it dispatches through the registry (`run_review.py:339`, `PROVIDERS[reviewer]["build_cmd"](build_args, session_id)`).
- Gemini config-overlay isolation is behavioral and tested: the temp dir excludes auto-saved policy files (verified by `test_run_review_gemini_effort_overlay_excludes_auto_saved_policies`), preserves existing settings (verified by `test_run_review_gemini_effort_overlay_preserves_existing_settings`). The isolation prevents stale approval policies from leaking across runs.
- Resume/fallback state tracked via local variables (`use_resume`, `fallback_used`), never by mutating `args`. Snapshot at `run_review.py:209` is explicit and prevents accidental cross-attempt contamination.
- CLI arg contract guarded by `TestArgContract.test_make_args_keys_match_parse_args_dests` (`scripts/tests/test_file_io_validation.py:TestArgContract`) — the next arg addition to `parse_args()` surfaces in the suite immediately, preventing loop-1-class failures.
- Production module now passes ruff with zero violations: `os.unlink` replaced with `Path.unlink`, import block sorted, stale noqa removed. `_common.metadata.extractors` names correctly imported without noqa since they are used in-module.

## Findings

### Finding #1: `run_review()` 405-LoC flat function body with no sub-function structure

**Why it matters** — `run_review()` (lines 201–612, ~411 LoC per file, ~67+ AST control-flow nodes) interleaves provider-specific environment setup, subprocess dispatch and retry, metadata/output extraction, and session persistence as a single flat function body. Navigating the function requires reading 400+ lines without named waypoints. Any change to one concern (e.g., how agy cleanup happens) risks touching unrelated concerns (e.g., subprocess retry logic).

**What is wrong** — The function has no named sub-functions or extracted module-level helpers decomposing the concerns. The concerns are: (1) `_build_env()` — provider env + Codex home setup; (2) `_dispatch_attempt()` — subprocess invocation, signal handling, capture; (3) `_extract_result()` — output/metadata extraction from capture; (4) `_persist_session()` — session save + summary write. Currently all four live as sequential code blocks in one function body with deeply nested control flow.

**Evidence** — `run_review.py:201–612` — single function body, no helpers. AST node count: ~67+ (estimated per loop 3 Critic analysis). Deletion test: removing any block breaks production behavior — the complexity earns its keep, but the flat structure makes boundaries invisible without named sub-functions.

**Architectural test failed** — Shallow module test (the function-level "module" has much behavior but no navigable internal structure — depth without leverage-through-naming).

**Dependency category** — `in-process`

**Leverage impact** — Low: callers invoke `run_review()` cleanly; the internal complexity is hidden from callers. The leverage failure is internal: maintainers cannot navigate the concerns independently.

**Locality impact** — Moderate: a change to agy cleanup (line ~603) requires reading past subprocess dispatch (~lines 340–440) and output extraction (~lines 470–530) to find the right block.

**Metric signal, if any** — ~411 LoC / ~67 AST control-flow nodes; no internal named structure.

**Why this weakens submission** — A 9.5-grade function at this scale has extractable concerns named by sub-functions. The current flat body is legible on first read but non-navigable during maintenance; this is the primary drag on both `architecture_quality` and `simplicity`.

**Severity** — Noticeable weakness

**ADR conflicts** — none

**Minimal correction path** — Extract 3–4 module-level helpers or named inner functions: `_run_attempt(args, session_id, codex_home, gemini_config_dir, agy_log_path, logger)` (subprocess setup + dispatch + capture); optionally `_build_attempt_env(args, reviewer, codex_home)` (env dict construction). Keep `run_review()` as the coordinator: setup → loop(attempt) → extract → persist. SPT: deletion test passes (extracted helpers are called, not inlined); no new seam (module-internal helpers, not new interfaces); tests after fix live at `run_review()` interface unchanged.

**Blast radius** — Change: `scripts/run_review.py` (function body reorganization). Avoid: all other files, `_common/**`.

## Simplification Check

- **Structurally necessary:** Removing the stale `# noqa: F401` from `_common.metadata.extractors` import passes SPT Q1 (fixes real technical debt — stale annotation contradicting actual usage). The PTH108 fix (`Path.unlink`) is the smallest honest idiom fix. The I001 fix (import sorting) is automatically reversible and provably correct.
- **New seam justified:** false — no new seam proposed.
- **Helpful simplification:** The noqa removal removes documentation that was misleading (implying these names were re-export-only, when they're used in the function body). The PTH108 fix uses the already-imported `Path` type.
- **Should NOT be done:** Do not refactor `run_review()` structure in this loop — that is F-005 and belongs in a later loop. Do not touch test files.
- **Tests after fix:** 119 tests pass (same count). No tests added or deleted.

## Improvement Backlog

1. **Decompose `run_review()` 405-LoC flat body** (stable_id F-005 / structural / noticeable weakness)
   - Why it matters: the monolith interleaves env setup, subprocess dispatch, output extraction, and session persistence with no named sub-function structure. Primary lever for both `architecture_quality` (7→7.5+) and `simplicity` (6→6.5+).
   - Score impact: architecture_quality +0.5 (7→7.5); simplicity +0.5 (6→6.5); credibility +0.5 (8→8.5).
   - Kind: structural deepening. Rank: needed for contest target.

2. **Derive `make_args()` from `parse_args([])` directly** (stable_id F-006 / simplification / helpful)
   - Why it matters: eliminates the two-step edit requirement; the sync test becomes redundant or belt-and-suspenders.
   - Score impact: test_strategy +0.5 (7.5→8); simplicity minor.
   - Kind: simplification. Rank: helpful.

## Deepening Candidates

**Candidate: Derive `make_args()` from `parse_args([])` directly** (previously backlog; promoted to F-006 this loop)
- Candidate module: `scripts/tests/_helpers.py:make_args()` function
- Source friction proven: F-003 (now resolved) — `make_args()` manually copies arg names from `parse_args()` and drifted once (loop 1). The sync test (loop 3) detects drift but does not eliminate the two-step edit requirement.
- Why the current interface is shallow: `make_args()` is a hand-rolled dict that proxies `parse_args()`. It provides no behavior beyond the argparse defaults — it is equivalent to calling `parse_args([])` with overrides.
- Behavior to move behind the deeper interface: arg-name set derivation; default-value derivation.
- Dependency category: `in-process`
- Test surface after the change: same test files; `make_args()` call sites are unchanged in signature; internal implementation becomes `parse_args([])` invocation.
- Smallest first step: `def make_args(**overrides): import unittest.mock; with unittest.mock.patch("sys.argv", ["run_review.py"]): args = run_review.parse_args(); vars(args).update(overrides); return args`. This eliminates the dict entirely, and the sync test then becomes redundant (can be removed or kept as belt-and-suspenders).
- What not to do: do not add a new seam or protocol; do not change the test call sites.

## Builder Notes

1. **RUF100 vs F401 interplay**
   - What appeared: `# noqa: F401 — re-exported for tests` on the `_common.metadata.extractors` import at line 36. Ruff reports RUF100 (unused noqa) because the names ARE used in the function body (lines 319, 471, 476, 490, 514). The noqa was originally added when these were pure re-exports but the module grew to use them directly.
   - Correct action: remove the noqa entirely. Verify with `ruff check --select F401 scripts/run_review.py` — must exit 0. If F401 reappears, the names drifted back to re-export-only and the noqa is required again.
   - The `_common.providers` block at :46-57 still legitimately carries `# noqa: F401` (re-exported names ARE used in tests via `mock.patch("run_review.X")` but NOT in the module body — different situation).

2. **I001 fix scope discipline**
   - What appeared: ruff `--fix --select I001` reorganized the `_common.session` import block to appear after `_common.providers`. This is the correct isort ordering (alphabetical within `_common.*` prefix group). The fix touched no logic.
   - How to validate: after `--fix`, inspect `git diff -- scripts/run_review.py` and confirm only import block lines changed. Nothing else.

3. **Scorecard humility check (Q9)**
   - Claim `framework_idioms: 6.5` after F-004 fix — uncertainty: test file violations (E401, I001, RUF100, F405) remain. Held at 6.5 not 7 because these are structural test infrastructure debt, not production code. If a future loop cleans test lint, 7 is defensible.
   - Claim `credibility: 8` — uncertainty: `run_review()` flat body is still undecomposed. If the reviewer weighs flat-monolith credibility drag more heavily, 7.5 remains defensible. Moved to 8 because the production lint cleanliness is a concrete proof of care.
   - Claim `architecture: 7` — SAME, uncertainty unchanged. The flat body is real drag; 7 is the honest score until F-005 lands.

## Final Judge Narrative

Loop 4 is the lint-cleanup loop. F-004 (PTH108 + I001 + RUF100 in `run_review.py`) is resolved with three minimal changes: import sort via `ruff --fix`, PTH108 → `Path.unlink()`, and removal of the now-stale `# noqa: F401` annotation that ruff correctly flagged as unused (the names are actively used in the module body, not just re-exported). The production module now passes ruff with zero violations. `framework_idioms` moves from 6 to 6.5 and `credibility` from 7.5 to 8. The suite stays at 119 green. The critical remaining lever is F-005: decomposing `run_review()`'s 405-LoC flat body into named sub-functions, which targets both `architecture_quality` (7→7.5+) and `simplicity` (6→6.5+). F-006 (derive `make_args()` from `parse_args([])`) is the test-helper deepening candidate.

## Loop 4 Result

Resolved F-004 in `scripts/run_review.py` via 3 minimal changes: (1) removed stale `# noqa: F401 — re-exported for tests` annotation from `_common.metadata.extractors` import at line 36 (RUF100 — noqa was unused because the names are actively used in the module body); (2) applied `ruff --fix --select I001` to sort the import block (moved `_common.session` after `_common.providers`, the correct isort order); (3) replaced `os.unlink(agy_log_path)` with `Path(agy_log_path).unlink()` at line 605 inside `contextlib.suppress(OSError)` (PTH108 — behaviorally identical). Post-change: `python3 -m ruff check scripts/run_review.py` → `All checks passed!`; `python3 -m pytest scripts/tests/` → **119 passed, 0 failed** (unchanged). Finding F-004 (stable_id F-004) **resolved**. `framework_idioms` 6 → 6.5; `credibility` 7.5 → 8.

## Loop 4 Implementation Review

Verdict: **approved** (inline, `ran_inline: true`). All three checks passed:
- Reality: post-diff `ruff check scripts/run_review.py` exits 0; PTH108/I001/RUF100 violations no longer present.
- Honesty: no new seam; no suppression-as-fix; `Path(agy_log_path).unlink()` inside `contextlib.suppress(OSError)` is behaviorally identical to `os.unlink`; noqa removal is correct (confirmed F401 does not reappear).
- Regression: import reordering is purely cosmetic; noqa removal has no runtime effect; `Path.unlink()` is a drop-in replacement for `os.unlink()`; 119 tests green.
