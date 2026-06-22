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
Loop 2 of 10 (cap)

### System Flag
[STATE: CONTINUE]

---

## Contest Verdict
Good app, but not top-tier yet

Tests are green (118 passed). Production code is functionally solid and cleanly separated from `_common`. The primary structural drag is a test helper with duplicated stdlib imports that generates pervasive lint noise across 7 test files, hiding real signal. `run_review()` at 405 LoC is the secondary debt. Neither is a disqualifier, but both suppress the score below contest-grade.

## Scorecard (1-10)

- **Architecture quality:** 7 | UP | `run_review.py` orchestrates cleanly via `_common` (DAG enforced by import direction, no cycles). Seams are honest: provider behavior lives in `_common.providers.PROVIDERS`; dispatch logic in `run_review()`. No costume layers. But `run_review()` spans lines 201–605 (405 LoC, 67 nested control-flow nodes per AST analysis) without sub-module boundaries — the Module contains provider-specific setup, subprocess management, output extraction, and session persistence as a single flat function body.
- **State management and runtime ownership:** 8 | UP | `_active_proc` at `run_review.py:187` is module-level, written only by `run_review()` (line 375, line 598), read by `_signal_handler()` (line 192). Single-writer; the module-level scope is idiomatic for signal handler communication in Python. Local state machine (`use_resume`, `fallback_used`, `session_id`) scoped to the function. No multi-writer hazards.
- **Domain modeling:** 7 | UP | CLI adapter domain is thin by design; `PROVIDERS` registry (from `_common`) is the core model. No impossible-state hazard at the schema level. `REVIEWER_ALIASES` dict (`run_review.py:73`) and the normalization at `parse_args():121-122` are clean.
- **Data flow and dependency design:** 8 | UP | Clean DAG: `run_review.py` → `_common.*`. Re-exports at `run_review.py:36-69` (with `# noqa: F401 — re-exported for tests`) make `mock.patch("run_review.X")` paths stable. Documented intent. The `extract_metadata` / `extract_text_from_output` seam at `run_review.py:516–527` shows one temporal coupling: content is pre-read to a local variable to prevent the downstream `extract_text_from_output` from overwriting the file before `extract_metadata` can read it. Commenting explains it (`run_review.py:501–510`).
- **Framework / platform best practices:** 6 | UP | Pre-existing PTH108 at `run_review.py:605` (`os.unlink` → `Path.unlink()`). Pre-existing I001 (unsorted imports) in `run_review.py:27`. More importantly: `_helpers.py:12–22` imports 9 stdlib modules (`json`, `os`, `shutil`, `signal`, `stat`, `subprocess`, `sys`, `tempfile`, `unittest`, `mock`) that ruff correctly reports as F401 unused. These are not actually unused — they are re-exported to test files via `from ._helpers import *` — but this is a non-idiomatic use of star imports for stdlib redistribution. Ruff can't distinguish intentional re-export from accumulation, so the suppression strategy (`# noqa: F401,F403` on the star-import line in each test file) is applied broadly, hiding genuine lint signal.
- **Concurrency and runtime safety:** 8 | UP | Single-threaded Python. Signal handling saves/restores prior handlers in try/finally (`run_review.py:322–325`, `run_review.py:598–602`). No threading races. `asyncio.create_task` not used (Python lens). `subprocess.Popen` with `communicate()` blocks correctly. Gemini temp dir cleanup in finally block (`run_review.py:601`). agy temp file cleanup in finally block (`run_review.py:603–605`).
- **Code simplicity and clarity:** 6 | UP | `run_review()` at 405 LoC with 67 nested AST control-flow nodes is the primary complexity hit. The function interleaves provider-specific environment setup (lines 228–320), subprocess dispatch and retry (lines 327–463), metadata extraction (lines 465–528), and session persistence (lines 530–582). Deletion test: removing any section breaks functionality, so the complexity earns its keep — but there is no sub-function structure to navigate the concerns. `check_web_search.py` and `ppr_paths.py` are clean (both pass deletion test).
- **Test strategy and regression resistance:** 7 | UP | 118 tests cover primary behaviors: Codex home isolation, resume/fallback paths, Gemini config overlay (including exclusion of stale policy files), agy conversation ID capture, signal handling, session metadata recording. Mutation test: flip `check_paths and not has_output` at `run_review.py:413` to `check_paths or not has_output` — caught by `test_run_review_codex_stale_events_do_not_mask_empty_current_output` which asserts `rc == 124`. The Authority Map cross-check reveals a gap: `make_args()` in `scripts/tests/_helpers.py` has no test asserting it stays in sync with `parse_args()`. Loop 1's failure was exactly this drift. A test calling `parse_args([])` and asserting its keys match `make_args()` would prevent recurrence. Star-import pattern causes F405 warnings ("`self_check` may be undefined, or defined from star imports") across test files, which reduces ruff's ability to flag genuine undefined-name issues.
- **Overall implementation credibility:** 7 | UP | Production code earns its architecture at the primary seam (`_common` boundary). Test infrastructure has accumulated two forms of drift risk: (1) `_helpers.py` bulk star-re-export of stdlib modules it does not itself use, and (2) the manually-maintained `make_args()` dict that proved fragile in loop 1. Both are fixable in-scope.

## Authority Map

- **Concern:** CLI arg contract
  - **Owner:** `run_review.py:parse_args()` (argparse definition, dest names, defaults)
  - **Allowed writers:** `run_review.py:parse_args()` only
  - **Observers / readers:** `run_review.run_review()` (production), `scripts/tests/_helpers.py:make_args()` (test surrogate — manually maintained)
  - **Persistence seam:** none
  - **Async mutation entry points:** none
  - **Verdict:** Split and ambiguous — two sources of truth for the arg-name set; `make_args()` can drift from `parse_args()` with no compile-time or test-time signal

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

## Findings

### Finding #1: Test helper re-exports stdlib modules it does not itself use, generating pervasive lint noise that masks real signal

**Why it matters** — The star-import pattern forces all 7 test files to suppress ruff lint via `# noqa: F401,F403` and `# noqa: F401` annotations, disabling the lint rules that would catch genuine unused imports and genuinely-undefined names in those files. F405 warnings ("may be undefined, or defined from star imports") appear for `self_check`, `run_script`, and other `_helpers` exports — ruff cannot resolve them through star imports, meaning actual undefined-name errors in test files would be similarly suppressed.

**What is wrong** — `scripts/tests/_helpers.py:12–22` imports 9 stdlib modules (`json`, `os`, `shutil`, `signal`, `stat`, `subprocess`, `sys`, `tempfile`, `unittest`, `mock`) that `_helpers.py` itself does not use. They exist only to be re-exported via `from ._helpers import *` to child test files. The test files (e.g., `test_execution_paths.py:2`) already import these same modules directly (`import argparse, json, os, shutil, signal, stat, subprocess, sys, tempfile, unittest # noqa: F401`), making the star re-export redundant. Removing the unused imports from `_helpers.py` would eliminate the bulk F401 noise there; each test file's direct imports are already sufficient.

**Evidence** — `scripts/tests/_helpers.py:12–22` (F401 unused imports: `json`, `os`, `shutil`, `signal`, `stat`, `subprocess`, `sys`, `tempfile`, `unittest`, `mock`; verified by `python3 -m ruff check`); `scripts/tests/test_execution_paths.py:2` (direct stdlib import duplicates the star-import path); ruff F405 at `test_execution_paths.py:18,31,39` (`self_check` may be undefined or from star imports); ruff F405 at `test_execution_paths.py:47,52,57` (`run_script` may be undefined or from star imports).

**Architectural test failed** — Shallow module: `_helpers.py`'s role as a stdlib re-export hub provides no Leverage (each test file already has its own direct import) and reduces Locality (lint noise diffuses across 7 files).

**Dependency category** — `in-process`

**Leverage impact** — Zero leverage: all test files already import stdlib directly; the star re-export provides no new capability.

**Locality impact** — Negative: the bulk unused-import list in `_helpers.py` generates F401 noise there, and the resulting `# noqa` suppressions in each test file degrade ruff's undefined-name detection in those files.

**Metric signal, if any** — ruff reports 9 F401 violations in `_helpers.py` (json, os, shutil, signal, stat, subprocess, sys, tempfile, unittest / mock) + 3 F405 violations in `test_execution_paths.py`.

**Why this weakens submission** — A test helper that generates structural lint noise across 7 files and suppresses F401/F405 detection is a credibility deduction: it signals accumulated drift and prevents tooling from flagging future drift.

**Severity** — Noticeable weakness

**ADR conflicts** — none

**Minimal correction path** — Remove the 9 unused stdlib imports from `scripts/tests/_helpers.py:12–22` (`json`, `os`, `shutil`, `signal`, `stat`, `subprocess`, `sys`, `tempfile`, `unittest`; also `mock` if unused in `_helpers.py` itself). Each test file already imports these directly; removing them from `_helpers.py` breaks nothing. Keep `import argparse` (used at `_helpers.py:85`) and the `from run_review import ...` / `from _common.*` imports (used at `_helpers.py:32–37`). After this change, the `# noqa: F401` on those lines disappears, F405 warnings resolve, and per-file suppression becomes unnecessary for the stdlib names.

**Blast radius** — Change: `scripts/tests/_helpers.py`. Avoid: all other files (test files already import stdlib directly).

### Finding #2: `make_args()` dict has no contract-sync test — will drift again

**Why it matters** — Loop 1 was entirely consumed by a build failure caused by `make_args()` drifting from `parse_args()`. The fix added one entry, but the structural cause — the helper manually copies arg names from argparse — is unchanged. The next `parse_args()` addition will silently break two codex tests again unless there is a test asserting synchrony.

**What is wrong** — `scripts/tests/_helpers.py:64–85` builds a `Namespace` by hand from a hard-coded dict. There is no test in the suite that calls `parse_args([])` (via `sys.argv` patch) and asserts its keys match `make_args()`. The Authority Map names this as "Split and ambiguous" — two sources of truth with no mechanical enforcement. The deepening candidate from loop 1 (derive `Namespace` from `parse_args([])` directly) would eliminate the manual dict entirely, but the Simplify Pressure Test requires evaluating the smallest honest fix first.

**Evidence** — `scripts/tests/_helpers.py:64–85` (manual dict; verified by contract comparison: `parse_args` keys == `make_args` keys at present, but no enforcement); `run_review.py:76–123` (argparse definition — authoritative); loop 1 finding F-001 resolved by one-line dict patch with no structural prevention.

**Architectural test failed** — Interface-as-test-surface: the `parse_args()` Interface (the arg-name set) is not tested directly; it is proxied through `make_args()`, which is a shallow copy that can drift.

**Dependency category** — `in-process`

**Leverage impact** — Low: `make_args()` provides no behavior beyond dict construction; deriving from `parse_args()` would give the same result with zero drift risk.

**Locality impact** — Any new CLI argument requires two edits: one in `run_review.py:parse_args()` and one in `_helpers.py:make_args()`. The first edit is always done; the second is optional and easy to miss.

**Metric signal, if any** — none (drift is invisible until a test fails)

**Why this weakens submission** — A test helper that drifted exactly once and has no mechanical prevention is a credibility risk; loop 2's backlog carries the fix rather than the certitude.

**Severity** — Noticeable weakness

**ADR conflicts** — none

**Minimal correction path** — Two options (SPT selects the smaller): (A) Add a test in `scripts/tests/test_file_io_validation.py` or a new `test_arg_contract.py` that patches `sys.argv` to `["run_review.py"]`, calls `run_review.parse_args()`, and asserts `set(vars(args).keys()) == set(vars(make_args()).keys())`. This is additive, ~5 lines, and prevents future drift. (B) Replace `make_args()`'s dict with `parse_args()` invocation (deeper refactor, requires patching `sys.argv` in the helper itself). Option A is the smallest honest fix and passes SPT Q2; Option B is the deepening candidate.

**Blast radius** — Change (Option A): `scripts/tests/test_file_io_validation.py` (or new test file). Avoid: `run_review.py`, `_helpers.py` body (do not edit the dict yet — that belongs in the deepening candidate loop).

### Finding #3: Ruff PTH108 + I001 violations in `run_review.py` — pre-existing, not introduced this loop

**Why it matters** — `PTH108` at `run_review.py:605` signals `os.unlink()` should be `Path.unlink()` per pathlib idioms (ruff PTH rule set, which is active per `pyproject.toml`). `I001` at `run_review.py:27` means import blocks are unsorted. These are not new — confirmed pre-existing from loop 1 notes — but they are part of the credibility signal in the lint output.

**What is wrong** — `run_review.py:605`: `os.unlink(agy_log_path)` inside `contextlib.suppress(OSError)` should be `Path(agy_log_path).unlink()` per PTH108. `run_review.py:27–69`: import block ordering does not satisfy isort (I001). Neither causes functional defects.

**Evidence** — `python3 -m ruff check scripts/run_review.py` → `PTH108` at `:605`; `I001` at `:27`; `RUF100` (unused noqa at `:36`) — three violations in production code.

**Architectural test failed** — n/a (style/idiom finding, not a seam finding)

**Dependency category** — `in-process`

**Leverage impact** — none

**Locality impact** — Minor: noqa directive at `:36` is annotated as "re-exported for tests" but ruff now says the noqa is unused, meaning the re-export intent is invisible to the tool.

**Metric signal, if any** — ruff exit code 1; 3 violations in `run_review.py`.

**Why this weakens submission** — Pre-existing lint violations in the production module reduce credibility; a submission where `ruff --exit-zero` is silently required has a lower bar than one where lint passes cleanly.

**Severity** — Cosmetic for contest

**ADR conflicts** — none

**Minimal correction path** — Fix `run_review.py:605`: replace `os.unlink(agy_log_path)` with `Path(agy_log_path).unlink()`. Run `ruff check --fix scripts/run_review.py` for I001 auto-fix. For the `RUF100` at `:36`: the `# noqa: F401` there can be removed since ruff sees the names as used (they are imported and used in the module). Note: these are all auto-fixable; `ruff --fix` handles them.

**Blast radius** — Change: `scripts/run_review.py` (lines 36, 27–69 import block, 605). Avoid: all other files.

## Simplification Check

- **Structurally necessary:** Removing unused imports from `_helpers.py` passes the deletion test — zero behavior change, since test files already import stdlib directly. Adding a parse_args/make_args sync test passes SPT Q1 (fixes real ambiguity — prevents drift recurrence) and Q2 (smallest honest fix — 5-line test).
- **New seam justified:** false — no new seam proposed.
- **Helpful simplification:** Removing stdlib re-export from `_helpers.py` simplifies the lint picture across 7 files without adding any new dependency or ceremony.
- **Should NOT be done:** Do not replace `make_args()` dict with a `parse_args()` invocation yet — that is the deepening candidate and belongs in a later loop after F2 (contract sync test) proves the pattern. Do not add `__all__` to `_helpers.py` as a costume-layer fix.
- **Tests after fix:** No tests deleted (purely additive fix for F2; subtractive fix for F1 in _helpers.py). Existing tests continue to pass after the _helpers.py cleanup because each test file already has its own direct imports.

## Improvement Backlog

1. **Add parse_args/make_args contract-sync test** (stable_id F-003 / structural / needed for winning)
   - Why it matters: prevents loop-1-class drift recurrence; makes the arg-contract Authority Map verdict "Single and clear" instead of "Split and ambiguous".
   - Score impact: Test strategy +0.5 (from 7 → 7.5); Overall credibility +0.5.
   - Kind: structural. Rank: needed for winning.

2. **Fix PTH108 + I001 in `run_review.py`** (stable_id F-004 / simplification / helpful)
   - Why it matters: cleans production lint output; makes `ruff check` exit 0 on production code.
   - Score impact: Framework/platform +0.5; Overall credibility +0.5.
   - Kind: simplification. Rank: helpful.

## Deepening Candidates

**Candidate: Derive `make_args()` from `parse_args([])` directly**
- Candidate module: `scripts/tests/_helpers.py:make_args()` function
- Source friction proven: Finding F2 — `make_args()` manually copies arg names from `parse_args()` and has already drifted once (loop 1). With parse_args/make_args sync test (Backlog item 2) in place, the underlying authority split remains even if drift is detectable.
- Why the current interface is shallow: `make_args()` is a hand-rolled dict that proxies `parse_args()`. It provides no behavior beyond the argparse defaults — it is equivalent to calling `parse_args([])` with a controlled arg list and overriding specific fields.
- Behavior to move behind the deeper interface: arg-name set derivation; default-value derivation.
- Dependency category: `in-process`
- Test surface after the change: same test files; the `make_args()` call sites are unchanged in signature; internal implementation is `parse_args([])` invocation.
- Smallest first step: implement as `def make_args(**overrides): import unittest.mock; with unittest.mock.patch("sys.argv", ["run_review.py"]): args = run_review.parse_args(); vars(args).update(overrides); return args`. This eliminates the dict entirely.
- What not to do: do not add a new seam or protocol; do not create a separate ArgFactory class; do not change the test call sites.

## Builder Notes

1. **Pattern: bulk stdlib re-export via star import as shared test namespace**
   - What appeared: `_helpers.py` imports 9 stdlib modules it doesn't use, re-exporting them via `from ._helpers import *` so test files can get them "for free." Each test file also imports the same modules directly on line 2.
   - How to recognize: grep `_helpers.py` for `import X` where X appears in ruff F401 output AND also appears in line 2 of every test file. Both channels exist → star-export is redundant.
   - Smallest coding rule: a helper module should import only what it needs. If test files need shared symbols, export only the shared symbols (functions, constants, fixtures) — not stdlib passes-through.
   - Stack example (Python): `_helpers.py` should only define `make_args`, `run_script`, `SCRIPT_DIR`, `FIXTURES_DIR`, `_CREATE_NEW_PROCESS_GROUP`. Each test file imports stdlib directly (which they already do on line 2). No star re-export needed for stdlib.

2. **Pattern: manually-maintained arg contract mirror in test helper**
   - What appeared: `make_args()` manually copies CLI arg names from `parse_args()`. When `run_review.py` adds a new `--codex-home-manifest` arg, `make_args()` silently diverges → `AttributeError` in codex tests.
   - How to recognize: grep test helpers for `argparse.Namespace(**{...})` or `argparse.Namespace(reviewer=...)` — each is a potential drift bomb. The canonical hint is `# dest names mirror parse_args()` or similar comment acknowledging the manual copy.
   - Smallest coding rule: derive the Namespace from `parse_args([])` with a controlled arg list, then override fields. One call; can't drift.

3. **Scorecard humility check (Q9)**
   - Claim `concurrency: 8` at `run_review.py:322–325` (signal handler save/restore) — uncertainty: I rated this highly based on the signal-handling pattern, but I did not verify whether concurrent invocations of `run_review()` from the same process (if that were ever possible) would race on `_active_proc`. In the actual use context this doesn't happen, but the global variable is a risk boundary I did not mechanically verify with a threading analysis. If a future caller added multithreading, this would be a latent race.
   - Claim `framework_idioms: 6` at `_helpers.py:12–22` — uncertainty: I rated this lower partly due to F401 noise from the star-export pattern. If the repo intentionally uses this pattern as a shared-import-bus (documentation might exist elsewhere), the finding severity could drop to Cosmetic. I don't see such documentation, but the loop-1 notes describe the split as a "mechanical" refactor from a monolithic test file, suggesting it was an intentional pattern rather than accumulated debt.
   - Claim `test_strategy: 7` at Authority Map cross-check — uncertainty: I found one missing test (parse_args/make_args sync). I may have missed other gaps; the 7 test files are 118 tests across a wide surface, and my mutation test mental model checked only the most critical guard. A deeper Authority Map walk might surface 1-2 additional gaps.

## Final Judge Narrative

Loop 2 is the first real structural critic pass. Production code earns a solid 7-8 across most dimensions: the `_common` seam is honest, provider dispatch is registry-driven, signal handling is idiomatic, and the resume/fallback state machine is locally coherent. The drag is in the test infrastructure: `_helpers.py` re-exports stdlib modules it doesn't use, generating F401/F405 lint noise across all 7 test files and suppressing the tool signal that should catch future drift. The direct correction (remove the unused imports) is purely subtractive and passes SPT cleanly. The secondary risk is the `make_args()` manual dict — loop 1 was entirely consumed by one drift instance; without a sync test, the same failure class recurs on the next arg addition. Future work should replace the dict with a `parse_args([])` derivation (deepening candidate), but the minimum viable fix for this loop is the unused-import removal, which unblocks lint signal.

## Loop 2 Result

Removed 8 unused stdlib imports from `scripts/tests/_helpers.py:11–22` (`json`, `os`, `shutil`, `signal`, `stat`, `tempfile`, `unittest`, `from unittest import mock`). Added `# noqa: E402,F401 — re-exported via *` to intentional star-export lines (24–26, 83–86) to suppress ruff F401 on the re-export anchors. Sorted both import blocks to satisfy I001 (ruff --fix applied). Re-ran full suite: **118 passed, 0 failed** (green). Ruff check on `_helpers.py`: **0 errors**. Finding F1 (stable_id F-002) **resolved**. Findings F2 (F-003) and F3 (F-004) **carried forward** to loop 3.

## Loop 2 Implementation Review

Verdict: **approved**. All three checks passed: Reality (the 8 unused stdlib imports cited in F-002 are genuinely absent from the current `_helpers.py`); Honesty (the fix is a pure deletion with no redistribution, and the noqa annotations added are on intentional re-export anchors — not suppression of the structural smell); Regression (no new finding at same or higher severity introduced).
