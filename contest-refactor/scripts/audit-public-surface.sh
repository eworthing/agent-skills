#!/usr/bin/env bash
# audit-public-surface.sh — flag public Swift declarations with no cross-module callers
#
# Usage: scripts/audit-public-surface.sh [<repo-root>]
# Default: current working directory.
#
# Walks Sources/<Module>/ looking for `public` decls, then greps sibling
# Sources/ modules for use sites. Reports decls with zero cross-module use sites.
#
# Stack: Apple / SPM. Output: markdown table to stdout.
# Portable Bash (macOS 3.2 + Linux 4+). No mapfile/readarray; no GNU-only flags.

set -u

ROOT="${1:-.}"
SOURCES_DIR="$ROOT/Sources"

if [ ! -d "$SOURCES_DIR" ]; then
  # Try nested SPM layout (e.g. BenchHypeKit/Sources/)
  alt=$(find "$ROOT" -maxdepth 3 -type d -name 'Sources' 2>/dev/null | head -1)
  if [ -n "$alt" ]; then
    SOURCES_DIR="$alt"
  else
    echo "audit-public-surface: no Sources/ directory under $ROOT" >&2
    exit 2
  fi
fi

TMP_MODULES=$(mktemp -t audit-public-surface-modules.XXXXXX)
trap 'rm -f "$TMP_MODULES"' EXIT INT TERM HUP

# Enumerate module directories
find "$SOURCES_DIR" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | sort > "$TMP_MODULES"
if [ ! -s "$TMP_MODULES" ]; then
  echo "audit-public-surface: no modules under $SOURCES_DIR" >&2
  exit 2
fi

echo "| Module | Symbol | Decl site | Cross-module uses |"
echo "|---|---|---|---|"

flagged_count=0

# Iterate modules
while IFS= read -r module_dir; do
  [ -z "$module_dir" ] && continue
  module=$(basename "$module_dir")

  # Find public decls — match common public keyword positions:
  #   public func, public class, public struct, public enum, public protocol,
  #   public actor, public typealias, public var, public let, public init,
  #   public extension, public static.
  decls=$(grep -rnE '^[[:space:]]*public[[:space:]]+(func|class|struct|enum|protocol|actor|typealias|var|let|init|extension|static)' \
    "$module_dir" 2>/dev/null | grep -v '/\.build/' | grep -v '/Tests/')

  if [ -z "$decls" ]; then
    continue
  fi

  # For each decl, extract the symbol name (best-effort) and count cross-module uses
  echo "$decls" | while IFS= read -r decl_line; do
    decl_file=$(echo "$decl_line" | cut -d: -f1)
    decl_lineno=$(echo "$decl_line" | cut -d: -f2)
    decl_text=$(echo "$decl_line" | cut -d: -f3-)

    # Symbol-name heuristic: strip leading whitespace + "public ", then strip
    # the kind keyword (func/class/...), then take the next identifier.
    symbol=$(echo "$decl_text" \
      | sed -E 's/^[[:space:]]*public[[:space:]]+(func|class|struct|enum|protocol|actor|typealias|var|let|init|extension|static)[[:space:]]+//' \
      | sed -E 's/^([A-Za-z_][A-Za-z0-9_]*).*/\1/' \
      | head -1)

    # Skip if symbol couldn't be extracted, is reserved (init, etc.), or empty
    if [ -z "$symbol" ] || [ "$symbol" = "init" ] || [ ${#symbol} -lt 2 ]; then
      continue
    fi

    # Count cross-module callers: grep symbol in OTHER module dirs
    cross_uses=0
    while IFS= read -r other_module_dir; do
      [ -z "$other_module_dir" ] && continue
      [ "$other_module_dir" = "$module_dir" ] && continue
      hits=$(grep -rn "\b${symbol}\b" "$other_module_dir" 2>/dev/null | grep -vc '/\.build/')
      cross_uses=$((cross_uses + hits))
    done < "$TMP_MODULES"

    if [ "$cross_uses" -eq 0 ]; then
      rel_file="${decl_file#"$ROOT"/}"
      echo "| $module | $symbol | $rel_file:$decl_lineno | 0 |"
      flagged_count=$((flagged_count + 1))
    fi
  done
done < "$TMP_MODULES"

# Note: flagged_count is local to the subshell (pipe) on bash 3.2; the table
# above is the authoritative output. Exit 0 always — this is an audit helper,
# not a gate.
exit 0
