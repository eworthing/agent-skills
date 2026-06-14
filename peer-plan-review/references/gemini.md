# Gemini CLI Reference — peer-plan-review

> ⚠️ **EOL 2026-06-18.** Google retires the legacy Gemini CLI on June 18, 2026.
> **Free/individual users lose access** (the CLI stops responding after that
> date). **Enterprise users keep it** — accounts with Gemini Code Assist
> Standard/Enterprise licenses or paid Gemini/Vertex API keys retain
> uninterrupted access. The successor is the **Antigravity CLI (`agy`)** — see
> [`antigravity.md`](antigravity.md). Prefer `agy` unless you depend on
> enterprise Gemini access; this provider is retained for enterprise users.

Source: TS source `packages/cli/src/config/config.ts` (v0.33.1, March 2026). Local binary observed: v0.43.0 — flag docs below are from the v0.33.1 verification.

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
  --approval-mode yolo \
  --output-format json \
  -p "PROMPT"
```

- **`-p` is REQUIRED for headless** — positional prompt defaults to interactive mode in TTY
- Cannot combine positional prompt and `-p`
- `--sandbox` / `-s`: filesystem sandbox
- `--approval-mode`: `default`, `auto_edit`, `yolo`, `plan` (4 values)
- **Use `yolo` for review** — `plan` and `auto_edit` hang on URL fetch permission prompts in headless mode; `yolo` auto-approves tools while `--sandbox` still prevents filesystem writes
- `--output-format`: `text`, `json`, `stream-json` (alias `-o`)
- Redirect stdout to capture output

## JSON response fields

`session_id`, `response`, `stats`, `error`

Stream-json events: `init`, `message`, `tool_use`, `tool_result`, `error`, `result`

## Model

`-m MODEL` (aliases: `auto`, `pro`, `flash`, `flash-lite`)

Concrete model IDs can also be passed directly (e.g., `gemini-3.1-pro-preview`, `gemini-3-flash-preview`).

**Default (no `-m`):** `gemini-3-flash-preview` (verified April 2026).

## Reasoning effort

No CLI flag. Use settings file with `thinkingConfig.thinkingBudget` (integer token count, default 8192) or `thinkingLevel: "HIGH"` (Gemini 3.x).

**Default (no effort flag):** `thinkingBudget: 8192` from Gemini's default `settings.json`. The skill only overlays effort when `--effort` is explicitly passed.

**Effort overlay works for all Gemini 3.x models** including `gemini-3.1-pro-preview` and `gemini-3-flash-preview`. The skill maps portable effort levels to thinking budgets: `low` → 2048, `medium` → 8192, `high` → 16384, `xhigh` → 32768.

Adapter builds a temp config overlay from top-level files in the real config dir (`$GEMINI_CONFIG_DIR` or `~/.gemini`) and points `GEMINI_CONFIG_DIR` at the overlay for every Gemini run. The overlay preserves auth (`oauth_creds.json`) and durable settings, excludes config subdirectories such as `cache`, `tmp`, `extensions`, `sessions`, and `policies`, and overlays `thinkingConfig` into `settings.json` only when `--effort` is explicitly passed.

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
