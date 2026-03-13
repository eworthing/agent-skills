# Gemini CLI Reference — peer-plan-review

Source: TS source `packages/cli/src/config/config.ts` (v0.33.1), verified March 2026.

## Install

```bash
npm i -g @google/gemini-cli    # or: brew install gemini-cli, npx @google/gemini-cli
```

## Binary

`gemini`

## Headless exec

```bash
gemini \
  --sandbox \
  --approval-mode plan \
  --output-format json \
  -p "PROMPT"
```

- **`-p` is REQUIRED for headless** — positional prompt defaults to interactive mode in TTY
- Cannot combine positional prompt and `-p`
- `--sandbox` / `-s`: filesystem sandbox
- `--approval-mode`: `default`, `auto_edit`, `yolo`, `plan` (4 values)
- **Use `plan` for review-only** — `default` allows tool use with prompting; `plan` is read-only mode
- `--output-format`: `text`, `json`, `stream-json` (alias `-o`)
- Redirect stdout to capture output

## JSON response fields

`session_id`, `response`, `stats`, `error`

Stream-json events: `init`, `message`, `tool_use`, `tool_result`, `error`, `result`

## Model

`-m MODEL` (aliases: `auto`, `pro`, `flash`, `flash-lite`)

## Reasoning effort

No CLI flag. Use settings file with `thinkingConfig.thinkingBudget` (integer token count, default 8192) or `thinkingLevel: "HIGH"` (Gemini 3.x).

Adapter clones the real config dir (`$GEMINI_CONFIG_DIR` or `~/.gemini`) to a temp directory, overlays the effort `thinkingConfig` into the existing `settings.json`, and points `GEMINI_CONFIG_DIR` at the clone. This preserves auth (`oauth_creds.json`), extensions, and other state.

## Resume

`--resume SESSION_ID` or `--resume INDEX` or `-r` for latest.
`--list-sessions` to enumerate.

## Exit codes

0=success, 1=generic, 41=auth, 42=input, 44=sandbox, 52=config, 53=turn-limit, 54=tool-exec, 130=cancelled

## Additional flags

- `--extensions ""`: disable all extensions
- `--allowed-mcp-server-names`: restrict MCP servers
- `--include-directories`: add directories to context
- `--yolo` / `-y`: legacy shortcut for `--approval-mode=yolo`
