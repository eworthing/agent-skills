# Minimal Script Template

Starter scaffold for a new portable shell script. Drop into `scripts/<verb>_<noun>.sh`,
make executable (`chmod +x`), and replace the marked sections.

## Template

```bash
#!/bin/bash
set -euo pipefail

# Ensure we're running under bash (script logic must remain compatible with bash 3.2)
if [[ -z "${BASH_VERSINFO:-}" ]] || [[ "${BASH_VERSINFO[0]}" -lt 3 ]]; then
  echo "ERROR: Requires bash (macOS ships bash 3.2)" >&2
  exit 2
fi

# --- Helpers ---
have() { command -v "$1" >/dev/null 2>&1; }
die()  { echo "ERROR: $*" >&2; exit 1; }

# --- Usage ---
usage() {
  cat <<EOF
Usage: $(basename "$0") [options]

Options:
  -h, --help     Show help
  --dry-run      Print actions without executing
  --verbose      Verbose output
EOF
}

# --- Long-option mapping ---
DRY_RUN="${DRY_RUN:-0}"
args=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --help)    args+=("-h") ;;
    --dry-run) DRY_RUN=1 ;;
    --verbose) VERBOSE=1 ;;
    --)        shift; break ;;
    *)         args+=("$1") ;;
  esac
  shift
done
set -- "${args[@]}" "$@"

case "${1:-}" in
  -h|--help) usage; exit 0 ;;
esac

# --- Required env / args ---
# [[ -z "${PROJECT_ROOT:-}" ]] && die "PROJECT_ROOT required"

# --- Temp dir + cleanup ---
TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/$(basename "$0" .sh).XXXXXX")"
cleanup() { rm -rf "$TMP_DIR"; }
trap cleanup EXIT INT TERM

# --- Script logic ---
# Replace this with the actual work.
```

## Quick Syntax Check

```bash
# Parses without executing
bash -n script.sh

# Trace execution
bash -x script.sh

# Shellcheck (if available) — catches many compatibility issues
if command -v shellcheck >/dev/null 2>&1; then
  shellcheck -s bash script.sh
fi
```

## Shellcheck

[Shellcheck](https://www.shellcheck.net/) is highly recommended.

```bash
brew install shellcheck
shellcheck scripts/*.sh
```

Key codes for portability:

- **SC2039** — non-POSIX feature (catches Bash 4+ issues)
- **SC2086** — double quote to prevent globbing/splitting
- **SC2034** — variable appears unused (catches typos)
- **SC3043** — `local` used in non-bash shell (only relevant if shebang is `/bin/sh`)

Run shellcheck in CI; it catches most BSD/GNU divergences automatically.

## Dry-Run Pattern

For destructive operations (file moves, deletions, network writes), gate them
behind `DRY_RUN`:

```bash
run_cmd() {
  if [[ "$DRY_RUN" == "1" ]]; then
    printf 'DRY-RUN: %s\n' "$*"
  else
    "$@"
  fi
}

run_cmd rm -rf "$stale_dir"
run_cmd mv "$tmp" "$dest"
```

`run_cmd` is one function the rest of the script calls — easier to audit than
scattering `if [[ $DRY_RUN ]]` checks everywhere.
