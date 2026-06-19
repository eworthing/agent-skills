# Codex CLI Reference — peer-plan-review

Source: Rust source `codex-rs/exec/src/cli.rs`, verified March 2026.

## Install

```bash
npm i -g @openai/codex    # or: brew install --cask codex
```

## Binary

`codex`

## Headless exec

```bash
codex exec \
  --sandbox read-only \
  -c approval_mode=never \
  --json \
  --output-last-message OUTPUT_FILE \
  -
```

- Prompt via **stdin** (the `-` arg reads from stdin)
- **Do NOT use `-p`** — in Codex, `-p` means `--profile`, not prompt
- `--output-last-message` / `-o`: writes final assistant message to file
- `--json`: JSONL event stream to stdout
- `--sandbox read-only`: no file modifications (values: `read-only`, `workspace-write`, `danger-full-access`)
- `-c approval_mode=never`: config override for exec path. **`--ask-for-approval` is TUI-only**, not available on `codex exec`
- Do NOT use `--ephemeral` if you need resume — it prevents session file persistence

## Model

`-m MODEL` or `--model MODEL`

**Default (no `-m`):** Last-used model from user config. On first install, defaults to OpenAI's current flagship model. Available models: `gpt-5.5`, `gpt-5.4`, `gpt-5.4-mini`, `gpt-5.3-codex`, `gpt-5.2`.

## Reasoning effort

`-c model_reasoning_effort=<level>`

Levels: `none`, `minimal`, `low`, `medium`, `high`, `xhigh`

**Default (no effort flag):** Last-used reasoning effort from user config. On first install, defaults to OpenAI's API default for the selected model.

## Resume

```bash
codex exec resume SESSION_ID \
  --json \
  -c approval_mode=never \
  --output-last-message OUTPUT_FILE \
  -
```

- **`--sandbox` is NOT available on `codex exec resume`** — the original session's sandbox policy applies automatically
- `--last`: resume most recent session
- `--all`: include sessions from other directories

## Session ID

Session files live under `$CODEX_HOME/sessions/` (default `~/.codex/sessions/`).
Path pattern: `YYYY/MM/DD/rollout-YYYY-MM-DDThh-mm-ss-{UUID}.jsonl`

Extract the session UUID from the first line of the session file:
`{"type": "session_meta", "payload": {"id": "UUID", "cwd": "...", ...}}`

The `thread_id` from `thread.started` JSONL events is an API thread ID, **not** the local session UUID needed for resume.

`CODEX_HOME` env var overrides `~/.codex`.

**Concurrency isolation.** Because session files live in a single shared
directory keyed only by cwd, two reviews running against the same repo at once
can't be told apart from `~/.codex/sessions/`. The adapter therefore points each
run at its own randomized `CODEX_HOME` (auth + config copied in, isolated
`sessions/`), recorded in the run's `session.json` and a review-scoped manifest.
Resume reuses that home; the home is reclaimed at Finalize (`ppr_paths.py
--cleanup`). On setup failure the adapter fails closed — it disables capture and
runs a fresh `exec` against the inherited home rather than risk a cross-run
binding.

## Additional flags

- `--color never`: machine-friendly output
- `-C DIR`: working directory
- `codex exec review --base main`: dedicated review subcommand
