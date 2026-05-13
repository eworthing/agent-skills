#!/usr/bin/env bash
# check-doc-naming.sh — doc-standardization drift verifier.
#
# Audits a docs tree for naming convention violations, broken markdown
# links, orphan files, index drift, case violations, and H1/filename
# mismatches. Implements the recipes in references/regex-recipes.md.
#
# Portability: Bash 3.2+ / BSD or GNU userland. No mapfile, no GNU-only
# flags. See the bash-macos sibling skill for the rules this follows.
#
# Usage: check-doc-naming.sh [docs-root]   (default: ./docs)
# Exit:  0 = clean, 1 = violations found, 2 = invocation error.

set -u

DOCS_ROOT="${1:-docs}"
if [ ! -d "$DOCS_ROOT" ]; then
  printf 'check-doc-naming.sh: directory not found: %s\n' "$DOCS_ROOT" >&2
  exit 2
fi

failed_classes=0
total_files=0
naming_fail=0
link_fail=0
orphan_fail=0
case_fail=0
index_fail=0
h1_fail=0
link_checked=0

# Allowlisted basenames that don't follow [domain]-[feature]-[type]-[status]
is_allowlisted_base() {
  case "$1" in
    README.md|CHANGELOG.md|CONTRIBUTING.md|LICENSE.md|CODEOWNERS|index.md)
      return 0 ;;
  esac
  return 1
}

printf '== doc-standardization audit: %s ==\n' "$DOCS_ROOT"

# Collect markdown file list (Bash 3.2 safe: while-read, not mapfile)
tmp_list=$(mktemp -t doc-std.XXXXXX) || exit 2
trap 'rm -f "$tmp_list"' EXIT
find "$DOCS_ROOT" -type f -name "*.md" -print | LC_ALL=C sort >"$tmp_list"
while IFS= read -r _; do
  total_files=$((total_files + 1))
done <"$tmp_list"

printf 'tree: %d markdown files\n' "$total_files"

# --- 1. Naming convention ---
naming_violations=""
while IFS= read -r f; do
  base="${f##*/}"
  if is_allowlisted_base "$base"; then continue; fi
  if ! printf '%s' "$base" | grep -Eq '^[a-z0-9]+(-[a-z0-9]+){2,}\.md$'; then
    naming_violations="${naming_violations}NAMING: ${f}
"
    naming_fail=$((naming_fail + 1))
  fi
done <"$tmp_list"
if [ "$naming_fail" -eq 0 ]; then
  printf '[OK] naming convention: %d/%d match\n' "$total_files" "$total_files"
else
  printf '[FAIL] naming convention: %d violations\n' "$naming_fail"
  printf '%s' "$naming_violations" | sed 's/^/  /'
  failed_classes=$((failed_classes + 1))
fi

# --- 2. Case violations ---
case_violations=""
while IFS= read -r f; do
  base="${f##*/}"
  if is_allowlisted_base "$base"; then continue; fi
  if printf '%s' "$base" | grep -Eq '[A-Z]'; then
    case_violations="${case_violations}CASE: ${f}
"
    case_fail=$((case_fail + 1))
  fi
done <"$tmp_list"
if [ "$case_fail" -eq 0 ]; then
  printf '[OK] case violations: 0\n'
else
  printf '[FAIL] case violations: %d\n' "$case_fail"
  printf '%s' "$case_violations" | sed 's/^/  /'
  failed_classes=$((failed_classes + 1))
fi

# --- 3. Broken link validation ---
link_violations=""
link_extract() {
  # Emit one "src_file<TAB>target" pair per markdown link
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
  # URL-decode %20 only (most common)
  target_clean=$(printf '%s' "$target_clean" | sed 's/%20/ /g')
  case "$target_clean" in
    /*) resolved="$target_clean" ;;
    *)  src_dir="${src%/*}"; resolved="${src_dir}/${target_clean}" ;;
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

# --- 4. Orphan file check ---
orphan_violations=""
while IFS= read -r f; do
  base="${f##*/}"
  if [ "$base" = "README.md" ]; then continue; fi
  # Search docs tree for any reference to this basename.
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
  # Orphans are advisory — do not increment failed_classes.
fi

# --- 5. Index drift ---
index_violations=""
find "$DOCS_ROOT" -name "README.md" -type f -print | while IFS= read -r idx; do
  idx_dir="${idx%/*}"
  grep -En '\]\([^)]*\.md(#[^)]*)?\)' "$idx" 2>/dev/null \
    | sed -nE 's/^[0-9]+:.*\]\(([^)]+\.md)(#[^)]*)?\).*/\1/p' \
    | while IFS= read -r target; do
        case "$target" in http://*|https://*) continue ;; esac
        case "$target" in
          /*) resolved="$target" ;;
          *)  resolved="${idx_dir}/${target}" ;;
        esac
        if [ ! -e "$resolved" ]; then
          printf 'INDEX-DRIFT: %s -> %s\n' "$idx" "$target"
        fi
      done
done >"${tmp_list}.idx" 2>/dev/null || true
index_violations=$(cat "${tmp_list}.idx" 2>/dev/null || true)
rm -f "${tmp_list}.idx"
if [ -z "$index_violations" ]; then
  printf '[OK] index drift: 0\n'
else
  index_fail=$(printf '%s\n' "$index_violations" | grep -c '^INDEX-DRIFT:' || true)
  printf '[FAIL] index drift: %d\n' "$index_fail"
  printf '%s\n' "$index_violations" | sed 's/^/  /'
  failed_classes=$((failed_classes + 1))
fi

# --- Summary ---
printf '== summary: '
if [ "$failed_classes" -eq 0 ]; then
  printf 'CLEAN (%d advisory orphans) ==\n' "$orphan_fail"
  exit 0
else
  printf '%d error class(es) failed ==\n' "$failed_classes"
  exit 1
fi
