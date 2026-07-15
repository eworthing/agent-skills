#!/usr/bin/env bash
# Run fixture tests for audit-platform-guards.py.
#
# The clean-* cases are the load-bearing ones: each is a real false positive the
# previous file-scoped implementation produced against a shipping 4-platform
# repo (19/19 hits, all wrong). A fixture with none of the audited symbols would
# pass vacuously — these all contain the symbol and guard it correctly.
#
# Portability: Bash 3.2+ / BSD or GNU userland. The auditor itself needs python3.

set -u

script_dir="$(cd "$(dirname "$0")" && pwd -P)"
skill_dir="$(cd "$script_dir/.." && pwd -P)"
auditor="$script_dir/audit-platform-guards.py"
fixtures="$skill_dir/tests/fixtures"

failures=0

# run_case <fixture> <expected_exit> <required-patterns|pipe-separated>
# Pass '' for required to assert only the exit status.
run_case() {
  name="$1"
  expected_status="$2"
  required="$3"

  output="$(python3 "$auditor" "$fixtures/$name" 2>&1)"
  status=$?

  if [ "$status" -ne "$expected_status" ]; then
    printf '[FAIL] %s: expected exit %s, got %s\n' "$name" "$expected_status" "$status"
    printf '%s\n' "$output" | sed 's/^/  /'
    failures=$((failures + 1))
    return
  fi

  if [ -n "$required" ]; then
    old_ifs="$IFS"
    IFS='|'
    for pattern in $required; do
      IFS="$old_ifs"
      if ! printf '%s\n' "$output" | grep -Fq "$pattern"; then
        printf '[FAIL] %s: missing output pattern: %s\n' "$name" "$pattern"
        printf '%s\n' "$output" | sed 's/^/  /'
        failures=$((failures + 1))
        return
      fi
      IFS='|'
    done
    IFS="$old_ifs"
  fi

  printf '[OK] %s\n' "$name"
}

# refuse_case <fixture> <pattern-that-must-NOT-appear>
refuse_case() {
  name="$1"
  forbidden="$2"

  output="$(python3 "$auditor" "$fixtures/$name" 2>&1)"

  if printf '%s\n' "$output" | grep -Fq "$forbidden"; then
    printf '[FAIL] %s: unexpected output pattern: %s\n' "$name" "$forbidden"
    printf '%s\n' "$output" | sed 's/^/  /'
    failures=$((failures + 1))
    return
  fi

  printf '[OK] %s (no %s)\n' "$name" "$forbidden"
}

# --- clean: correctly guarded code must produce ZERO hits ------------------
# Each pins a false positive from the field run.
run_case clean-file-wrapped-tvos     0 'No platform-guard issues found.'
run_case clean-else-sheet-branch     0 'No platform-guard issues found.'
run_case clean-doc-comment-only      0 'No platform-guard issues found.'
run_case clean-os-ios-gated-haptics  0 'No platform-guard issues found.'
run_case clean-three-way-tabview     0 'No platform-guard issues found.'
run_case clean-elseif-else-is-ios    0 'No platform-guard issues found.'
run_case clean-canimport-pasteboard  0 'No platform-guard issues found.'
# D1's own field FP: an app that injects \.editMode on tvOS owns that channel,
# so its tvOS readers are live, not dead. D1 must stay silent here.
run_case clean-app-injects-editmode-tvos 0 'No platform-guard issues found.'

# Belt and braces: assert the specific stale trap codes never fire on clean code.
refuse_case clean-file-wrapped-tvos    APPLE-MP-FAIL
refuse_case clean-os-ios-gated-haptics APPLE-MP-FAIL
refuse_case clean-elseif-else-is-ios   APPLE-MP-FAIL
refuse_case clean-app-injects-editmode-tvos APPLE-MP-INFO

# --- fail: real breaks must still be caught --------------------------------
run_case fail-t1-haptics-canimport 1 'APPLE-MP-FAIL tvOS T1-canImport-vs-os|UIKit symbol unavailable on tvOS'
run_case fail-t1b-ondrop-tvos      1 'APPLE-MP-FAIL tvOS T1b-drop-receiving-tvos'
run_case fail-t2-editmode-macos    1 'APPLE-MP-FAIL macOS T2-editmode-macos'
run_case fail-t3-tabview-page      1 'APPLE-MP-FAIL macOS T3-tabview-page-unguarded'
run_case fail-t4-topbar            1 'APPLE-MP-FAIL macOS T4-topbar-placement-unguarded'
run_case fail-t5-fullscreencover   1 'APPLE-MP-FAIL macOS T5-fullscreencover-unguarded'

# --- info: dead code reported, but never fails the gate --------------------
run_case info-editmode-tvos-deadcode 0 'APPLE-MP-INFO tvOS D1-editmode-tvos-deadcode'
run_case info-topbar-tvos-deadcode   0 'APPLE-MP-INFO tvOS D2-topbar-tvos-deadcode'
refuse_case info-editmode-tvos-deadcode APPLE-MP-FAIL
refuse_case info-topbar-tvos-deadcode   APPLE-MP-FAIL

# --- evals.json integrity -------------------------------------------------
# The agent-facing evals reference fixtures by relative path. An eval pointing
# at a moved or renamed fixture is silently useless — it still "passes" by never
# running. Assert the JSON parses and every referenced file resolves.
evals_json="$skill_dir/evals/evals.json"
if ! python3 - "$evals_json" <<'PY'
import json, pathlib, sys

path = pathlib.Path(sys.argv[1])
try:
    data = json.loads(path.read_text())
except (OSError, json.JSONDecodeError) as exc:
    print(f"[FAIL] evals.json does not parse: {exc}")
    sys.exit(1)

bad = 0
names = set()
for ev in data.get("evals", []):
    name = ev.get("name", f"id={ev.get('id')}")
    if name in names:
        print(f"[FAIL] evals.json: duplicate eval name {name}")
        bad += 1
    names.add(name)
    for key in ("id", "name", "prompt", "expected_output"):
        if key not in ev:
            print(f"[FAIL] evals.json: {name} missing '{key}'")
            bad += 1
    for rel in ev.get("files", []):
        if not (path.parent / rel).resolve().is_file():
            print(f"[FAIL] evals.json: {name} references missing fixture {rel}")
            bad += 1

# Eval fixtures must not explain themselves. tests/fixtures headers document the
# regression they pin — correct there, disqualifying here: an agent reading
# "Every tvOS reader below is live" is doing comprehension, not judgment. That
# contamination made eval 0 pass cold, proving nothing, until it was caught by
# actually running it.
TELLS = ("Expect:", "false positive", "Regression:", "Field false positive", "Info D")
for fixture in sorted((path.parent / "fixtures").rglob("*.swift")):
    head = "\n".join(fixture.read_text().splitlines()[:20])
    hit = next((t for t in TELLS if t in head), None)
    if hit:
        print(f"[FAIL] evals/fixtures: {fixture.name} leaks its answer ({hit!r} in header)")
        bad += 1

if bad:
    sys.exit(1)
print(
    f"[OK] evals.json: {len(data.get('evals', []))} evals, all fixtures resolve, "
    "no eval fixture leaks its answer"
)
PY
then
  failures=$((failures + 1))
fi

if [ "$failures" -eq 0 ]; then
  printf '== apple-multiplatform tests: PASS ==\n'
  exit 0
fi

printf '== apple-multiplatform tests: FAIL (%d) ==\n' "$failures"
exit 1
