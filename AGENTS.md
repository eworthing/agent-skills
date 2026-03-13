# Local Development

## Setup

For local development, symlink each skill directory into `~/.claude/skills/` so that edits in the repo are immediately picked up by Claude Code:

```bash
ln -s /Users/Shared/git/agent-skills/peer-plan-review ~/.claude/skills/peer-plan-review
```

Do **not** use `cp -r` for local dev — copied directories require re-copying after every change.

Do **not** use `npx skills add` for local dev — it clones from GitHub into a managed cache and won't reflect local edits.

## Verifying the symlink

```bash
ls -la ~/.claude/skills/peer-plan-review
# Should show: -> /Users/Shared/git/agent-skills/peer-plan-review
```

Changes take effect in the next Claude Code session (no restart of the current session needed).

## Adding a new skill

1. Create a new directory in this repo with a `SKILL.md` at its root.
2. Symlink it into `~/.claude/skills/`:
   ```bash
   ln -s /Users/Shared/git/agent-skills/<skill-name> ~/.claude/skills/<skill-name>
   ```
3. Add the skill path to `.claude/settings.json` if not already present.

## Distribution

For installing on other machines (not local dev), use the copy or `npx skills add` methods documented in the README.
