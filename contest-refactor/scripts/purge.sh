#!/usr/bin/env bash
# purge.sh — contest-refactor deep-reset helper.
#
# Wipes critic-memory artifacts (CURRENT_REVIEW.*, REVIEW_HISTORY.*,
# findings_registry.json, LOOP_STATE.*) by atomic per-file `mv` into a backup
# directory, then appends a JSON Lines audit entry to PURGE_LOG.jsonl.
# Works from any CWD — operates on files in the current directory.
#
# Usage:
#   purge.sh --backup-dir <path>              # full purge (mv + log)
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

# --- Helper: JSON-escape a string for embedding inside a JSON string literal ---
json_escape() {
  printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'
}

# --- Helper: build a JSON array literal from newline-separated stdin ---
json_array_from_lines() {
  awk 'BEGIN{first=1; printf "["}
       NF{ if(!first) printf ","; printf "\"%s\"", $0; first=0 }
       END{printf "]"}'
}

# --- Helper: get current loop + state from CURRENT_REVIEW.json if present (best-effort) ---
prior_field() {
  # $1 = field name (e.g., "loop", "state")
  if [ -f CURRENT_REVIEW.json ]; then
    # Try jq if available; fall back to grep
    if command -v jq >/dev/null 2>&1; then
      jq -r ".$1 // empty" CURRENT_REVIEW.json 2>/dev/null
    else
      grep -E "\"$1\"[[:space:]]*:" CURRENT_REVIEW.json 2>/dev/null \
        | head -1 \
        | sed -E "s/.*\"$1\"[[:space:]]*:[[:space:]]*\"?([^\",}]*)\"?.*/\1/" \
        | tr -d '[:space:]'
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

  # Append purge_partial_recovery JSONL entry. Script owns the write.
  TS=$(iso_ts)
  ESC_BACKUP=$(json_escape "$BACKUP_DIR")
  RECOVERED=$(ls -1 "$BACKUP_DIR" 2>/dev/null | grep -v '^\.purge-errors\.log$' | json_array_from_lines)
  printf '{"event":"purge_partial_recovery","ts":"%s","backup_path":"%s","files_recovered":%s}\n' \
    "$TS" "$ESC_BACKUP" "$RECOVERED" >> "$LOG_FILE"

  echo "# purge --recover"
  echo "Verified no target files remain in CWD."
  echo "Appended purge_partial_recovery entry to $LOG_FILE."
  exit 0
fi

# --- Default mode: full purge ---
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

# Create backup dir
if ! mkdir -p "$BACKUP_DIR" 2>/dev/null; then
  echo "purge: mkdir failed: $BACKUP_DIR" >&2
  echo "State untouched. Fix permissions/disk and retry." >&2
  exit 1
fi

# Per-file atomic mv. Capture MOVED and FAILED lists.
MOVED=""
FAILED=""
ERR_LOG="$BACKUP_DIR/.purge-errors.log"

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
echo "$MOVED" | sed 's/^/  - /'
if [ -n "$FAILED" ]; then
  echo "Failed:"
  echo "$FAILED" | sed 's/^/  - /'
  echo "Errors: $ERR_LOG"
  echo "State partial. See halt-handoff.md § Purge Partial-Failure handoff."
  exit 3
fi
echo "Appended purge entry to $LOG_FILE."
exit 0
