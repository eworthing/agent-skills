#!/usr/bin/env bash
# check-doc-naming.sh - doc-standardization audit script.
#
# Audits a docs tree for filename hygiene, default grammar drift, broken
# Markdown links, orphan files, README index drift, and H1/topic drift.
#
# Portability: Bash 3.2+ / BSD or GNU userland. No mapfile, no GNU-only flags.
# set -u only: grep no-match is expected in this scanner.
#
# Usage: check-doc-naming.sh [docs-root]   (default: ./docs)
# Exit:  0 = no blocking violations, 1 = blocking violations found,
#        2 = invocation error.

set -u

DOCS_ROOT="${1:-docs}"
if [ ! -d "$DOCS_ROOT" ]; then
  printf 'check-doc-naming.sh: directory not found: %s\n' "$DOCS_ROOT" >&2
  exit 2
fi

failed_classes=0
total_files=0
naming_fail=0
naming_warn=0
case_fail=0
link_fail=0
link_checked=0
orphan_fail=0
index_fail=0
h1_fail=0

types_re='spec|guide|ref|research|audit|plan|decision'
states_re='draft|proposed|active|implemented|deprecated'

is_allowlisted_base() {
  case "$1" in
    README.md|CHANGELOG.md|CONTRIBUTING.md|LICENSE.md|CODEOWNERS|index.md)
      return 0 ;;
  esac
  return 1
}

is_declared_bundle_path() {
  case "$1" in
    */vendor/*|*/_archive/*|*/archive/*|*/code-flow/*)
      return 0 ;;
  esac
  return 1
}

is_adr_path() {
  case "$1" in
    */adr/[0-9][0-9][0-9][0-9]-*.md)
      return 0 ;;
  esac
  return 1
}

is_default_name() {
  printf '%s' "$1" | grep -Eq "^[a-z0-9]+(-[a-z0-9]+)*-(${types_re})-(${states_re})\\.md$"
}

is_dated_record_name() {
  printf '%s' "$1" | grep -Eq "^[a-z0-9]+(-[a-z0-9]+)*-(${types_re})-[0-9]{4}-[0-9]{2}-[0-9]{2}\\.md$"
}

has_standard_hygiene() {
  printf '%s' "$1" | grep -Eq '^[a-z0-9]+(-[a-z0-9]+)*\.md$'
}

has_approved_type_token() {
  printf '%s' "$1" | grep -Eq "(^|-)(${types_re})-"
}

has_approved_status_token() {
  printf '%s' "$1" | grep -Eq "(^|-)(${states_re})(-|\\.)"
}

last_slug_token() {
  base_no_ext="${1%.md}"
  printf '%s\n' "$base_no_ext" | awk -F- '{print $NF}'
}

topic_token_for_h1() {
  base_no_ext="${1%.md}"
  topic_part="$base_no_ext"
  if is_default_name "$1"; then
    topic_part=$(printf '%s\n' "$base_no_ext" | awk -F- '{for (i=1; i<=NF-2; i++) { if (i > 1) printf "-"; printf $i }}')
  elif is_dated_record_name "$1"; then
    topic_part=$(printf '%s\n' "$base_no_ext" | awk -F- '{for (i=1; i<=NF-4; i++) { if (i > 1) printf "-"; printf $i }}')
  elif is_adr_path "$2"; then
    topic_part=$(printf '%s\n' "$base_no_ext" | sed -E 's/^[0-9]{4}-//')
  fi
  printf '%s\n' "$topic_part" | awk -F- '{print $1}'
}

printf '== doc-standardization audit: %s ==\n' "$DOCS_ROOT"

tmp_list=$(mktemp -t doc-std.XXXXXX) || exit 2
trap 'rm -f "$tmp_list" "${tmp_list}.idx"' EXIT

find "$DOCS_ROOT" -type f -name "*.md" -print | LC_ALL=C sort >"$tmp_list"
while IFS= read -r _; do
  total_files=$((total_files + 1))
done <"$tmp_list"

printf 'tree: %d markdown files\n' "$total_files"

# --- 1. Filename hygiene and naming convention ---
naming_failures=""
naming_warnings=""
case_violations=""
while IFS= read -r f; do
  base="${f##*/}"
  if is_allowlisted_base "$base"; then continue; fi
  if is_declared_bundle_path "$f"; then continue; fi

  if ! has_standard_hygiene "$base"; then
    case_violations="${case_violations}CASE: ${f}
"
    case_fail=$((case_fail + 1))
    continue
  fi

  if is_adr_path "$f"; then continue; fi
  if is_default_name "$base"; then continue; fi
  if is_dated_record_name "$base"; then continue; fi

  if has_approved_type_token "$base"; then
    final_token=$(last_slug_token "$base")
    if ! printf '%s' "$final_token" | grep -Eq "^(${states_re}|[0-9]{2})$"; then
      naming_failures="${naming_failures}NAMING: ${f} (recognized type with invalid status/date)
"
      naming_fail=$((naming_fail + 1))
      continue
    fi
  fi

  if has_approved_status_token "$base"; then
    naming_failures="${naming_failures}NAMING: ${f} (recognized status without approved type)
"
    naming_fail=$((naming_fail + 1))
    continue
  fi

  naming_warnings="${naming_warnings}NAMING: ${f} (project-local lower-kebab name; verify against README contract)
"
  naming_warn=$((naming_warn + 1))
done <"$tmp_list"

if [ "$case_fail" -eq 0 ]; then
  printf '[OK] filename hygiene: 0 case/space violations\n'
else
  printf '[FAIL] filename hygiene: %d case/space violation(s)\n' "$case_fail"
  printf '%s' "$case_violations" | sed 's/^/  /'
  failed_classes=$((failed_classes + 1))
fi

if [ "$naming_fail" -eq 0 ]; then
  printf '[OK] naming convention: 0 blocking violations\n'
else
  printf '[FAIL] naming convention: %d blocking violation(s)\n' "$naming_fail"
  printf '%s' "$naming_failures" | sed 's/^/  /'
  failed_classes=$((failed_classes + 1))
fi

if [ "$naming_warn" -eq 0 ]; then
  printf '[OK] naming advisories: 0\n'
else
  printf '[WARN] naming advisories: %d project-local name(s)\n' "$naming_warn"
  printf '%s' "$naming_warnings" | sed 's/^/  /'
fi

# --- 2. Broken link validation ---
link_violations=""
link_extract() {
  while IFS= read -r f; do
    grep -En '\]\([^)]*\.md(#[^)]*)?\)' "$f" 2>/dev/null \
      | sed -nE 's/^([0-9]+):.*\]\(([^)]+)\).*/\1\	\2/p' \
      | while IFS=$'\t' read -r lineno target; do
          printf '%s\t%s\t%s\n' "$f" "$lineno" "$target"
        done
  done <"$tmp_list"
}

while IFS=$'\t' read -r src lineno target; do
  case "$target" in
    http://*|https://*|mailto:*|'#'*) continue ;;
  esac
  target_clean="${target%%#*}"
  if [ -z "$target_clean" ]; then continue; fi
  target_clean=$(printf '%s' "$target_clean" | sed 's/%20/ /g')
  case "$target_clean" in
    /*) resolved="$target_clean" ;;
    *) src_dir="${src%/*}"; resolved="${src_dir}/${target_clean}" ;;
  esac
  link_checked=$((link_checked + 1))
  if [ ! -e "$resolved" ]; then
    link_violations="${link_violations}BROKEN: ${src}:${lineno} -> ${target}
"
    link_fail=$((link_fail + 1))
  fi
done <<EOF
$(link_extract)
EOF

if [ "$link_fail" -eq 0 ]; then
  printf '[OK] links: 0 broken (%d checked)\n' "$link_checked"
else
  printf '[FAIL] links: %d broken (%d checked)\n' "$link_fail" "$link_checked"
  printf '%s' "$link_violations" | sed 's/^/  /'
  failed_classes=$((failed_classes + 1))
fi

# --- 3. Orphan file check ---
orphan_violations=""
while IFS= read -r f; do
  base="${f##*/}"
  if [ "$base" = "README.md" ]; then continue; fi
  ref_count=$(grep -rEl "\\]\\([^)]*${base}([#)])" "$DOCS_ROOT" --include="*.md" 2>/dev/null \
    | grep -cv "^${f}$" || true)
  if [ "${ref_count:-0}" -eq 0 ]; then
    orphan_violations="${orphan_violations}ORPHAN: ${f}
"
    orphan_fail=$((orphan_fail + 1))
  fi
done <"$tmp_list"

if [ "$orphan_fail" -eq 0 ]; then
  printf '[OK] orphan check: 0 orphaned\n'
else
  printf '[WARN] orphan check: %d orphaned (advisory)\n' "$orphan_fail"
  printf '%s' "$orphan_violations" | sed 's/^/  /'
fi

# --- 4. Index drift ---
index_violations=""
find "$DOCS_ROOT" -name "README.md" -type f -print | while IFS= read -r idx; do
  idx_dir="${idx%/*}"
  grep -En '\]\([^)]*\.md(#[^)]*)?\)' "$idx" 2>/dev/null \
    | sed -nE 's/^[0-9]+:.*\]\(([^)]+\.md)(#[^)]*)?\).*/\1/p' \
    | while IFS= read -r target; do
        case "$target" in http://*|https://*|mailto:*|'#'*) continue ;; esac
        target_clean="${target%%#*}"
        target_clean=$(printf '%s' "$target_clean" | sed 's/%20/ /g')
        case "$target_clean" in
          /*) resolved="$target_clean" ;;
          *) resolved="${idx_dir}/${target_clean}" ;;
        esac
        if [ ! -e "$resolved" ]; then
          printf 'INDEX-DRIFT: %s references missing %s\n' "$idx" "$target"
        fi
      done
done >"${tmp_list}.idx" 2>/dev/null || true
index_violations=$(cat "${tmp_list}.idx" 2>/dev/null || true)

if [ -z "$index_violations" ]; then
  printf '[OK] index drift: 0\n'
else
  index_fail=$(printf '%s\n' "$index_violations" | grep -c '^INDEX-DRIFT:' || true)
  printf '[FAIL] index drift: %d\n' "$index_fail"
  printf '%s\n' "$index_violations" | sed 's/^/  /'
  failed_classes=$((failed_classes + 1))
fi

# --- 5. H1 / topic mismatch (advisory) ---
h1_violations=""
while IFS= read -r f; do
  base="${f##*/}"
  if is_allowlisted_base "$base"; then continue; fi
  if is_declared_bundle_path "$f"; then continue; fi
  h1=$(grep -m1 -E '^# ' "$f" 2>/dev/null | sed 's/^# //' | tr '[:upper:]' '[:lower:]' | tr -cd 'a-z0-9 ')
  h1_topic=$(topic_token_for_h1 "$base" "$f")
  if [ -n "$h1_topic" ] && [ -n "$h1" ]; then
    if ! printf '%s' "$h1" | grep -q "$h1_topic"; then
      h1_violations="${h1_violations}H1-DRIFT: ${f} -> H1 \"${h1}\" missing slug token \"${h1_topic}\"
"
      h1_fail=$((h1_fail + 1))
    fi
  fi
done <"$tmp_list"

if [ "$h1_fail" -eq 0 ]; then
  printf '[OK] H1 drift: 0\n'
else
  printf '[WARN] H1 drift: %d (advisory)\n' "$h1_fail"
  printf '%s' "$h1_violations" | sed 's/^/  /'
fi

printf '== summary: '
if [ "$failed_classes" -eq 0 ]; then
  printf 'CLEAN (%d naming + %d orphan + %d H1 advisory) ==\n' "$naming_warn" "$orphan_fail" "$h1_fail"
  exit 0
else
  printf '%d error class(es) failed ==\n' "$failed_classes"
  exit 1
fi
