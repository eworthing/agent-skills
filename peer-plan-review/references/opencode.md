# opencode Reference — peer-plan-review

Source: binary help + model listing, verified April 2026.

## Install

```bash
brew install opencode
# or: npm i -g opencode
```

## Binary

`opencode`

## Headless exec

```bash
opencode run "PROMPT" \
  --format json \
  --dangerously-skip-permissions \
  -m opencode-go/deepseek-v4-pro \
  --variant high
```

- Prompt is a **positional argument** — NOT `-p` (that's `--password` for remote attach)
- `--format json`: JSONL event stream to stdout — required for session ID and text extraction
- `--dangerously-skip-permissions`: auto-approve all permissions without prompting (prevents headless hangs)
- No `--sandbox` or `--permission-mode` flags exist — safety is handled by the `--dangerously-skip-permissions` flag combined with prompt instructions to keep the reviewer read-only

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

Common opencode-go models: `deepseek-v4-pro`, `deepseek-v4-flash`, `kimi-k2.6`, `mimo-v2.5`, `mimo-v2.5-pro`, `qwen3.6-plus`, `minimax-m2.7`, `glm-5.1`

## Reasoning effort

`--variant <level>` — provider-specific, passed through to the model API. Supported values depend on the model:

- DeepSeek V4 models: `low`, `medium`, `high`, `max`
- MiMo V2/V2.5 models: `low`, `medium`, `high`
- Kimi, Qwen, GLM, MiniMax: no variant support (flag silently ignored)

The adapter maps portable `xhigh` → `max`.

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
