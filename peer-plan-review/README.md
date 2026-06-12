# peer-plan-review

A Claude Code skill that sends an implementation plan to another AI agent
(Codex, Gemini CLI, Claude Code, Copilot, opencode, or Antigravity) for
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
  gemini.md           Gemini CLI reference
  claude.md           Claude Code CLI reference
  copilot.md          Copilot CLI reference
  opencode.md         opencode CLI reference
  antigravity.md      Antigravity CLI (agy) reference — Gemini CLI's successor
  adapter-cli.md      run_review.py flag list and session-file contract
  adversarial.md      prompt additions for adversarial stance
  output-format.md    structured-output template injected into every prompt
  env.md              env vars read by the runner
scripts/
  run_review.py       adapter CLI entrypoint
  ppr_paths.py        canonical temp-path helper (thin CLI over _common.session.paths)
  _common/            shared infrastructure vendored from /common/common/
                      (providers registry, session I/O + paths, metadata
                      extraction, JSONL event log, process-tree kill);
                      regenerate with: python3 common/scripts/sync_common.py
  test_run_review.py  pytest suite (120 tests)
  check_web_search.py manual web-search diagnostic (invokes real CLIs; not pytest)
  fixtures/           provider output samples for tests
agents/openai.yaml    OpenAI subagent wiring
```

## Quick smoke test

```bash
python3 scripts/run_review.py --self-check                # verify all 6 CLIs
python3 scripts/run_review.py --list-models               # print known aliases
cd scripts && python3 -m pytest test_run_review.py
```

## Requirements

- Python 3.9+ (stdlib only)
- At least one of: `codex`, `gemini`, `claude`, `copilot`, `opencode`, `agy` CLI on `$PATH`
- Reviewer auth configured via each CLI's normal mechanism

Cross-platform: macOS, Linux, Windows.
