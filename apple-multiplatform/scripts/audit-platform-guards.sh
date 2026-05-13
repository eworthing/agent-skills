#!/usr/bin/env bash
# audit-platform-guards.sh — Static audit for cross-platform guard mistakes.
#
# Scans Swift files for the most common high-frequency traps documented in
# apple-multiplatform/SKILL.md:
#
#   T1. canImport(UIKit) gating UIKit symbols that are missing on tvOS at the
#       symbol level (haptics, drag-and-drop receiving).
#   T2. @Environment(\.editMode) gated by `#if !os(tvOS)` alone — still
#       compiles on macOS, where editMode does not exist.
#   T3. TabView .page style without an os(macOS) branch.
#   T4. .topBarLeading / .topBarTrailing without an os(macOS) branch.
#   T5. .fullScreenCover without an os(macOS) branch.
#
# Output format (matches references/recovery.md "Standardized Error Output"):
#   APPLE-MP-FAIL <platform> <error-class> <file>:<line>: <message>
#
# Exit status: 0 = no hits, 1 = one or more hits, 2 = usage error.
#
# Portable to macOS bash 3.2 + Linux bash 4+. No mapfile, no GNU-only flags.

set -u

usage() {
  echo "usage: $0 [path]" >&2
  echo "  path defaults to the current directory." >&2
  exit 2
}

[ "$#" -le 1 ] || usage
ROOT="${1:-.}"
[ -d "$ROOT" ] || { echo "error: $ROOT is not a directory" >&2; exit 2; }

# Build the grep invocation as an array to avoid filename expansion of
# `*.swift` when the grep invocation is expanded unquoted later. Bash 3.2 supports arrays.
if command -v rg >/dev/null 2>&1; then
  GREP_CMD=(rg -n --type swift)
else
  GREP_CMD=(grep -rn --include='*.swift')
fi

HITS=0

# Emit one diagnostic in the standardized format.
emit() {
  platform="$1"
  class="$2"
  location="$3"
  message="$4"
  printf 'APPLE-MP-FAIL %s %s %s: %s\n' "$platform" "$class" "$location" "$message"
  HITS=$((HITS + 1))
}

# Read a colon-separated `file:line:content` triple from rg/grep output and
# call a handler with $1=file $2=line $3=rest. Portable to bash 3.2.
scan() {
  pattern="$1"
  handler="$2"
  "${GREP_CMD[@]}" "$pattern" "$ROOT" 2>/dev/null | while IFS= read -r line; do
    file=$(printf '%s' "$line" | awk -F: '{print $1}')
    lineno=$(printf '%s' "$line" | awk -F: '{print $2}')
    rest=$(printf '%s' "$line" | cut -d: -f3-)
    "$handler" "$file" "$lineno" "$rest"
  done
}

# T1. canImport(UIKit) co-located with high-risk symbols in the same file.
check_t1() {
  files_with_canimport=$("${GREP_CMD[@]}" -l 'canImport\(UIKit\)' "$ROOT" 2>/dev/null | sort -u)
  for f in $files_with_canimport; do
    [ -f "$f" ] || continue
    risk_lines=$(grep -nE 'UIImpactFeedbackGenerator|UISelectionFeedbackGenerator|UINotificationFeedbackGenerator|\.onDrop\(|DropDelegate' "$f" 2>/dev/null)
    [ -n "$risk_lines" ] || continue
    # Heredoc-fed loop avoids subshell so HITS counter propagates.
    while IFS= read -r hit; do
      [ -n "$hit" ] || continue
      ln=$(printf '%s' "$hit" | awk -F: '{print $1}')
      emit tvOS T1-canImport-vs-os "$f:$ln" \
        "canImport(UIKit) guard with tvOS-unavailable symbol — use #if os(iOS)"
    done <<EOF
$risk_lines
EOF
  done
}

# T2. editMode gated by `#if !os(tvOS)` only — macOS still lacks it.
check_t2() {
  files_with_editmode=$("${GREP_CMD[@]}" -l '@Environment\(\\\.editMode\)' "$ROOT" 2>/dev/null | sort -u)
  for f in $files_with_editmode; do
    [ -f "$f" ] || continue
    if grep -qE '#if[[:space:]]+!os\(tvOS\)([[:space:]]|$)' "$f" 2>/dev/null; then
      if ! grep -qE 'os\(macOS\)|os\(iOS\)' "$f" 2>/dev/null; then
        ln=$(grep -nE '@Environment\(\\\.editMode\)' "$f" | head -n 1 | awk -F: '{print $1}')
        emit macOS T2-editmode-tvos-only-guard "$f:${ln:-1}" \
          "editMode wrapped by bare #if !os(tvOS) — macOS also lacks editMode, use #if os(iOS)"
      fi
    fi
  done
}

# T3. TabView .page without an os(macOS) branch in the same file.
check_t3() {
  files=$("${GREP_CMD[@]}" -l 'tabViewStyle\(\.page' "$ROOT" 2>/dev/null | sort -u)
  for f in $files; do
    [ -f "$f" ] || continue
    if ! grep -qE 'os\(macOS\)' "$f" 2>/dev/null; then
      ln=$(grep -nE 'tabViewStyle\(\.page' "$f" | head -n 1 | awk -F: '{print $1}')
      emit macOS T3-tabview-page-unguarded "$f:${ln:-1}" \
        ".tabViewStyle(.page) without os(macOS) branch — unavailable on macOS"
    fi
  done
}

# T4. .topBarLeading / .topBarTrailing without an os(macOS) branch.
check_t4() {
  files=$("${GREP_CMD[@]}" -l '\.topBar(Leading|Trailing)' "$ROOT" 2>/dev/null | sort -u)
  for f in $files; do
    [ -f "$f" ] || continue
    if ! grep -qE 'os\(macOS\)' "$f" 2>/dev/null; then
      ln=$(grep -nE '\.topBar(Leading|Trailing)' "$f" | head -n 1 | awk -F: '{print $1}')
      emit macOS T4-topbar-placement-unguarded "$f:${ln:-1}" \
        ".topBarLeading/.topBarTrailing without os(macOS) branch — placements unavailable on macOS"
    fi
  done
}

# T5. .fullScreenCover without an os(macOS) branch.
check_t5() {
  files=$("${GREP_CMD[@]}" -l 'fullScreenCover' "$ROOT" 2>/dev/null | sort -u)
  for f in $files; do
    [ -f "$f" ] || continue
    if ! grep -qE 'os\(macOS\)' "$f" 2>/dev/null; then
      ln=$(grep -nE 'fullScreenCover' "$f" | head -n 1 | awk -F: '{print $1}')
      emit macOS T5-fullscreencover-unguarded "$f:${ln:-1}" \
        ".fullScreenCover without os(macOS) branch — modifier unavailable on macOS"
    fi
  done
}

check_t1
check_t2
check_t3
check_t4
check_t5

if [ "$HITS" -gt 0 ]; then
  printf '\n%s hit(s). See apple-multiplatform/references/recovery.md for fixes.\n' "$HITS" >&2
  exit 1
fi

echo "No platform-guard issues found."
exit 0
