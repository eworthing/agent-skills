# Copilot CLI Reference — peer-plan-review

Source: GitHub docs, GA Feb 2026, verified March 2026.

## Install

```bash
npm i -g @github/copilot
# or: brew install copilot-cli, curl -fsSL https://gh.io/copilot-install | bash
```

## Binary

`copilot`

## Headless exec

```bash
copilot -p "PROMPT" -s \
  --no-ask-user \
  --yolo \
  --deny-tool=write,shell,memory \
  --no-custom-instructions \
  --no-auto-update \
  --output-format json
```

- `--output-format json`: JSONL event stream to stdout — required for session ID extraction and structured text capture
- `-p "prompt"` / `--prompt="prompt"`: run once and exit
- `-s` / `--silent`: suppress stats/decoration, agent response only
- `--no-ask-user`: disables `ask_user` tool (prevents interactive pauses)
- `--no-custom-instructions`: skip repo `AGENTS.md`
- `--no-auto-update`: prevent update prompts

**Do NOT use `--autopilot`:** It enables built-in tools (`report_intent`,
`task_complete`, `skill`, `sql`) that cause Copilot to encrypt response
content (`encryptedContent` populated, `content` empty in JSONL) and skip
producing visible review text. Without `--autopilot`, Copilot outputs
the review directly with populated `content` fields.

## Tool permissions

- `--allow-tool=TOOL,...` and `--deny-tool=TOOL,...` (deny takes precedence)
- Tool kinds: `shell`, `write`, `read`, `url`, `memory`, plus MCP server names
- Built-in tools (not in categories): `skill`, `sql`, `report_intent`, `task_complete`
- For review: `--yolo --deny-tool=write,shell,memory`
  (`--allow-tool=url` alone hangs on URL fetch permission prompts in headless;
  `--yolo` auto-approves all tools while `--deny-tool` still blocks write/shell/memory;
  intermediate messages may have encrypted content, but the final `assistant.message`
  has populated `content` — text extraction works by filtering empty-content messages)
- **URL blocking**: `--deny-tool=url` for blanket deny. **NOT `--deny-url`** which requires domain args.

## Model

`--model MODEL` or `COPILOT_MODEL` env var

**Default (no `--model`):** `GPT-5.4 mini` (verified April 2026).

## Reasoning effort

`--reasoning-effort low|medium|high|xhigh` (confirmed v1.0.5, direct 1:1 mapping)

**Default (no effort flag):** Last-used reasoning effort from user config. On first install, defaults to `medium`.

## Resume

`--continue`: most recent session. `--resume=SESSION-ID`: specific session.
`--resume` without ID shows interactive picker.

Resume works correctly without `--autopilot`. The adapter uses `--resume`
for rounds 2+ to preserve conversation context.

## Output

`--output-format text|json` (JSONL when json; no `stream-json`)

JSONL event types used by the adapter:
- `{"type": "result", "sessionId": "..."}` — session ID for resume
- `{"type": "assistant.message", "data": {"content": "..."}}` — response text

## Auth

Keychain preferred. Env precedence: `COPILOT_GITHUB_TOKEN` > `GH_TOKEN` > `GITHUB_TOKEN` > keychain > `gh auth token`.
`--secret-env-vars=VAR,...`: redact specific env var values from output.

## Additional flags

- `--no-color`: machine-friendly output
- `--autopilot`: multi-step autonomous continuation (**avoid** — see above)
- `--max-autopilot-continues=COUNT`: safety cap on autonomous steps
- `--available-tools=TOOL,...`: whitelist-only (too restrictive — blocks core infrastructure)
- `--excluded-tools=TOOL,...`: blacklist
- `--config-dir=PATH`: CI isolation
- `--share=PATH`: export transcript
- `--add-dir=PATH`: additional directories
- `--log-level=LEVEL`: logging verbosity
- `--yolo`: alias for `--allow-all`
