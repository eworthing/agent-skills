#!/usr/bin/env bash
# cr-batch.sh — drive code-review-opencode from a script or an agent.
#
# Why this exists: `opencode run "/code-review-opencode ..."` does not resolve slash
# commands (opencode issue #7345), and the command endpoint blocks until the
# whole review finishes. This wrapper starts a project server, creates a
# session with the requested model variant, posts the command in the
# background, and leaves a session id you can poll.
#
# Usage:
#   scripts/cr-batch.sh start <path-or-range>   # prints the session id, returns at once
#   scripts/cr-batch.sh status <session-id>    # running | succeeded | failed (+ report)
#   scripts/cr-batch.sh wait <session-id>      # block until done, then print status
#   scripts/cr-batch.sh report <session-id>    # print the JSON report artifact
#   scripts/cr-batch.sh plan <path-or-range>   # print the exact command text
#   scripts/cr-batch.sh stop                   # stop the server this script started
#
# Environment:
#   CR_REPO        repository containing .opencode/plugins/code-review-opencode (default: $PWD)
#   CR_PORT        server port (default: 49411)
#   CR_MODEL       provider/model[#variant] (default: opencode-go/deepseek-v4.1-flash#max)
#   CR_CONCURRENCY child concurrency (default: 6)
#   CR_REPORT_DIR  report artifact directory (default: $CR_REPO/.code-review-reports)
#   CR_STATE_DIR   server + session bookkeeping (default: $CR_REPORT_DIR/.driver)
set -eu

PROG=$(basename "$0")
REPO=${CR_REPO:-$PWD}
PORT=${CR_PORT:-49411}
MODEL=${CR_MODEL:-opencode-go/deepseek-v4.1-flash#max}
CONCURRENCY=${CR_CONCURRENCY:-6}
REPORT_DIR=${CR_REPORT_DIR:-${CODE_REVIEW_REPORT_DIR:-$REPO/.code-review-reports}}
STATE_DIR=${CR_STATE_DIR:-$REPORT_DIR/.driver}
BASE_URL="http://127.0.0.1:$PORT"

mkdir -p "$REPORT_DIR" "$STATE_DIR"

die() {
  echo "$PROG: $*" >&2
  exit 1
}

password() {
  [ -s "$STATE_DIR/password" ] || return 1
  cat "$STATE_DIR/password"
}

api() {
  method=$1
  path=$2
  body=${3-}
  pw=$(password) || die "no server password; run '$PROG start <target>' first"
  if [ -n "$body" ]; then
    curl -fsS -u "opencode:$pw" -H 'Content-Type: application/json' \
      -X "$method" "$BASE_URL$path" -d "$body"
  else
    curl -fsS -u "opencode:$pw" -X "$method" "$BASE_URL$path"
  fi
}

server_ok() {
  pw=$(password) || return 1
  curl -fsS -u "opencode:$pw" "$BASE_URL/api/session" >/dev/null 2>&1
}

start_server() {
  if server_ok; then
    return 0
  fi
  # Distinguish "nothing is listening" (curl exit 7, code 000) from "something
  # else owns the port" without depending on lsof.
  probe=$(curl -s -o /dev/null -w '%{http_code}' "$BASE_URL/api/session" 2>/dev/null || true)
  if [ "${probe:-000}" != "000" ]; then
    die "port $PORT is already used by another process; set CR_PORT"
  fi
  (
    cd "$REPO"
    CODE_REVIEW_REPORT_DIR="$REPORT_DIR" CODE_REVIEW_CONCURRENCY="$CONCURRENCY" \
      nohup opencode serve --port "$PORT" >"$STATE_DIR/server.log" 2>&1 &
    echo $! >"$STATE_DIR/pid"
  )
  i=0
  while [ "$i" -lt 120 ]; do
    if [ -s "$STATE_DIR/server.log" ] && grep -q 'server password ' "$STATE_DIR/server.log"; then
      awk '/server password/{print $3}' "$STATE_DIR/server.log" | tail -1 >"$STATE_DIR/password"
      return 0
    fi
    i=$((i + 1))
    sleep 0.5
  done
  die "server did not start; see $STATE_DIR/server.log"
}

model_json() {
  python3 - "$MODEL" <<'PY'
import json, sys
value = sys.argv[1]
variant = None
if "#" in value:
    value, variant = value.split("#", 1)
provider, model = value.split("/", 1)
ref = {"providerID": provider, "id": model}
if variant:
    ref["variant"] = variant
print(json.dumps(ref))
PY
}

command_text() {
  printf '%s\n' "max --max-findings all --concurrency $CONCURRENCY --model $MODEL $1"
}

cmd_plan() {
  [ $# -ge 1 ] || die "usage: $PROG plan <path-or-range>"
  command_text "$1"
}

cmd_start() {
  [ $# -ge 1 ] || die "usage: $PROG start <path-or-range>"
  target=$1
  start_server
  session_body=$(python3 - "$target" "$(model_json)" <<'PY'
import json, sys
print(json.dumps({"title": "code-review-opencode batch: " + sys.argv[1], "model": json.loads(sys.argv[2])}))
PY
)
  sid=$(api POST /api/session "$session_body" |
    python3 -c 'import json,sys; print(json.load(sys.stdin)["data"]["id"])')
  printf '%s\n' "$target" >"$STATE_DIR/$sid.target"
  # The command endpoint returns only when the review is over. Post it from a
  # detached helper so the caller gets the session id immediately.
  nohup "$0" __post "$sid" "$target" "$(command_text "$target")" >"$STATE_DIR/$sid.command.log" 2>&1 &
  echo "$sid"
}

cmd_post() {
  [ $# -ge 3 ] || die "__post needs a session id, target, and command text"
  sid=$1
  body=$(python3 - "$3" <<'PY'
import json, sys
print(json.dumps({"name": "code-review-opencode", "text": sys.argv[1]}))
PY
)
  if api POST "/api/session/$sid/command" "$body"; then
    printf '%s\n' succeeded >"$STATE_DIR/$sid.command-status"
  else
    rc=$?
    printf 'failed:%s\n' "$rc" >"$STATE_DIR/$sid.command-status"
    return "$rc"
  fi
}

cmd_status() {
  [ $# -ge 1 ] || die "usage: $PROG status <session-id>"
  sid=$1
  session=$(api GET "/api/session/$sid")
  [ -f "$STATE_DIR/$sid.target" ] || die "missing target association for $sid; refusing to infer the report"
  target=$(cat "$STATE_DIR/$sid.target" 2>/dev/null || true)
  command_status=$(cat "$STATE_DIR/$sid.command-status" 2>/dev/null || true)
  if [ "$command_status" = "failed" ] || case "$command_status" in failed:*) true ;; *) false ;; esac; then
    printf 'command: %s\n' "$command_status"
    return 3
  fi
  validation=$(python3 "$(dirname "$0")/cr_completion.py" --directory "$REPORT_DIR" --session-id "$sid" --target "$target" 2>&1) && valid=0 || valid=$?
  if [ "$valid" -eq 0 ]; then
    printf 'session: %s\n' "$sid"
    printf 'completion: %s\n' "$validation"
    return 0
  fi
  if [ "$valid" -eq 2 ]; then
    printf 'completion: %s\n' "$validation"
    return 3
  fi
  if [ "$command_status" = succeeded ]; then
    printf 'completion: %s\n' "$validation"
    return 3
  fi
  python3 - "$session" "$command_status" <<'PY'
import json, sys
session = json.loads(sys.argv[1])["data"]
command_status = sys.argv[2]
outcome = session.get("outcome")
print("session:", session.get("id"))
print("command:", command_status or "running")
print("session outcome:", outcome or "not set")
if command_status.startswith("failed:"):
    print("command request failed:", command_status.split(":", 1)[1])
    status = 3
elif command_status != "succeeded":
    print("report: pending")
    status = 4
else:
    print("command request: completed without a matching completion record")
    status = 3
sys.exit(status)
PY
  return 4
}

cmd_wait() {
  [ $# -ge 1 ] || die "usage: $PROG wait <session-id>"
  sid=$1
  while :; do
    if cmd_status "$sid"; then
      return 0
    else
      status=$?
    fi
    [ "$status" -eq 4 ] || return "$status"
    sleep 2
  done
}

cmd_report() {
  [ $# -ge 1 ] || die "usage: $PROG report <session-id>"
  sid=$1
  [ -f "$STATE_DIR/$sid.target" ] || die "missing target association for $sid; refusing to infer the report"
  target=$(cat "$STATE_DIR/$sid.target" 2>/dev/null || true)
  path=$(python3 "$(dirname "$0")/cr_completion.py" --directory "$REPORT_DIR" --session-id "$sid" --target "$target" --path-only 2>/dev/null || true)
  [ -n "$path" ] || die "no report for $sid yet"
  cat "$path"
}

cmd_stop() {
  if [ -f "$STATE_DIR/pid" ]; then
    pid=$(cat "$STATE_DIR/pid")
    kill "$pid" 2>/dev/null || true
    rm -f "$STATE_DIR/pid"
  fi
}

case "${1-}" in
  start) shift; cmd_start "$@" ;;
  status) shift; cmd_status "$@" ;;
  wait) shift; cmd_wait "$@" ;;
  report) shift; cmd_report "$@" ;;
  plan) shift; cmd_plan "$@" ;;
  stop) cmd_stop ;;
  __post) shift; cmd_post "$@" ;;
  *)
    sed -n '2,30p' "$0" | sed 's/^# \{0,1\}//'
    exit 2
    ;;
esac
