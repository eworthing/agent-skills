#!/usr/bin/env bash
# purge.sh — contest-refactor deep-reset helper.
#
# Wipes critic-memory artifacts (CURRENT_REVIEW.*, REVIEW_HISTORY.*,
# findings_registry.json, LOOP_STATE.*) by atomic per-file `mv` into a backup
# directory, then appends a JSON Lines audit entry to PURGE_LOG.jsonl.
# Works from any CWD — operates on files in the current directory.
#
# Usage:
#   purge.sh --confirm --backup-dir <path>    # full purge (mv + log)
#   purge.sh --dry-run                        # list targets; no acting
#   purge.sh --recover --backup-dir <path>    # post-manual-recovery audit
#   purge.sh -h | --help
#
# Exit codes:
#   0  success (including "nothing to purge")
#   1  total failure (mkdir backup-dir failed; no files moved)
#   2  precondition error (bad args, backup-dir already exists, etc.)
#   3  partial failure (some files moved, some failed)
#
# Portable Bash (macOS 3.2 + Linux 4+). No mapfile, no GNU-only flags.

set -u

# --- Constants ---
TARGET_FILES="CURRENT_REVIEW.json CURRENT_REVIEW.md REVIEW_HISTORY.json REVIEW_HISTORY.md findings_registry.json LOOP_STATE.json LOOP_STATE.json.deleting"
LOG_FILE="PURGE_LOG.jsonl"

# --- Args ---
MODE="purge"
BACKUP_DIR=""
CONFIRM=0

usage() {
  sed -n '2,15p' "$0" | sed 's/^# //;s/^#//'
}

while [ $# -gt 0 ]; do
  case "$1" in
    --backup-dir)
      shift
      [ $# -gt 0 ] || { echo "purge: --backup-dir requires a path" >&2; exit 2; }
      BACKUP_DIR="$1"
      ;;
    --dry-run)
      MODE="dry-run"
      ;;
    --recover)
      MODE="recover"
      ;;
    --confirm)
      CONFIRM=1
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "purge: unknown arg: $1" >&2
      exit 2
      ;;
  esac
  shift
done

# --- Helper: ISO 8601 UTC timestamp (BSD/GNU date compatible) ---
iso_ts() {
  date -u +%Y-%m-%dT%H:%M:%SZ
}

# --- Helper: enumerate present target files (one per line on stdout) ---
present_targets() {
  for f in $TARGET_FILES; do
    [ -f "$f" ] && echo "$f"
  done
}

# --- Helper: best-effort validate that present targets look like
#     contest-refactor artifacts. Catches accidental purge in unrelated
#     directories that happen to have files with the same names. Returns 0
#     if at least one target file has a marker field; 1 if files present
#     but none match. Empty input (no targets) → returns 0 (caller handles
#     nothing-to-purge path separately).
looks_like_contest_refactor_artifacts() {
  local found_marker=0
  for f in $TARGET_FILES; do
    [ -f "$f" ] || continue
    # JSON files should have schema_version or loop key; markdown files have
    # known headings. Cheap grep is sufficient — false positives are tolerable
    # (real artifacts have multiple markers); false negatives (skipping a
    # legitimate purge) are bad, so be permissive.
    case "$f" in
      *.json)
        if grep -qE '"schema_version"|"loop"|"state"|"findings"' "$f" 2>/dev/null; then
          found_marker=1
          break
        fi
        ;;
      *.md)
        if grep -qE '^### Loop Counter|^## Contest Verdict|^### Discovery|^### System Flag|HALT_SUCCESS|HALT_STAGNATION' "$f" 2>/dev/null; then
          found_marker=1
          break
        fi
        ;;
    esac
  done
  # Special-case: LOOP_STATE.json[.deleting] alone is enough (they exist only
  # if a loop ran). Detect by their distinct presence even without content match.
  if [ "$found_marker" = "0" ]; then
    if [ -f LOOP_STATE.json ] || [ -f LOOP_STATE.json.deleting ]; then
      found_marker=1
    fi
  fi
  [ "$found_marker" = "1" ]
}

# --- Helper: JSON-escape a string for embedding inside a JSON string literal ---
# Strategy: drop control chars (U+0000..U+001F) defensively via `tr -d`, then
# escape backslash + double-quote per RFC 8259. Real-world inputs to this
# function (state enum from a closed set, git SHA hex, backup-dir path) never
# legitimately contain control chars; dropping them prevents accidental JSONL
# corruption if a malformed CURRENT_REVIEW.json somehow contains escaped
# control sequences that get unescaped by jq -r.
json_escape() {
  printf '%s' "$1" \
    | tr -d '\000-\037' \
    | sed 's/\\/\\\\/g; s/"/\\"/g'
}

# --- Helper: build a JSON array literal from newline-separated stdin ---
json_array_from_lines() {
  awk 'BEGIN{first=1; printf "["}
       NF{ if(!first) printf ","; printf "\"%s\"", $0; first=0 }
       END{printf "]"}'
}

indent_lines() {
  while IFS= read -r line; do
    [ -z "$line" ] && continue
    printf '  - %s\n' "$line"
  done
}

# --- Helper: get current loop + state from CURRENT_REVIEW.json if present (best-effort) ---
prior_field() {
  # $1 = field name (e.g., "loop", "state")
  if [ -f CURRENT_REVIEW.json ]; then
    # Try jq if available; fall back to grep
    if command -v jq >/dev/null 2>&1; then
      jq -r ".$1 // empty" CURRENT_REVIEW.json 2>/dev/null
    else
      # Match field value; sed pattern stops at quote/comma/brace so a value
      # containing legitimate internal whitespace is preserved verbatim.
      # Do NOT pipe to `tr -d '[:space:]'` — would mangle multi-word values.
      grep -E "\"$1\"[[:space:]]*:" CURRENT_REVIEW.json 2>/dev/null \
        | head -1 \
        | sed -E "s/.*\"$1\"[[:space:]]*:[[:space:]]*\"?([^\",}]*)\"?.*/\1/"
    fi
  fi
}

prior_head_sha() {
  if command -v git >/dev/null 2>&1 && git rev-parse --git-dir >/dev/null 2>&1; then
    git rev-parse HEAD 2>/dev/null
  fi
}

# --- Dry-run mode ---
if [ "$MODE" = "dry-run" ]; then
  echo "# purge --dry-run"
  echo "CWD: $(pwd)"
  echo "Target files present:"
  present_targets | sed 's/^/  - /'
  echo "(no action taken)"
  exit 0
fi

# --- Recover mode ---
if [ "$MODE" = "recover" ]; then
  [ -n "$BACKUP_DIR" ] || { echo "purge --recover: --backup-dir <path> required" >&2; exit 2; }
  [ -d "$BACKUP_DIR" ] || { echo "purge --recover: backup dir not found: $BACKUP_DIR" >&2; exit 2; }

  # Verify no target files remain in CWD
  REMAINING=""
  for f in $TARGET_FILES; do
    if [ -f "$f" ]; then
      REMAINING="$REMAINING $f"
    fi
  done
  if [ -n "$REMAINING" ]; then
    echo "purge --recover: target files still present in CWD:" >&2
    for f in $REMAINING; do echo "  - $f" >&2; done
    echo "Move each into $BACKUP_DIR/ first, then re-run --recover." >&2
    exit 1
  fi

  # Safety check: backup dir must contain at least one expected target
  # file. Catches "wrong backup dir" mistakes where the named path is
  # technically a directory but holds unrelated content.
  FOUND_TARGET=0
  for f in $TARGET_FILES; do
    if [ -f "$BACKUP_DIR/$f" ]; then
      FOUND_TARGET=1
      break
    fi
  done
  if [ "$FOUND_TARGET" = "0" ]; then
    echo "purge --recover: backup dir $BACKUP_DIR contains NO expected target files." >&2
    echo "Expected at least one of:" >&2
    for f in $TARGET_FILES; do echo "  - $f" >&2; done
    echo "Verify the --backup-dir path matches the original purge's backup." >&2
    exit 2
  fi

  # Append purge_partial_recovery JSONL entry. Script owns the write.
  TS=$(iso_ts)
  ESC_BACKUP=$(json_escape "$BACKUP_DIR")
  RECOVERED=$(
    for path in "$BACKUP_DIR"/*; do
      [ -e "$path" ] || continue
      name=$(basename "$path")
      [ "$name" = ".purge-errors.log" ] && continue
      printf '%s\n' "$name"
    done | json_array_from_lines
  )
  printf '{"event":"purge_partial_recovery","ts":"%s","backup_path":"%s","files_recovered":%s}\n' \
    "$TS" "$ESC_BACKUP" "$RECOVERED" >> "$LOG_FILE"

  echo "# purge --recover"
  echo "Verified no target files remain in CWD."
  echo "Verified backup dir contains expected target files."
  echo "Appended purge_partial_recovery entry to $LOG_FILE."
  exit 0
fi

# --- Default mode: full purge ---
[ "$CONFIRM" = "1" ] || { echo "purge: --confirm required for destructive purge" >&2; exit 2; }
[ -n "$BACKUP_DIR" ] || { echo "purge: --backup-dir <path> required (or --dry-run, --recover)" >&2; exit 2; }
if [ -e "$BACKUP_DIR" ]; then
  echo "purge: backup-dir already exists: $BACKUP_DIR" >&2
  echo "Append a -<rand> suffix to avoid collision." >&2
  exit 2
fi

# Enumerate targets
TARGETS=$(present_targets)
if [ -z "$TARGETS" ]; then
  echo "# purge"
  echo "Nothing to purge — no target files in CWD."
  echo "(no backup dir created, no PURGE_LOG.jsonl entry)"
  exit 0
fi

# Safety check: refuse to purge if target files exist but don't look like
# contest-refactor artifacts. Prevents accidental data loss in unrelated
# directories that happen to have files with colliding names.
if ! looks_like_contest_refactor_artifacts; then
  echo "purge: target files present in CWD but do NOT look like contest-refactor artifacts." >&2
  echo "Refusing to purge to prevent accidental data loss." >&2
  echo "Present files (no contest-refactor markers found):" >&2
  echo "$TARGETS" | indent_lines >&2
  echo "" >&2
  echo "If these ARE contest-refactor artifacts that lack expected markers" >&2
  echo "(e.g., truncated/corrupted), invoke /contest-refactor first to repair" >&2
  echo "state, OR manually delete the files outside this helper." >&2
  exit 2
fi

# Create backup dir
if ! mkdir -p "$BACKUP_DIR" 2>/dev/null; then
  echo "purge: mkdir failed: $BACKUP_DIR" >&2
  echo "State untouched. Fix permissions/disk and retry." >&2
  exit 1
fi

# Per-file atomic mv. Capture MOVED and FAILED lists via sidecar files (bash
# 3.2 subshells lose variable mutations across pipes). Trap to clean up
# sidecars if the script is killed mid-loop — without it, a leftover
# .moved/.failed would make the backup-dir look corrupt + collide with the
# duplicate-existence check on next invocation.
MOVED=""
FAILED=""
ERR_LOG="$BACKUP_DIR/.purge-errors.log"
trap 'rm -f "$BACKUP_DIR/.moved" "$BACKUP_DIR/.failed"' EXIT INT TERM HUP

echo "$TARGETS" | while IFS= read -r f; do
  [ -z "$f" ] && continue
  if mv "$f" "$BACKUP_DIR/" 2>>"$ERR_LOG"; then
    echo "$f" >> "$BACKUP_DIR/.moved"
  else
    echo "$f" >> "$BACKUP_DIR/.failed"
  fi
done

# Read lists back (subshell-safe pattern; bash 3.2 doesn't carry vars out of pipes)
[ -f "$BACKUP_DIR/.moved" ] && MOVED=$(cat "$BACKUP_DIR/.moved")
[ -f "$BACKUP_DIR/.failed" ] && FAILED=$(cat "$BACKUP_DIR/.failed")
rm -f "$BACKUP_DIR/.moved" "$BACKUP_DIR/.failed"
trap - EXIT INT TERM HUP

# Build JSON arrays
MOVED_JSON=$(echo "$MOVED" | json_array_from_lines)
FAILED_JSON=$(echo "$FAILED" | json_array_from_lines)

# Capture prior loop/state/head (best-effort; may be empty if files were missing)
# Note: CURRENT_REVIEW.json was the source — already mv'd. So we read from BACKUP_DIR copy.
if [ -f "$BACKUP_DIR/CURRENT_REVIEW.json" ]; then
  PRIOR_LOOP=$( (cd "$BACKUP_DIR" && prior_field loop) )
  PRIOR_STATE=$( (cd "$BACKUP_DIR" && prior_field state) )
else
  PRIOR_LOOP=""
  PRIOR_STATE=""
fi
PRIOR_HEAD=$(prior_head_sha)

# Build prior fields as JSON values (null when empty)
[ -z "$PRIOR_LOOP" ] && PRIOR_LOOP_JSON="null" || PRIOR_LOOP_JSON="$PRIOR_LOOP"
[ -z "$PRIOR_STATE" ] && PRIOR_STATE_JSON="null" || PRIOR_STATE_JSON="\"$(json_escape "$PRIOR_STATE")\""
[ -z "$PRIOR_HEAD" ] && PRIOR_HEAD_JSON="null" || PRIOR_HEAD_JSON="\"$(json_escape "$PRIOR_HEAD")\""

# Append JSONL entry
TS=$(iso_ts)
ESC_BACKUP=$(json_escape "$BACKUP_DIR")
printf '{"event":"purge","ts":"%s","backup_path":"%s","files_moved":%s,"files_failed":%s,"prior_loop":%s,"prior_state":%s,"prior_head_sha":%s}\n' \
  "$TS" "$ESC_BACKUP" "$MOVED_JSON" "$FAILED_JSON" \
  "$PRIOR_LOOP_JSON" "$PRIOR_STATE_JSON" "$PRIOR_HEAD_JSON" \
  >> "$LOG_FILE"

# Summary
echo "# purge"
echo "Backup: $BACKUP_DIR/"
echo "Moved:"
echo "$MOVED" | indent_lines
if [ -n "$FAILED" ]; then
  echo "Failed:"
  echo "$FAILED" | indent_lines
  echo "Errors: $ERR_LOG"
  echo "State partial. See halt-handoff.md § Purge Partial-Failure handoff."
  exit 3
fi
echo "Appended purge entry to $LOG_FILE."
exit 0
