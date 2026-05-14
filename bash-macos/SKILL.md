---
name: bash-macos
author: eworthing
description: >-
  Keeps shell scripts portable across macOS (Bash 3.2, BSD userland) and Linux
  (Bash 4+, GNU coreutils). Use when writing or editing .sh files, debugging
  "command not found", "invalid option", or "mapfile: command not found" errors,
  fixing GNU-vs-BSD sed/grep/date/readlink issues, or renaming shell scripts
  (snake_case verb-first).
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

## References

- [references/forbidden-features.md](references/forbidden-features.md) — full Bash 4+ feature matrix + workarounds
- [references/template.md](references/template.md) — minimal portable script template + shellcheck guide
- [references/output-modes.md](references/output-modes.md) — three-mode compact/verbose/raw output helpers
- [references/naming.md](references/naming.md) — full naming verb table and checklist

## Shell Target

Target `/bin/bash` 3.2 explicitly. Note the macOS shell landscape:

- `/bin/bash` — Bash 3.2.x (frozen since GPLv3). Skill target. See
  [Supported on Bash 3.2](#supported-on-bash-32) for the explicit allow-list
  of features that DO work here.
- `/bin/sh` — separate binary; runs in POSIX mode. Does **not** honor `[[`,
  `((`, arrays, or `local`. If your shebang is `#!/bin/sh`, none of the
  bashisms in this skill apply.
- `/bin/zsh` — default *user* login shell since Catalina (2019). Scripts with
  `#!/bin/bash` still run under bash, not zsh. zsh has different array indexing
  (1-based), different glob behavior, and no `set -o pipefail` by default.

Shebang + version guard:

```bash
#!/bin/bash
set -euo pipefail

if [[ -z "${BASH_VERSINFO:-}" ]] || [[ "${BASH_VERSINFO[0]}" -lt 3 ]]; then
  echo "ERROR: Requires bash (macOS ships bash 3.2)" >&2
  exit 2
fi
```

## Forbidden Features (Bash 4+ only)

Bash 4+ features that don't exist on macOS's `/bin/bash`:

- `declare -A` (associative arrays)
- `mapfile` / `readarray`
- `${var,,}` / `${var^^}` case conversion
- `shopt -s globstar` (`**`)
- `coproc`, `wait -n`, `local -n`

See [references/forbidden-features.md](references/forbidden-features.md) for
the full matrix with workarounds for each.

## Supported on Bash 3.2

These DO work — no need to drop to POSIX `sh`:

- `[[ ... ]]`, `(( ... ))`, indexed arrays (`${arr[@]}`, `${#arr[@]}`)
- `local` in functions; `printf -v` assignment
- Process substitution `<(...)` / `>(...)`, herestrings `<<<`, `read -a`
- `=~` regex (POSIX ERE; captures in `BASH_REMATCH`; engine differs BSD vs GNU)
- `set -o pipefail`, `trap ... ERR` (with `set -E` for in-function propagation)
- ANSI-C quoting `$'...'`

Drop to `/bin/sh` only when the shebang demands it.

## BSD vs GNU Userland

macOS uses BSD tools, not GNU. Common incompatibilities:

| GNU Flag | BSD Equivalent | Notes |
|----------|----------------|-------|
| `sed -r` | `sed -E` | Extended regex |
| `sed -i` | `sed -i ''` | **In-place differs.** BSD `sed` requires a backup suffix arg (use `''` for none). GNU `sed` uses `-i` or `-i''` (no space). |
| `grep -P` | `grep -E` | No PCRE; use extended regex |
| `date -d` | `date -j -f` | Date parsing differs completely |
| `readlink -f` | See below | Works on recent macOS; use `realpath_portable()` fallback if targeting older macOS |
| `xargs -r` | Largely unneeded | BSD `xargs` already skips empty stdin; `-r` is accepted on modern macOS (tested 13+) but mostly cosmetic. For unknown versions, guard the pipeline: `[[ -n "$(cmd)" ]] && cmd \| xargs ...` |
| `stat -c` | `stat -f` | Different format syntax |

### Avoid `sed -i` for portability

Prefer writing to a temp file and moving it into place (works on BSD and GNU `sed`):

```bash
sed -E 's/pattern/replacement/g' "$file" > "$TMP_DIR/out" && mv "$TMP_DIR/out" "$file"
```

### Portable date arithmetic

BSD `date` has no `-d`. Use `-v±Nu` (BSD) or branch:

```bash
seven_days_ago=$(date -v-7d +%s)              # BSD / macOS
seven_days_ago=$(date -d '7 days ago' +%s)    # GNU / Linux — NOT macOS

# Portable both ways:
if date -v-7d +%s >/dev/null 2>&1; then
  seven_days_ago=$(date -v-7d +%s)
else
  seven_days_ago=$(date -d '7 days ago' +%s)
fi
```

### Portable realpath (no `readlink -f`)

Pure-bash, no external interpreter (macOS no longer ships a working
`python3` at `/usr/bin/python3` by default — it's a CLT stub that prompts
to install Xcode CLT, so scripts can't rely on it). Resolves to an
absolute path; does not follow symlinks beyond the final component —
sufficient for most script-local path resolution:

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

### Command existence check

```bash
have() { command -v "$1" >/dev/null 2>&1; }

if have jq; then
  # use jq
else
  # fallback
fi
```

## Required Patterns

### Error handling

```bash
die() { echo "ERROR: $*" >&2; exit 1; }
```

**`set -E` for ERR trap in functions.** Bash 3.2's `ERR` trap does not
propagate into shell functions, subshells, or command substitutions by default.
If you want a `trap '...' ERR` handler to fire from inside functions, set
`-E` (alias `set -o errtrace`):

```bash
set -Eeuo pipefail
trap 'echo "FAILED at line $LINENO" >&2' ERR
```

Without `-E`, the trap silently never fires from helper functions and you lose
the failure signal.

### `local` + command substitution

`local` returns 0, hiding the inner command's exit status from `set -e`:

```bash
# WRONG - failing_cmd's failure swallowed by local's exit 0
local x="$(failing_cmd)"

# CORRECT - separate declaration from assignment
local x
x="$(failing_cmd)"
```

Same trap with `declare`, `readonly`, `export`.

### `pipefail` + SIGPIPE

Under `set -o pipefail`, `producer | head -n1` exits non-zero: `head` closes
the pipe and `producer` dies of `SIGPIPE` (exit 141).

```bash
producer | head -n1                                # fires under set -eo pipefail

# Mitigation A (preferred) — drain so producer finishes naturally:
producer | { head -n1; cat >/dev/null; }

# Mitigation B — swallow producer's exit; also hides real failures, not
# just SIGPIPE:
{ producer || true; } | head -n1
```

`awk 'NR==1 {print; exit}'` is **not** a fix — `exit` closes the pipe the
same way `head` does.

### Argument validation

Fail fast on missing required input. Use `${VAR:-}` form under `set -u` —
bare `$VAR` triggers "unbound variable" before the test runs:

```bash
[[ -z "${PROJECT_ROOT:-}" ]] && die "PROJECT_ROOT env var required"
[[ $# -lt 1 ]] && { usage; die "missing <target> argument"; }
[[ -f "$1" ]] || die "not a file: $1"
```

### Dry-run pattern

Gate destructive operations behind a single `run_cmd` helper driven by
`DRY_RUN="${DRY_RUN:-0}"` — easier to audit than scattering `if [[ $DRY_RUN ]]`
everywhere. See [references/template.md](references/template.md) for the
helper.

### Color output helpers

Use `printf '%b\n'` for ANSI-colored status output, not `echo -e` (`echo -e`
is not POSIX and `/bin/sh` on macOS prints `-e` literally):

```bash
GREEN='\033[0;32m'; YELLOW='\033[0;33m'; RED='\033[0;31m'; NC='\033[0m'
info() { printf '%b\n' "${GREEN}✓${NC} $1"; }
warn() { printf '%b\n' "${YELLOW}⚠${NC} $1"; }
fail() { printf '%b\n' "${RED}✗${NC} $1"; }
```

### Safe temp directory

```bash
TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/project.XXXXXX")"
cleanup() { rm -rf "$TMP_DIR"; }
trap cleanup EXIT INT TERM
```

### Quoting rules

- **Always** quote variables: `"$var"`, `"${arr[@]}"`
- **Never** parse `ls` output
- Use `printf '%s\n'` instead of `echo -e`

## Verification Checklist

Before marking a script complete:

- [ ] `#!/bin/bash` + `set -euo pipefail` (add `-E` if using `trap ERR`)
- [ ] No Bash 4+ features ([forbidden-features.md](references/forbidden-features.md))
- [ ] `sed -E` not `sed -r`; `grep -E` not `grep -P`
- [ ] BSD `date` uses `-v` or `-j -f`, not `-d`
- [ ] All variables quoted; never parses `ls`
- [ ] `bash -n script.sh` + `shellcheck -s bash script.sh` pass
- [ ] Runs on macOS: `/bin/bash script.sh --help`
- [ ] Name is snake_case verb-first (e.g. `run_tests.sh`)
- [ ] Destructive ops gated behind `DRY_RUN` or confirmation
- [ ] Verbose subprocess output uses 3-mode compact/verbose/raw pattern

## Token-Efficient Output

Scripts producing verbose subprocess output (builds, linters, tests, coverage)
must offer three modes: `compact` (default; one-line-per-stage + top 10 lines
on failure), `--verbose` (top 50 lines), `--raw` (passthrough teed to
`${ROOT_DIR}/.artifacts/<tool>/latest.log`).

See [references/output-modes.md](references/output-modes.md) for `capture_run`,
`show_failure_detail`, per-stage functions, and mode dispatch.

## Common Gotcha: Arrays in Conditionals

On Bash 3.2 with `set -u`, an array that was never declared triggers
"unbound variable" when expanded — even inside the `${#...}` length
operator. The `:-` default does **not** apply inside `${#...}`; the
unbound check fires first.

```bash
# WRONG - ${#name:-default} does not work; the :- never applies inside ${#...}
if [[ ${#arr[@]:-0} -gt 0 ]]; then ...   # still errors if arr never declared

# CORRECT - declare the array empty before use
arr=()
if [[ ${#arr[@]} -gt 0 ]]; then ...

# CORRECT - guard the expansion when the array may be unset
for x in ${arr[@]+"${arr[@]}"}; do ...
```

**Note on the `${arr[@]+"${arr[@]}"}` idiom:** the outer `${arr[@]+...}`
is deliberately left unquoted — the one documented exception to the
"always quote variables" rule above. Quoting the whole expression
(`"${arr[@]+\"${arr[@]}\"}"`) would expand to a single empty string when
the array is unset, defeating the guard. The **inner** `"${arr[@]}"`
stays quoted to preserve element boundaries.

## Script Naming Conventions

Use **lowercase snake_case**, **verb-first**, max 4 words. Never collide with
shell builtins (`test`, `exec`, `time`, `kill`, `wait`).

Examples: `run_tests.sh`, `validate_config.py`, `build_image.sh`,
`sync_logs.sh` — never `SyncLogs.sh` or `sync-logs.sh`.

Extensions: include `.sh`/`.py` for project-local scripts; omit for
PATH-installed tools; none for git hooks (Git convention: `pre-commit`).

See [references/naming.md](references/naming.md) for the full verb table,
prefix vs subdirectory guidance, and naming checklist.
