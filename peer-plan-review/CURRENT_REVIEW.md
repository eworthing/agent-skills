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
Loop 7 of 10 (cap)

### System Flag
[STATE: HALT_STAGNATION]

---

## Contest Verdict
Good app, honest ceiling reached

Tests are green (119 passed). Production lint is clean. Loop 7 resolved F-007 subtractively: `README.md` lines 41–42 and 52 documented a test command (`cd scripts && python3 -m pytest test_run_review.py test_web_search.py`) that collected zero tests (`test_web_search.py` absent; `test_run_review.py` is a unittest shim), plus a stale count (118). The README now documents `python3 -m pytest scripts/tests/` with the correct count (119). The Residual Accounting Pass confirms all remaining score gaps (arch 7, domain 7, simplicity 6.5, framework_idioms 6.5) have irreducible or SPT-rejected residuals — no viable next action with positive expected score gain. HALT_STAGNATION is honest.

## Scorecard (1-10)

- **Architecture quality:** 7 | SAME | `run_review.py` orchestrates via `_common` (import-direction DAG, no cycles); registry dispatch at `run_review.py:409` (`PROVIDERS[reviewer]["build_cmd"](build_args, session_id)`); clean import DAG at `run_review.py:25-69`. This loop's change was README-only, so production architecture is unchanged. Residual blocking 10: `run_review()` is a 330-LoC coordinating function (`run_review.py:318-647`) with the two-attempt loop + codex-setup phases inline (F-005, carried Priority 2 — irreducible without ceremony; 9-anchor not met). Named accepted-irreducible per Residual Accounting Pass.
- **State management and runtime ownership:** 8 | SAME | `_active_proc` at `run_review.py:187` is module-level, written only inside `run_review()` (the attempt loop + finally), read by `_signal_handler()` at `:191`. Single-writer; idiomatic for signal-handler communication. Local resume state machine (`use_resume`, `fallback_used`, `session_id`) is function-scoped. No multi-writer hazard. Unchanged this loop. Residual: lifecycle authority (signal save/restore + resume-state locals) lives inside the one large `run_review()` function (tied to F-005); 9-anchor not fully met, honest 8.
- **Domain modeling:** 7 | SAME | CLI adapter domain is thin by design; the `PROVIDERS` registry (from `_common`) is the core model. `_build_session_data` (`run_review.py:265`) names the session-dict assembly in one place but it remains an untyped dict (no smart constructor). Session dict is post-mutated at `run_review.py:607-612` after `_build_session_data` returns, and consumed by `_common.session.save_session()` (vendored — off-limits). Unchanged this loop. Residual: no discriminated type for provider-specific output / session dict (`run_review.py:280`); TypedDict would add ceremony with no test strengthening; 9-anchor not met; CLI-adapter-thin context noted; honest 7.
- **Data flow and dependency design:** 8 | SAME | Clean DAG: `run_review.py` → `_common.*`. Re-exports at `run_review.py:46-69` (`# noqa: F401`) keep `mock.patch("run_review.X")` paths stable. The loop-5 helpers take explicit inputs / return explicit outputs. The `extract_metadata`/`extract_text_from_output` seam pre-reads `output_content` (`run_review.py:574-579`) to mitigate temporal coupling, with a comment. Unchanged this loop. Residual: a couple of ambient `os.environ` reads (`run_review.py:345`, `:212`); 9-anchor nearly met, idiomatic for a CLI adapter; honest 8.
- **Framework / platform best practices:** 6.5 | SAME | `python3 -m ruff check scripts/run_review.py scripts/check_web_search.py scripts/ppr_paths.py` → `All checks passed!` (production clean, held). Dimension stays 6.5 because test-file violations persist across the other test modules: F405 ×154 (star-import undefined-name from `from ._helpers import *`), RUF100 ×19, I001 ×7, E401 ×7 — **accepted residual** (test-only; the star-import pattern is a deliberate ergonomic choice; fixing means replacing star imports across 7 files = ceremony with no behavior change; SPT-rejected on Q2; `accepted_on: 2026-06-22`, `expires: 2026-12-22`). Logged as F-008 (accepted pattern, no priority fix this cycle).
- **Concurrency and runtime safety:** 8 | SAME | Single-threaded Python. Signal handlers saved/restored in try/finally (`run_review.py:392-395` set, `:632-635` restore); the save/restore and `_active_proc` set/clear ordering were untouched this loop. `subprocess.Popen` with `communicate(timeout=)` blocks correctly with a `TimeoutExpired` kill-tree path (`run_review.py:448-455`). Gemini/agy temp cleanup in finally. No threading races. Residual: the SIGTERM/SIGINT save-restore + `_active_proc` ordering is correct but verified by construction + the suite mocking `signal.signal`, not by a direct concurrency test; honest 8.
- **Code simplicity and clarity:** 6.5 | SAME | README fix is documentation-only — production simplicity unchanged: `run_review()` is still a 330-LoC coordinating function (`run_review.py:318-647`). The loop-5 phase extractions still stand. Residual: attempt-loop + codex-setup phases remain inline (F-005, re-derived from source as irreducible). Simplicity at 6.5 cannot honestly be promoted to a 9.5 accepted residual (9-anchor not met), so it sits at its earned score with the cohesive-core blocker named (Residual Accounting Pass).
- **Test strategy and regression resistance:** 8.5 | **UP** | F-007 resolved this loop — `README.md` now documents `python3 -m pytest scripts/tests/` (canonical command) with count 119. The "regression-discoverability gap" cited in the loop-6 test_strategy residual is cleared: a new contributor following the README will now find the real suite. 119 tests green (unchanged). Residual blocking 10: end-to-end coverage of the `run_review()` attempt loop is transitive via `test_execution_paths.py`; the contract-sync test (`TestArgContract`) now duplicates a structurally-guaranteed property (belt-and-suspenders, kept); honest 8.5.
- **Overall implementation credibility:** 8.5 | **UP** | README doc-rot resolved — the primary doc-vs-code credibility drain cited in loop-6 residuals is gone. The fix is genuinely subtractive (net −2 lines: dropped `test_web_search.py` reference, corrected `test_run_review.py` label to `tests/`, corrected count from 118 to 119, corrected command from `cd scripts && python3 -m pytest test_run_review.py test_web_search.py` to `python3 -m pytest scripts/tests/`). Production code, tests, lint state unchanged. Residual blocking 10: no new doc-vs-code gaps identified. Honest 8.5 — code-level credibility is solid; remaining score caps are architecture (7) and simplicity (6.5) from F-005, which are structural, not credibility items.

## Authority Map

- **Concern:** CLI arg contract
  - **Owner:** `run_review.py:parse_args()` (argparse definition, dest names, defaults)
  - **Allowed writers:** `run_review.py:parse_args()` only
  - **Observers / readers:** `run_review.run_review()` (production); `scripts/tests/_helpers.py:make_args()` **derives** from `parse_args()` (no longer an independent writer of the arg-name set)
  - **Persistence seam:** none
  - **Async mutation entry points:** none
  - **Verdict:** Single and clear (resolved loop 6) — `parse_args()` is now the sole source of truth for both the arg-name set AND the defaults. `make_args()` reads `parse_args()` under a saved/restored `sys.argv` and layers overrides; it can no longer drift.

- **Concern:** Active subprocess handle
  - **Owner:** module-level `_active_proc` at `run_review.py:187`
  - **Allowed writers:** `run_review.run_review()` (sets/clears inside the attempt loop + finally, both inline)
  - **Observers / readers:** `_signal_handler()` (reads at `run_review.py:191`)
  - **Persistence seam:** none
  - **Async mutation entry points:** SIGTERM / SIGINT via signal handler
  - **Verdict:** Single and clear — one writer, one reader, idiomatic Python signal-handler pattern. Unchanged this loop.

- **Concern:** Session state
  - **Owner:** session JSON file (written by `save_session()` from `_common.session`)
  - **Allowed writers:** `run_review.run_review()` via `save_session()` (session dict assembled by `_build_session_data` at `run_review.py:265`)
  - **Observers / readers:** `run_review.run_review()` via `load_session()`; tests read the file post-run
  - **Persistence seam:** JSON file at `args.session_file`
  - **Async mutation entry points:** none
  - **Verdict:** Single and clear — serialized via file; `run_review()` is sole writer per execution. Unchanged this loop.

## Strengths That Matter

- README now accurately describes the test layout: `python3 -m pytest scripts/tests/` with count 119 — the first-contact credibility drain is closed.
- CLI arg contract has a single source of truth: `scripts/tests/_helpers.py:make_args()` derives keys + defaults from `run_review.parse_args()` (`run_review.py:76-123`) rather than restating them, closing the drift class that consumed loop 1. The fix is net-subtractive (17 insertions / 23 deletions, loop 6).
- `run_review.py` cleanly delegates all provider-specific logic to `_common.providers.PROVIDERS`: command construction, cap flags, effort maps, session-id extraction. The orchestrator dispatches through the registry (`run_review.py:409`) without branching on provider internals.
- Gemini config-overlay isolation is behavioral and tested: the loop-5 helper `_setup_gemini_config` (`run_review.py:202`) excludes auto-saved policy files and preserves existing settings (`test_run_review_gemini_effort_overlay_excludes_auto_saved_policies` / `_preserves_existing_settings`).
- Resume/fallback state is tracked via local variables (`use_resume`, `fallback_used`) and never by mutating `args` (`run_review.py:326-328`); the snapshot is explicit, preventing cross-attempt contamination — and is the honest reason the attempt loop resists extraction (F-005).
- Codex per-run `CODEX_HOME` isolation fails closed: setup failure clears `session_id`/`use_resume` to force a fresh exec rather than resuming into a missing home (`run_review.py:383-385`).

## Findings

No new findings this loop. F-007 resolved. F-008 logged as accepted pattern (test-lint star-import; SPT-rejected Q2).

## Simplification Check

- **Structurally necessary:** F-007 fix passes SPT Q1–Q5: it fixes a real doc-vs-code rot (README documenting a zero-collecting test command actively misled readers), is the smallest honest fix (update two README blocks, drop the dead file reference, correct count), adds no new seam (documentation only), keeps runtime behavior honest (no code changed), and improves the product (new contributors can now find and run the suite).
- **New seam justified:** false — README-only change.
- **Helpful simplification:** dropping the `test_web_search.py` reference (it never existed as a pytest module) is subtractive; the updated command is shorter and correct.
- **Should NOT be done:** Do NOT fix F-005 (irreducible without ceremony). Do NOT fix test-lint F405 violations (star-import is deliberate test ergonomics; SPT-rejected Q2). Do NOT introduce TypedDict for session dict (ceremony, vendored consumer off-limits).
- **Tests after fix:** 119 tests pass (unchanged count). README change only — no test added, removed, or modified.

## Improvement Backlog

1. **Decompose `run_review()` flat body — residual phases (irreducible without ceremony)** (stable_id F-005 / structural / noticeable weakness) — **Priority 1 (promoted from P2 now that F-007 is resolved)**
   - Why it matters: after loop 5's three extractions, `run_review()` is 330 LoC. The remaining two-attempt resume/fresh subprocess loop and the per-run `CODEX_HOME` setup thread `use_resume`/`session_id`/`fallback_used`/`returncode` both into and out of any candidate helper (re-derived from source at `run_review.py:397-533` + `:386-389`), so extracting them adds ceremony and fails SPT.
   - Score impact: no clean score path — simplicity (6.5) and arch (7) cannot honestly reach a 9.5 accepted residual from here. The `CodexCapture` deepening candidate is the only remaining move (marginal win, non-trivial blast radius).
   - Kind: structural. Rank: helpful.
   - Status: **accepted-irreducible** — re-derived independently in loops 4, 5, 6, and 7. If it does not change, a future loop should formally retire it rather than re-derive.

2. **Test-lint star-import pattern (F-008)** — **accepted residual (no priority fix)**
   - Why it matters: `python3 -m ruff check scripts/tests/` → 187 errors: F405 ×154 / RUF100 ×19 / I001 ×7 / E401 ×7 across `scripts/tests/test_*.py` from `from ._helpers import *`.
   - SPT disposition: Q2 fails — replacing star imports across 7 test files is ceremony with no behavior change or test-coverage gain. Accepted as deliberate ergonomic pattern.
   - Score impact: caps `framework_idioms` at 6.5 until addressed or accepted-expiry (2026-12-22).
   - `accepted_on: 2026-06-22`, `expires: 2026-12-22`.

## Deepening Candidates

**Candidate: return a `CodexCapture` value type from the codex-setup phase** (derived from F-005)
- Candidate module: the inline codex `CODEX_HOME` setup block in `run_review()` (`run_review.py:368-389`).
- Source friction proven: F-005 — the block mutates `session_id`/`use_resume` inout on its fail-closed path (`run_review.py:383-385`), which is one of the two reasons `run_review()` resists extraction.
- Why the current shape is acceptable-but-improvable: converting the two inout locals to a returned frozen value (`CodexCapture(home, capture_enabled, sessions_before, clear_session)`) would let the caller apply `session_id = None`/`use_resume = False` explicitly, removing one inout pair.
- Behavior to move behind the deeper interface: per-run home reuse-or-create + capture-var derivation + the fail-closed clear decision.
- Dependency category: `in-process`
- Test surface after the change: same end-to-end tests in `test_execution_paths.py` (codex stale-events + last-message paths exercise this block transitively).
- Smallest first step: introduce `CodexCapture = namedtuple(...)`; have a helper return it; caller applies the clear when `clear_session` is set.
- What not to do: do not extract the two-attempt loop (4 inout locals — irreducible); do not add a protocol or class hierarchy.

## Builder Notes

1. **Residual Accounting Pass (loop 7)**
   - All dimensions below 9.5 have named residuals: arch (7) ← F-005 attempt-loop inline; state (8) ← tied to F-005; domain (7) ← untyped session dict (TypedDict adds ceremony, vendored consumer off-limits); framework_idioms (6.5) ← 187 test-lint violations (accepted residual, expires 2026-12-22); simplicity (6.5) ← run_review() flat body F-005; concurrency (8) ← signal handler verified by construction not by direct test; test_strategy (8.5) ← belt-and-suspenders contract test, attempt-loop coverage transitive only; credibility (8.5) ← no remaining doc-rot identified.
   - No viable next action with positive expected score gain exists for arch, domain, simplicity, or framework_idioms. HALT_STAGNATION is the honest signal.

2. **F-007 verification**
   - `ls scripts/test_web_search.py` → No such file (confirmed pre-fix).
   - `python3 -m pytest scripts/tests/` → 119 passed (confirmed pre- and post-fix).
   - README edit is minimal: dropped the dead `test_web_search.py` line, relabeled `test_run_review.py` to `tests/`, corrected count 118→119, replaced the `cd scripts && python3 -m pytest ...` command with `python3 -m pytest scripts/tests/`.
   - No code files, no test files, no lint state changed.

## Final Judge Narrative

Loop 7 resolved F-007 — the last queued finding in the Priority 1 slot. `README.md` lines 41–42 and 52 documented a test command (`cd scripts && python3 -m pytest test_run_review.py test_web_search.py`) that collected zero tests (verified), a non-existent file (`test_web_search.py` — confirmed `ls: No such file`), and a stale count (118 vs the real 119). The fix is subtractive: the `test_web_search.py` reference is deleted, `test_run_review.py  pytest suite (118 tests)` is replaced with `tests/  pytest suite (119 tests)`, and the command is replaced with `python3 -m pytest scripts/tests/`. The Residual Accounting Pass then ran independently. Every remaining score gap has a named, re-derived-this-loop residual: arch (7) and simplicity (6.5) are both blocked by F-005 (attempt-loop + codex-setup inline; three-loop-consecutive irreducibility verdict, no SPT-viable fix exists); domain (7) is blocked by the untyped session dict (TypedDict adds ceremony, and the consumer `save_session` is in vendored `_common`); framework_idioms (6.5) is blocked by 187 test-lint violations (accepted residual — star-import pattern is deliberate, SPT Q2 rejects ceremony replacement across 7 files). No viable next action exists that would move any dimension above its current ceiling. HALT_STAGNATION is correct and honest. `test_strategy` ticks 8→8.5 (the discoverability gap is closed) and `credibility` ticks 8→8.5 (doc-rot drain removed). The suite remains at 119 green; production lint remains clean.

## Loop 7 Result

Resolved F-007 (stable_id F-007) in `README.md`: dropped the stale `test_web_search.py` line, relabeled the `test_run_review.py` shim entry to `tests/`, corrected count from 118 to 119, replaced `cd scripts && python3 -m pytest test_run_review.py test_web_search.py` with `python3 -m pytest scripts/tests/`. Change is README-only (no script, no test, no lint state). **Evidence change is honest:** `python3 -m pytest scripts/tests/` → 119 passed (unchanged); `python3 -m ruff check scripts/run_review.py scripts/check_web_search.py scripts/ppr_paths.py` → `All checks passed!` (unchanged); `ls scripts/test_web_search.py` → `No such file` (confirms the deleted reference was dead). The fix is genuinely subtractive (net −2 lines: one deleted, one replaced with shorter text, one command line shortened). Finding F-007 (stable_id F-007) **resolved**. `test_strategy` 8→8.5 (discoverability gap cleared); `credibility` 8→8.5 (doc-rot drain removed). Residual Accounting Pass → HALT_STAGNATION: remaining gaps (arch 7, domain 7, simplicity 6.5, framework_idioms 6.5) all have irreducible or SPT-rejected residuals; no viable next action.

## Loop 7 Implementation Review

Verdict: **approved** (inline, `ran_inline: true`). All three checks passed:
- Reality: `python3 -m pytest scripts/tests/` → 119 passed (unchanged count post-edit); `python3 -m ruff check scripts/run_review.py scripts/check_web_search.py scripts/ppr_paths.py` → `All checks passed!` (production code untouched); README now documents `python3 -m pytest scripts/tests/` with count 119 and no reference to the non-existent `test_web_search.py`.
- Honesty: change is README-only and purely subtractive (one line deleted, labels and command corrected); no behavior changed; no new seam; no suppression-as-fix.
- Regression: no risk boundary crossed (README only — no isolation/signal/visibility/test change); 119 tests green; production lint clean; no new finding at equal-or-higher severity introduced.
