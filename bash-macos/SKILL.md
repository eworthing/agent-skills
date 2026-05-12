---
name: bash-macos
author: eworthing
description: >-
  Prevents GNU and Bash 4 assumptions in repository shell scripts and keeps scripts
  compatible with macOS Bash 3.2 and BSD tools. Also applies naming conventions
  (lowercase snake_case, verb-first). Relevant when creating or editing .sh files,
  creating or renaming shell or Python scripts in scripts/ or the repo root,
  debugging script failures on macOS, or dealing with sed, readlink, mapfile,
  or shell portability issues.
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - Glob
---

# Bash macOS Compatibility

## Purpose

Ensure shell scripts run on macOS's stock `/bin/bash` (3.2.x) and BSD userland.
macOS does NOT ship Bash 4+ or GNU coreutils by default.

## When to Use

- Writing or editing any `*.sh` file
- Proposing shell commands for macOS dev machines
- Debugging "command not found" or "invalid option" errors in scripts

## Bash Version Target

Target Bash 3.2 (macOS default). Use this shebang and guard:

```bash
#!/bin/bash
set -euo pipefail

# Ensure we're running under bash (script logic must remain compatible with bash 3.2)
if [[ -z "${BASH_VERSINFO:-}" ]] || [[ "${BASH_VERSINFO[0]}" -lt 3 ]]; then
  echo "ERROR: Requires bash (macOS ships bash 3.2)" >&2
  exit 2
fi
```

## Forbidden Features (Bash 4+ only)

| Feature | Bash Version | Workaround |
|---------|--------------|------------|
| `declare -A` (associative arrays) | 4.0+ | Use indexed arrays or functions |
| `mapfile` / `readarray` | 4.0+ | Use `while read` loop |
| `${var,,}` lowercase | 4.0+ | Use `tr '[:upper:]' '[:lower:]'` |
| `${var^^}` uppercase | 4.0+ | Use `tr '[:lower:]' '[:upper:]'` |
| `shopt -s globstar` (`**`) | 4.0+ | Use `find` instead |
| `coproc` | 4.0+ | Use named pipes |
| `wait -n` | 4.3+ | Use `wait` without `-n` |

### Associative Array Workaround

```bash
# WRONG - Bash 4+ only
declare -A colors
colors["red"]="#FF0000"
echo "${colors[$key]}"

# CORRECT - Use functions or case statements
get_color() {
  case "$1" in
    red)   echo "#FF0000" ;;
    blue)  echo "#0000FF" ;;
    *)     echo "#000000" ;;
  esac
}
color=$(get_color "red")
```

### mapfile Workaround

```bash
# WRONG - Bash 4+ only
mapfile -t lines < "$file"

# CORRECT - Works on Bash 3.2
lines=()
while IFS= read -r line; do
  lines+=("$line")
done < "$file"
```

## BSD vs GNU Userland

macOS uses BSD tools, not GNU. Common incompatibilities:

| GNU Flag | BSD Equivalent | Notes |
|----------|----------------|-------|
| `sed -r` | `sed -E` | Extended regex |
| `sed -i` | `sed -i ''` | **In-place differs.** BSD `sed` requires a backup suffix arg (use `''` for none). GNU `sed` uses `-i` or `-i''` (no space). |
| `grep -P` | `grep -E` | No PCRE; use extended regex |
| `date -d` | `date -j -f` | Date parsing differs completely |
| `readlink -f` | See below | Works on recent macOS; use `realpath_portable()` fallback if targeting older macOS |
| `xargs -r` | Restructure | Accepted on recent macOS; restructure if targeting older macOS |
| `stat -c` | `stat -f` | Different format syntax |

### Avoid `sed -i` for portability

Prefer writing to a temp file and moving it into place (works on BSD and GNU `sed`):

```bash
sed -E 's/pattern/replacement/g' "$file" > "$TMP_DIR/out" && mv "$TMP_DIR/out" "$file"
```

### Portable realpath (no `readlink -f`)

```bash
realpath_portable() {
  python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$1"
}
```

### Command Existence Check

```bash
have() { command -v "$1" >/dev/null 2>&1; }

if have jq; then
  # use jq
else
  # fallback
fi
```

## Required Patterns

### Long options

Bash `getopts` only supports short options; accept `--help` (and friends) by mapping long options to short ones before parsing.

```bash
args=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --help) args+=("-h") ;;
    --) shift; break ;;
    *) args+=("$1") ;;
  esac
  shift
done
set -- "${args[@]}" "$@"
```

### Error Handling

```bash
die() { echo "ERROR: $*" >&2; exit 1; }
```

### Color Output Helpers

Use ANSI color codes for scannable success/warning/failure output:

```bash
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m'  # No Color

info() { echo -e "${GREEN}✓${NC} $1"; }
warn() { echo -e "${YELLOW}⚠${NC} $1"; }
fail() { echo -e "${RED}✗${NC} $1"; }
```

Prefer `info`/`fail` over raw `echo` for user-facing status messages. Use `warn` for non-fatal issues.

### Safe Temp Directory

```bash
TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/project.XXXXXX")"
cleanup() { rm -rf "$TMP_DIR"; }
trap cleanup EXIT INT TERM
```

### Quoting Rules

- **Always** quote variables: `"$var"`, `"${arr[@]}"`
- **Never** parse `ls` output
- Use `printf '%s\n'` instead of `echo -e`

## Minimal Script Template

```bash
#!/bin/bash
set -euo pipefail

# Ensure we're running under bash (script logic must remain compatible with bash 3.2)
if [[ -z "${BASH_VERSINFO:-}" ]] || [[ "${BASH_VERSINFO[0]}" -lt 3 ]]; then
  echo "ERROR: Requires bash (macOS ships bash 3.2)" >&2
  exit 2
fi

have() { command -v "$1" >/dev/null 2>&1; }
die() { echo "ERROR: $*" >&2; exit 1; }

usage() {
  cat <<EOF
Usage: $(basename "$0") [options]

Options:
  -h, --help   Show help
EOF
}

case "${1:-}" in
  -h|--help) usage; exit 0 ;;
esac

# Script logic here
```

## Verification Checklist

Before marking a script complete:

- [ ] Shebang is `#!/bin/bash` or `#!/bin/sh`
- [ ] No `declare -A` (associative arrays)
- [ ] No `mapfile` or `readarray`
- [ ] No `${var,,}` or `${var^^}` case conversion
- [ ] Uses `sed -E` not `sed -r`
- [ ] Uses `grep -E` not `grep -P`
- [ ] All variables quoted
- [ ] Syntax check passes: `bash -n script.sh`
- [ ] Shellcheck passes (if available): `shellcheck -s bash script.sh`
- [ ] Runs on macOS: `/bin/bash script.sh --help`
- [ ] Name follows snake_case verb-first (e.g. `run_tests.sh`)
- [ ] If script produces verbose subprocess output, uses three-mode compact/verbose/raw output with `capture_run` and `.artifacts/<tool>/latest.log`

## Quick Syntax Check

```bash
# Verify script parses without errors
bash -n script.sh

# Run with verbose debugging
bash -x script.sh

# Shellcheck (if available) - catches many compatibility issues
if have shellcheck; then
  shellcheck -s bash script.sh
fi
```

### Shellcheck Integration

[Shellcheck](https://www.shellcheck.net/) is highly recommended. Install via:

```bash
brew install shellcheck
```

Run on all project scripts:

```bash
shellcheck scripts/*.sh
```

Key shellcheck codes for compatibility:
- **SC2039**: Uses non-POSIX features (catches Bash 4+ issues)
- **SC2086**: Double quote to prevent globbing/splitting
- **SC2034**: Variable appears unused (helps find typos)

## Token-Efficient Output

Scripts that produce verbose subprocess output (builds, linters, test runners,
coverage reporters) must offer three output modes so AI agents see only what
they need, while full logs remain available on disk.

| Mode | Flag | Behavior |
|------|------|----------|
| compact | *(default)* | One-line-per-stage success summary; top 10 lines on failure |
| verbose | `--verbose` | Top 50 lines of failing stages |
| raw | `--raw` | Full unfiltered passthrough, teed to log file |

### Standard Log Location

```bash
ARTIFACT_DIR="${ROOT_DIR}/.artifacts/<tool-name>"
LOG_FILE="${ARTIFACT_DIR}/latest.log"
mkdir -p "${ARTIFACT_DIR}"
: > "${LOG_FILE}"
```

### Core Helpers

```bash
STAGE_TMP="$(mktemp)"
TEMP_FILES=()
cleanup() {
    rm -f "${STAGE_TMP}" 2>/dev/null || true
    [[ ${#TEMP_FILES[@]} -gt 0 ]] && rm -f "${TEMP_FILES[@]}" 2>/dev/null || true
}
trap cleanup EXIT

compact_lines() { echo 10; }
verbose_lines() { echo 50; }

strip_ansi() {
    sed $'s/\x1b\[[0-9;]*[a-zA-Z]//g'
}

capture_run() {
    local rc=0
    "$@" > "${STAGE_TMP}" 2>&1 || rc=$?
    cat "${STAGE_TMP}" >> "${LOG_FILE}"
    local clean_tmp
    clean_tmp="$(mktemp)"
    TEMP_FILES+=("${clean_tmp}")
    strip_ansi < "${STAGE_TMP}" > "${clean_tmp}"
    mv "${clean_tmp}" "${STAGE_TMP}"
    return "${rc}"
}

show_top_lines() {
    local max="$1"
    local total
    total="$(wc -l < "${STAGE_TMP}" | tr -d ' ')"
    head -n "${max}" "${STAGE_TMP}" | sed 's/^/- /'
    if [[ "${total}" -gt "${max}" ]]; then
        echo "- ... and $((total - max)) more lines in log"
    fi
}

show_matching_lines() {
    local pattern="$1"
    local max="$2"
    local matches
    matches="$(grep -E "${pattern}" "${STAGE_TMP}" 2>/dev/null || true)"
    if [[ -n "${matches}" ]]; then
        printf '%s\n' "${matches}" | head -n "${max}" | sed 's/^/- /'
        return 0
    fi
    return 1
}

show_failure_detail() {
    show_matching_lines "$1" "$2" || show_top_lines "$2"
}

fail_lines() {
    if [[ "${OUTPUT_MODE}" == "verbose" ]]; then
        verbose_lines
    else
        compact_lines
    fi
}
```

`capture_run` runs the command, saves raw output to the log file, then writes
ANSI-stripped text back to `STAGE_TMP` so stage parsers see clean text.

`show_failure_detail` tries to grep for a diagnostic pattern (e.g. `"error:"`,
`"BUILD FAILED"`) first, then falls back to raw top lines if none match.

### Output Mode Dispatch

Accept `--verbose` and `--raw` flags during argument parsing:

```bash
OUTPUT_MODE="compact"
while [[ $# -gt 0 ]]; do
    case "$1" in
        --verbose) OUTPUT_MODE="verbose"; shift ;;
        --raw)     OUTPUT_MODE="raw";     shift ;;
        # ... other flags
    esac
done
```

### Raw Mode Passthrough

When raw mode is active, bypass capture and tee directly to the log file:

```bash
if [[ "${OUTPUT_MODE}" == "raw" ]]; then
    set -e
    echo "Running <stage>..."
    <command> 2>&1 | tee -a "${LOG_FILE}"
    exit 0
fi
```

### Per-Stage Functions

Each logical stage gets a function with this shape:

```bash
FAILED=false

run_<stage>_stage() {
    local rc=0
    capture_run <command> args || rc=$?
    if [[ "${rc}" -eq 0 ]]; then
        echo "<stage>: ok"
    else
        FAILED=true
        echo "<stage>: FAIL"
        show_top_lines "$(fail_lines)"
    fi
    return "${rc}"
}
```

If the stage has a natural diagnostic pattern, use `show_failure_detail` instead
of `show_top_lines`:

```bash
    echo "<stage>: FAIL"
    show_failure_detail "error:|<pattern>" "$(fail_lines)"
```

### Control Flow Between Stages

When one stage depends on the previous passing, check the status variable:

```bash
run_format_stage || true
run_lint_stage || true

if [[ "${FAILED}" == true ]]; then
    echo "tests: skipped"
    exit 1
fi

run_test_stage || true
```

The `|| true` prevents `set -e` from exiting mid-gate; the `FAILED` variable
carries the semantic signal.

## Common Gotcha: Arrays in Conditionals

```bash
# WRONG - empty array expansion fails with set -u
if [[ ${#arr[@]} -gt 0 ]]; then ...

# CORRECT - guard with default
if [[ ${#arr[@]:-0} -gt 0 ]]; then ...
# Or initialize array before use
arr=()
```

## Script Naming Conventions

Name scripts using **lowercase snake_case** with **verb-first** structure.

### Core Rules

1. **Lowercase + underscores** -- `sync_logs.sh`, never `SyncLogs.sh` or `sync-logs.sh`
2. **Verb-first structure** -- `run_tests.sh`, `validate_config.py`, `build_image.sh`
3. **Max 4 words** -- `run_ui_tests.sh` ok, `run_all_ui_tests_for_platform.sh` too long
4. **Avoid builtins** -- never use `test`, `exec`, `time`, `kill`, `wait`

### Extension Rules

| Context | Extension | Example |
|---------|-----------|---------|
| Project-local scripts | **Include** `.sh`/`.py` | `./scripts/run_ui_tests.sh` |
| PATH-installed tools | **Omit** extension | `/usr/local/bin/deploy_config` |
| Git hooks | **None** (Git convention) | `pre-commit` |

### Common Verbs

| Verb | Purpose | Example |
|------|---------|---------|
| `run_` | Execute tests or processes | `run_ui_tests.sh` |
| `validate_` | Check correctness | `validate_skill.py` |
| `build_` | Compile or construct | `build_visual_audit_report.py` |
| `sync_` | Synchronize resources | `sync_skills.sh` |
| `install_` | Set up components | `install_hooks.sh` |
| `setup_` | Set up dev environment | `setup_dev.sh` |
| `check_` | Verify conditions | `check_accessibility.py` |
| `generate_` | Produce artifacts | `generate_report.sh` |

### Organization: Prefix vs Subdirectory

| Approach | Use When | Example |
|----------|----------|---------|
| **Verb prefix** | Scripts independently invoked | `run_ui_tests.sh`, `run_unit_tests.sh` |
| **Domain prefix** | Need quick tab-completion grouping | `audit_check_a11y.py`, `audit_score_parity.py` |
| **Subdirectory** | 4+ scripts with shared imports | `scripts/visual_audit/*.py` |

### Naming Checklist

- [ ] Lowercase with underscores?
- [ ] Starts with a verb?
- [ ] 4 words or fewer?
- [ ] No collision (`which {name}` returns nothing)?
- [ ] Not a shell builtin (`type {name}` returns nothing)?

## Constraints

- Target Bash 3.2 (macOS default)
- Assume BSD userland (sed, grep, date, stat)
- Never use GNU-only flags without detection/fallback
- Always quote variable expansions
