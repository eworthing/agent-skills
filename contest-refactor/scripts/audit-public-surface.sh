#!/usr/bin/env bash
# audit-public-surface.sh — flag public Swift declarations with no cross-module callers
#
# Usage: scripts/audit-public-surface.sh [<repo-root>]
#        scripts/audit-public-surface.sh --since <rev> [<repo-root>]
# Default: current working directory.
#
# --since <rev> switches to PUBLIC-CONTRACT BACK-COMPAT mode (candidate DD-07):
# scans `git diff <rev>..worktree` for public declarations that were removed or
# whose signature changed. A symbol whose name reappears on an added line is
# `changed`; one that does not is `removed`. Both are candidate evidence
# (promotion_allowed: false) -- a removal inside an unreleased window is not a
# break, and this script cannot know the release boundary. Step 3 re-derives.
#
# Walks Sources/<Module>/ looking for `public` decls, then greps sibling
# Sources/ modules for use sites. Reports decls with zero cross-module use sites.
#
# Stack: Apple / SPM. Output: markdown table to stdout.
# Portable Bash (macOS 3.2 + Linux 4+). No mapfile/readarray; no GNU-only flags.

set -u

SINCE=""
POSITIONAL=""
while [ $# -gt 0 ]; do
  case "$1" in
    --since)
      SINCE="${2:-}"
      if [ -z "$SINCE" ]; then
        echo "audit-public-surface: --since needs a revision" >&2
        exit 2
      fi
      shift 2
      ;;
    --since=*) SINCE="${1#--since=}"; shift ;;
    -h|--help)
      sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'
      exit 0
      ;;
    *) POSITIONAL="$1"; shift ;;
  esac
done

ROOT="${POSITIONAL:-.}"

# --- back-compat mode (DD-07) ------------------------------------------------
if [ -n "$SINCE" ]; then
  cd "$ROOT" 2>/dev/null || { echo "audit-public-surface: no such dir: $ROOT" >&2; exit 2; }
  if ! git rev-parse --git-dir >/dev/null 2>&1; then
    echo "audit-public-surface: not a git repository: $ROOT" >&2
    exit 2
  fi
  if ! git rev-parse --verify --quiet "$SINCE" >/dev/null 2>&1; then
    echo "audit-public-surface: unknown revision: $SINCE" >&2
    exit 2
  fi

  DIFF=$(mktemp -t audit-pub-compat.XXXXXX) || exit 2
  trap 'rm -f "$DIFF"' EXIT INT TERM HUP
  # Swift `public`/`open`, Rust `pub`, TS/JS `export`. -U0 keeps hunks tight so a
  # neighbouring edit never masquerades as a contract change.
  git diff -U0 "$SINCE" -- '*.swift' '*.rs' '*.ts' '*.go' > "$DIFF" 2>/dev/null

  echo "# public-contract back-compat since $SINCE (candidate evidence, promotion_allowed: false)"
  echo
  echo "| status | symbol | file |"
  echo "| --- | --- | --- |"

  # Two passes over the same diff: pass 1 collects every identifier that appears
  # on an added line, pass 2 emits each removed public declaration. A symbol that
  # comes back on an added line is `changed`; one that does not is `removed`.
  # All of it in awk -- a shell read-loop over diff text is fragile about leading
  # dashes and IFS, and this needs neither.
  awk '
    FNR == NR {
      if ($0 ~ /^\+/ && $0 !~ /^\+\+\+/) { added = added " " $0 }
      next
    }
    /^\+\+\+ b\// { file = substr($0, 7); next }
    /^-/ && !/^--- / {
      if ($0 !~ /(^|[^A-Za-z_])(public|open|pub|export)[ \t]/) next
      if (!match($0, /(func|var|let|class|struct|enum|protocol|typealias|actor|fn|type|interface|const)[ \t]+[A-Za-z_][A-Za-z0-9_]*/)) next
      seg = substr($0, RSTART, RLENGTH)
      n = split(seg, parts, /[ \t]+/)
      sym = parts[n]
      status = (added ~ ("[^A-Za-z0-9_]" sym "[^A-Za-z0-9_]")) ? "changed" : "removed"
      printf "| %s | `%s` | %s |\n", status, sym, file
    }
  ' "$DIFF" "$DIFF"

  # Exit 0 always -- an audit helper, never a gate. Same contract as the
  # enumeration mode below.
  exit 0
fi
# --- end back-compat mode ----------------------------------------------------
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

TMP_MODULES=$(mktemp -t audit-public-surface-modules.XXXXXX) || exit 2
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
