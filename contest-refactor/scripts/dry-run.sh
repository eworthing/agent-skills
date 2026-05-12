#!/usr/bin/env bash
# dry-run.sh — preflight for /contest-refactor.
# Walks Step 0 (Context Discovery) on the CWD or given path, reports what the loop WOULD do.
# No code edits. No commits. No build/test invocation. Read-only.
#
# Usage:  ./dry-run.sh [path]
# Output: human-readable preflight to stdout. Non-zero exit = critical preflight problem.

set -u

target="${1:-$PWD}"
exit_code=0

if [ ! -d "$target" ]; then
  echo "ERROR: $target is not a directory" >&2
  exit 2
fi

cd "$target" || exit 2

printf '=== contest-refactor preflight ===\n'
printf 'target: %s\n\n' "$target"

# --- Source roots ---
printf '[source roots]\n'
roots=()
for d in src app lib BenchHypeKit/Sources internal pkg cmd; do
  if [ -d "$d" ]; then
    roots+=("$d")
  fi
done
if [ ${#roots[@]} -eq 0 ]; then
  printf '  (none of the canonical roots found; review will scan repo root)\n'
else
  for r in "${roots[@]}"; do printf '  - %s\n' "$r"; done
fi
printf '\n'

# --- Stack detection (first match wins, mirrors lenses.md) ---
# Look at root + one level deep to catch monorepo/sub-package layouts.
printf '[stack detection]\n'
stack="generic"
lens="references/lens-generic.md"
swift_pkg=$(find . -maxdepth 2 -name 'Package.swift' -type f 2>/dev/null | head -1)
xcode_proj=$(find . -maxdepth 2 -name '*.xcodeproj' -type d 2>/dev/null | head -1)
xcode_ws=$(find . -maxdepth 2 -name '*.xcworkspace' -type d 2>/dev/null | head -1)
if [ -n "$swift_pkg" ] || [ -n "$xcode_proj" ] || [ -n "$xcode_ws" ]; then
  stack="apple"
  lens="references/lens-apple.md"
elif [ -f Cargo.toml ]; then
  stack="rust (generic lens)"
elif [ -f go.mod ]; then
  stack="go (generic lens)"
elif [ -f pyproject.toml ] || [ -f tox.ini ] || [ -f pytest.ini ] || [ -f setup.py ]; then
  stack="python (generic lens)"
elif [ -f package.json ]; then
  stack="node (generic lens)"
elif [ -f build.gradle ] || [ -f pom.xml ]; then
  stack="jvm (generic lens)"
fi
printf '  stack: %s\n  lens:  %s\n' "$stack" "$lens"
[ -n "$swift_pkg" ] && printf '  Package.swift: %s\n' "$swift_pkg"
[ -n "$xcode_proj" ] && printf '  xcodeproj:     %s\n' "$xcode_proj"
printf '\n'

# --- Test/build command discovery ---
printf '[test/build command candidates]\n'
candidates=()
if [ -n "$swift_pkg" ]; then
  pkg_dir=$(dirname "$swift_pkg")
  candidates+=("(cd $pkg_dir && swift test)")
fi
[ -f Cargo.toml ] && candidates+=("cargo test")
[ -f go.mod ] && candidates+=("go test ./...")
[ -f pyproject.toml ] && candidates+=("pytest")
[ -f tox.ini ] && candidates+=("tox")
[ -f package.json ] && candidates+=("npm test  (or yarn test / pnpm test)")
[ -f Makefile ] && candidates+=("make test")
[ -f build.gradle ] && candidates+=("./gradlew test")
[ -f pom.xml ] && candidates+=("mvn test")
[ -x scripts/run_local_gate.sh ] && candidates+=("./scripts/run_local_gate.sh --quick  (project-local; preferred)")
if [ ${#candidates[@]} -eq 0 ]; then
  printf '  WARNING: no test/build config detected. Loop cannot establish ground truth.\n'
  exit_code=1
else
  for c in "${candidates[@]}"; do printf '  - %s\n' "$c"; done
fi
printf '\n'

# --- Validate test command runtime risk ---
printf '[runtime validation]\n'
test_count=0
for ext in swift rs go py ts tsx js mjs java kt scala rb; do
  while IFS= read -r f; do
    test_count=$((test_count + 1))
  done < <(find . -type f -name "*Test*.${ext}" -o -name "*test*.${ext}" -o -name "*_test.${ext}" 2>/dev/null | head -2000)
done
printf '  test-like files: %s\n' "$test_count"
if [ "$test_count" -gt 800 ]; then
  printf '  WARNING: large test corpus (>800 files). Step 0 should refuse full suite as loop oracle; require --quick variant.\n'
  printf '  SUGGESTION: invoke /contest-refactor with --test-filter <pattern> for incremental ground truth.\n'
  printf '              full-suite reverify is required before HALT_SUCCESS (G21).\n'
  exit_code=1
elif [ "$test_count" -gt 200 ]; then
  printf '  NOTE: medium test corpus (>200 files). Loop runtime per iteration may exceed 5 min.\n'
  printf '        consider --test-filter <pattern> for incremental scoping (G21 reverify before HALT_SUCCESS).\n'
fi
printf '\n'

# --- ADR / domain context ---
printf '[domain context]\n'
if [ -f CONTEXT.md ]; then
  printf '  CONTEXT.md: present (%s lines)\n' "$(wc -l < CONTEXT.md | tr -d ' ')"
elif [ -f CONTEXT-MAP.md ]; then
  printf '  CONTEXT-MAP.md: present\n'
else
  printf '  no CONTEXT.md (loop will proceed silently)\n'
fi

if [ -d docs/adr ]; then
  adr_count=$(find docs/adr -maxdepth 2 -name '*.md' -type f 2>/dev/null | wc -l | tr -d ' ')
  printf '  docs/adr/: %s ADR file(s)\n' "$adr_count"
  if [ "$adr_count" -gt 0 ]; then
    find docs/adr -maxdepth 2 -name '*.md' -type f 2>/dev/null | sort | head -10 | sed 's|^|    |'
    [ "$adr_count" -gt 10 ] && printf '    ... and %s more\n' "$((adr_count - 10))"
  fi
else
  printf '  docs/adr/: not present\n'
fi
printf '\n'

# --- Loop cap ---
printf '[loop cap]\n'
cap="${CONTEST_REFACTOR_LOOP_CAP:-10}"
printf '  default: 10  current env: %s\n' "$cap"
if [ -f CURRENT_REVIEW.md ]; then
  directive=$(head -1 CURRENT_REVIEW.md | grep -oE 'loop_cap: *[0-9]+' || true)
  if [ -n "$directive" ]; then
    printf '  override directive in CURRENT_REVIEW.md: %s\n' "$directive"
  fi
fi
printf '\n'

# --- Existing review state ---
printf '[review artifacts]\n'
[ -f CURRENT_REVIEW.md ] && printf '  CURRENT_REVIEW.md: present (will be archived to REVIEW_HISTORY.md and overwritten)\n' \
                        || printf '  CURRENT_REVIEW.md: absent (first loop)\n'
[ -f REVIEW_HISTORY.md ] && printf '  REVIEW_HISTORY.md: present (%s loops archived)\n' \
                          "$(grep -c '^--- Loop ' REVIEW_HISTORY.md 2>/dev/null || echo 0)" \
                        || printf '  REVIEW_HISTORY.md: absent\n'
[ -f CURRENT_REVIEW.json ] && printf '  CURRENT_REVIEW.json: present\n' \
                          || printf '  CURRENT_REVIEW.json: absent\n'
if [ -f LOOP_STATE.json ]; then
  printf '  WARNING: LOOP_STATE.json present — prior /contest-refactor loop interrupted mid-Step-3.\n'
  printf '           Resume by re-invoking /contest-refactor (Resume Detection routes via Precedence Matrix row 5),\n'
  printf '           or pass --reset to discard partial state.\n'
  exit_code=1
fi
printf '\n'

# --- Git sanity ---
printf '[git]\n'
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)
  dirty=$(git status --porcelain 2>/dev/null | wc -l | tr -d ' ')
  printf '  branch: %s\n  dirty paths: %s\n' "$branch" "$dirty"
  if [ "$dirty" -gt 0 ]; then
    printf '  NOTE: working tree has uncommitted changes. Loop commits per-iteration; clean tree recommended before starting.\n'
  fi
else
  printf '  WARNING: not a git repository. Loop cannot commit per-iteration; revert-on-break unavailable.\n'
  exit_code=1
fi
printf '\n'

# --- Summary ---
printf '=== preflight summary ===\n'
if [ "$exit_code" -eq 0 ]; then
  printf 'OK. /contest-refactor can proceed.\n'
else
  printf 'BLOCKED. Resolve warnings above before invoking /contest-refactor.\n'
fi

exit "$exit_code"
