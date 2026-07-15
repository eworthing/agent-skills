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

if [ "$failures" -eq 0 ]; then
  printf '== apple-multiplatform tests: PASS ==\n'
  exit 0
fi

printf '== apple-multiplatform tests: FAIL (%d) ==\n' "$failures"
exit 1
