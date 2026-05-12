# Token-Efficient Output

Scripts that produce verbose subprocess output (builds, linters, test runners,
coverage reporters) must offer three output modes so AI agents see only what
they need, while full logs remain available on disk.

| Mode | Flag | Behavior |
|------|------|----------|
| compact | *(default)* | One-line-per-stage success summary; top 10 lines on failure |
| verbose | `--verbose` | Top 50 lines of failing stages |
| raw | `--raw` | Full unfiltered passthrough, teed to log file |

## Standard Log Location

```bash
ARTIFACT_DIR="${ROOT_DIR}/.artifacts/<tool-name>"
LOG_FILE="${ARTIFACT_DIR}/latest.log"
mkdir -p "${ARTIFACT_DIR}"
: > "${LOG_FILE}"
```

## Core Helpers

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

## Output Mode Dispatch

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

## Raw Mode Passthrough

When raw mode is active, bypass capture and tee directly to the log file:

```bash
if [[ "${OUTPUT_MODE}" == "raw" ]]; then
    set -e
    echo "Running <stage>..."
    <command> 2>&1 | tee -a "${LOG_FILE}"
    exit 0
fi
```

## Per-Stage Functions

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

## Control Flow Between Stages

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
