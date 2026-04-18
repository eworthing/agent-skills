# peer-plan-review

A Claude Code skill that sends an implementation plan to another AI agent
(Codex, Gemini CLI, Claude Code, or Copilot) for iterative review. The host
agent owns the plan and revises it between rounds; the reviewer critiques only
and never edits files.

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
  env.md              env vars read by the runner
scripts/
  run_review.py       adapter CLI entrypoint
  ppr_io.py           session I/O, output parsing, summaries
  ppr_providers.py    provider command builders
  ppr_metadata.py     model/effort/session extraction
  ppr_log.py          structured JSONL event logger
  test_run_review.py  84-test pytest suite
  fixtures/           provider output samples for tests
agents/openai.yaml    OpenAI subagent wiring
```

## Quick smoke test

```bash
python3 scripts/run_review.py --self-check                 # verify all 4 CLIs
python3 scripts/run_review.py --list-models                # print known aliases
cd scripts && python3 -m pytest test_run_review.py        # run suite
```

## Requirements

- Python 3.9+ (stdlib only)
- At least one of: `codex`, `gemini`, `claude`, `copilot` CLI on `$PATH`
- Reviewer auth configured via each CLI's normal mechanism

Cross-platform: macOS, Linux, Windows.
