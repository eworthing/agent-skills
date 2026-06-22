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
Loop 1 of 10 (cap)

### System Flag
[STATE: CONTINUE]

---

## Contest Verdict
Functionally solid, but structurally compromised

Test suite is red (2 deterministic failures) due to a stale test helper that duplicates the CLI arg contract without `codex_home_manifest`. Production CLI is unaffected. All structural scoring is unverifiable while the suite is red; loop 1 restores green before loop 2 can score architecture honestly.

## Scorecard (1-10)

- **Architecture quality:** 1 | SAME | loop 1 build failure; baseline unmeasurable _(unverifiable_due_to_build_failure)_
- **State management and runtime ownership:** 1 | SAME | loop 1 build failure; baseline unmeasurable _(unverifiable_due_to_build_failure)_
- **Domain modeling:** 1 | SAME | loop 1 build failure; baseline unmeasurable _(unverifiable_due_to_build_failure)_
- **Data flow and dependency design:** 1 | SAME | loop 1 build failure; baseline unmeasurable _(unverifiable_due_to_build_failure)_
- **Framework / platform best practices:** 1 | SAME | loop 1 build failure; baseline unmeasurable _(unverifiable_due_to_build_failure)_
- **Concurrency and runtime safety:** 1 | SAME | loop 1 build failure; baseline unmeasurable _(unverifiable_due_to_build_failure)_
- **Code simplicity and clarity:** 1 | SAME | loop 1 build failure; baseline unmeasurable _(unverifiable_due_to_build_failure)_
- **Test strategy and regression resistance:** 1 | SAME | loop 1 build failure; baseline unmeasurable _(unverifiable_due_to_build_failure)_
- **Overall implementation credibility:** 1 | SAME | scripts/tests/_helpers.py:66–82 omits codex_home_manifest → AttributeError at run_review.py:306; scores floor to 1 on build-failure path.

## Authority Map

- **Concern:** CLI arg contract
  - **Owner:** `run_review.py parse_args()` (argparse definition, dest names, defaults)
  - **Allowed writers:** `run_review.py parse_args()` only
  - **Observers / readers:** `run_review.run_review()` (production), `scripts/tests/_helpers.py make_args()` (test surrogate — stale, causing the failure)
  - **Persistence seam:** none
  - **Async mutation entry points:** none
  - **Verdict:** Split and ambiguous — two sources of truth for arg names; helper drifted from parse_args.

## Strengths That Matter

- Production CLI is unaffected: argparse provides `None` default for `--codex-home-manifest`; only the test helper's manually-constructed `Namespace` omits it.
- Root cause is localized to a single dict in `scripts/tests/_helpers.py` (lines 66–82); blast radius is minimal.

## Findings

### Finding #1: Test suite red blocks structural review

**Why it matters** — A red test suite prevents any verifiable structural scoring; all 9 scorecard dimensions floor to 1 while tests fail.

**What is wrong** — `scripts/tests/_helpers.py::make_args()` (lines 66–82) hard-codes a parallel copy of the CLI arg names. When `run_review.py` added `--codex-home-manifest` (parse_args lines 108–114, dest `codex_home_manifest`), the helper was not updated. `run_review.py:306` reads `args.codex_home_manifest`; the `Namespace` produced by `make_args()` omits it → `AttributeError`. Both failing tests exercise the codex provider path.

**Evidence** — `scripts/tests/test_execution_paths.py::TestRunReviewExecution::test_run_review_codex_accepts_last_message_file_without_json_stdout`; `scripts/tests/test_execution_paths.py::TestRunReviewExecution::test_run_review_codex_stale_events_do_not_mask_empty_current_output`; `scripts/run_review.py:306` (`args.codex_home_manifest`).

**Architectural test failed** — n/a (build-failure finding, not a structural Seam finding)

**Dependency category** — null

**Leverage impact** — Test helper's duplicated arg contract provides no leverage; it is a maintenance liability that will drift again on any new arg addition.

**Locality impact** — Changes to `run_review.py`'s arg contract must be reflected in two places; no single-file update is complete.

**Metric signal, if any** — 2 of 118 tests fail deterministically; re-run confirms (not a flake).

**Why this weakens submission** — A red test suite makes implementation credibility unverifiable and blocks all structural scoring; no dimension above 1 can be grounded while tests fail.

**Severity** — Likely disqualifier

**ADR conflicts** — none

**Minimal correction path** — Add `"codex_home_manifest": None,` to the `make_args()` defaults dict in `scripts/tests/_helpers.py` after the `"review_id"` entry. That is the entire fix. (Deeper refactor — deriving the Namespace from `parse_args()` itself so it can't drift — is a future structural candidate; noted in Builder Notes but not in scope this loop per the Simplify Pressure Test for build-failure restoration.)

**Blast radius** — Change: `scripts/tests/_helpers.py`. Avoid: `scripts/run_review.py`, `scripts/check_web_search.py`, `scripts/ppr_paths.py`, `scripts/_common/**`, all markdown files, all other test files.

## Simplification Check
- **Structurally necessary:** restores green suite — the minimum change for loop 2 to run structural scoring honestly.
- **New seam justified:** false
- **Helpful simplification:** none this loop; the deeper "derive Namespace from parse_args()" refactor is noted in Builder Notes as a future candidate.
- **Should NOT be done:** do not refactor parse_args() itself, do not add type annotations, do not clean up pre-existing ruff violations — all out of scope for the build-failure restoration loop.
- **Tests after fix:** existing tests run against the fixed helper; no tests deleted or added.

## Improvement Backlog
1. **Restore green test suite** (structural / needed for winning)
   - Why it matters: all structural scoring is blocked while the suite is red; loop 2 cannot honestly evaluate architecture until it can run tests and trust the results.
   - Score impact: unlocks all 9 dimensions for real scoring in loop 2.

## Deepening Candidates

The `make_args()` helper represents a deepening candidate: derive the `Namespace` directly from `run_review.parse_args([])` (or a variant that accepts a list of args) so the helper cannot drift from the real arg contract. This would replace the hand-rolled dict with a single call. However, this deepening is out of scope for the build-failure restoration loop (SPT: smallest honest fix this loop is the one-line dict entry; deepening adds more changes than the restoration requires). Surface in loop 2 as a credibility candidate if the test strategy score warrants it.

## Builder Notes

1. **Pattern: duplicated arg contract in test helper**
   - What appeared: `make_args()` manually copies every CLI arg name into a dict, producing a `Namespace` the production argparse would supply. When a new arg is added to `run_review.py`, the helper is silently out of sync; tests that exercise that arg fail with `AttributeError`.
   - How to recognize: grep for `argparse.Namespace(**` or `argparse.Namespace(reviewer=` in test helpers — each is a potential stale-arg bomb.
   - Smallest coding rule: have the test helper call the actual `parse_args([])` with a controlled arg list, then `vars()` the result and override the fields you need. One call; can't drift.
   - Stack example (Python): `args = parse_args([]); args.reviewer = "claude"; args.plan_file = tmp` — no manual dict, no drift risk.

2. **Pattern: build-failure restoration scope discipline**
   - What appeared: the build-failure loop is tempted to fix several adjacent issues (unused imports, import sort, deeper refactor of parse_args) while "already in the file." Each would widen blast radius, risk additional failures, and fail the Simplify Pressure Test (smallest honest fix for the loop's purpose is the one-line addition).
   - How to recognize: when the failing test names a single `AttributeError` with a single missing attribute, the fix is one line. Pre-existing lint violations in the file are not this loop's responsibility; they belong in a later credibility finding.
   - Smallest coding rule: add only the missing entry; commit only the changed file; let later loops address adjacent issues through the normal scoring process.

3. **Scorecard humility check (Q9)**
   - Build-failure scores are all 1 with `unverifiable_due_to_build_failure: true`; no humility needed — they're deliberately unclaimed. The uncertainty is: once loop 2 scores real structure, will the test strategy dimension clear 7? The `make_args()` drift pattern suggests the test helper's arg contract is fragile; that's a known-unknown for loop 2.

## Final Judge Narrative

Loop 1 is a build-failure restoration loop, not a structural critic pass. The scorecard is floored at 1 across all dimensions — not because the code is weak, but because a red test suite makes all structural claims unverifiable. The fix is a single dict entry. Once loop 2 can run green tests, real scoring begins. The one structural note worth carrying forward: `make_args()` is an authority-duplication smell (the test helper duplicates the CLI arg contract rather than deriving it), which will appear as a credibility or test-strategy finding in loop 2 if the Simplify Pressure Test passes. Future work should avoid the pattern; the deepening candidate (derive from `parse_args([])`) is the right long-term fix but not for this loop.

## Loop 1 Result

Added `"codex_home_manifest": None,` to the `make_args()` defaults dict in `scripts/tests/_helpers.py` (after `"review_id"`, line 82). Re-ran full suite: **118 passed, 0 failed** (green). `python3 -m ruff check scripts/tests/_helpers.py` returns 19 pre-existing violations (F401 unused imports, I001 import sort) — all pre-existing, none introduced by this change. Targeted finding F1 (stable_id F-001, "Test suite red blocks structural review") is **resolved** — both formerly-failing test node IDs now pass. No unintended scorecard regression observed.
