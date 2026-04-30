# Environment Variables

Variables read by `scripts/run_review.py` and the provider adapters.

## Skill-specific

| Variable | Used by | Effect |
|----------|---------|--------|
| `GEMINI_CONFIG_DIR` | `gemini` adapter | Source dir used to build a temp overlay from top-level files for each Gemini run. Defaults to `~/.gemini`. The overlay preserves auth (`oauth_creds.json`) and durable settings, excludes config subdirectories such as `cache`, `tmp`, `extensions`, `sessions`, and `policies`, and adds `thinkingConfig.thinkingBudget` only when `--effort` is set. |
| `CODEX_HOME` | `codex` adapter | Forwarded to the `codex` binary. Lets callers point Codex at a non-default config home without editing it. |
| `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC` | `claude` adapter | Force-set to `1` for every `claude` invocation to keep peer reviews off telemetry paths. Host-set values are overwritten. |

The runner never writes credentials and never promotes secrets into log files.
Session files and error logs contain session IDs, model names, and effort
levels — no tokens.

## Standard process env

Both adapters inherit the full parent environment (`os.environ.copy()`), so
anything your reviewer CLI normally reads — e.g. `ANTHROPIC_API_KEY`,
`OPENAI_API_KEY`, `GEMINI_API_KEY`, auth cache paths — continues to work
unchanged.
