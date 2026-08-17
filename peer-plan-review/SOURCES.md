# peer-plan-review — Transport Hardening Sources

Provenance and adaptation record for the OpenCode read-only + partial-timeout change.

## Provenance

| Source | Trust | Contribution | Usage |
|---|---|---|---|
| `refs/competitors/peer-plan-review/sub-agents-skills` @ `695aac17cf4bacf5d5ec19160767650bbdd14774` | Upstream impl / high | `--auto` + deny-policy env; partial-result handling | MIT; concepts adapted onto the existing runner — its orchestration architecture not copied. |
| OpenCode `permissions.mdx` (docs) | Official / high | Deny rules stay enforced under `run --auto`; permission keys + precedence | Provider-specific; re-check when the OpenCode CLI changes. |
| OpenCode `cli.mdx` (docs) | Official / high | `OPENCODE_PERMISSION` accepts inline JSON via env | Keep JSON compact + deterministic. |
| Local `common/`, `peer-plan-review`, tests; commit `39365d5` | Canonical local / high | Current provider/session contracts; origin of the stale `--dangerously-skip-permissions` flag | Local source of truth overrides competitor structure. |

## Doc honesty — CLI contract verification

The OpenCode deny-key contract was **live-verified 2026-07-14** against opencode **1.17.19**
(macOS, real `$HOME` auth, fresh empty temp cwd, production argv + env):

- Command: `opencode run --format json --auto` (built by the production `build_opencode_cmd`),
  child env `OPENCODE_PERMISSION={"edit":"deny","bash":"deny","task":"deny",`
  `"external_directory":"deny","question":"deny"}`.
- Probe prompt instructed two canaries: create `canary.txt` ('x') in cwd; run `echo canary-shell`.
  Two runs (second explicitly forcing tool-call attempts). Exit 0 both times.
- **Both canaries blocked both times**: `canary.txt` absent on disk; no shell execution in the
  JSONL events. Enforcement mechanism: the deny policy **removes the write/edit and bash tools
  from the model's function schema entirely** — the model reported "no file-write/create tool …
  only `read` for file I/O" / "no Bash/shell-execute tool … in my tool set". Consequently there
  are no per-call denial *events* to cite (a denied call can never be issued); the protocol's
  original PASS shape (structured per-call denial evidence) is unobservable by construction.
  Temp dir removed after each run.

Still asserted-not-proven: per-key granularity beyond edit/bash (`task`/`external_directory`/
`question` were not individually probed). The `opencode run --help` self-check remains the
**fail-closed guard** at runtime: if a future OpenCode drops `--auto`, self-check fails before any
review runs.

## Adopt / reject / defer

- **Adopt:** OpenCode `run --auto` + explicit deny `OPENCODE_PERMISSION`; real-subcommand
  (`run --help`) self-check; retention of captured stdout after a killed process.
- **Replace locally:** existing provider registry, runner env, artifact files, failure summary, and
  vendoring workflow — not the competitor's generic invocation/result framework.
- **Reject:** generic agent profiles, caller-backend detection, safe-edit/yolo modes, streaming-
  normalization layer.
- **Defer:** OpenCode XDG isolation until a concurrency failure is reproduced (ephemeral isolation
  would break the existing resume contract).
- **Stop rationale:** further retrieval is low-yield until the OpenCode CLI contract or a concurrency
  failure changes.

## Coverage matrix

| Scenario | Test |
|---|---|
| Command contract (`--auto`, no legacy flag, deny JSON) | `test_opencode_basic`; `test_build_opencode_cmd_*` |
| Happy path — read-only env applied to child | `test_run_review_opencode_sets_read_only_permissions` |
| Permission/self-check failure + success | `test_self_check_opencode_requires_auto_flag` / `_accepts_auto_flag` |
| Resume timeout → fresh fallback (unchanged) | `test_run_review_resume_timeout_falls_back_to_fresh` |
| Terminal timeout, output retained (opencode) | `test_run_review_final_opencode_timeout_preserves_partial_output` |
| Terminal timeout, no output | `test_run_review_final_attempt_timeout_writes_failure_summary` |
| Codex events retained on timeout | `test_run_review_codex_timeout_preserves_partial_events` |
| Failure-summary shape + `partial_output` | `test_writes_minimal_shape`; `test_records_partial_output` |
| Sync (mirrors byte-identical) | `sync_common.py --check` |
| Portability (opencode excluded from quorum surface; 3.11 stdlib-only) | `quorum-review/scripts/tests` |

## Trigger precision — intentionally unchanged

- Should trigger: "review this implementation plan with opencode", "get a peer review of this plan".
- Should not trigger: "run an OpenCode coding task", "review this code diff".
- Decision: no frontmatter edit. Transport safety and timeout recovery do not change activation
  semantics.
