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
Loop 3 of 10 (cap)

### System Flag
[STATE: CONTINUE]

---

## Contest Verdict
Good app, but not top-tier yet

Tests are green (119 passed). Production code is functionally solid and cleanly separated from `_common`. Loop 3 added the parse_args/make_args contract-sync test, closing the authority split that caused loop 1's red suite. The remaining contest-grade drag is in production lint (I001/PTH108/RUF100 in `run_review.py`) and the `run_review()` 405-LoC complexity — neither is a disqualifier.

## Scorecard (1-10)

- **Architecture quality:** 7 | SAME | `run_review.py` orchestrates cleanly via `_common` (DAG enforced by import direction, no cycles). Seams are honest: provider behavior lives in `_common.providers.PROVIDERS`; dispatch logic in `run_review()`. No costume layers. But `run_review()` spans lines 201–605 (405 LoC, 67+ nested control-flow nodes per AST analysis) without sub-module boundaries — provider-specific setup, subprocess management, output extraction, and session persistence are a single flat function body.
- **State management and runtime ownership:** 8 | SAME | `_active_proc` at `run_review.py:187` is module-level, written only by `run_review()` (line 375, line 598), read by `_signal_handler()` (line 192). Single-writer; idiomatic for signal handler communication in Python. Local state machine (`use_resume`, `fallback_used`, `session_id`) scoped to the function. No multi-writer hazards.
- **Domain modeling:** 7 | SAME | CLI adapter domain is thin by design; `PROVIDERS` registry (from `_common`) is the core model. No impossible-state hazard at the schema level. `REVIEWER_ALIASES` dict (`run_review.py:73`) and the normalization at `parse_args():121-122` are clean.
- **Data flow and dependency design:** 8 | SAME | Clean DAG: `run_review.py` → `_common.*`. Re-exports at `run_review.py:36-69` (with `# noqa: F401 — re-exported for tests`) make `mock.patch("run_review.X")` paths stable. The `extract_metadata` / `extract_text_from_output` seam at `run_review.py:516–527` shows temporal coupling mitigated by pre-reading content at `run_review.py:501–510`; commenting explains it.
- **Framework / platform best practices:** 6 | SAME | Pre-existing PTH108 at `run_review.py:605` (`os.unlink` → `Path.unlink()`). Pre-existing I001 (unsorted imports) and RUF100 (unused noqa) in `run_review.py:27,36`. Test files retain E401 + I001 + RUF100 violations on their stdlib import lines, plus F405 warnings from star imports. These are carried forward as F-004.
- **Concurrency and runtime safety:** 8 | SAME | Single-threaded Python. Signal handling saves/restores prior handlers in try/finally (`run_review.py:322–325`, `run_review.py:598–602`). No threading races. `subprocess.Popen` with `communicate()` blocks correctly. Gemini and agy temp cleanup in finally block.
- **Code simplicity and clarity:** 6 | SAME | `run_review()` at 405 LoC with 67+ nested AST control-flow nodes is the primary complexity hit. The function interleaves provider-specific environment setup, subprocess dispatch and retry, metadata extraction, and session persistence as a single flat function body. Deletion test: removing any section breaks functionality, so the complexity earns its keep — but no sub-function structure to navigate concerns. Loop 3 change is purely additive (new test); simplicity score unchanged.
- **Test strategy and regression resistance:** 7.5 | UP | **Structural proof:** `scripts/tests/test_file_io_validation.py:TestArgContract.test_make_args_keys_match_parse_args_dests` (added this loop) — derives the canonical key set from `run_review.parse_args()` itself (via `sys.argv` patch) and asserts equality with `make_args()`'s key set. This test will catch the next CLI arg addition immediately. 119 tests green. The Authority Map CLI arg contract concern is now guarded mechanically; verdict moves from "Split and ambiguous" toward enforced. The remaining gap: `make_args()` dict still manually maintained (derivation candidate — deepening backlog); the sync test only detects drift, it does not prevent the two-step edit requirement.
- **Overall implementation credibility:** 7.5 | UP | **Structural proof:** F-003 resolved — the contract-sync test closes the recurrence risk that caused loop 1's build failure. Production code earns its architecture at the `_common` boundary. Remaining credibility drag: F-004 open (production lint violations) and `make_args()` dict still manually maintained (though now guarded by the new test).

## Authority Map

- **Concern:** CLI arg contract
  - **Owner:** `run_review.py:parse_args()` (argparse definition, dest names, defaults)
  - **Allowed writers:** `run_review.py:parse_args()` only
  - **Observers / readers:** `run_review.run_review()` (production), `scripts/tests/_helpers.py:make_args()` (test surrogate — manually maintained, now guarded by sync test)
  - **Persistence seam:** none
  - **Async mutation entry points:** none
  - **Verdict:** Split and ambiguous — two sources of truth for the arg-name set; `make_args()` can still drift (requires two-step edit), though drift is now detected immediately by `TestArgContract.test_make_args_keys_match_parse_args_dests`.

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
- CLI arg contract now guarded by `TestArgContract.test_make_args_keys_match_parse_args_dests` (`scripts/tests/test_file_io_validation.py:TestArgContract`) — the next arg addition to `parse_args()` surfaces in the suite immediately, preventing loop-1-class failures.

## Findings

### Finding #1: Ruff PTH108 + I001 + RUF100 violations in `run_review.py` — pre-existing, carried forward

**Why it matters** — `PTH108` at `run_review.py:605` signals `os.unlink()` should be `Path.unlink()` per pathlib idioms (ruff PTH rule set, which is active per `pyproject.toml`). `I001` at `run_review.py:27` means import blocks are unsorted. `RUF100` at `run_review.py:36` means the `noqa: F401` is unused (ruff now sees `_codex_session_files` etc. as used — the annotation is stale). These are all pre-existing.

**What is wrong** — `run_review.py:605`: `os.unlink(agy_log_path)` inside `contextlib.suppress(OSError)` should be `Path(agy_log_path).unlink()` per PTH108. `run_review.py:27–69`: import block ordering does not satisfy isort (I001). `run_review.py:36`: `# noqa: F401` directive is unused (RUF100) since the imported names are used within the module.

**Evidence** — `python3 -m ruff check scripts/run_review.py` → `PTH108` at `:605`; `I001` at `:27`; `RUF100` at `:36` — three violations, all auto-fixable.

**Architectural test failed** — n/a (style/idiom finding, not a seam finding)

**Dependency category** — `in-process`

**Leverage impact** — none

**Locality impact** — Minor: stale noqa at `:36` was documenting re-export intent that ruff now contradicts.

**Metric signal, if any** — ruff exit code 1; 3 violations in production module.

**Why this weakens submission** — Pre-existing lint violations in the production module reduce credibility; a submission where `ruff check` exits 1 on the primary source file is below contest-grade.

**Severity** — Cosmetic for contest

**ADR conflicts** — none

**Minimal correction path** — Fix `run_review.py:605`: replace `os.unlink(agy_log_path)` with `Path(agy_log_path).unlink()`. Remove the `# noqa: F401` at `:36` (ruff now sees those names as used). Run `ruff check --fix scripts/run_review.py` for I001 auto-fix.

**Blast radius** — Change: `scripts/run_review.py` (lines 36, 27–69 import block, 605). Avoid: all other files.

## Simplification Check

- **Structurally necessary:** Adding a contract-sync test passes SPT Q1 (fixes real ambiguity — prevents drift recurrence proved by loop 1) and Q2 (smallest honest fix — 7-line test class). No structural ceremony added.
- **New seam justified:** false — no new seam proposed.
- **Helpful simplification:** The sync test removes the drift hazard without changing any production code or test helper structure.
- **Should NOT be done:** Do not replace `make_args()` dict with a `parse_args()` invocation in this loop — that is the deepening candidate and belongs in a later loop. Do not split the test into multiple files.
- **Tests after fix:** 119 tests pass (1 new test added). No tests deleted.

## Improvement Backlog

1. **Fix PTH108 + I001 + RUF100 in `run_review.py`** (stable_id F-004 / simplification / helpful)
   - Why it matters: cleans production lint output; makes `ruff check scripts/run_review.py` exit 0.
   - Score impact: Framework/platform +0.5 (from 6 → 6.5); Overall credibility +0.5 (from 7.5 → 8).
   - Kind: simplification. Rank: helpful.

## Deepening Candidates

**Candidate: Derive `make_args()` from `parse_args([])` directly**
- Candidate module: `scripts/tests/_helpers.py:make_args()` function
- Source friction proven: Finding F-003 (now resolved) — `make_args()` manually copies arg names from `parse_args()` and drifted once (loop 1). The sync test (loop 3) detects drift but does not eliminate the two-step edit requirement.
- Why the current interface is shallow: `make_args()` is a hand-rolled dict that proxies `parse_args()`. It provides no behavior beyond the argparse defaults — it is equivalent to calling `parse_args([])` with overrides.
- Behavior to move behind the deeper interface: arg-name set derivation; default-value derivation.
- Dependency category: `in-process`
- Test surface after the change: same test files; `make_args()` call sites are unchanged in signature; internal implementation becomes `parse_args([])` invocation.
- Smallest first step: `def make_args(**overrides): import unittest.mock; with unittest.mock.patch("sys.argv", ["run_review.py"]): args = run_review.parse_args(); vars(args).update(overrides); return args`. This eliminates the dict entirely, and the sync test then becomes redundant (can be removed or kept as belt-and-suspenders).
- What not to do: do not add a new seam or protocol; do not change the test call sites.

## Builder Notes

1. **Pattern: manually-maintained arg contract mirror in test helper**
   - What appeared: `make_args()` manually copies CLI arg names from `parse_args()`. When `run_review.py` adds a new arg, `make_args()` silently diverges → `AttributeError` in tests.
   - How to recognize: grep test helpers for `argparse.Namespace(**{...})` — each is a potential drift bomb. The canonical hint is a comment like `# dest names mirror parse_args()`.
   - Smallest coding rule: add a contract-sync test that calls `parse_args([])` (via `sys.argv` patch) and asserts key equality with `make_args()`. If the dict drifts, the test fails immediately on the next run.
   - Stack example (Python): `TestArgContract.test_make_args_keys_match_parse_args_dests` in `test_file_io_validation.py` is the reference pattern. One `mock.patch("sys.argv", [...])` context; one `set()` comparison; informative diff message.

2. **Pattern: introspection test over manual contract mirror**
   - What appeared: Rather than adding a parallel assertion list (which would itself drift), the sync test derives the canonical key set from `run_review.parse_args()` itself — the sole authority. The test cannot drift from the source of truth because it IS reading the source of truth.
   - How to recognize: when a test asserts "X matches Y" and X could be derived from Y, derive X from Y instead of enumerating X manually.
   - Smallest coding rule: `set(vars(authoritative_function()).keys())` as the left side of the assertion; never a hard-coded set of string names.

3. **Scorecard humility check (Q9)**
   - Claim `test_strategy: 7.5` at `TestArgContract.test_make_args_keys_match_parse_args_dests` — uncertainty: I rated UP based on the contract-sync test. I have not walked every test file for authority-map gaps; there may be 1–2 additional surfaces not covered (e.g., `check_web_search.py` has its own test module not yet audited in depth for authority-map cross-check completeness). If a gap exists there, 7.5 is inflated.
   - Claim `credibility: 7.5` at F-003 resolved — uncertainty: The remaining drag (F-004 open, `make_args()` two-step edit risk) is real. I rounded up to 7.5 because the structural recurrence risk is closed. If the reviewer weighs the remaining manual dict differently, 7 would be defensible.
   - Claim `framework_idioms: 6` at `run_review.py:605` / `run_review.py:27,36` — uncertainty: These are all auto-fixable cosmetic violations. The score could be 6.5 since the test file violations are pre-existing infrastructure debt, not production code debt. I held at 6 because F-004 covers all three production violations.

## Final Judge Narrative

Loop 3 is the authority-split resolution loop. The contract-sync test (`TestArgContract.test_make_args_keys_match_parse_args_dests`) closes the recurrence class that consumed all of loop 1: any future arg addition to `parse_args()` now surfaces immediately in the suite without requiring a manual `make_args()` update. The change is purely additive (7 lines), passes SPT cleanly, and the 119-test suite is green. Test strategy moves to 7.5 and overall credibility to 7.5. The remaining backlog is F-004 (production lint — PTH108 + I001 + RUF100 in `run_review.py`), which is cosmetic but fixable in one pass. The deepening candidate (derive `make_args()` directly from `parse_args([])`, eliminating the dict entirely) is the loop-4 structural target if warranted by score dynamics.

## Loop 3 Result

Added `TestArgContract.test_make_args_keys_match_parse_args_dests` to `scripts/tests/test_file_io_validation.py`. The test patches `sys.argv` to `["run_review.py"]`, calls `run_review.parse_args()`, and asserts its key set equals `make_args()`'s key set. Derives the canonical truth from the argparse definition directly — cannot drift from `parse_args()` by construction. Re-ran full suite: **119 passed, 0 failed** (green, up from 118). Finding F-003 (stable_id F-003) **resolved**. Finding F-004 (stable_id F-004) **carried forward** to loop 4.
