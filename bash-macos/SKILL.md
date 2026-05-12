---
name: bash-macos
author: eworthing
description: >-
  Prevents GNU and Bash 4 assumptions in repository shell scripts and keeps scripts
  compatible with macOS Bash 3.2 and BSD tools. Also applies naming conventions
  (lowercase snake_case, verb-first). Use when creating or editing .sh files,
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

Use when:

- Writing or editing any `*.sh` file
- Proposing shell commands for macOS dev machines
- Debugging "command not found" or "invalid option" errors in scripts

See also:

- [references/output-modes.md](references/output-modes.md) — three-mode compact/verbose/raw output helpers
- [references/naming.md](references/naming.md) — full naming verb table and checklist

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

Pure-bash, no external interpreter (macOS 12.3+ does not ship `python3` by
default). Resolves to an absolute path; does not follow symlinks beyond the
final component — sufficient for most script-local path resolution:

```bash
realpath_portable() {
  local target="$1"
  if [[ -d "$target" ]]; then
    (cd "$target" && pwd -P)
  else
    local dir
    dir="$(cd "$(dirname "$target")" && pwd -P)"
    printf '%s/%s\n' "$dir" "$(basename "$target")"
  fi
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

Use ANSI color codes for scannable success/warning/failure output. Use
`printf` rather than `echo -e` — `echo -e` is not POSIX and some shells
(including `/bin/sh` on macOS when not run as bash) print `-e` literally:

```bash
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m'

info() { printf '%b\n' "${GREEN}✓${NC} $1"; }
warn() { printf '%b\n' "${YELLOW}⚠${NC} $1"; }
fail() { printf '%b\n' "${RED}✗${NC} $1"; }
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

Scripts producing verbose subprocess output (builds, linters, test runners,
coverage) must offer three modes:

| Mode | Flag | Behavior |
|------|------|----------|
| compact | *(default)* | One-line-per-stage summary; top 10 lines on failure |
| verbose | `--verbose` | Top 50 lines of failing stages |
| raw | `--raw` | Full passthrough, teed to log file |

Logs go to `${ROOT_DIR}/.artifacts/<tool-name>/latest.log`.

See [references/output-modes.md](references/output-modes.md) for the full
helper set (`capture_run`, `show_failure_detail`, per-stage functions, mode
dispatch, control flow).

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

Use **lowercase snake_case**, **verb-first**, max 4 words. Never collide with
shell builtins (`test`, `exec`, `time`, `kill`, `wait`).

Examples: `run_tests.sh`, `validate_config.py`, `build_image.sh`,
`sync_logs.sh` — never `SyncLogs.sh` or `sync-logs.sh`.

Extensions: include `.sh`/`.py` for project-local scripts; omit for
PATH-installed tools; none for git hooks (Git convention: `pre-commit`).

See [references/naming.md](references/naming.md) for the full verb table,
prefix vs subdirectory guidance, and naming checklist.
