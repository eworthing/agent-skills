# Runner Invocation

Single invocation shape used for every round. Round 1 omits `--resume`;
subsequent rounds add it.

```bash
python3 <skill-dir>/scripts/run_review.py \
  --reviewer <provider> \
  --plan-file <plan.md> \
  --prompt-file <prompt.md> \
  --output-file <review.md> \
  --session-file <session.json> \
  --events-file <events.jsonl> \
  --error-log <errors.jsonl> \
  --review-id <REVIEW_ID> \
  [--codex-home-manifest <homes.list>] \
  [--resume] \
  [--model MODEL] \
  [--effort LEVEL] \
  [--timeout SECONDS] \
  [--summary-file <summary.json>]
```

## Flags

- `--reviewer`: `codex`, `gemini`, `claude`, `copilot`, `opencode`, or `agy`
  (alias `antigravity`; experimental — see [`antigravity.md`](antigravity.md)).
  Required.
- `--resume`: include on rounds 2+ only. The runner falls back to a fresh
  execution once if the resume attempt fails (nonzero exit, timeout, or no
  usable output).
- `--model`: provider-specific model ID or known alias. `--list-models
  --reviewer <provider>` prints known aliases (claude, gemini), a live
  listing (opencode, agy), or doc-sourced known models (codex, copilot).
- `--effort`: portable `low | medium | high | xhigh`. The adapter maps this to
  each provider's native flag or setting internally. Pass *only* this; do not
  pass provider-native effort flags. For `agy` there is no native effort flag —
  effort is encoded as a model-name variant (e.g. `Gemini 3.5 Flash (High)`);
  `xhigh` maps to `High` (agy's max).
- `--timeout`: seconds. Default 600. Raise for large plans or slower reviewers.
- `--codex-home-manifest`: review-scoped list of per-run Codex homes for
  concurrency-safe isolation + terminal cleanup. Codex only; defaults to a path
  derived from `--session-file` if omitted. The `ppr_paths.py --format shell`
  output exports it as `$CODEX_HOME_MANIFEST`.
- `--summary-file`: optional machine-readable JSON with verdict, model, effort,
  round, finding count, and blocking count. Useful for non-Claude hosts.

## Session file contract

After each round, the session file contains:

- `session_id`, `model`, `model_requested`, `effort`, `effort_requested`,
  `effort_source`
- `round` (incremented each run)
- `resume_requested`, `resume_attempted`, `resume_fallback_used`, `resume_reason`
- For Gemini: `thinking_tokens`

Writes are atomic (`.tmp` + rename) so a mid-write crash cannot truncate it.

## Environment

Variables read by `run_review.py` and the provider adapters:

| Variable | Used by | Effect |
|----------|---------|--------|
| `GEMINI_CONFIG_DIR` | `gemini` adapter | Source dir used to build a temp overlay from top-level files for each Gemini run. Defaults to `~/.gemini`. The overlay preserves auth (`oauth_creds.json`) and durable settings, excludes config subdirectories such as `cache`, `tmp`, `extensions`, `sessions`, and `policies`, and adds `thinkingConfig.thinkingBudget` only when `--effort` is set. |
| `CODEX_HOME` | `codex` adapter | Source home the adapter copies `auth.json` + `config.toml` from. For each run it sets `CODEX_HOME` to a randomized per-run home (isolated `sessions/`) so concurrent Codex reviews don't share session storage; the per-run home is recorded in `session.json` + a review-scoped manifest and reclaimed at Finalize. |
| `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC` | `claude` adapter | Force-set to `1` for every `claude` invocation to keep peer reviews off telemetry paths. Host-set values are overwritten. |

The runner never writes credentials and never promotes secrets into log files. Session files and
error logs contain session IDs, model names, and effort levels — no tokens.

Both adapters inherit the full parent environment (`os.environ.copy()`), so anything your reviewer
CLI normally reads — `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY`, auth cache paths —
continues to work. `agy` reads **no API-key env var**; it authenticates from its cached Google/GCP
(Vertex) login under `~/.gemini/antigravity-cli/` (see [`antigravity.md`](antigravity.md)).
