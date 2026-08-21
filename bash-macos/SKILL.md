---
name: bash-macos
description: >-
  Keeps shell scripts portable across macOS (Bash 3.2, BSD userland) and Linux
  (Bash 4+, GNU coreutils). Use when writing or editing .sh files, debugging
  "command not found", "invalid option", "mapfile: command not found",
  "declare: -A: invalid option", or "sed: illegal option -- r" errors,
  fixing GNU-vs-BSD sed/grep/date/stat/readlink/base64 issues, or renaming shell scripts
  (snake_case verb-first).
---

# Bash macOS Compatibility

Write shell scripts that execute reliably on stock macOS (`/bin/bash` 3.2.x, BSD userland) and Linux (`/bin/bash` 4+, GNU coreutils) without runtime dependencies.

## References

| Open when you need to... | Read |
|--------------------------|------|
| replace Bash 4+ features (associative arrays, case conversion, globstar, `\|&`) with portable equivalents | [references/forbidden-features.md](references/forbidden-features.md) |
| scaffold a new script with arg parsing, safe temp cleanup, and dry-run execution | [references/template.md](references/template.md) |
| implement 3-mode (`compact`, `--verbose`, `--raw`) output for multi-stage automation | [references/output-modes.md](references/output-modes.md) |
| choose script names, verb prefixes, directory layout, or avoid builtin collisions | [references/naming.md](references/naming.md) |

## Shell Target & Strict Mode

macOS ships Bash 3.2.57 at `/bin/bash` (GPLv2 freeze). Do not confuse targets:
- `/bin/bash` (Bash 3.2.x): Skill target. Supports `[[ ... ]]`, indexed arrays, `local`, and process substitution `<(...)`.
- `/bin/sh` (POSIX): Does **not** support `[[`, arrays, or `local`.
- `/bin/zsh` (macOS login shell): 1-based array indexing, different glob rules.

Header template for all `.sh` scripts:

```bash
#!/bin/bash
set -euo pipefail

if [[ -z "${BASH_VERSINFO:-}" ]] || [[ "${BASH_VERSINFO[0]}" -lt 3 ]]; then
  echo "ERROR: Requires bash 3.2+" >&2
  exit 2
fi
```

## BSD vs GNU Userland

macOS provides BSD userland utilities, not GNU coreutils:

| GNU Tool / Flag | BSD Equivalent | Notes |
|---|---|---|
| `sed -r` | `sed -E` | Extended regex |
| `sed -i` | Atomic temp file + `mv` | BSD `sed -i ''` requires empty backup arg; GNU `sed -i` takes no backup arg. Prefer temp file + `mv`. |
| `grep -P` | `grep -E` | BSD `grep` lacks PCRE; use POSIX ERE |
| `date -d '7 days ago'` | `date -v-7d` | Date math differs; use epoch math or `-v` branching |
| `stat -c %s` | `stat -f %z` | File size: GNU uses `-c %s`, BSD uses `-f %z` |
| `base64 -w 0` | `base64 \| tr -d '\n'` | BSD `base64` wraps at 76 columns by default |
| `head -n -1` | `sed '$d'` | Negative line count fails on BSD (`illegal line count`) |
| `find . -name ...` | `find . -name ...` | BSD `find` strictly requires paths before flags |
| `readlink -f` | `/bin/realpath` or helper | Ships on macOS 13+; use `realpath_portable()` for older OS |
| `xargs -r` | Omit `-r` | BSD `xargs` skips empty input by default |

### Portable `sed` In-Place Editing

Avoid `sed -i` divergences by writing to a temporary file and moving into place:

```bash
sed -E 's/pattern/replacement/g' "$file" > "$TMP_DIR/out" && mv "$TMP_DIR/out" "$file"
```

### Portable Date Arithmetic

```bash
if date -v-7d +%s >/dev/null 2>&1; then
  seven_days_ago=$(date -v-7d +%s)            # macOS / BSD
else
  seven_days_ago=$(date -d '7 days ago' +%s)  # Linux / GNU
fi
```

### Zero-Dependency Realpath

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

## Essential Script Patterns

### Array Mechanics (Bash 3.2)

Indexed arrays are fully supported; associative arrays (`declare -A`) are **not**.

```bash
# Declaration and append
arr=()
arr+=("item 1" "item 2")

# Expansion under strict mode (set -u)
# Outer ${arr[@]+...} is intentionally unquoted to avoid emitting an empty string on unset arrays
for item in ${arr[@]+"${arr[@]}"}; do
  printf 'Item: %s\n' "$item"
done

# Associative array replacement: use case statement lookup
get_mime_type() {
  case "$1" in
    html|htm) echo "text/html" ;;
    json)     echo "application/json" ;;
    *)        echo "application/octet-stream" ;;
  esac
}
```

### Local Variable Assignment Split

`local` returns 0, masking failures in command substitutions under `set -e`:

```bash
# WRONG: failure in failing_cmd is swallowed
local result="$(failing_cmd)"

# CORRECT: separate declaration from assignment
local result
result="$(failing_cmd)"
```

Apply the same separation to `declare`, `export`, and `readonly`.

### Intentional Non-Zero Commands & Traps

1. **Scanners and Grep under `set -e`**:
   `grep` returning 1 (no match) is normal control flow, not an error:
   ```bash
   hits=$(grep -nE "$pattern" "$file" || true)
   [[ -n "$hits" ]] || return 0
   ```
2. **Subshell Trap Propagation**:
   Bash 3.2 does not inherit `ERR` traps into functions by default. Add `-E`:
   ```bash
   set -Eeuo pipefail
   trap 'echo "FAILED at line $LINENO" >&2' ERR
   ```
3. **SIGPIPE with `pipefail`**:
   `cmd | head -n1` fails under `pipefail` with exit 141. Drain stdout:
   ```bash
   producer | { head -n1; cat >/dev/null; }
   ```

### Safe Temp Directory & Cleanup

```bash
TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/$(basename "$0" .sh).XXXXXX")"
cleanup() { rm -rf "$TMP_DIR"; }
trap cleanup EXIT INT TERM
```

### Dry-Run Wrapper & Quoting

Gate state-changing operations through a centralized `run_cmd` function:

```bash
DRY_RUN="${DRY_RUN:-0}"
run_cmd() {
  if [[ "$DRY_RUN" == "1" ]]; then
    printf 'DRY-RUN: %s\n' "$*"
  else
    "$@"
  fi
}

# Quoting rules:
# - Double-quote all variable expansions: "$var", "${arr[@]}"
# - Use printf '%b\n' for ANSI colors, not unportable echo -e
```

## Script Naming Conventions

Use **lowercase snake_case**, **verb-first**, maximum 4 words (`run_tests.sh`, `validate_config.py`, `build_image.sh`). Never name scripts after shell builtins (`test`, `exec`, `time`, `kill`, `wait`).

See [references/naming.md](references/naming.md) for verb tables, prefixes, and extension rules.

## Token-Efficient Output

Scripts running multi-stage tasks (linters, builds, tests) must provide 3 output modes: `compact` (default), `--verbose`, and `--raw`. See [references/output-modes.md](references/output-modes.md) for `capture_run` and stage dispatch patterns.

## Verification Checklist

Before completing any shell script:

1. **Syntax Parse**: `bash -n <script.sh>` passes without errors.
2. **Static Analysis**: `shellcheck -s bash <script.sh>` passes.
3. **Portability Scan**: `python3 scripts/validate_portability.py <script.sh>` detects zero Bash 4+ or BSD/GNU violations.
4. **macOS Execution**: `/bin/bash <script.sh> --help` and `--dry-run` run successfully.
