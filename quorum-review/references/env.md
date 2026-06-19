# Environment Variables — quorum-review

Variables read by the orchestrator and adapter. All are optional; sensible defaults apply.

## Reviewer CLI configuration (consumed via `_common/`)

| Variable | Default | Purpose |
|---|---|---|
| `CODEX_HOME` | `~/.codex` | Source home the adapter copies `auth.json` + `config.toml` from. For each run it sets `CODEX_HOME` to a randomized per-run home with an isolated `sessions/`, so the parallel panel's Codex reviewers (and the verifier) never share session storage; the per-run home is snapshotted before/after exec to capture this run's session, recorded in `session.json` + a `qr-<quorum_id>-codex-homes.list` manifest, and reclaimed at the final round (`qr_paths.py --cleanup`). |
| `GEMINI_CONFIG_DIR` | `~/.gemini` | Source directory cloned to a per-effort temp overlay when `--effort` is set. Auth, extensions, and other Gemini state survive the overlay; only `settings.json` is rewritten with the requested `thinkingBudget`. |
| `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC` | `1` (set automatically when `--reviewer claude`) | Suppresses Claude CLI telemetry. The adapter sets this when invoking claude; you don't need to export it yourself. |

## Quorum-review telemetry

| Variable | Default | Purpose |
|---|---|---|
| `QUORUM_PARSE_FAILURES_LOG` | `${TMPDIR}/qr-<quorum_id>-parse-failures.jsonl` (per quorum) or `${TMPDIR}/qr-parse-failures.jsonl` (no quorum_id context) | Path the Tier-1/Tier-2 parsers append to when a reviewer's output cannot be parsed. Tests redirect this to per-test tmp paths so multiset assertions over `parser_name` stay isolated. |

## Standard tooling

| Variable | Purpose |
|---|---|
| `TMPDIR` | Used as the default base for all per-quorum temp files (ledger, merge log, per-reviewer prompts/reviews/sessions, deliberation context, tally JSON, parse failures). The orchestrator's `--tmpdir` flag overrides it explicitly. |

## Provider authentication

Provider CLIs handle their own auth; the adapter does not read or write provider credentials. See the per-provider reference (`references/claude.md` etc.) for details — typically Keychain (Copilot), browser-login token (Gemini), `ANTHROPIC_API_KEY` (Claude Code), or a cached Vertex login (`agy` — no API-key env var; see `references/antigravity.md`).
