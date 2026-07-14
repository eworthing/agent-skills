# peer-plan-review — Transport Hardening Sources

Provenance and adaptation record for the OpenCode read-only + partial-timeout change.

## Provenance

| Source | Trust | Contribution | Usage |
|---|---|---|---|
| `refs/competitors/sub-agents-skills` @ `695aac17cf4bacf5d5ec19160767650bbdd14774` | Upstream impl / high | `--auto` + deny-policy env; partial-result handling | MIT; concepts adapted onto the existing runner — its orchestration architecture not copied. |
| OpenCode `permissions.mdx` (docs) | Official / high | Deny rules stay enforced under `run --auto`; permission keys + precedence | Provider-specific; re-check when the OpenCode CLI changes. |
| OpenCode `cli.mdx` (docs) | Official / high | `OPENCODE_PERMISSION` accepts inline JSON via env | Keep JSON compact + deterministic. |
| Local `common/`, `peer-plan-review`, tests; commit `39365d5` | Canonical local / high | Current provider/session contracts; origin of the stale `--dangerously-skip-permissions` flag | Local source of truth overrides competitor structure. |

## Doc honesty — unverified CLI contract

The OpenCode CLI contract — `--auto`, the five deny keys
`edit`/`bash`/`task`/`external_directory`/`question`, and `OPENCODE_PERMISSION` acceptance — is
**asserted from OpenCode docs, not proven against a running binary's behavior in this environment.**
The one thing checked live during this change: `opencode run --help` on the installed binary
advertises `--auto` (self-check exit 0). That same `opencode run --help` self-check is the
**fail-closed guard** at runtime: if a future OpenCode drops `--auto`, self-check fails before any
review runs. The deny-key *enforcement* itself is not exercised by any test here.

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
| Portability (opencode excluded from quorum surface; 3.9 stdlib-only) | `quorum-review/scripts/tests` |

## Trigger precision — intentionally unchanged

- Should trigger: "review this implementation plan with opencode", "get a peer review of this plan".
- Should not trigger: "run an OpenCode coding task", "review this code diff".
- Decision: no frontmatter edit. Transport safety and timeout recovery do not change activation
  semantics.
