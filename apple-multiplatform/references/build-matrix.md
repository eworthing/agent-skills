# Per-Platform Build Matrix

Build every supported destination before merging. macOS and Catalyst
frequently surface compatibility issues that tvOS and iOS-simulator builds
miss; do not skip them.

## Canonical Destinations

```bash
# iOS Simulator (latest)
xcodebuild build -scheme YourScheme \
  -destination 'generic/platform=iOS Simulator'

# iPadOS — same SDK as iOS, but verify on an iPad device class
xcodebuild build -scheme YourScheme \
  -destination 'platform=iOS Simulator,name=iPad Pro (12.9-inch) (6th generation)'

# Mac Catalyst
xcodebuild build -scheme YourScheme \
  -destination 'platform=macOS,variant=Mac Catalyst'

# macOS (native)
xcodebuild build -scheme YourScheme \
  -destination 'platform=macOS'

# tvOS Simulator
xcodebuild build -scheme YourScheme \
  -destination 'generic/platform=tvOS Simulator'
```

For projects with multiple schemes (app, widget extension, watch companion),
build each scheme against each destination it claims to support. If your
project ships a wrapper script, prefer it — these `xcodebuild` invocations
are the lowest-common-denominator equivalents.

## Expected Pass Output

```
** BUILD SUCCEEDED **
```

That single line at the end of stdout is the only signal you need. If it is
absent, the build failed even if exit code did not propagate (rare; happens
under some CI shells without `PIPESTATUS` handling).

## Expected Failure Output — Common Patterns

### tvOS — UIKit symbol missing

```
/path/to/Haptics.swift:14:9: error: cannot find 'UIImpactFeedbackGenerator' in scope
        UIImpactFeedbackGenerator(style: .medium).impactOccurred()
        ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
** BUILD FAILED **
```

Cause: `#if canImport(UIKit)` evaluated true on tvOS but the specific symbol
is unavailable. Fix: replace guard with `#if os(iOS)`. See
`references/tvos.md` haptics section.

### macOS — `.topBarLeading` unavailable

```
/path/to/Toolbar.swift:22:35: error: type 'ToolbarItemPlacement' has no member 'topBarLeading'
            ToolbarItem(placement: .topBarLeading) { ... }
                                   ^~~~~~~~~~~~~~~
** BUILD FAILED **
```

Fix: branch the modifier:

```swift
.toolbar {
    #if os(macOS)
    ToolbarItem(placement: .navigation) { /* ... */ }
    #else
    ToolbarItem(placement: .topBarLeading) { /* ... */ }
    #endif
}
```

### macOS — `TabView .page` unavailable

```
/path/to/RootView.swift:18:24: error: static method 'page' requires that 'PageTabViewStyle' conform to ...
        .tabViewStyle(.page)
                       ^~~~
** BUILD FAILED **
```

Fix: branch the style per platform. See `references/macos.md` TabView section.

### macOS — `.fullScreenCover` unavailable

```
/path/to/Modal.swift:30:9: error: value of type 'some View' has no member 'fullScreenCover'
        .fullScreenCover(isPresented: $show) { ModalContent() }
         ^~~~~~~~~~~~~~~~
** BUILD FAILED **
```

Fix: branch to `.sheet` on macOS. See `references/macos.md` modal section.

### Post-split visibility — one platform first

```
/path/to/ModelExtensions.swift:8:9: error: 'helper' is inaccessible due to 'private' protection level
        helper.doThing()
        ^~~~~~
** BUILD FAILED **
```

Cause: a `private` declaration is file-scoped; after moving the extension to a
new file, cross-file access broke. Often surfaces on macOS first because Swift
whole-module optimization is platform-conditional. Fix: promote to `internal`
or keep the extension in the same file. See `swift-file-splitting`.

## CI Wrapper

Minimal portable wrapper to fail fast on the first broken destination:

```bash
#!/usr/bin/env bash
set -e
set -o pipefail

SCHEME="$1"
[ -n "$SCHEME" ] || { echo "usage: $0 <scheme>"; exit 2; }

DESTS=(
  'generic/platform=iOS Simulator'
  'platform=macOS,variant=Mac Catalyst'
  'platform=macOS'
  'generic/platform=tvOS Simulator'
)

for d in "${DESTS[@]}"; do
  echo "==> Building $SCHEME for $d"
  xcodebuild build -scheme "$SCHEME" -destination "$d" \
    | tail -n 50
done

echo "All destinations succeeded."
```

Run on every PR. Failure on any destination blocks merge.

## Related Skills

- `swift-file-splitting` — visibility-preserving file extraction (precedes most
  post-split build failures)
- `bash-macos` — Bash 3.2 + GNU/BSD portable shell rules
