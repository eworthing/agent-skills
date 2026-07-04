#!/usr/bin/env bash
# Run fixture tests for check-doc-naming.sh.
#
# Portability: Bash 3.2+ / BSD or GNU userland.

set -u

script_dir="$(cd "$(dirname "$0")" && pwd -P)"
skill_dir="$(cd "$script_dir/.." && pwd -P)"
checker="$script_dir/check-doc-naming.sh"
fixtures="$skill_dir/tests/fixtures"

failures=0

run_case() {
  name="$1"
  expected_status="$2"
  required="$3"
  shift 3
  docs_root="$fixtures/$name/docs"

  output="$(bash "$checker" "$docs_root" "$@" 2>&1)"
  status=$?

  if [ "$status" -ne "$expected_status" ]; then
    printf '[FAIL] %s: expected exit %s, got %s\n' "$name" "$expected_status" "$status"
    printf '%s\n' "$output" | sed 's/^/  /'
    failures=$((failures + 1))
    return
  fi

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

  printf '[OK] %s\n' "$name"
}

run_case clean-project-local-taxonomy 0 '[WARN] naming advisories|== summary: CLEAN'
run_case clean-strict-type-status 0 '[OK] naming convention: 0 blocking violations|== summary: CLEAN'
run_case clean-dated-records 0 '[OK] naming convention: 0 blocking violations|== summary: CLEAN'
run_case clean-adr-numbering 0 '[OK] naming convention: 0 blocking violations|== summary: CLEAN'
run_case clean-declared-bundle-exemption 0 '[OK] filename hygiene: 0 case/space violations|== summary: CLEAN'
run_case fail-broken-link 1 '[FAIL] links|BROKEN:'
run_case fail-index-drift 1 '[FAIL] index drift|INDEX-DRIFT:'
run_case fail-invalid-status 1 '[FAIL] naming convention|invalid status/date'
run_case fail-uppercase-or-space 1 '[FAIL] filename hygiene|CASE:'
run_case warn-orphan 0 '[WARN] orphan check|ORPHAN:'
run_case warn-h1-drift 0 '[WARN] H1 drift|H1-DRIFT:'

# Flag-driven local-contract discovery: same fixture flagged vs. bare.
run_case fail-undeclared-custom-bundle 1 'CASE:'
run_case fail-undeclared-custom-bundle 0 'CLEAN' --bundle-glob '*/legal/*'
run_case fail-custom-type-vocab 1 'recognized status without approved type'
run_case fail-custom-type-vocab 0 'CLEAN' --types rfc

# H1-drift precision: full topic phrase, not just the first slug token.
run_case warn-multiword-h1-drift 0 'H1-DRIFT'
run_case clean-multiword-h1 0 '[OK] H1 drift'

if [ "$failures" -eq 0 ]; then
  printf '== doc-standardization tests: PASS ==\n'
  exit 0
fi

printf '== doc-standardization tests: FAIL (%d) ==\n' "$failures"
exit 1
