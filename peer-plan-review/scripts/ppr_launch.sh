#!/usr/bin/env bash
# ppr_launch.sh — canonical launch entrypoint for one peer-plan-review round.
#
# Wraps scripts/run_review.py so a round is a single command: derives every
# canonical temp path from the review id (ppr_paths.py), always passes the
# runner's coupled flags together (--error-log needs --review-id), tees runner
# output to <tmp>/ppr-<id>-runner.log, writes the true runner exit code to
# <tmp>/ppr-<id>-exit.code, and exits with that same code so a background
# host's completion notification reflects real success or failure.
#
# Launch it in the background (Claude Code: run_in_background: true) and wait
# for the completion notification. Do not wrap it in a foreground poll loop —
# the host shell ceiling (~120 s) kills foreground waits long before a real
# review finishes.
#
# Usage:
#   ppr_launch.sh --review-id <id> --reviewer <provider> \
#     [--model <model>] [--effort <low|medium|high|xhigh>] \
#     [--timeout <seconds>] [--resume] [extra run_review.py flags...]
#
# --model/--effort are forwarded only when supplied. Unrecognized flags pass
# through verbatim to run_review.py (e.g. --summary-file).

set -euo pipefail

usage() {
  sed -n '2,23p' "$0" | sed 's/^# \{0,1\}//'
}

REVIEW_ID=""
REVIEWER=""
MODEL=""
EFFORT=""
TIMEOUT=1200
RESUME=0
EXTRA_ARGS=()

while [ $# -gt 0 ]; do
  case "$1" in
    --review-id) REVIEW_ID="${2:?--review-id needs a value}"; shift 2 ;;
    --reviewer)  REVIEWER="${2:?--reviewer needs a value}"; shift 2 ;;
    --model)     MODEL="${2:?--model needs a value}"; shift 2 ;;
    --effort)    EFFORT="${2:?--effort needs a value}"; shift 2 ;;
    --timeout)   TIMEOUT="${2:?--timeout needs a value}"; shift 2 ;;
    --resume)    RESUME=1; shift ;;
    -h|--help)   usage; exit 0 ;;
    *)           EXTRA_ARGS+=("$1"); shift ;;
  esac
done

if [ -z "$REVIEW_ID" ]; then
  echo "Error: --review-id is required" >&2
  exit 2
fi
if [ -z "$REVIEWER" ]; then
  echo "Error: --reviewer is required" >&2
  exit 2
fi

# Resolve the skill dir from this script's own location (works via symlink
# install; no readlink -f, which BSD/macOS lacks).
SKILL_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)

# Export PLAN_FILE/PROMPT_FILE/OUTPUT_FILE/SESSION_FILE/EVENTS_FILE/ERROR_LOG/
# CODEX_HOME_MANIFEST (and TMPDIR) for this review id.
eval "$(python3 "$SKILL_DIR/scripts/ppr_paths.py" --review-id "$REVIEW_ID" --format shell)"

RUNNER_LOG="${TMPDIR}/ppr-${REVIEW_ID}-runner.log"
EXIT_CODE_FILE="${TMPDIR}/ppr-${REVIEW_ID}-exit.code"

# Fail fast before spending reviewer time: the host must have snapshotted the
# plan and built the prompt for this round already.
if [ ! -s "$PLAN_FILE" ]; then
  echo "Error: plan snapshot missing or empty: $PLAN_FILE" >&2
  exit 2
fi
if [ ! -s "$PROMPT_FILE" ]; then
  echo "Error: prompt missing or empty: $PROMPT_FILE" >&2
  exit 2
fi

CMD=(python3 "$SKILL_DIR/scripts/run_review.py"
  --reviewer "$REVIEWER"
  --plan-file "$PLAN_FILE"
  --prompt-file "$PROMPT_FILE"
  --output-file "$OUTPUT_FILE"
  --session-file "$SESSION_FILE"
  --events-file "$EVENTS_FILE"
  --error-log "$ERROR_LOG"
  --review-id "$REVIEW_ID"
  --codex-home-manifest "$CODEX_HOME_MANIFEST"
  --timeout "$TIMEOUT")
if [ -n "$MODEL" ]; then
  CMD+=(--model "$MODEL")
fi
if [ -n "$EFFORT" ]; then
  CMD+=(--effort "$EFFORT")
fi
if [ "$RESUME" -eq 1 ]; then
  CMD+=(--resume)
fi
# bash 3.2 + set -u: guard expansion of a possibly-empty array.
CMD+=(${EXTRA_ARGS[@]+"${EXTRA_ARGS[@]}"})

# Run the runner. errexit is suspended around the pipeline so a runner failure
# still reaches the exit-code write below; PIPESTATUS[0] preserves the runner's
# code through the tee.
set +e
"${CMD[@]}" 2>&1 | tee "$RUNNER_LOG"
runner_rc=${PIPESTATUS[0]}
set -e

printf '%s\n' "$runner_rc" > "$EXIT_CODE_FILE"

# Best-effort resume-degradation warning (#6): if a requested resume silently
# fell back to a fresh exec, say so. Never masks the runner exit code.
if [ -f "$SESSION_FILE" ]; then
  warn=$(python3 - "$SESSION_FILE" <<'PY' 2>/dev/null || true
import json
import sys

try:
    with open(sys.argv[1], encoding="utf-8") as fh:
        session = json.load(fh)
except Exception:
    sys.exit(0)
if session.get("resume_requested") and not session.get("resume_attempted"):
    reason = session.get("resume_reason", "unknown")
    print(f"WARNING: resume degraded to fresh exec (resume_reason={reason})")
PY
)
  if [ -n "$warn" ]; then
    printf '%s\n' "$warn" >&2
    printf '%s\n' "$warn" >> "$RUNNER_LOG"
  fi
fi

exit "$runner_rc"
