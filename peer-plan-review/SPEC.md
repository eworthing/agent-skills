# peer-plan-review — Maintenance Invariants

Terse contract for the transport layer. Details live in the docs each line points to;
this file only pins the invariants a change must not break.

1. **Trigger unchanged.** Host owns plan revision; the reviewer only critiques. See `SKILL.md`.
2. **Read-only reviewers.** Every provider except the documented experimental `agy` exception is
   read-only through enforced controls, not prompt intent. See `EVAL.md` §6.3 + `references/antigravity.md`.
3. **OpenCode needs `--auto` + the exact deny policy.** `build_opencode_cmd` emits `--auto` (never
   `--dangerously-skip-permissions`); the child gets `OPENCODE_PERMISSION` = deny for
   `edit/bash/task/external_directory/question`. `self_check` fails closed unless `opencode run --help`
   advertises `--auto`. See `references/opencode.md` + `SOURCES.md`.
4. **Timeout = failure but retains output.** A terminal timeout returns `rc != 0` / `verdict: null`,
   yet preserves captured stdout in the review/events artifact and sets `partial_output` in the
   failure summary. See `references/adapter-cli.md`.
5. **Edit canonical `common/common/` only.** Never hand-edit a `scripts/_common/` mirror; regenerate
   with `sync_common.py` and keep `sync_common.py --check` at exit 0.
6. **Validation gates:** focused tests, both consumer suites (`peer-plan-review`, `quorum-review`),
   repo-level `common/scripts/sync_common.py --check`, `common/scripts/check_shim_contract.py`,
   `common/scripts/check_module_size.py`, Ruff (0.15.6), the repository evaluator, and the
   skill-writer validator. Live count recorded once, in `EVAL.md` Runtime probes.
7. **Evaluation standards:** Keep only runnable cases with a named harness and versioned
   fixtures/results. The prompt efficacy harness lives in `evals/`; generated prompts and live
   runs remain gitignored.
