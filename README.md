# Agent Skills

Reusable skills for AI coding agents — Claude Code, Codex CLI, opencode, Gemini CLI, and Copilot CLI.

## Skills

### [bash-macos](bash-macos/)

Keeps shell scripts portable across macOS (Bash 3.2, BSD userland) and Linux (Bash 4+, GNU coreutils). Use when writing or editing `.sh` files, debugging "command not found" / "invalid option" / "mapfile: command not found" errors, fixing GNU-vs-BSD `sed`/`grep`/`date`/`readlink` issues, or renaming shell scripts (snake_case verb-first).

### [contest-refactor](contest-refactor/)

Triggers an autonomous Actor-Critic refactoring loop against the current codebase. Aggressively refactors the workspace to a 9.5+ standard using a strict ICA-grounded architectural rubric (deletion test, two-adapter rule, depth-as-leverage). Use when you invoke `/contest-refactor` or request an Actor-Critic iterative refactor.

### [peer-plan-review](peer-plan-review/)

Sends an implementation plan to another AI agent (Codex, Gemini CLI, Claude Code, Copilot, or opencode) for iterative review, then revises and re-submits until the reviewer approves or the round limit is reached.

**Features:**
- Cross-agent review loop (max 5 rounds) with verdict parsing
- Provider adapters: Codex (stdin + JSONL), Gemini (JSON), Claude Code (JSON), Copilot (JSONL), opencode
- Session resume for multi-round context continuity
- Process tree kill on timeout/cancellation
- Automatic model + effort detection from reviewer output

**Usage:** `/peer-plan-review <codex|gemini|claude|copilot|opencode> [model] [effort]`

### [quorum-review](quorum-review/)

Multi-provider consensus review system (v3). Orchestrates anonymous quorum reviews for plans, specs, and code diffs with canonical issue IDs, conservative merges, and an independent verifier.

### [swift-linting](swift-linting/)

Resolves SwiftFormat and SwiftLint issues and explains repository formatting rules. Use when pre-commit hooks fail, commits are blocked by formatting or lint errors, or code changes require `swiftlint:disable`, function-body cleanup, or formatting adjustments.

### [swift-file-splitting](swift-file-splitting/)

Splits oversized Swift files into smaller units while preserving visibility and build correctness. Use when a Swift file nears the SwiftLint `file_length` limit, when SwiftLint reports a `file_length` violation, or when extracting types or extensions into new files.

## Installation

All three CLI agents discover skills from a per-user skills directory. Symlink the skills you want — this keeps a single source of truth in the repo and lets edits propagate to every agent immediately.

```bash
SRC="$(pwd)"     # run from this repo's root
SKILL=peer-plan-review   # repeat per skill

# Claude Code
ln -s "$SRC/$SKILL" "$HOME/.claude/skills/$SKILL"

# Codex CLI
ln -s "$SRC/$SKILL" "$HOME/.codex/skills/$SKILL"

# opencode
ln -s "$SRC/$SKILL" "$HOME/.config/opencode/skills/$SKILL"
```

To install every skill in this repo into all three agents:

```bash
SRC="$(pwd)"
for skill in bash-macos contest-refactor peer-plan-review quorum-review swift-linting swift-file-splitting; do
  for dest in "$HOME/.claude/skills" "$HOME/.codex/skills" "$HOME/.config/opencode/skills"; do
    [ -e "$dest/$skill" ] && continue   # don't clobber existing entries
    ln -s "$SRC/$skill" "$dest/$skill"
  done
done
```

Codex also accepts the `agents/openai.yaml` configuration if you prefer YAML-declared agents.

## Repo Conventions

- One directory per skill at the repo root.
- Each skill has `SKILL.md` (frontmatter + body), optional `references/` (progressive disclosure), and optional `scripts/` (helper executables).
- Shell scripts target portable Bash (macOS 3.2 + Linux 4+) — see [`bash-macos`](bash-macos/).
- Each skill ships an `EVAL.md` scored against the multi-framework rubric in the local `skill-evaluator` plugin (target ≥ 90/100 before publishing).

## License

MIT
