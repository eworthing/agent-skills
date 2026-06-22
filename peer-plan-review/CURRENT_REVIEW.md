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
Loop 6 of 10 (cap)

### System Flag
[STATE: CONTINUE]

---

## Contest Verdict
Good app, but not top-tier yet

Tests are green (119 passed). Production lint is clean (`ruff check scripts/run_review.py` exits 0). Loop 6 resolved F-006 subtractively: `make_args()` in `scripts/tests/_helpers.py` no longer carries a 17-key hand-maintained dict duplicating the CLI arg contract; it now derives every key + default from `run_review.parse_args()` itself (the single source of truth). Net −6 LoC (17 insertions, 23 deletions) plus deletion of the now-unused `argparse` import. The loop-3 contract-sync test becomes belt-and-suspenders (kept). Source proof refuted the loop-5 "fails SPT Q4" framing: an AST scan of all 39 `make_args()` call sites shows 38 pass `reviewer=` explicitly and the one bare call (`test_make_args_keys_match_parse_args_dests`) reads only keys, never the reviewer value, so the `reviewer="claude"`→`None` default change is behavior-identical. `test_strategy` 7.5 → 8. F-005 (decompose `run_review()` residual phases) is demoted from Priority 1 to Priority 2 with an honest irreducibility disposition. A new finding F-007 (README documents a test command that collects zero tests) takes Priority 1.

## Scorecard (1-10)

- **Architecture quality:** 7 | SAME | `run_review.py` orchestrates via `_common` (import-direction DAG, no cycles); registry dispatch at `run_review.py:409` (`PROVIDERS[reviewer]["build_cmd"](build_args, session_id)`); clean import DAG at `run_review.py:25-69`. The three loop-5 phase helpers (`run_review.py:202` `_setup_gemini_config`, `:249` `_build_stdin`, `:265` `_build_session_data`) improve Locality without new interfaces. This loop's change was test-helper only (`scripts/tests/_helpers.py`), so production architecture is unchanged. Residual blocking 10: `run_review()` is a 330-LoC coordinating function (`run_review.py:318-647`) with the two-attempt loop + codex-setup phases inline (F-005, demoted to Priority 2 — irreducible without ceremony; 9-anchor not met).
- **State management and runtime ownership:** 8 | SAME | `_active_proc` at `run_review.py:187` is module-level, written only inside `run_review()` (the attempt loop + finally), read by `_signal_handler()` at `:191`. Single-writer; idiomatic for signal-handler communication. Local resume state machine (`use_resume`, `fallback_used`, `session_id`) is function-scoped. No multi-writer hazard. Unchanged this loop. Residual: lifecycle authority (signal save/restore + resume-state locals) lives inside the one large `run_review()` function (tied to F-005); 9-anchor not fully met, honest 8.
- **Domain modeling:** 7 | SAME | CLI adapter domain is thin by design; the `PROVIDERS` registry (from `_common`) is the core model. `_build_session_data` (`run_review.py:265`) names the session-dict assembly in one place but it remains an untyped dict (no smart constructor). No impossible-state hazard at the schema level. Unchanged this loop. Residual: no discriminated type for provider-specific output / session dict (`run_review.py:280`); 9-anchor not met; CLI-adapter-thin context noted; honest 7.
- **Data flow and dependency design:** 8 | SAME | Clean DAG: `run_review.py` → `_common.*`. Re-exports at `run_review.py:46-69` (`# noqa: F401`) keep `mock.patch("run_review.X")` paths stable. The loop-5 helpers take explicit inputs / return explicit outputs. The `extract_metadata`/`extract_text_from_output` seam pre-reads `output_content` (`run_review.py:574-579`) to mitigate temporal coupling, with a comment. Unchanged this loop. Residual: a couple of ambient `os.environ` reads (`run_review.py:345`, `:212`); 9-anchor nearly met, idiomatic for a CLI adapter; honest 8.
- **Framework / platform best practices:** 6.5 | SAME | `python3 -m ruff check scripts/run_review.py scripts/check_web_search.py scripts/ppr_paths.py` → `All checks passed!` (production clean, held). `scripts/tests/_helpers.py` is now ruff-clean too (this loop removed its last F401 by deleting the unused `argparse` import and correcting the `run_review` noqa). Dimension stays 6.5 because test-file violations persist across the other test modules: F405 ×154 (star-import undefined-name from `from ._helpers import *`), RUF100 ×19, I001 ×7, E401 ×7 — **accepted residual** (test-only; the star-import pattern is a deliberate ergonomic choice; fixing means replacing star imports across 7 files = ceremony with no behavior change; SPT-rejected on Q2; `accepted_on: 2026-06-22`, `expires: 2026-12-22`).
- **Concurrency and runtime safety:** 8 | SAME | Single-threaded Python. Signal handlers saved/restored in try/finally (`run_review.py:392-395` set, `:632-635` restore); the save/restore and `_active_proc` set/clear ordering were untouched this loop. `subprocess.Popen` with `communicate(timeout=)` blocks correctly with a `TimeoutExpired` kill-tree path (`run_review.py:448-455`). Gemini/agy temp cleanup in finally. No threading races. Residual: the SIGTERM/SIGINT save-restore + `_active_proc` ordering is correct but verified by construction + the suite mocking `signal.signal`, not by a direct concurrency test; honest 8.
- **Code simplicity and clarity:** 6.5 | SAME | This loop's change improved the test helper (`make_args`), not production code, so production simplicity is unchanged: `run_review()` is still a 330-LoC coordinating function (`run_review.py:318-647`, verified by awk span). The loop-5 phase extractions still stand. No production simplicity delta this loop; the F-006 win is recorded under `test_strategy`. Residual: attempt-loop + codex-setup phases remain inline (F-005, re-derived from source as irreducible). simplicity at 6.5 cannot honestly be promoted to a 9.5 accepted residual (9-anchor not met), so it sits at its earned score with the cohesive-core blocker named (Residual Accounting Pass).
- **Test strategy and regression resistance:** 8 | **UP** | **Structural proof:** F-006 resolved this loop — `scripts/tests/_helpers.py` `make_args()` no longer duplicates the CLI arg contract in a hand-maintained 17-key dict; it derives every key + default from `run_review.parse_args()` (single source of truth). The `_helpers.py` diff in this loop's commit (`git diff --stat`: 17 insertions, 23 deletions) deletes the dict literal and the `argparse` import. The drift class that consumed loop 1 (helper drifting from `parse_args` when `--codex-home-manifest` was added) is now **structurally impossible** — a new `parse_args()` argument flows into `make_args()` automatically. 119 tests green (unchanged), including all 39 `make_args()` call sites and `TestArgContract` (now belt-and-suspenders, kept). Residual blocking 10: README.md documents a test command that collects zero tests (F-007 — discoverability gap, Priority 1 next loop); the contract-sync test now duplicates a structurally-guaranteed property. Honest 8.
- **Overall implementation credibility:** 8 | SAME | The code earns its architecture: this loop's fix is genuinely subtractive (net −6 LoC, duplicated authority deleted), not a costume relocation. The loop-5 SPT downgrades on F-005 remain honestly recorded. The orchestrator-registry pattern, signal safety, and per-run Codex home isolation remain well-tested. This loop also corrected a loop-5 analytical error (F-006 was mislabeled "not pure-subtractive / fails SPT Q4"; source proof shows zero readers of the changed default). Residual blocking 10: `README.md:41-52` documents a stale/broken test command and count (F-007), a doc-vs-code credibility drag; Priority 1 next loop.

## Authority Map

- **Concern:** CLI arg contract
  - **Owner:** `run_review.py:parse_args()` (argparse definition, dest names, defaults)
  - **Allowed writers:** `run_review.py:parse_args()` only
  - **Observers / readers:** `run_review.run_review()` (production); `scripts/tests/_helpers.py:make_args()` now **derives** from `parse_args()` (no longer an independent writer of the arg-name set)
  - **Persistence seam:** none
  - **Async mutation entry points:** none
  - **Verdict:** Single and clear (improved this loop) — `parse_args()` is now the sole source of truth for both the arg-name set AND the defaults. `make_args()` reads `parse_args()` under a saved/restored `sys.argv` and layers overrides; it can no longer drift. The loop-5 "Split and ambiguous" verdict is resolved by F-006.

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

- CLI arg contract now has a single source of truth: `scripts/tests/_helpers.py:make_args()` derives keys + defaults from `run_review.parse_args()` (`run_review.py:76-123`) rather than restating them, closing the drift class that consumed loop 1. The fix is net-subtractive (17 insertions / 23 deletions).
- `run_review.py` cleanly delegates all provider-specific logic to `_common.providers.PROVIDERS`: command construction, cap flags, effort maps, session-id extraction. The orchestrator dispatches through the registry (`run_review.py:409`) without branching on provider internals.
- Gemini config-overlay isolation is behavioral and tested: the loop-5 helper `_setup_gemini_config` (`run_review.py:202`) excludes auto-saved policy files and preserves existing settings (`test_run_review_gemini_effort_overlay_excludes_auto_saved_policies` / `_preserves_existing_settings`).
- Resume/fallback state is tracked via local variables (`use_resume`, `fallback_used`) and never by mutating `args` (`run_review.py:326-328`); the snapshot is explicit, preventing cross-attempt contamination — and is the honest reason the attempt loop resists extraction (F-005).
- Codex per-run `CODEX_HOME` isolation fails closed: setup failure clears `session_id`/`use_resume` to force a fresh exec rather than resuming into a missing home (`run_review.py:383-385`).

## Findings

### Finding #1: README documents a test command that collects zero tests + a stale test count

**Why it matters** — A new contributor (or an AI agent) following `README.md` to run the suite is told to run `cd scripts && python3 -m pytest test_run_review.py test_web_search.py` (`README.md:52`) against files described as the pytest suite (`README.md:41-42`). One of those files does not exist and the other is a unittest discovery shim, so the documented command collects **zero tests** — the reader would conclude the project is untested. This undermines the credibility of an otherwise well-tested adapter (119 real tests live under `scripts/tests/`).

**What is wrong** — `README.md:42` references `scripts/test_web_search.py` which does not exist (web-search tests were not split into a pytest module). `README.md:41` claims "test_run_review.py pytest suite (118 tests)" — stale count (the suite is 119) and mislabeled (`test_run_review.py` is a 16-LoC `unittest.TestLoader().discover` shim, not a pytest test module). The canonical command is `python3 -m pytest scripts/tests/`.

**Evidence** —
- `README.md:41` "test_run_review.py  pytest suite (118 tests)" — stale count (actual 119) + mislabel (shim, not pytest module).
- `README.md:42` "test_web_search.py  web-search adapter pytest suite" — file does not exist (`ls scripts/test_web_search.py` → No such file).
- `README.md:52` "cd scripts && python3 -m pytest test_run_review.py test_web_search.py" — verified to print "no tests ran" (zero collected) because `test_web_search.py` is missing and `test_run_review.py` exposes no pytest-discoverable test functions.
- `scripts/test_run_review.py` is a `unittest.TestLoader().discover(str(here / "tests"), ...)` shim (16 LoC), not a pytest test module.

**Architectural test failed** — n/a (doc-vs-code rot — `method.md` Step 6 doc-vs-code grep + `lens-generic` failure-modes/observability).

**Dependency category** — `in-process`

**Leverage impact** — Low (documentation, not runtime) — but high friction at first contact for any new contributor or CI author.

**Locality impact** — Low — the fix is local to `README.md`.

**Why this weakens submission** — A documented entrypoint that silently collects zero tests is a doc-vs-code credibility leak per `method.md` Step 6: a reviewer trusting the README would believe the suite is empty or broken. It is the kind of small honesty gap the rubric penalizes when it would mislead a reader about regression resistance.

**Severity** — Noticeable weakness

**ADR conflicts** — none

**Minimal correction path** — Update `README.md` to document the canonical command `python3 -m pytest scripts/tests/`; correct the test count to 119; drop or correct the `test_web_search.py` reference (point at the actual web-search tests or remove the stale line). Subtractive where possible (delete the dead reference).

**Blast radius** — Change: `README.md` only. Avoid: all `scripts/**`, `_common/**`.

## Simplification Check

- **Structurally necessary:** the F-006 fix passes SPT Q1–Q5: it fixes a real duplicated-authority ambiguity (the 17-key dict restated `parse_args`' contract and defaults), is the smallest honest fix (derive from the existing `parse_args`; net −6 LoC), adds no duplicate layer (it **removes** one), keeps runtime behavior honest (source-proven: zero call sites read the `reviewer` default that changed from `"claude"` to `None`), and improves the product (drift becomes structurally impossible).
- **New seam justified:** false — no new seam proposed or created; `make_args()` now reads the existing `parse_args()` Interface instead of duplicating it.
- **Helpful simplification:** deleting the `make_args()` dict + the now-unused `argparse` import is the highest-payoff subtraction available this loop; the loop-3 contract-sync test (`test_make_args_keys_match_parse_args_dests`) is now belt-and-suspenders — kept (cheap; documents intent), removable in a future loop as a separable subtraction.
- **Should NOT be done:** Do NOT extract the `run_review()` attempt loop or codex-setup into helpers (F-005 — re-derived from source as fails SPT: 4–5 inout locals). Do NOT rewrite the test star-import pattern to silence F405 (test-only ceremony, no behavior change). Do NOT fix README doc-rot (F-007) in this same commit — it is a separate concern and scope; queued Priority 1.
- **Tests after fix:** 119 tests pass (unchanged count). No tests added or deleted; all 39 `make_args()` call sites green; `TestArgContract` green (now structurally guaranteed).

## Improvement Backlog

1. **Fix README test-command doc-rot** (stable_id F-007 / simplification / noticeable weakness) — **Priority 1 (new this loop)**
   - Why it matters: `README.md:41-52` documents `pytest test_run_review.py test_web_search.py` which collects zero tests (`test_web_search.py` absent; `test_run_review.py` is a unittest shim), telling a new contributor the project is untested when 119 tests exist under `scripts/tests/`.
   - Score impact: credibility +0.5 (8→8.5) and/or `test_strategy` discoverability residual cleared once README points at `python3 -m pytest scripts/tests/` with the correct count.
   - Kind: simplification. Rank: helpful.

2. **Decompose `run_review()` flat body — residual phases (irreducible without ceremony)** (stable_id F-005 / structural / noticeable weakness) — **demoted to Priority 2**
   - Why it matters: after loop 5's three extractions, `run_review()` is 330 LoC. The remaining two-attempt resume/fresh subprocess loop and the per-run `CODEX_HOME` setup thread `use_resume`/`session_id`/`fallback_used`/`returncode` both into and out of any candidate helper (re-derived from source this loop at `run_review.py:397-533` + `:386-389`), so extracting them adds ceremony and fails SPT — demoted from Priority 1.
   - Score impact: no clean score path — simplicity (6.5) cannot honestly reach a 9.5 accepted residual from here; the only remaining move is the marginal `CodexCapture` value-return (a deepening candidate), a small win with non-trivial blast radius. Likely retire or accept-as-irreducible in a future loop if it reappears unchanged.
   - Kind: structural. Rank: helpful.

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

1. **Source-check beats inherited framing (F-006 re-derivation)**
   - What appeared: loop 5 carried F-006 as "not pure-subtractive; fails SPT Q4" because `make_args()` defaulted `reviewer="claude"` while `parse_args([])` yields `reviewer=None`.
   - Correct action: I tested that claim against source with an AST scan of all 39 `make_args()` call sites: 38 pass `reviewer=` explicitly and the single bare call (`test_make_args_keys_match_parse_args_dests`) compares only `set(vars(make_args()).keys())`, never reading `.reviewer`. So the default change is behavior-identical and Q4 passes.
   - Recognition rule: when a prior loop asserts a fix "changes behavior unless every call site is updated", enumerate the call sites mechanically before accepting the demotion — the count may be zero.

2. **Subtractive fix hygiene cascade**
   - What appeared: deleting the dict made the `argparse` import unused.
   - Correct action: removed the `argparse` import, which in turn made the `import run_review` `F401` noqa unnecessary (because `make_args` now USES `run_review.parse_args()`) — corrected the noqa to `E402`-only. Net: `scripts/tests/_helpers.py` went from carrying lint debt to fully ruff-clean, and the test-file total error count stayed flat at 187 (no new debt).
   - Recognition rule: after a deletion, re-lint the touched file and fix the noqa directives the deletion invalidated — don't leave a stale `# noqa: F401` that ruff then flags as RUF100.

3. **Scorecard humility check (Q9)**
   - Claim `test_strategy: 8` (UP) at `scripts/tests/_helpers.py` `make_args()` — uncertainty: a stricter reviewer could argue F-006 is a test-helper cleanup that does not raise the *product's* regression resistance and should leave `test_strategy` at 7.5; I scored UP because the change closes the exact drift class that caused a real prior build failure (loop 1) and makes it structurally impossible, which is a regression-resistance improvement, not cosmetics.
   - Claim Finding #1 severity "Noticeable weakness" — uncertainty: it could be read as merely "Cosmetic for contest" since it is documentation; I held Noticeable because a documented command that collects zero tests actively misleads a reader about whether the suite exists (verified: "no tests ran"), a credibility harm, not a typo.
   - Claim F-005 demotion to Priority 2 rather than retirement — uncertainty: it is NOT mechanically retirement-eligible (no `rejected_attempt` occurrences, no resolved-then-reappeared pattern per Step 1.6 Branch A/B), so demotion is the correct lever; a reviewer could argue simplicity should be promoted to a 9.5 accepted-residual instead — I rejected that because simplicity sits at 6.5, far below the 9-anchor, so an accepted residual there would be fake-clean reward (forbidden).

## Final Judge Narrative

Loop 6 resolved F-006 as a clean subtractive win, correcting a loop-5 analytical error in the process. The hand-maintained 17-key dict in `scripts/tests/_helpers.py:make_args()` — a parallel copy of the CLI arg contract that caused the loop-1 build failure when `--codex-home-manifest` was added — is deleted; `make_args()` now derives every key and default from `run_review.parse_args()` under a saved/restored `sys.argv`, then layers overrides. Net change is −6 LoC (17 insertions, 23 deletions) plus removal of the now-unused `argparse` import, leaving `_helpers.py` fully ruff-clean. Loop 5 had demoted F-006 to "not pure-subtractive / fails SPT Q4", reasoning that `make_args` defaulted `reviewer="claude"` whereas `parse_args([])` yields `reviewer=None`. An AST scan of all 39 `make_args()` call sites refuted that: 38 pass `reviewer=` explicitly and the one bare call reads only the namespace keys, never the reviewer value — so the default change is behavior-identical and SPT Q4 passes. The CLI-arg-contract concern in the Authority Map moves from "Split and ambiguous" to "Single and clear": `parse_args()` is now the sole source of truth for both the arg-name set and the defaults, and `make_args()` can no longer drift, making the loop-3 contract-sync test belt-and-suspenders (kept). `test_strategy` 7.5 → 8. F-005 (decompose `run_review()`'s residual phases) was re-derived from current source — the two-attempt loop genuinely threads `use_resume`/`session_id`/`fallback_used`/`returncode` in+out and reads them post-loop, so extracting fails SPT — and is demoted from Priority 1 to Priority 2; simplicity holds at its earned 6.5 with the cohesive-core blocker named (it cannot honestly be promoted to a 9.5 accepted residual from 6.5). A newly surfaced finding, F-007, takes Priority 1: `README.md` documents `pytest test_run_review.py test_web_search.py`, which collects zero tests (`test_web_search.py` does not exist; `test_run_review.py` is a unittest discovery shim) and reports a stale count (118 vs the real 119) — a doc-vs-code credibility leak that would tell a new contributor the project is untested. Suite green (119); production lint clean.

## Loop 6 Result

Resolved F-006 (stable_id F-006) in `scripts/tests/_helpers.py`: replaced `make_args()`'s hand-maintained 17-key default dict (which duplicated the `run_review.py` CLI arg contract and its defaults) with derivation from `run_review.parse_args()` itself — saved/restored `sys.argv` to `["run_review.py"]`, called `parse_args()` to get the canonical `Namespace` with real defaults, then applied `**overrides` via `setattr`. Also deleted the now-unused `import argparse` and corrected the `import run_review` noqa from `E402,F401` to `E402` (`run_review` is now used directly by `make_args`, not only re-exported). Net diff: 17 insertions, 23 deletions (−6 LoC). **Evidence change is honest:** `python3 -m ruff check scripts/run_review.py scripts/check_web_search.py scripts/ppr_paths.py` → `All checks passed!` (production unchanged); `python3 -m ruff check scripts/tests/_helpers.py` → `All checks passed!` (was carrying an `argparse` F401 before; now clean); `python3 -m pytest scripts/tests/` → 119 passed, 0 failed (unchanged count) — all 39 `make_args()` call sites and `TestArgContract` green. **SPT Q4 (behavior-honest) is source-proven, not asserted:** an AST scan of `make_args()` call sites shows 38/39 pass `reviewer=` explicitly and the 1 bare call (`test_make_args_keys_match_parse_args_dests`) reads `set(vars(make_args()).keys())` only — so the reviewer default changing from `"claude"` to `None` changes no test's behavior. The fix is genuinely subtractive (net −6 LoC; a duplicate authority layer removed, none added). Finding F-006 (stable_id F-006) **resolved**. `test_strategy` 7.5 → 8; no unintended scorecard regression.

## Loop 6 Implementation Review

Verdict: **approved** (inline, `ran_inline: true`). All three checks passed:
- Reality: post-diff `ruff check` on production exits 0 and on `scripts/tests/_helpers.py` exits 0 (the file is now fully clean); `pytest scripts/tests/` reports 119 passed; the `make_args()` dict literal is gone and the function derives from `run_review.parse_args()` (verified by reading the file and by a runtime probe: bare `make_args().reviewer` is `None`, `make_args(reviewer="codex", model="gpt-5.4")` returns `reviewer="codex"`/`model="gpt-5.4"`).
- Honesty: no new seam (a duplicate layer was removed, not added); the change is net-subtractive (17 insertions / 23 deletions); the SPT Q4 behavior-preservation claim is backed by an AST enumeration of all 39 call sites (38 explicit `reviewer=`, 1 keys-only bare call) rather than asserted; no suppression-as-fix.
- Regression: no risk boundary crossed (test-helper only — no isolation/Sendable/signal/visibility/conditional-compilation change); 119 tests green at the same count including the contract-sync test; `make_args(reviewer=...)` still bypasses alias normalization exactly as the deleted dict did (overrides applied post-parse); no new finding at equal-or-higher severity introduced by the change (F-007 is pre-existing README doc-rot surfaced by this loop's audit, not caused by the diff).
