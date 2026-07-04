#!/usr/bin/env bash
# audit-hardcoded-tokens.sh — Static audit for hardcoded design values that
# should be design tokens.
#
# Scans Swift files for the high-frequency violations documented in
# swiftui-design-tokens/SKILL.md § Auditing for Hardcoded Values:
#
#   C1. Hardcoded colors — Color.black/.white/... .opacity(), Color(red:/#/...),
#       UIColor(...). Should be semantic Palette.* tokens with Asset Catalog
#       light/dark variants.
#   C2. Raw type scale — Font.system(size:) literals instead of TypeScale.*.
#   C3. Magic spacing — .padding(<number>) literals instead of Metrics.spacing*.
#
# Output format (matches apple-multiplatform's standardized error output):
#   DTOKEN-FAIL <category> <file>:<line>: <message>
#
# Exit status: 0 = no hits, 1 = one or more hits, 2 = usage error.
#
# Engine is grep -E only (POSIX/BSD/GNU all ship it) — no ripgrep dependency,
# no mapfile, no GNU-only flags. Portable to macOS bash 3.2 + Linux bash 4+.

set -u

usage() {
  echo "usage: $0 [path]" >&2
  echo "  path defaults to the current directory." >&2
  echo "  Files under a Design/ directory are skipped (token definitions)." >&2
  exit 2
}

[ "$#" -le 1 ] || usage
ROOT="${1:-.}"
[ -d "$ROOT" ] || { echo "error: $ROOT is not a directory" >&2; exit 2; }

# grep invocation as an array so `--include='*.swift'` is not filename-expanded
# when the command is later expanded. Bash 3.2 supports arrays.
GREP_CMD=(grep -rnE --include='*.swift')

# Emit one diagnostic in the standardized format.
emit() {
  category="$1"
  location="$2"
  message="$3"
  printf 'DTOKEN-FAIL %s %s: %s\n' "$category" "$location" "$message"
}

# Run one pattern, emit a finding per matching line. Token-definition files
# (any path containing /Design/) are expected to hold raw values, so skip them.
# The pipe runs this in a subshell, so the running total is computed separately
# by count() below for the exit status.
scan() {
  category="$1"
  pattern="$2"
  message="$3"
  "${GREP_CMD[@]}" "$pattern" "$ROOT" 2>/dev/null | while IFS= read -r line; do
    file=$(printf '%s' "$line" | awk -F: '{print $1}')
    case "$file" in
      */Design/*|Design/*) continue ;;
    esac
    lineno=$(printf '%s' "$line" | awk -F: '{print $2}')
    emit "$category" "$file:$lineno" "$message"
  done
}

# The while-read loop above runs in a subshell (pipe), so its HITS increments
# do not propagate. Recompute the total from a final count instead.
count() {
  category="$1"
  pattern="$2"
  n=$("${GREP_CMD[@]}" "$pattern" "$ROOT" 2>/dev/null \
    | awk -F: '{print $1}' \
    | grep -vE '(^|/)Design/' \
    | wc -l | tr -d ' ')
  echo "$n"
}

C1A='Color\.(black|white|gray|red|blue|green|orange|yellow|pink|purple)\.opacity\('
C1B='Color\((red:|white:|hue:)|Color\(#|UIColor\('
C2='Font\.system\(size:'
C3='\.padding\([0-9]'

scan HARDCODED-COLOR "$C1A" "hardcoded color with opacity — use a semantic Palette.* token"
scan HARDCODED-COLOR "$C1B" "raw Color/UIColor literal — use a semantic Palette.* token"
scan RAW-FONT        "$C2"  "raw Font.system(size:) — use a TypeScale.* token"
scan MAGIC-SPACING   "$C3"  "numeric padding literal — use a Metrics.spacing* token"

TOTAL=0
for pat in "$C1A" "$C1B" "$C2" "$C3"; do
  n=$(count X "$pat")
  TOTAL=$((TOTAL + n))
done

if [ "$TOTAL" -gt 0 ]; then
  printf '\n%s hit(s). Expected false positives (Design/ token files, SwiftUI\n' "$TOTAL" >&2
  printf 'previews, Color.clear spacers, user-selectable presets) are documented\n' >&2
  printf 'in swiftui-design-tokens/SKILL.md.\n' >&2
  exit 1
fi

echo "No hardcoded design-token violations found."
exit 0
