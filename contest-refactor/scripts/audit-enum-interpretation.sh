#!/usr/bin/env bash
# audit-enum-interpretation.sh — flag domain enums interpreted outside their home
#
# Usage: scripts/audit-enum-interpretation.sh [<repo-root>]
# Default: current working directory.
#
# Mechanical helper for the leaf-module duplication sweep. A domain enum whose
# cases get switched/compared (`==`/`!=`/`switch`) from OUTSIDE the module (or
# file, for flat repos) that declares it is a signal for root causes A1/A2/R3/
# S3/S9/A3 in the motivating audit: the enum's meaning gets reimplemented or
# drifts at call sites instead of living as a computed property on the enum
# type itself. Output is candidate evidence for the Critic — never a finding
# on its own, never a score input. promotion_allowed: false. Exit 0 always,
# regardless of findings (or of an unsupported stack).
#
# Two attribution tiers, both required to build enough recall without drowning
# in false positives from common case names shared across many enums:
#   Tier 1 (qualified)   — `Enum.case`, `== Enum.case`, `!= Enum.case`, or a
#                           `switch` line naming Enum directly. Unambiguous by
#                           construction (the enum name is right there).
#   Tier 2 (unqualified) — `== .case`, `!= .case`, `case .case:`. Attributed
#                           only when `case` maps to exactly one enum in the
#                           whole inventory; ambiguous case names (`.none`,
#                           `.active`, ...) are skipped rather than guessed.
#
# Stack: Swift only (v1). A repo with no Swift sources degrades to a one-line
# stderr note and prints nothing to stdout — exit 0 (mirrors audit_boundaries.py's
# unsupported-stack behavior).
#
# Portable Bash (macOS 3.2 floor): no mapfile, no associative arrays, no `[[ ]]`
# regex reliance — parallel temp files + awk stand in for assoc-array lookups.
# Assumes BSD grep/awk/sed (macOS stock); alternation needs `-E`, not bare `\|`.

set -u

ROOT="${1:-.}"
PRUNE_RE='/(\.build|\.git|node_modules|Pods|vendor|DerivedData)(/|$)'
CAP=200

cleanup() { rm -f "$TMP_ROOTS" "$TMP_SWIFT" "$TMP_ENUM_RAW" "$TMP_ENUM_HOME" \
  "$TMP_CASE_OWNER" "$TMP_CASE_UNAMBIG" "$TMP_T1_SITES" "$TMP_T2_SITES" \
  "$TMP_ROWS" 2>/dev/null; }
TMP_ROOTS=$(mktemp -t audit-enum-roots.XXXXXX) || exit 2
TMP_SWIFT=$(mktemp -t audit-enum-swift.XXXXXX) || exit 2
TMP_ENUM_RAW=$(mktemp -t audit-enum-raw.XXXXXX) || exit 2
TMP_ENUM_HOME=$(mktemp -t audit-enum-home.XXXXXX) || exit 2
TMP_CASE_OWNER=$(mktemp -t audit-enum-caseowner.XXXXXX) || exit 2
TMP_CASE_UNAMBIG=$(mktemp -t audit-enum-unambig.XXXXXX) || exit 2
TMP_T1_SITES=$(mktemp -t audit-enum-t1.XXXXXX) || exit 2
TMP_T2_SITES=$(mktemp -t audit-enum-t2.XXXXXX) || exit 2
TMP_ROWS=$(mktemp -t audit-enum-rows.XXXXXX) || exit 2
trap cleanup EXIT INT TERM HUP

# --- Source root discovery ---------------------------------------------------
# Union of Sources/src/lib/app dirs up to two levels below ROOT (covers nested
# SPM layouts like BenchHypeKit/Sources/<Module>, which a -maxdepth 1 search
# would miss). Falls back to ROOT itself when none are found.
find "$ROOT" -maxdepth 2 -type d \( -name Sources -o -name src -o -name lib -o -name app \) 2>/dev/null \
  | grep -vE "$PRUNE_RE" > "$TMP_ROOTS"

SRC_ROOTS_ARR=()
while IFS= read -r d; do
  [ -z "$d" ] && continue
  SRC_ROOTS_ARR+=("$d")
done < "$TMP_ROOTS"
if [ "${#SRC_ROOTS_ARR[@]}" -eq 0 ]; then
  SRC_ROOTS_ARR=("$ROOT")
fi

# --- Swift file inventory -----------------------------------------------------
{
  for r in "${SRC_ROOTS_ARR[@]}"; do
    find "$r" -type f -name '*.swift' 2>/dev/null
  done
} | grep -vE "$PRUNE_RE" | sort -u > "$TMP_SWIFT"

if [ ! -s "$TMP_SWIFT" ]; then
  echo "audit-enum-interpretation: no Swift source files found under $ROOT — unsupported stack (v1: Swift only)" >&2
  exit 0
fi

# --- Home resolution ----------------------------------------------------------
# Home = path component directly under the matched source root (module name),
# or — for a flat repo where the file sits directly under its source root —
# the declaring file itself (prefixed FILE: to keep the namespace distinct
# from module names when comparing "inside vs outside home").
home_of_file() {
  file="$1"
  best_root=""
  best_len=-1
  for r in "${SRC_ROOTS_ARR[@]}"; do
    case "$file" in
      "$r"/*)
        len=${#r}
        if [ "$len" -gt "$best_len" ]; then
          best_len=$len
          best_root="$r"
        fi
        ;;
    esac
  done
  if [ -z "$best_root" ]; then
    best_root="$ROOT"
  fi
  rel="${file#"$best_root"/}"
  case "$rel" in
    */*)
      echo "${rel%%/*}"
      ;;
    *)
      relroot="${file#"$ROOT"/}"
      echo "FILE:${relroot}"
      ;;
  esac
}

# --- Inventory pass: enum declarations ----------------------------------------
DECL_RE='^[[:space:]]*(public|internal|package|fileprivate|private)?[[:space:]]*(indirect[[:space:]]+)?enum[[:space:]]+[A-Z][A-Za-z0-9_]*'

: > "$TMP_ENUM_RAW"
while IFS= read -r f; do
  [ -z "$f" ] && continue
  grep -nHE "$DECL_RE" "$f" 2>/dev/null >> "$TMP_ENUM_RAW"
done < "$TMP_SWIFT"

RAW_COUNT=$(wc -l < "$TMP_ENUM_RAW" | tr -d ' ')
if [ "$RAW_COUNT" -gt "$CAP" ]; then
  TMP_ENUM_RAW_CAPPED=$(mktemp -t audit-enum-rawcap.XXXXXX) || exit 2
  head -n "$CAP" "$TMP_ENUM_RAW" > "$TMP_ENUM_RAW_CAPPED"
  mv "$TMP_ENUM_RAW_CAPPED" "$TMP_ENUM_RAW"
  echo "audit-enum-interpretation: found >$CAP enum declarations; processing first $CAP (file-then-line order)" >&2
fi

: > "$TMP_ENUM_HOME"
: > "$TMP_CASE_OWNER"

while IFS= read -r rawline; do
  [ -z "$rawline" ] && continue
  ef="${rawline%%:*}"
  rest="${rawline#*:}"
  el="${rest%%:*}"
  content="${rest#*:}"

  name=$(printf '%s\n' "$content" \
    | sed -E 's/^[[:space:]]*(public|internal|package|fileprivate|private)?[[:space:]]*(indirect[[:space:]]+)?enum[[:space:]]+//' \
    | sed -E 's/^([A-Z][A-Za-z0-9_]*).*/\1/')
  [ -z "$name" ] && continue
  case "$name" in
    CodingKeys|Never) continue ;;
  esac

  indent=$(printf '%s\n' "$content" | sed -E 's/^([[:space:]]*).*/\1/')

  window_out=$(awk -v start="$el" -v indent="$indent" '
    NR <= start { next }
    {
      if (NR - start > 60) { exit }
      if (match($0, "^" indent "}")) { print "WEND:" NR; exit }
      if (match($0, "^[ \t]*case[ \t]+")) {
        rest = substr($0, RSTART + RLENGTH)
        depth = 0
        cur = ""
        n = length(rest)
        for (i = 1; i <= n; i++) {
          c = substr(rest, i, 1)
          if (c == "(") { depth++; cur = cur c; continue }
          if (c == ")") { depth--; cur = cur c; continue }
          if (c == "," && depth == 0) { print "CASE:" cur; cur = ""; continue }
          cur = cur c
        }
        if (cur != "") print "CASE:" cur
      }
    }
  ' "$ef")

  has_case=0
  while IFS= read -r wl; do
    [ -z "$wl" ] && continue
    case "$wl" in
      CASE:*)
        has_case=1
        tok="${wl#CASE:}"
        cname=$(printf '%s\n' "$tok" | sed -E 's/^[[:space:]]*//' | sed -E 's/^([A-Za-z_][A-Za-z0-9_]*).*/\1/')
        [ -n "$cname" ] && printf '%s\t%s\n' "$cname" "$name" >> "$TMP_CASE_OWNER"
        ;;
    esac
  done <<EOF
$window_out
EOF

  if [ "$has_case" -eq 0 ]; then
    continue
  fi

  home=$(home_of_file "$ef")
  printf '%s\t%s\t%s\t%s\n' "$name" "$home" "$ef" "$el" >> "$TMP_ENUM_HOME"
done < "$TMP_ENUM_RAW"

# Dedup enums by name (first-seen home wins if a name repeats across homes —
# a known limitation for repos with duplicate enum names in different modules;
# attribution below is by name, not by decl-site).
TMP_ENUM_HOME_DEDUP=$(mktemp -t audit-enum-homededup.XXXXXX) || exit 2
awk -F'\t' '!seen[$1]++' "$TMP_ENUM_HOME" > "$TMP_ENUM_HOME_DEDUP"
mv "$TMP_ENUM_HOME_DEDUP" "$TMP_ENUM_HOME"

if [ ! -s "$TMP_ENUM_HOME" ]; then
  echo "audit-enum-interpretation: no domain enums found under $ROOT (after excluding CodingKeys/Never/namespace enums)" >&2
  exit 0
fi

# --- Ambiguity gate for Tier 2 -------------------------------------------------
# case -> single enum, only when that case name maps to exactly one distinct
# enum across the whole inventory.
sort -u "$TMP_CASE_OWNER" | sort -t "$(printf '\t')" -k1,1 | awk -F'\t' '
{
  if ($1 != prev && prev != "") {
    if (n == 1) print prev "\t" only
  }
  if ($1 != prev) { n = 0 }
  n++
  only = $2
  prev = $1
}
END {
  if (prev != "" && n == 1) print prev "\t" only
}
' > "$TMP_CASE_UNAMBIG"

# --- Tier 1: qualified sites (Enum.case / == Enum.case / != Enum.case / switch Enum) ---
: > "$TMP_T1_SITES"
while IFS=$'\t' read -r ename ehome _ _; do
  [ -z "$ename" ] && continue
  pat="\\b${ename}\\.[A-Za-z_]|\\bswitch\\b.*\\b${ename}\\b"
  while IFS= read -r sf; do
    [ -z "$sf" ] && continue
    hits=$(grep -nE "$pat" "$sf" 2>/dev/null) || true
    [ -z "$hits" ] && continue
    shome=$(home_of_file "$sf")
    printf '%s\n' "$hits" | while IFS= read -r hl; do
      [ -z "$hl" ] && continue
      sline="${hl%%:*}"
      if [ "$shome" != "$ehome" ]; then
        printf '%s\t%s\t%s\t%s\n' "$ename" "$ehome" "$sf" "$sline" >> "$TMP_T1_SITES"
      fi
    done
  done < "$TMP_SWIFT"
done < "$TMP_ENUM_HOME"

# --- Tier 2: unqualified sites (== .case / != .case / case .case) ------------
: > "$TMP_T2_SITES"
while IFS=$'\t' read -r cname ename; do
  [ -z "$cname" ] && continue
  ehome=$(awk -F'\t' -v e="$ename" '$1 == e { print $2; exit }' "$TMP_ENUM_HOME")
  [ -z "$ehome" ] && continue
  pat="(==|!=)[[:space:]]*\\.${cname}\\b|\\bcase[[:space:]]+\\.${cname}\\b"
  while IFS= read -r sf; do
    [ -z "$sf" ] && continue
    hits=$(grep -nE "$pat" "$sf" 2>/dev/null) || true
    [ -z "$hits" ] && continue
    shome=$(home_of_file "$sf")
    printf '%s\n' "$hits" | while IFS= read -r hl; do
      [ -z "$hl" ] && continue
      sline="${hl%%:*}"
      if [ "$shome" != "$ehome" ]; then
        printf '%s\t%s\t%s\t%s\n' "$ename" "$ehome" "$sf" "$sline" >> "$TMP_T2_SITES"
      fi
    done
  done < "$TMP_SWIFT"
done < "$TMP_CASE_UNAMBIG"

# --- Report: one row per enum per tier, >=2 outside-home sites required ------
# Site file paths are rewritten ROOT-relative and the "FILE:" flat-home prefix
# is stripped for display, both inside awk (avoids fragile shell re-splitting
# of an already-<br>-joined cell).
: > "$TMP_ROWS"
build_rows() {
  tierfile="$1"
  tierlabel="$2"
  sort -t "$(printf '\t')" -k1,1 -k3,3 -k4,4n "$tierfile" | awk -F'\t' -v tier="$tierlabel" -v root="$ROOT/" '
    function flush(   disp) {
      if (count >= 2) {
        disp = ehome
        if (index(disp, "FILE:") == 1) { disp = substr(disp, 6) }
        printf "| %s | %s | %s | %d | %s |\n", ename, disp, tier, count, sites
      }
    }
    {
      key = $1
      if (key != prevkey && prevkey != "") { flush(); count = 0; sites = ""; shown = 0 }
      ename = $1; ehome = $2
      relfile = $3
      if (index(relfile, root) == 1) { relfile = substr(relfile, length(root) + 1) }
      site = relfile ":" $4
      count++
      if (shown < 6) {
        sites = (sites == "") ? site : sites "<br>" site
        shown++
      }
      prevkey = key
    }
    END { flush() }
  '
}

build_rows "$TMP_T1_SITES" "1 (qualified)" >> "$TMP_ROWS"
build_rows "$TMP_T2_SITES" "2 (unqualified)" >> "$TMP_ROWS"

if [ ! -s "$TMP_ROWS" ]; then
  echo "audit-enum-interpretation: no enum flagged (<2 outside-home interpretation sites for every candidate)" >&2
  exit 0
fi

echo "| enum | home | tier | outside-site count | sites (file:line, first 6) |"
echo "|---|---|---|---|---|"
sort -t '|' -k2,2 -k4,4 "$TMP_ROWS"

n_rows=$(wc -l < "$TMP_ROWS" | tr -d ' ')
echo "" >&2
echo "audit-enum-interpretation: ${n_rows} enum/tier row(s) flagged — candidate evidence for the Critic (root causes A1/A2/R3/S3/S9/A3); not a finding by itself and not a loop gate. promotion_allowed: false." >&2

exit 0
