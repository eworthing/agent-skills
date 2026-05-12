#!/usr/bin/env bash
# pre-split-check.sh — Inspect a Swift file before splitting.
#
# Reports: line count, MARK sections, extensions, private/fileprivate members,
# and any obvious cross-file-access concerns. Read-only; never modifies the file.
#
# Usage:
#   ./pre-split-check.sh path/to/SomeView.swift
#
# Portable across macOS (Bash 3.2, BSD userland) and Linux (Bash 4+, GNU coreutils).
# Exits non-zero only on missing arg or missing file.

set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "Usage: $0 <path/to/file.swift>" >&2
  exit 2
fi

FILE="$1"

if [ ! -f "$FILE" ]; then
  echo "Error: file not found: $FILE" >&2
  exit 1
fi

LINES=$(wc -l < "$FILE" | tr -d ' ')

# Default caps mirror swift-linting/SKILL.md and `.swiftlint.yml` `file_length`.
MAIN_CAP=600
OVERLAY_CAP=400

case "$FILE" in
  *Overlay*|*overlay*) CAP="$OVERLAY_CAP" ; KIND="overlay" ;;
  *)                   CAP="$MAIN_CAP"    ; KIND="main"    ;;
esac

echo "=== pre-split-check: $FILE ==="
echo "Lines:        $LINES  (cap for $KIND files: $CAP)"

if [ "$LINES" -le "$CAP" ]; then
  echo "Status:       Under cap — splitting may be premature. Confirm before proceeding."
elif [ "$LINES" -lt $((CAP + 100)) ]; then
  echo "Status:       Just over cap — small split may suffice."
else
  echo "Status:       Well over cap — meaningful split required."
fi

echo
echo "--- MARK sections (suggested split boundaries) ---"
if grep -n "// MARK:" "$FILE" >/dev/null 2>&1; then
  grep -n "// MARK:" "$FILE"
else
  echo "(none — consider adding MARK comments before splitting)"
fi

echo
echo "--- extension blocks ---"
if grep -nE "^extension " "$FILE" >/dev/null 2>&1; then
  grep -nE "^extension " "$FILE"
else
  echo "(none)"
fi

echo
echo "--- private / fileprivate members ---"
echo "(these must change to 'internal' if accessed from an extension file)"
if grep -nE "^[[:space:]]*(private|fileprivate)[[:space:]]+(var|let|func|class|struct|enum)" "$FILE" >/dev/null 2>&1; then
  grep -nE "^[[:space:]]*(private|fileprivate)[[:space:]]+(var|let|func|class|struct|enum)" "$FILE"
else
  echo "(none — no visibility changes needed)"
fi

echo
echo "--- summary ---"
PRIVATE_COUNT=$(grep -cE "^[[:space:]]*(private|fileprivate)[[:space:]]+(var|let|func|class|struct|enum)" "$FILE" || true)
MARK_COUNT=$(grep -c "// MARK:" "$FILE" || true)
EXT_COUNT=$(grep -cE "^extension " "$FILE" || true)
echo "  $PRIVATE_COUNT private/fileprivate members"
echo "  $MARK_COUNT MARK sections"
echo "  $EXT_COUNT existing extensions in-file"
echo
echo "Next steps:"
echo "  1. Commit any pending work (Step 0 of workflow)."
echo "  2. Decide split boundaries (use MARK list above)."
echo "  3. For each private member that will be accessed across files, plan to widen to internal."
echo "  4. See references/examples.md for before/after patterns."
