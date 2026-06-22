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
Loop 5 of 10 (cap)

### System Flag
[STATE: CONTINUE]

---

## Contest Verdict
Good app, but not top-tier yet

Tests are green (119 passed). Production lint is clean (`ruff check scripts/run_review.py` exits 0). Loop 5 partially resolved F-005: extracted the three genuinely self-contained phases of `run_review()` into named module-level helpers (`_setup_gemini_config`, `_build_stdin`, `_build_session_data`), dropping the function body from ~405 to 328 lines. The two largest phases (the two-attempt resume/fresh subprocess loop, and the codex-home setup that mutates `session_id`/`use_resume`) were left inline because extracting them fails the Simplify Pressure Test honesty bar (5+ mutable locals threaded in+out adds ceremony). The remaining flat-but-cohesive body is the honest state; this is the contest-grade ceiling for this dimension without a costume layer.

## Scorecard (1-10)

- **Architecture quality:** 7 | SAME | `run_review.py` orchestrates cleanly via `_common` (DAG enforced by import direction, no cycles). Seams are honest: provider behavior lives in `_common.providers.PROVIDERS`; dispatch logic in `run_review()`. No costume layers. The three extracted phase helpers (`run_review.py:202` `_setup_gemini_config`, `:249` `_build_stdin`, `:265` `_build_session_data`) improve Locality without adding interfaces. The residual: the attempt-loop phase remains inline (it cannot extract honestly — see Finding #1), so the function-level "module" is still larger than a 9-anchor structure. Structural proof (unchanged seam): `run_review.py:457` (`PROVIDERS[reviewer]["build_cmd"](build_args, session_id)` — registry dispatch); `run_review.py:25-69` (clean import DAG).
- **State management and runtime ownership:** 8 | SAME | `_active_proc` at `run_review.py:187` is module-level, written only by `run_review()`, read by `_signal_handler()` (line 192). Single-writer; idiomatic for signal-handler communication in Python. The extractions preserved this exactly: the attempt loop (sole writer of `_active_proc`) was deliberately left inline. Local state machine (`use_resume`, `fallback_used`, `session_id`) scoped to the function. No multi-writer hazards.
- **Domain modeling:** 7 | SAME | CLI adapter domain is thin by design; `PROVIDERS` registry (from `_common`) is the core model. No impossible-state hazard at the schema level. `_build_session_data` (`run_review.py:265`) now names the session-dict assembly as one place, but it remains an untyped dict (no smart constructor). Residual: no discriminated type for provider-specific output / session — accepted as residual (CLI adapter thin-by-design).
- **Data flow and dependency design:** 8 | SAME | Clean DAG: `run_review.py` → `_common.*`. Re-exports at `run_review.py:46-69` (with `# noqa: F401`) keep `mock.patch("run_review.X")` paths stable. The extracted helpers take explicit inputs and return explicit outputs (`_setup_gemini_config(args, env) -> str|None` mutates only the shared `env` accumulator by design; `_build_session_data(...)` is pure). The `extract_metadata` / `extract_text_from_output` seam still pre-reads `output_content` to mitigate temporal coupling; commenting explains it.
- **Framework / platform best practices:** 6.5 | SAME | `python3 -m ruff check scripts/run_review.py` → `All checks passed!` (held from loop 4). Production module has zero ruff violations after the extraction. The smaller composed functions are more idiomatic Python than the prior flat body, but the dimension stays at 6.5 because the test-file violations (E401 + I001 + RUF100 on stdlib import lines; F405 from star imports in `_helpers.py`) remain as pre-existing infrastructure debt — accepted residual, test-only.
- **Concurrency and runtime safety:** 8 | SAME | Single-threaded Python. Signal handling saves/restores prior handlers in try/finally; the save/restore and the `_active_proc` set/clear ordering were untouched by the extractions (the attempt loop was left inline precisely to preserve them). No threading races. `subprocess.Popen` with `communicate()` blocks correctly. Gemini and agy temp cleanup in finally block.
- **Code simplicity and clarity:** 6.5 | UP | **Structural proof:** `run_review()` body dropped from ~405 LoC (loop 4, `git show d1bdfb4:peer-plan-review/scripts/run_review.py`) to 328 LoC this loop; three cohesive phases now read as named helpers (`_setup_gemini_config` at `run_review.py:202`, `_build_stdin` at `:249`, `_build_session_data` at `:265`). A reader understands each extracted phase from its name+signature without reading the whole body. Residual blocking higher: the attempt-loop + codex-capture phases stay inline (honest SPT downgrade — extracting them threads 4–5 mutable locals in+out, adding ceremony). Queued as F-005 (carried).
- **Test strategy and regression resistance:** 7.5 | SAME | `TestArgContract.test_make_args_keys_match_parse_args_dests` guards the arg-contract. 119 tests green — the extracted helpers are reached transitively through the existing end-to-end tests in `test_execution_paths.py` (gemini overlay, stdin pipe, agy preamble, session persistence). No new test files needed (Indirect Interface coverage carve-out; see Loop 5 Result). Remaining gap: `make_args()` dict still manually maintained (guarded by sync test, two-step edit). Carried as F-006.
- **Overall implementation credibility:** 8 | SAME | The code earns its architecture: extractions are honest (no costume layer), the SPT downgrade is recorded rather than papered over with shallow `_part1()/_part2()` splits. The orchestrator-registry pattern, signal safety, and session isolation remain well-tested. Remaining credibility drag: the attempt-loop phase is still inline (irreducible without ceremony) and `make_args()` dict is still manually maintained (guarded but two-step).

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
  - **Allowed writers:** `run_review.run_review()` (sets/clears inside the function body; the attempt loop and finally block, both left inline this loop)
  - **Observers / readers:** `_signal_handler()` (reads at :192)
  - **Persistence seam:** none
  - **Async mutation entry points:** SIGTERM / SIGINT via signal handler
  - **Verdict:** Single and clear — one writer, one reader, idiomatic Python signal-handler pattern. The single-writer invariant is preserved this loop because the writing block was not extracted.

- **Concern:** Session state
  - **Owner:** session JSON file (written by `save_session()` from `_common.session`)
  - **Allowed writers:** `run_review.run_review()` via `save_session()` (session dict assembled by `_build_session_data` at :265, written by the caller)
  - **Observers / readers:** `run_review.run_review()` via `load_session()`; tests read the file post-run
  - **Persistence seam:** JSON file at `args.session_file`
  - **Async mutation entry points:** none
  - **Verdict:** Single and clear — serialized via file; run_review() is the sole writer per execution. `_build_session_data` is pure assembly (no I/O), so the single-writer property holds.

## Strengths That Matter

- `run_review.py` cleanly delegates all provider-specific logic to `_common.providers.PROVIDERS`: command construction, cap flags, effort maps, session ID extraction. The orchestrator doesn't branch on provider internals — it dispatches through the registry (`run_review.py:457`, `PROVIDERS[reviewer]["build_cmd"](build_args, session_id)`).
- Gemini config-overlay isolation is behavioral and tested: the temp dir excludes auto-saved policy files (verified by `test_run_review_gemini_effort_overlay_excludes_auto_saved_policies`), preserves existing settings (verified by `test_run_review_gemini_effort_overlay_preserves_existing_settings`). After this loop the logic lives in one named helper (`_setup_gemini_config`), unchanged in behavior.
- Resume/fallback state tracked via local variables (`use_resume`, `fallback_used`), never by mutating `args`. The snapshot is explicit and prevents accidental cross-attempt contamination — and is the reason the attempt loop resists honest extraction (those locals are read after the loop).
- The SPT honesty bar was applied as a gate, not a formality: two phases that would have produced ceremony-laden helpers (5+ inout locals) were left inline with the reasoning recorded, instead of shallow `_part1()/_part2()` splits that relocate lines without improving Locality.
- CLI arg contract guarded by `TestArgContract.test_make_args_keys_match_parse_args_dests` — the next arg addition to `parse_args()` surfaces in the suite immediately.

## Findings

### Finding #1: `run_review()` attempt-loop + codex-capture phases remain inline (irreducible without ceremony)

**Why it matters** — After this loop's three extractions, `run_review()` is 328 lines (down from ~405). The two largest remaining phases are the two-attempt resume/fresh subprocess loop (`run_review.py` ~445–581) and the per-run Codex `CODEX_HOME` setup (~411–437). Both are cohesive concerns a reader would prefer to grasp by name. They are not extracted because doing so honestly would require threading 4–5 mutable locals both into and out of the helper.

**What is wrong** — The attempt loop reads and mutates `use_resume`, `session_id`, `fallback_used`, and `returncode` across iterations, and those values are read again after the loop (session-id capture reads `session_id`; `_build_session_data` reads `fallback_used`). The codex-setup block mutates `session_id` and `use_resume` on its fail-closed path and produces `codex_home` + two capture vars. Extracting either as a helper means a 4-tuple return plus 6+ parameters — ceremony that fails Simplify Pressure Test Q2 (smallest honest fix) and Q3 (no duplicate layer / no added indirection).

**Evidence** — `run_review.py` attempt loop body threads `use_resume`/`session_id`/`fallback_used` mutably (the resume-fallback branch sets `use_resume = False; session_id = None; fallback_used = True; continue`), and post-loop code at the session-id capture + `_build_session_data` call sites reads those same locals. Per the contest directive's HONESTY BAR and `method.md` Simplify Pressure Test fake-clean anti-examples, a split that just renames region comments into shallow helpers is fake simplification and is rejected.

**Architectural test failed** — Shallow module test (a `_run_attempt(...)` helper with 6 inputs + a 4-tuple output would have Interface ≈ Implementation — no Depth, only relocation). The deletion test on such a helper would *pass* (it would be a pass-through of mutable state), which is the signal to NOT create it.

**Dependency category** — `in-process`

**Leverage impact** — Low: callers invoke `run_review()` cleanly; the residual flat region is internal.

**Locality impact** — Moderate: the attempt-loop and codex-setup phases must still be read in the function body rather than understood from a signature.

**Why this weakens submission** — A perfect 9-anchor would have every cohesive phase behind a named helper. The honest finding is that these two phases *cannot* reach that bar without adding ceremony — so the dimension is held at 6.5/7 rather than inflated. This is the contest-grade ceiling for the dimension absent a costume layer.

**Severity** — Noticeable weakness

**ADR conflicts** — none

**Minimal correction path** — Either accept the inline phases as the honest state (recommended — they earn their inline placement per the deletion test), OR, if a future loop wants the codex-setup phase behind a helper, return a small frozen result type (`CodexCapture(home, capture_enabled, sessions_before, clear_session)`) and have the caller apply the `session_id = None; use_resume = False` clear, converting one inout pair to a value return. That is a marginal win, not a clear one; defer unless re-prioritized.

**Blast radius** — Change (if pursued): `scripts/run_review.py` only. Avoid: all other files, `_common/**`.

## Simplification Check

- **Structurally necessary:** The three extractions (`_setup_gemini_config`, `_build_stdin`, `_build_session_data`) pass SPT Q1–Q5: each fixes real low-Locality (a cohesive phase was inlined), is the smallest honest fix (a single named helper with explicit inputs→outputs), adds no duplicate layer (module-internal privates, not new interfaces), keeps runtime behavior identical (119 tests green, same count), and improves the product (a reader navigates by name).
- **New seam justified:** false — no new seam proposed; the helpers are module-internal, reached only by `run_review()`.
- **Helpful simplification:** the gemini-overlay phase (~40 lines) and the 25-field session-dict assembly are the two highest-payoff extractions; `_build_stdin` is small but removes an `if`-nest from the body.
- **Should NOT be done:** Do not extract the attempt loop or codex-setup into helpers (fails the SPT honesty bar — 4–5 inout locals). Do not touch test files. Do not pursue F-006 as "delete the dict" — it is not pure-subtractive (see backlog note).
- **Tests after fix:** 119 tests pass (same count). No tests added or deleted; extracted helpers covered transitively (Indirect Interface coverage carve-out).

## Improvement Backlog

1. **Decompose `run_review()` flat body — residual phases** (stable_id F-005 / structural / noticeable weakness) — **carried forward (partial this loop)**
   - Why it matters: three cohesive phases were extracted this loop (simplicity 6→6.5); the attempt-loop + codex-setup phases remain inline because honest extraction adds ceremony.
   - Score impact: simplicity already +0.5 (6→6.5) this loop; further movement requires either accepting the inline phases (promote to accepted residual) or the marginal `CodexCapture` value-return.
   - Kind: structural. Rank: helpful (the cheap wins are taken; remainder is at the honesty ceiling).

2. **Derive `make_args()` from `parse_args([])` directly** (stable_id F-006 / simplification / helpful) — **carried forward**
   - Why it matters: would eliminate the two-step edit requirement on arg changes.
   - **Not pure-subtractive (correction to prior loop framing):** `parse_args()` takes no argv parameter and calls `p.parse_args()` reading `sys.argv`; deriving defaults requires either adding an argv param to `parse_args` or `mock.patch("sys.argv", ...)`. More important, `make_args()` defaults `reviewer="claude"` (a *test* convenience) whereas `parse_args([])` yields `reviewer=None` — so the swap changes the test default and fails SPT Q4 (behavior change) unless every call site that relies on the implicit claude default is updated. The loop-3 sync test already detects drift; deleting the dict is a marginal win with non-trivial blast radius.
   - Score impact: test_strategy +0.5 (7.5→8) if done cleanly. Kind: simplification. Rank: helpful (lower priority given the not-pure-subtractive correction).

## Deepening Candidates

**Candidate: return a `CodexCapture` value type from the codex-setup phase** (derived from Finding #1)
- Candidate module: the inline codex `CODEX_HOME` setup block in `run_review()`.
- Source friction proven: Finding #1 — the block mutates `session_id`/`use_resume` inout, which is why it resisted extraction this loop.
- Why the current shape is acceptable-but-improvable: inout mutation of two locals is the only thing blocking a clean extraction; converting to a value return removes it.
- Behavior to move behind the deeper interface: per-run home reuse-or-create + capture-var derivation + the fail-closed clear decision.
- Dependency category: `in-process`
- Test surface after the change: same end-to-end tests in `test_execution_paths.py` (codex stale-events + last-message paths already exercise this block transitively).
- Smallest first step: introduce `CodexCapture = namedtuple(...)`; have the helper return it; caller applies `session_id = None; use_resume = False` when `clear_session` is set.
- What not to do: do not extract the two-attempt loop (4 inout locals — irreducible); do not add a protocol or class hierarchy.

## Builder Notes

1. **SPT honesty bar as an extraction gate**
   - What appeared: `run_review()` had ~6 candidate phases. Three (gemini overlay, stdin prep, session-dict assembly) had clean inputs→outputs; three (attempt loop, codex setup, multi-input session-id capture) threaded mutable locals in+out.
   - Correct action: extract only the clean-boundary phases. For the rest, record the inout-threading count as the rejection reason. A `_run_attempt()` taking 6 params and returning a 4-tuple is line-relocation, not Locality — its deletion test *passes*, which is the tell that it's a pass-through.
   - Recognition rule: if a candidate helper needs 5+ mutable locals both in and out, leave the phase inline and note why.

2. **Indirect Interface coverage carve-out for private helpers**
   - What appeared: three new module-level privates (`_setup_gemini_config`, `_build_stdin`, `_build_session_data`) with no new test files.
   - Why no new tests: they are reached only through `run_review()`, whose end-to-end tests in `test_execution_paths.py` already assert the behavior — `test_run_review_gemini_effort_overlay_preserves_existing_settings` (asserts the overlay settings.json + `popen_env["GEMINI_CONFIG_DIR"]`), `test_run_review_gemini_pipes_prompt_via_stdin` (asserts stdin payload), `test_agy_prepends_readonly_preamble_to_prompt` (asserts the agy preamble), and every test reading back `session.json` (asserts `_build_session_data` output). Each assertion would fail if the corresponding helper body were replaced with a no-op.
   - Rule: private helpers transitively covered by already-green Interface tests need no new test files (carve-out); do not delete the existing tests.

3. **Scorecard humility check (Q9)**
   - Claim `simplicity: 6.5` (UP) at `run_review.py:202/249/265` — uncertainty: a stricter reviewer could argue the win is modest (77 lines moved, function still 328 LoC) and hold at 6. Scored 6.5 because the three extractions are genuine named-phase wins with explicit signatures, proven by the LoC drop against `d1bdfb4`.
   - Claim `architecture: 7` (SAME) — uncertainty: one could argue the extractions nudge it to 7.5. Held at 7 because the dominant structural fact (a 328-line coordinating function with two inline cohesive phases) is unchanged in kind; only `simplicity` earned the delta.
   - Claim Finding #1 "irreducible without ceremony" — uncertainty: the `CodexCapture` value-return is a real (if marginal) path, so "irreducible" is slightly strong for the codex block specifically; the attempt loop genuinely is irreducible. Recorded as a deepening candidate rather than asserting impossibility.

## Final Judge Narrative

Loop 5 is the honest-partial decomposition of F-005. Three cohesive phases of `run_review()` — the Gemini config overlay (`_setup_gemini_config`), the stdin prompt prep (`_build_stdin`), and the 25-field session-dict assembly (`_build_session_data`) — are extracted into named module-level helpers, dropping the function body from ~405 to 328 lines and moving `simplicity` from 6 to 6.5. The decisive judgment was *what not to extract*: the two-attempt resume/fresh subprocess loop and the per-run `CODEX_HOME` setup thread 4–5 mutable locals (`use_resume`, `session_id`, `fallback_used`, `returncode`) both into and out of any candidate helper, so extracting them would add ceremony and fail the Simplify Pressure Test — they are left inline with the rejection recorded, not papered over with shallow `_part1()/_part2()` splits. This also preserves the risk-boundary invariants the directive named: `_active_proc`'s single writer, the SIGTERM/SIGINT save/restore ordering, `env` isolation, and resume/fresh semantics all live in the un-extracted attempt loop and finally block, so the green 119-test suite is direct evidence they held. F-005 is carried forward (cheap wins taken; remainder at the honesty ceiling). F-006 is carried with a correction: it is not the "pure subtractive dict deletion" prior loops assumed — `parse_args([])` flips the test's `reviewer` default and needs an argv seam, so it fails SPT Q4 as specified.

## Loop 5 Result

Partially resolved F-005 (stable_id F-005) in `scripts/run_review.py` by extracting the three genuinely self-contained phases of `run_review()` into named module-level private helpers: `_setup_gemini_config(args, env) -> str|None` (the ~40-line Gemini temp config overlay), `_build_stdin(reviewer, prompt_file) -> str|None` (prompt read + agy read-only preamble), and `_build_session_data(args, session, meta, reviewer, new_session_id, fallback_used) -> dict` (the 25-field resume-metadata session dict assembly). The `run_review()` body dropped from ~405 LoC (loop 4) to 328 LoC. The two largest phases — the two-attempt resume/fresh subprocess loop and the per-run `CODEX_HOME` setup — were deliberately **left inline**: extracting either threads 4–5 mutable locals (`use_resume`, `session_id`, `fallback_used`, `returncode`) both into and out of the helper, which fails the Simplify Pressure Test honesty bar (Q2 smallest honest fix, Q3 no duplicate layer) and would only relocate lines. **Risk-boundary preservation (Meta-Rule 4):** the un-extracted attempt loop + finally block retain sole ownership of module-level `_active_proc` (single writer), the SIGTERM/SIGINT save/restore ordering, the `env["CODEX_HOME"]` mutation, and the resume/fresh attempt semantics — none crossed a helper boundary, so the invariants are preserved by construction; the green suite is the primary evidence (it mocks `subprocess.Popen`/`signal.signal` and exercises gemini/codex/agy/resume-fallback/session-persistence end-to-end), with this note covering the `_active_proc`/signal path the suite does not directly assert. **Tests (Replace-don't-layer + Indirect Interface carve-out):** the extracted helpers are private and reached transitively through `run_review()`'s already-green end-to-end tests — `interface_test_coverage_path` cites `scripts/tests/test_execution_paths.py` (`test_run_review_gemini_effort_overlay_preserves_existing_settings`, `test_run_review_gemini_pipes_prompt_via_stdin`, `test_agy_prepends_readonly_preamble_to_prompt`, and the session-persistence assertions); no new test files added, no existing tests deleted. Post-change: `python3 -m ruff check scripts/run_review.py` → `All checks passed!`; `python3 -m pytest scripts/tests/` → **119 passed, 0 failed** (unchanged). Finding F-005 (stable_id F-005) **carried_forward** (partial). `simplicity` 6 → 6.5; no unintended scorecard regression.

## Loop 5 Implementation Review

Verdict: **approved** (inline, `ran_inline: true`). All three checks passed:
- Reality: post-diff `ruff check scripts/run_review.py` exits 0; `pytest scripts/tests/` → 119 passed; the three helpers exist at `run_review.py:202/249/265` and are called from `run_review()`; the body LoC dropped from ~405 to 328 (verified via `awk` span measurement).
- Honesty: no new seam (helpers are module-internal privates, not interfaces); the SPT downgrade on the attempt-loop/codex-setup phases is recorded with the inout-threading reason rather than forced into shallow splits; the three extractions are behavior-preserving (pure relocations with identical control flow); `_build_session_data` is pure assembly (no I/O). The `simplicity` delta cites a concrete LoC drop against `d1bdfb4`, not a cosmetic claim.
- Regression: extractions preserve `_active_proc` single-writer, signal save/restore ordering, `env` isolation, and resume/fresh semantics (all in the un-extracted attempt loop); 119 tests green, same count; no new findings at equal-or-higher severity.
