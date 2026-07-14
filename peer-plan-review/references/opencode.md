# opencode Reference — peer-plan-review

Source: binary help + model listing, verified 2026-06-29.

## Install

```bash
brew install opencode
# or: npm i -g opencode
```

## Binary

`opencode`

## Headless exec

```bash
OPENCODE_PERMISSION='{"edit":"deny","bash":"deny","task":"deny","external_directory":"deny","question":"deny"}' \
  opencode run "" \
  --format json \
  --auto \
  -m opencode-go/deepseek-v4-pro \
  --variant high
```

- Prompt text is piped through stdin; the empty positional message keeps `run`
  out of interactive mode.
- `--format json` emits the JSONL event stream required for session and text
  extraction.
- `--auto` approves requests that are not explicitly denied; the adapter's
  `OPENCODE_PERMISSION` value denies edit, shell, nested-task, external-directory,
  and interactive-question tools.
- OpenCode permissions are application-level controls, not an OS sandbox. Keep
  the reviewer prompt read-only as defense in depth.

## JSONL event types

```
{"type": "step_start", "sessionID": "ses_...", "part": {...}}
{"type": "reasoning", "sessionID": "ses_...", "part": {"type": "reasoning", "text": "..."}}
{"type": "text", "sessionID": "ses_...", "part": {"type": "text", "text": "..."}}
{"type": "step_finish", "sessionID": "ses_...", "part": {"type": "step-finish", "tokens": {...}}}
{"type": "error", "sessionID": "ses_...", "error": {"name": "...", "data": {...}}}
```

- `text` events contain the assistant response — collect all for review content
- `reasoning` events contain internal thinking — skipped during text extraction
- `sessionID` is present on every event — extract from the first line
- Model info is **not** in the JSONL stream — use `opencode export <sessionID>` to retrieve it

## Model

`-m provider/model` (e.g., `-m opencode-go/deepseek-v4-pro`)

List available models: `opencode models opencode-go`

Common opencode-go models (live, verified 2026-06-29): `deepseek-v4-pro`, `deepseek-v4-flash`, `glm-5.2`, `glm-5.1`, `kimi-k2.6`, `kimi-k2.7-code`, `mimo-v2.5`, `mimo-v2.5-pro`, `minimax-m3`, `minimax-m2.7`, `qwen3.7-plus`, `qwen3.7-max`, `qwen3.6-plus`

**Default (no `-m`):** Last-used model from the current project session. If no prior session exists, falls back to the provider's configured default (verified April 2026: `opencode-go/qwen3.6-plus`).

## Reasoning effort

`--variant <level>` — provider-specific, passed through to the model API. Supported values depend on the model:

- DeepSeek V4 models: `low`, `medium`, `high`, `max`
- MiMo V2/V2.5 models: `low`, `medium`, `high`
- Kimi, Qwen, GLM, MiniMax: no variant support (flag silently ignored)

The adapter maps portable `xhigh` → `max`.

**Default (no effort flag):** Model-dependent. Many opencode-go models ignore `--variant` entirely. No effort is injected by the skill when unspecified.

## Resume

`-s <sessionID>` — continue a specific session. Use without `--fork` to stay in the same session.

`-c` — continue the most recent session (shorthand).

`--fork` — fork the session before continuing (creates a new session ID). Do NOT use for peer review rounds — the adapter needs the same session for context continuity.

## Session management

`opencode session list` — list all sessions with IDs and titles.

`opencode export <sessionID>` — export full session data as JSON (messages, model info, permissions). Used by the adapter to extract actual model/variant metadata after a run.

`opencode import <file>` — import a session from JSON.

## Auth

`opencode providers` / `opencode auth` — manage provider credentials.

## Additional flags

- `--agent <name>` — use a specific agent profile (build, plan, general, explore)
- `--dir <path>` — working directory
- `--thinking` — show reasoning/thinking blocks in output
- `--file <path>` — attach files to the message (repeatable)
- `--title <text>` — session title
- `--port <n>` — port for local server
