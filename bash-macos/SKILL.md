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
warn() { echo "WARN: $*" >&2; }
```

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
| `check_` | Verify conditions | `check_accessibility.py` |
| `toggle_` | Switch state on/off | `toggle_crash_dialogs.sh` |

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
