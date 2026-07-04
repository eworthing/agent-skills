#!/usr/bin/env bash
# pre-split-check.sh — Inspect a Swift file before splitting.
#
# Reports: line count, MARK sections, extensions, private/fileprivate members,
# any obvious cross-file-access concerns, and the project registration model
# (SPM / buildable-folder / legacy groups) so the caller knows whether the
# workflow's Xcode-registration step is likely a no-op. Read-only; never
# modifies the file and never changes exit status based on project detection.
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
EXT_CAP=400   # extension files: OriginalFile+Feature.swift

# Extension files follow the `Base+Feature.swift` naming convention.
case "$(basename "$FILE")" in
  *+*.swift) CAP="$EXT_CAP"  ; KIND="extension" ;;
  *)         CAP="$MAIN_CAP" ; KIND="main"      ;;
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
echo "--- project registration model ---"
echo "(is the workflow's Xcode-registration step likely a no-op for this file?)"
# Walk up from the file's directory recording the NEAREST enclosing SPM package
# and/or .xcodeproj. Bounded (depth cap + repo root), read-only, non-fatal — this
# section never alters the script's exit status. "Project has synchronized groups"
# is only a heuristic: the file must actually sit under a blue (synchronized)
# folder, which this script can't see — so buildable-folder verdicts stay
# conditional. Portable: plain while/case/dirname, no realpath/mapfile/find -printf.
DEPTH_CAP=8
start_dir=$(dirname "$FILE")
[ -n "$start_dir" ] || start_dir="."

pkg_dir=""
xcodeproj_dir=""
xcodeproj_first=""
xcodeproj_count=0
xcodeproj_list=""
cur="$start_dir"
depth=0
while [ "$depth" -lt "$DEPTH_CAP" ]; do
  # Check this directory for markers BEFORE any stop condition (so the repo root
  # itself is inspected, not skipped).
  if [ -z "$pkg_dir" ] && [ -f "$cur/Package.swift" ]; then
    pkg_dir="$cur"
  fi
  if [ -z "$xcodeproj_dir" ]; then
    for proj in "$cur"/*.xcodeproj; do
      [ -d "$proj" ] || continue          # literal glob when nothing matches
      xcodeproj_dir="$cur"
      xcodeproj_count=$((xcodeproj_count + 1))
      xcodeproj_list="$xcodeproj_list $proj"
      [ -n "$xcodeproj_first" ] || xcodeproj_first="$proj"
    done
  fi
  # Stop at repo root (.git) or filesystem root — after the checks above.
  [ -d "$cur/.git" ] && break
  case "$cur" in
    /|.) break ;;
  esac
  parent=$(dirname "$cur")
  [ "$parent" != "$cur" ] || break        # no upward progress
  cur="$parent"
  depth=$((depth + 1))
done

[ -n "$pkg_dir" ] && echo "  SPM package:   $pkg_dir/Package.swift"
[ -n "$xcodeproj_dir" ] && echo "  Xcode project:$xcodeproj_list  (in $xcodeproj_dir)"

if [ -n "$pkg_dir" ] && [ -n "$xcodeproj_dir" ]; then
  echo "Verdict:      MIXED project — both an SPM package and an .xcodeproj enclose this file."
  echo "              Prefer the nearest owner; verify manually which target builds it."
elif [ -n "$pkg_dir" ]; then
  echo "Verdict:      SPM — sources auto-discovered. Skip Xcode registration (Step 6)."
elif [ -n "$xcodeproj_dir" ]; then
  if [ "$xcodeproj_count" -gt 1 ]; then
    echo "Verdict:      MULTIPLE .xcodeproj in $xcodeproj_dir — verify manually."
    echo "              Do not assume one project's folder model applies to this file."
  elif [ -f "$xcodeproj_first/project.pbxproj" ] && \
       grep -q PBXFileSystemSynchronizedRootGroup "$xcodeproj_first/project.pbxproj" 2>/dev/null; then
    echo "Verdict:      Buildable folders present in $(basename "$xcodeproj_first")."
    echo "              IF this file is under a blue (synchronized) folder it is auto-included — skip Step 6."
    echo "              ELSE (yellow group) register per references/xcodeproj.md. Confirm via the blue-folder cue + a build."
  else
    echo "Verdict:      Legacy groups — register this file per references/xcodeproj.md."
  fi
else
  echo "Verdict:      No SPM package or .xcodeproj found within range — verify registration manually."
fi

echo
echo "Next steps:"
echo "  1. Commit any pending work (Step 0 of workflow)."
echo "  2. Decide split boundaries (use MARK list above)."
echo "  3. For each private member that will be accessed across files, plan to widen to internal."
echo "  4. See references/examples.md for before/after patterns."
