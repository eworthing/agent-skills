#!/usr/bin/env bash
# audit-churn.sh — top-N most-churned source files over a time window
#
# Usage: scripts/audit-churn.sh [<repo-root>] [<since>] [<top-N>]
# Defaults: cwd, "6 months ago", 20.
#
# Output: markdown table to stdout. Columns: rank, edits, path.
# Filters to source-code extensions: swift, ts, tsx, js, jsx, py, rs, go, java, kt.
# Portable Bash (macOS 3.2 + Linux 4+). Requires git in PATH.

set -u

ROOT="${1:-.}"
SINCE="${2:-6 months ago}"
TOP_N="${3:-20}"

if ! command -v git >/dev/null 2>&1; then
  echo "audit-churn: git not in PATH" >&2
  exit 2
fi

if [ ! -d "$ROOT/.git" ] && ! git -C "$ROOT" rev-parse --git-dir >/dev/null 2>&1; then
  echo "audit-churn: $ROOT is not a git repository" >&2
  exit 2
fi

# Source-dir candidates — first match wins. Use indexed array so paths with
# spaces survive (`set --` + "$@" pattern; portable to bash 3.2).
set --
for d in Sources src lib app pkg internal; do
  if [ -d "$ROOT/$d" ]; then
    set -- "$@" "$d"
  fi
done

# Nested SPM (BenchHypeKit/Sources/, etc.). NUL-delimited find -> while-read
# keeps paths-with-spaces intact.
while IFS= read -r d; do
  [ -z "$d" ] && continue
  rel="${d#"$ROOT"/}"
  # Skip if already collected
  already=0
  for existing in "$@"; do
    [ "$existing" = "$rel" ] && already=1 && break
  done
  [ "$already" = "1" ] && continue
  set -- "$@" "$rel"
done <<EOF
$(find "$ROOT" -maxdepth 3 -type d -name 'Sources' 2>/dev/null | head -3)
EOF

if [ "$#" -eq 0 ]; then
  echo "audit-churn: no source dirs (Sources/, src/, lib/, app/, pkg/, internal/) found under $ROOT" >&2
  exit 2
fi

# Gather churn — git log --name-only across source paths. "$@" preserves
# per-path quoting.
churn=$(git -C "$ROOT" log --since="$SINCE" --name-only --pretty=format: -- "$@" 2>/dev/null \
  | grep -E '\.(swift|ts|tsx|js|jsx|py|rs|go|java|kt)$' \
  | sort \
  | uniq -c \
  | sort -rn \
  | head -"$TOP_N")

if [ -z "$churn" ]; then
  echo "audit-churn: no source-file edits since '$SINCE' in source dirs: $*" >&2
  exit 0
fi

echo "| Rank | Edits | Path |"
echo "|---|---|---|"

rank=1
echo "$churn" | while IFS= read -r line; do
  edits=$(echo "$line" | awk '{print $1}')
  path=$(echo "$line" | awk '{$1=""; sub(/^ /, ""); print}')
  echo "| $rank | $edits | $path |"
  rank=$((rank + 1))
done
