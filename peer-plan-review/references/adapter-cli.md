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
  (alias `antigravity`; experimental — not guaranteed read-only, see
  [`antigravity.md`](antigravity.md)). Required.
- `--resume`: include on rounds 2+ only. The runner falls back to a fresh
  execution once if resume fails with no usable output.
- `--model`: provider-specific model ID or known alias. `--list-models
  --reviewer <provider>` prints the known aliases.
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

See `references/env.md` for env vars the runner reads
(`GEMINI_CONFIG_DIR`, `CODEX_HOME`, `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC`).
