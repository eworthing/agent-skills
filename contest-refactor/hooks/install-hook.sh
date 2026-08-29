#!/bin/bash
# Install / uninstall the contest-refactor pre-commit validator hook.
#
# MERGES into an existing config. It never rewrites a config wholesale, because
# these files hold hooks this tool did not install (e.g. a code-discovery gate)
# and destroying them would be a far worse failure than not installing.
#
#   install-hook.sh claude_code | codex        register the hook
#   install-hook.sh --uninstall <provider>     remove ONLY our entry
#   install-hook.sh --dry-run <provider>       print the merged config, write nothing
#
# Every write takes a timestamped backup first. Portable bash 3.2 + 4+.

set -u

SKILL_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HOOK="$SKILL_ROOT/hooks/precommit-validator"
MARKER="precommit-validator"

usage() { printf 'usage: %s [--uninstall|--dry-run] <claude_code|codex>\n' "$0" >&2; exit 2; }

MODE="install"
case "${1:-}" in
  --uninstall) MODE="uninstall"; shift ;;
  --dry-run)   MODE="dry-run";   shift ;;
  -h|--help)   usage ;;
esac
PROVIDER="${1:-}"
[ -n "$PROVIDER" ] || usage

case "$PROVIDER" in
  claude_code) CONFIG="$HOME/.claude/settings.json" ;;
  codex)       CONFIG="$HOME/.codex/hooks.json" ;;
  *) printf 'error: unsupported provider %s (claude_code|codex)\n' "$PROVIDER" >&2
     printf 'note: opencode uses a plugin, not a hooks config; its blocking\n' >&2
     printf '      capability is not yet demonstrated. See TIER3-PROVIDER-DEMOS.\n' >&2
     exit 2 ;;
esac

[ -f "$HOOK" ] || { printf 'error: hook script missing: %s\n' "$HOOK" >&2; exit 2; }

python3 - "$CONFIG" "$HOOK" "$MODE" "$MARKER" <<'PY'
import json, os, shutil, sys, time

config_path, hook_path, mode, marker = sys.argv[1:5]

if os.path.isfile(config_path):
    try:
        with open(config_path, encoding="utf-8") as fh:
            cfg = json.load(fh)
    except (json.JSONDecodeError, OSError) as exc:
        sys.stderr.write(f"error: cannot parse {config_path}: {exc}\n")
        sys.stderr.write("refusing to touch a config we cannot read back safely.\n")
        raise SystemExit(2) from None
else:
    cfg = {}

hooks = cfg.setdefault("hooks", {})
pre = hooks.setdefault("PreToolUse", [])
if not isinstance(pre, list):
    sys.stderr.write("error: hooks.PreToolUse is not a list; refusing to modify.\n")
    raise SystemExit(2)

ours = [e for e in pre if marker in json.dumps(e)]
theirs = [e for e in pre if marker not in json.dumps(e)]

if mode == "uninstall":
    if not ours:
        print(f"not installed for this provider: {config_path}")
        raise SystemExit(0)
    hooks["PreToolUse"] = theirs
else:
    if ours:
        print(f"already installed ({len(ours)} entry) — no change: {config_path}")
        raise SystemExit(0)
    hooks["PreToolUse"] = theirs + [
        {"matcher": "Bash", "hooks": [{"type": "command", "command": hook_path}]}
    ]

rendered = json.dumps(cfg, indent=2) + "\n"

if mode == "dry-run":
    print(f"--- dry run: {config_path} would become ---")
    print(rendered)
    print(f"(preserved {len(theirs)} pre-existing PreToolUse entr"
          f"{'y' if len(theirs) == 1 else 'ies'} untouched)")
    raise SystemExit(0)

if os.path.isfile(config_path):
    backup = f"{config_path}.bak-{time.strftime('%Y%m%d-%H%M%S')}"
    shutil.copy2(config_path, backup)
    print(f"backup: {backup}")

os.makedirs(os.path.dirname(config_path), exist_ok=True)
tmp = config_path + ".tmp"
with open(tmp, "w", encoding="utf-8") as fh:
    fh.write(rendered)
os.replace(tmp, config_path)
print(f"{'uninstalled from' if mode == 'uninstall' else 'installed into'} {config_path}")
print(f"preserved {len(theirs)} pre-existing PreToolUse entries")
PY
