# Agent Skills

Reusable skills for AI coding agents — Claude Code, Codex, Gemini CLI, and Copilot CLI.

## Skills

### [peer-plan-review](peer-plan-review/)

Send an implementation plan to another AI agent for iterative review. The host agent revises the plan based on reviewer feedback and re-submits until the reviewer approves. Supports all four major coding CLIs as reviewers with session resume, model/effort selection, and structured output parsing.

**Features:**
- Cross-agent review loop (max 5 rounds) with verdict parsing
- Provider-specific adapters: Codex (stdin + JSONL), Gemini (JSON), Claude Code (JSON), Copilot (JSONL)
- Session resume for multi-round context continuity
- Process tree kill on timeout/cancellation
- Automatic model and effort detection from reviewer output

**Usage:** `/peer-plan-review <codex|gemini|claude|copilot> [model] [effort]`

## Installation

### Claude Code

Copy the skill directory into your Claude Code skills folder:

```bash
cp -r peer-plan-review ~/.claude/skills/
```

Or symlink it:

```bash
ln -s "$(pwd)/peer-plan-review" ~/.claude/skills/peer-plan-review
```

Then add the skill to your Claude Code settings (`.claude/settings.json`):

```json
{
  "skills": ["~/.claude/skills/peer-plan-review/SKILL.md"]
}
```

### Codex

The `agents/openai.yaml` file provides the Codex agent configuration.

## License

MIT
