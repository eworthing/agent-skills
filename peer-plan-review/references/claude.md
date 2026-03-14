# Claude Code Reference — peer-plan-review

Source: Official docs at code.claude.com, verified March 2026.

## Install

```bash
curl -fsSL https://claude.ai/install.sh | bash
# or: npm i -g @anthropic-ai/claude-code (deprecated)
```

## Binary

`claude`

## Headless exec

```bash
CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1 \
claude -p "PROMPT" \
  --permission-mode plan \
  --tools "Read,Grep,Glob,WebSearch,WebFetch" \
  --allowedTools "WebSearch,WebFetch" \
  --output-format json \
  --max-turns 10 \
  --no-session-persistence \
  --append-system-prompt "You are a code reviewer. Analyze the plan and provide feedback. End with VERDICT: APPROVED or VERDICT: REVISE on the last line."
```

- `-p "prompt"` / `--print "prompt"`: runs once and exits (no interactive TUI)
- `--permission-mode plan`: read-only mode — no file modifications or command execution
- `--tools "Read,Grep,Glob,WebSearch,WebFetch"`: available tools (belt-and-suspenders with plan mode)
- `--allowedTools "WebSearch,WebFetch"`: auto-approve web tools without prompting (prevents headless hangs)
- `--output-format`: `text`, `json`, `stream-json`
- `--max-turns N`: limits agentic turns
- `--no-session-persistence`: ephemeral session
- `--append-system-prompt "..."`: adds to defaults (preferred over `--system-prompt` which replaces)

## JSON response fields

`result`, `session_id`, `structured_output` (if `--json-schema` used)

## Model

`--model sonnet|opus|haiku|<full-id>` (e.g., `claude-opus-4-6`). `--fallback-model` for overload fallback.

## Reasoning effort

`--effort <level>`: `low`, `medium`, `high`, `max` (default `medium` for Opus 4.6).

`xhigh` maps to `max` (Claude's highest level).

Legacy: `CLAUDE_CODE_EFFORT_LEVEL` env var also works but prefer the CLI flag.

## Resume

`--resume <id>` / `-r <id>`: specific session. `--continue` / `-c`: most recent.

## Script-friendly env vars

- `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1`: suppress telemetry
- `DISABLE_AUTOUPDATER=1`: no auto-update
- `CLAUDE_CODE_DISABLE_TERMINAL_TITLE=1`: no terminal title changes
- `ANTHROPIC_API_KEY`: required for auth

## Additional flags

- `--disallowedTools "Edit,Write,Bash"`: remove tools from context
- `--allowedTools`: auto-approve without prompting
- `--max-budget-usd N.NN`: spend cap
- `--add-dir`: additional directories
- `--worktree` / `-w`: isolated git worktree
- `--debug`: verbose logging
