# peer-plan-review

A Claude Code skill that sends an implementation plan to another AI agent
(Codex, Claude Code, Copilot, opencode, Antigravity `agy`, or Gemini CLI) for
iterative review.
The host agent owns the plan and revises it between rounds; the reviewer
critiques only and never edits files.

Useful when you want a second opinion on a plan before touching code.

## What it does

1. Host snapshots the current plan with line numbers.
2. Adapter invokes the chosen reviewer CLI in read-only mode.
3. Reviewer returns structured findings (`[B1]`, `[N1]`, `VERDICT:`) + reasoning.
4. Host revises the plan, re-runs with `--resume`, repeats up to 5 rounds.
5. Loop ends on `VERDICT: APPROVED` or round limit.

## Layout

```
SKILL.md              agent-facing protocol
references/
  codex.md            Codex CLI reference (install, flags, resume, effort)
  claude-code.md      Claude Code CLI reference
  copilot.md          Copilot CLI reference
  opencode.md         opencode CLI reference
  antigravity.md      Antigravity (agy) reference — experimental, not read-only
  gemini.md           Gemini CLI reference (EOL 2026-06-18; enterprise-only)
  adapter-cli.md      run_review.py flags, session-file contract, env vars
  adversarial.md      prompt additions for adversarial stance
  output-format.md    structured-output template injected into every prompt
  domain-context.md   how to author an optional domain-context block
scripts/
  run_review.py       adapter CLI entrypoint
  ppr_paths.py        thin CLI wrapper over _common/session/paths.py
  _common/            shared modules vendored from /common/common/ via
                      sync_common.py (session I/O, output parsing, summaries,
                      PROVIDERS registry + command builders, model/effort/
                      session extraction, JSONL event logger, process-tree kill)
  tests/              pytest suite
  check_web_search.py manual diagnostic: per-provider headless web-fetch check
  fixtures/           provider output samples for tests
agents/openai.yaml    OpenAI subagent wiring
```

## Quick smoke test

```bash
python3 scripts/run_review.py --self-check                # verify all 6 CLIs
python3 scripts/run_review.py --list-models               # print known aliases
python3 -m pytest scripts/tests/
```

## Requirements

- Python 3.9+ (stdlib only)
- At least one of: `codex`, `claude`, `copilot`, `opencode`, `agy` (Antigravity), or `gemini` CLI on `$PATH`
- Reviewer auth configured via each CLI's normal mechanism

Cross-platform: macOS, Linux, Windows.
