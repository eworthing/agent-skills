#!/usr/bin/env bash
# install-global.sh — expose code-review-opencode to every OpenCode project.
#
# OpenCode discovers global plugins under ~/.config/opencode/plugins/ and
# global agents under ~/.config/opencode/agents/. Both entries here are
# symlinks into this checkout, so source edits are visible immediately.
#
# Usage:
#   scripts/install-global.sh            # create or refresh the symlinks
#   scripts/install-global.sh --check    # verify the links without changing them
#   scripts/install-global.sh --uninstall
set -eu

PROG=$(basename "$0")
ROOT=$(cd "$(dirname "$0")/.." && pwd)
CONFIG_DIR=${XDG_CONFIG_HOME:-$HOME/.config}/opencode
PLUGIN_SRC="$ROOT/.opencode/plugins/code-review-opencode"
AGENT_SRC="$ROOT/.opencode/agents"
PLUGIN_LINK="$CONFIG_DIR/plugins/code-review-opencode"

die() {
  echo "$PROG: $*" >&2
  exit 1
}

check_source() {
  [ -d "$PLUGIN_SRC" ] || die "plugin source not found: $PLUGIN_SRC"
  [ -d "$AGENT_SRC" ] || die "agent source not found: $AGENT_SRC"
}

# Refuse to replace a real directory or file. Only a missing path or an
# existing symlink is safe to (re)point.
link_path() {
  target=$1
  link=$2
  if [ -e "$link" ] && [ ! -L "$link" ]; then
    die "refusing to replace non-symlink path: $link"
  fi
  mkdir -p "$(dirname "$link")"
  ln -sfn "$target" "$link"
  printf '%s -> %s\n' "$link" "$target"
}

check_link() {
  target=$1
  link=$2
  [ -L "$link" ] || die "missing symlink: $link"
  actual=$(readlink "$link")
  [ "$actual" = "$target" ] || die "wrong target: $link -> $actual (expected $target)"
  printf 'ok: %s -> %s\n' "$link" "$target"
}

install_all() {
  check_source
  link_path "$PLUGIN_SRC" "$PLUGIN_LINK"
  for agent in "$AGENT_SRC"/*.md; do
    [ -e "$agent" ] || continue
    link_path "$agent" "$CONFIG_DIR/agents/$(basename "$agent")"
  done
}

check_all() {
  check_source
  check_link "$PLUGIN_SRC" "$PLUGIN_LINK"
  for agent in "$AGENT_SRC"/*.md; do
    [ -e "$agent" ] || continue
    check_link "$agent" "$CONFIG_DIR/agents/$(basename "$agent")"
  done
}

uninstall_all() {
  # Remove only links that still point into this checkout.
  for link in "$PLUGIN_LINK" "$CONFIG_DIR"/agents/review-*.md; do
    [ -L "$link" ] || continue
    case $(readlink "$link") in
      "$ROOT"/*) rm -f "$link"; printf 'removed %s\n' "$link" ;;
    esac
  done
}

case "${1-}" in
  "") install_all ;;
  --check) check_all ;;
  --uninstall) uninstall_all ;;
  *)
    echo "usage: $PROG [--check|--uninstall]" >&2
    exit 2
    ;;
esac
