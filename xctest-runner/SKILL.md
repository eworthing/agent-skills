---
name: xctest-runner
author: eworthing
description: >-
  Runs targeted XCTest subsets with .xctestrun and xcodebuild test-without-building.
  Relevant when executing a single test or suite slice, diagnosing Executed 0 tests,
  or reproducing CI-only XCTest failures with selective execution.
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
---

# XCTest Selection + .xctestrun

## Purpose

Run *only the tests you care about* while keeping selection, destinations, temp files, and exit
codes correct. This skill covers the conceptual model and guardrails for selective iOS test execution.

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
