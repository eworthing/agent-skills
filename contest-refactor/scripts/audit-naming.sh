#!/usr/bin/env bash
# audit-naming.sh — flag fuzzy-named types clustered within a module
#
# Usage: scripts/audit-naming.sh [<repo-root>]
# Default: cwd.
#
# Greps for types matching *Service, *Manager, *Helper, *Util, *Handler,
# *Provider, *Wrapper. Reports per-module clusters where 2+ such types
# share a prefix (e.g., UserService + UserManager in same module).
#
# Output: markdown table to stdout. Columns: module, prefix, fuzzy types, sites.
# Portable Bash (macOS 3.2 + Linux 4+). Works for Swift; pattern adaptable.

set -u

ROOT="${1:-.}"

# Resolve source dir candidates
SOURCE_BASES=""
for d in Sources src lib app pkg internal; do
  if [ -d "$ROOT/$d" ]; then
    SOURCE_BASES="$SOURCE_BASES $ROOT/$d"
  fi
done
nested=$(find "$ROOT" -maxdepth 3 -type d -name 'Sources' 2>/dev/null | head -3)
for d in $nested; do
  case " $SOURCE_BASES " in
    *" $d "*) ;;
    *) SOURCE_BASES="$SOURCE_BASES $d" ;;
  esac
done

if [ -z "$SOURCE_BASES" ]; then
  echo "audit-naming: no source dirs found under $ROOT" >&2
  exit 2
fi

# Suffix regex
SUFFIXES='(Service|Manager|Helper|Util|Utility|Handler|Provider|Wrapper)'

# Grep for type declarations (Swift: class/struct/enum/actor/protocol)
# matching the fuzzy suffix. Extract (file, type-name).
all_hits=""
for base in $SOURCE_BASES; do
  hits=$(grep -rnE "^[[:space:]]*(public|internal|fileprivate|private)?[[:space:]]*(final[[:space:]]+)?(class|struct|enum|actor|protocol)[[:space:]]+[A-Z][A-Za-z0-9_]*${SUFFIXES}\b" \
    "$base" 2>/dev/null \
    | grep -v '/\.build/' \
    | grep -vE '/(Tests|TestSupport)/')
  if [ -n "$hits" ]; then
    all_hits="$all_hits
$hits"
  fi
done

if [ -z "$all_hits" ]; then
  echo "audit-naming: no fuzzy-named types found in $SOURCE_BASES" >&2
  exit 0
fi

# Build module-keyed table:
#   module | prefix | types | sites
echo "| Module | Prefix | Fuzzy types | Sites |"
echo "|---|---|---|---|"

# Per-line extraction: derive module name + type name + file:line
# Module = path component immediately after Sources/
# Type   = identifier after class/struct/etc keyword
# Prefix = type with suffix stripped

# Use a temp file for awk-driven cluster detection (bash 3.2 has no assoc arrays)
TMPF=$(mktemp -t audit-naming.XXXXXX)
trap 'rm -f "$TMPF"' EXIT INT TERM HUP
echo "$all_hits" | while IFS= read -r line; do
  [ -z "$line" ] && continue
  file=$(echo "$line" | cut -d: -f1)
  lineno=$(echo "$line" | cut -d: -f2)
  decl=$(echo "$line" | cut -d: -f3-)

  # Module = component after Sources/
  module=$(echo "$file" | sed -E 's@.*/Sources/([^/]+)/.*@\1@')
  if [ "$module" = "$file" ]; then
    # Fallback: use parent dir name
    module=$(basename "$(dirname "$file")")
  fi

  # Type name
  type_name=$(echo "$decl" \
    | sed -E 's/^[[:space:]]*(public|internal|fileprivate|private)?[[:space:]]*(final[[:space:]]+)?(class|struct|enum|actor|protocol)[[:space:]]+//' \
    | sed -E 's/^([A-Z][A-Za-z0-9_]*).*/\1/' \
    | head -1)

  # Prefix = type without suffix
  prefix=$(echo "$type_name" | sed -E "s/${SUFFIXES}\$//")

  rel="${file#$ROOT/}"
  echo "${module}|${prefix}|${type_name}|${rel}:${lineno}" >> "$TMPF"
done

# Cluster: group by module + prefix; report only clusters with >= 2 distinct types
sort "$TMPF" | awk -F'|' '
{
  key = $1 "|" $2
  if (key != prev_key && prev_key != "") {
    if (count >= 2) {
      printf "| %s | %s | %s | %s |\n", prev_module, prev_prefix, types, sites
    }
    types = ""
    sites = ""
    count = 0
  }
  if (index(types, $3) == 0) {
    types = (types == "") ? $3 : types ", " $3
    count++
  }
  sites = (sites == "") ? $4 : sites "<br>" $4
  prev_key = key
  prev_module = $1
  prev_prefix = $2
}
END {
  if (count >= 2) {
    printf "| %s | %s | %s | %s |\n", prev_module, prev_prefix, types, sites
  }
}
'

rm -f "$TMPF"
