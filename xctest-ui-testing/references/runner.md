# XCTest Selection + `.xctestrun` Execution

> Reference for the parent `xctest-ui-testing` skill. Folded in 2026-05-13 from the eliminated `xctest-runner` skill.

Run *only the tests you care about* while keeping selection,
destinations, temp files, and exit codes correct. This file covers the
conceptual model and guardrails for selective XCTest execution on iOS,
macOS, and tvOS.

Triggers: single test / class / suite slice, debugging flaky UI tests,
diagnosing "Executed 0 tests", reproducing CI-only XCTest failures with
selective execution, preserving an `.xcresult` for post-mortem inspection,
or building / modifying a wrapper runner script (list / range / glob /
match / class / id selection modes, `-retry-tests-on-failure`,
zero-test guardrails, `PIPESTATUS` exit propagation).

## When to Use This Skill

- You want to run a subset of UI tests ("run only these tests")
- You're debugging flaky UI tests (drag/drop, timing issues)
- You're building or modifying a test runner script
- CI/local runs report "Executed 0 tests" unexpectedly

## Workflow

### Step 1: Understand the .xctestrun Model (Build vs Run Destinations)

The key insight: you can split building and running tests. This enables selective execution:

- **build-for-testing**: uses a **generic** destination (fast, stable)
- **test-without-building**: uses a **real** destination (booted simulator)

```bash
# Build once
xcodebuild build-for-testing \
    -scheme MyApp \
    -destination 'generic/platform=iOS Simulator'

# Run selectively (multiple times if needed)
xcodebuild test-without-building \
    -xctestrun path/to/MyApp.xctestrun \
    -destination 'platform=iOS Simulator,name=iPhone 16'
```

If you change destination logic in a test runner, preserve this invariant:
- Generic destinations are fine for *build-for-testing*
- Generic destinations are not acceptable for *test execution*

### Step 2: Select Tests

Use `-only-testing` to run specific tests:

```bash
# Run a single test class
xcodebuild test-without-building \
    -xctestrun path/to/MyApp.xctestrun \
    -destination 'platform=iOS Simulator,name=iPhone 16' \
    -only-testing 'MyAppUITests/SettingsTests'

# Run a single test method
xcodebuild test-without-building \
    -xctestrun path/to/MyApp.xctestrun \
    -destination 'platform=iOS Simulator,name=iPhone 16' \
    -only-testing 'MyAppUITests/SettingsTests/testDarkModeToggle'
```

### Step 3: Find the Right .xctestrun File

After `build-for-testing`, Xcode places `.xctestrun` files in DerivedData. Select the newest one for your platform:

```bash
# Find the latest .xctestrun for iOS Simulator
XCTESTRUN=$(find ~/Library/Developer/Xcode/DerivedData \
    -name '*.xctestrun' \
    -path '*iphonesimulator*' \
    -newer /tmp/build_start_marker \
    | head -1)
```

### Step 4: Essential Guardrails

When building or modifying test runner scripts, maintain these invariants:

1. **Latest `.xctestrun` selection** — Select by mtime within DerivedData, filtered by platform pattern
2. **Single cleanup trap** — Remove temp files and ephemeral xcresults in one trap handler
3. **Exit code propagation** — When piping through formatters, use `${PIPESTATUS[0]}` (bash) or equivalent
4. **Zero-test detection** — Explicitly treat "Executed 0 tests" as failure. This catches destination mismatches silently passing CI
5. **"No tests matched" fails fast** — When a selection pattern resolves to zero candidates, exit non-zero *before* invoking `xcodebuild`. Silent zero-match is the most common source of "tests passed but nothing ran" CI green
6. **Preserve `.xcresult` on demand** — Keep a `--keep-result` (or equivalent) opt-in so flaky failures can be inspected with `xcrun xcresulttool` after the fact; default to cleanup to avoid DerivedData bloat

```bash
# Zero-test detection example
RESULT_OUTPUT=$(xcodebuild test-without-building ... 2>&1)
if echo "$RESULT_OUTPUT" | grep -q "Executed 0 tests"; then
    echo "ERROR: No tests were executed. Check destination and test selection."
    exit 1
fi
```

### Step 5: iOS Simulator Destinations

```bash
# List available simulators
xcrun simctl list devices available

# Common destination format
-destination 'platform=iOS Simulator,name=iPhone 16'
-destination 'platform=iOS Simulator,name=iPad Pro 13-inch (M4)'
```

### Step 6: Recommended Runner-Script Flag Surface

A useful wrapper around `xcodebuild test-without-building` exposes multiple
selection modes — picking tests by qualified ID is the only thing
`xcodebuild` understands directly, but humans and CI usually want broader
matching. Recommended flag surface:

| Flag | Selects | Example |
|------|---------|---------|
| `--list` | Enumerate without running (sanity check before selecting) | `runner --list` |
| `--range "N-M"` | Sequential subset from the enumerated list | `runner --range "1-10"` |
| `--glob "<pattern>"` | Shell-style glob on test names | `runner --glob "testToolbar*"` |
| `--match "<substring>"` | Substring match across class and method names | `runner --match "DragDrop"` |
| `--class <ClassName>` | Whole-class selection | `runner --class SettingsTests` |
| `--id "<Bundle/Class/method()>"` | Fully qualified single test (passes straight to `-only-testing`) | `runner --id "AppUITests/SettingsTests/testDarkModeToggle()"` |
| `--keep-result` | Skip post-run cleanup of `.xcresult` for flake investigation | `runner --keep-result --id ...` |

Implementation pattern: resolve every flag to one or more
`-only-testing` arguments before invoking `xcodebuild`. Fail fast if the
resolved set is empty.

```bash
# Pseudocode
case "$mode" in
  list)  enumerate_tests ;;
  range) selected=$(enumerate_tests | sed -n "${start},${end}p") ;;
  glob)  selected=$(enumerate_tests | grep -E "$pattern_to_regex") ;;
  match) selected=$(enumerate_tests | grep "$substring") ;;
  class) selected="$bundle/$class" ;;
  id)    selected="$qualified_id" ;;
esac
[ -z "$selected" ] && { echo "ERROR: no tests matched"; exit 1; }
xcodebuild test-without-building -xctestrun "$xctestrun" \
    -destination "$destination" \
    $(printf -- '-only-testing %s ' $selected)
```

## Common Mistakes to Avoid

1. **Picking the wrong `.xctestrun`** — Always select the newest per-platform build output
2. **Destination mismatch** — Building for one destination and executing with another yields 0 tests
3. **Broken cleanup** — Multiple traps or overwritten temp vars leak files or delete the wrong thing
4. **Incorrect exit codes** — Piping through formatters without `PIPESTATUS` hides failures
5. **Allowing "0 tests selected"** — Fail fast and print the enumerated list for debugging

## Examples

### Debug a single flaky UI test

1. Build for testing: `xcodebuild build-for-testing -scheme MyApp -destination 'generic/platform=iOS Simulator'`
2. Run just the failing test with `-only-testing`
3. If flake persists, preserve `.xcresult` and inspect with `xcrun xcresulttool`

### Retry flaky tests

```bash
# Retry failed tests up to 3 times
xcodebuild test-without-building \
    -xctestrun path/to/MyApp.xctestrun \
    -destination 'platform=iOS Simulator,name=iPhone 16' \
    -retry-tests-on-failure \
    -test-iterations 3
```

## Constraints

- UI test runners require macOS with Xcode installed
- Prefer wrapper scripts over raw `xcodebuild` calls in documentation to avoid drift
