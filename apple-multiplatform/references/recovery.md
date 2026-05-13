# Recovery Playbook — Build Failures

Per-error recipe for common cross-platform compile failures. Each entry has:
**Minimal repro** (smallest code that triggers it), **Audit** (command or
checklist that confirms scope), **Fix** (code change).

For the source pattern table in summary form, see `SKILL.md`. For per-platform
gotcha detail, see `references/{tvos,macos,catalyst}.md`.

---

## E1. `Cannot find 'X' in scope` — one platform only

**Minimal repro (tvOS)**:

```swift
#if canImport(UIKit)
import UIKit
let gen = UIImpactFeedbackGenerator(style: .medium)  // tvOS: error
#endif
```

**Audit**: run `scripts/audit-platform-guards.sh` from this skill, or:

```bash
rg -n 'canImport\(UIKit\)' --type swift | xargs -I{} echo {}
rg -n 'UIImpactFeedback|UISelectionFeedback|UINotificationFeedback' --type swift
```

If a file appears in both lists, the symbol is gated by `canImport(UIKit)` but
needs `os(iOS)`.

**Fix**: replace the framework-level guard with an OS-level guard.

```swift
#if os(iOS)
let gen = UIImpactFeedbackGenerator(style: .medium)
#endif
```

---

## E2. `Value of type 'X' has no member 'Y'` — one platform

**Minimal repro (macOS)**:

```swift
.toolbar {
    ToolbarItem(placement: .topBarLeading) { Button("Edit") {} }
}
```

**Audit**:

```bash
rg -n '\.topBarLeading|\.topBarTrailing' --type swift
```

Every match must sit inside a `#if !os(macOS)` (or equivalent) branch.

**Fix**: branch the modifier per platform.

```swift
.toolbar {
    #if os(macOS)
    ToolbarItem(placement: .navigation) { Button("Edit") {} }
    #else
    ToolbarItem(placement: .topBarLeading) { Button("Edit") {} }
    #endif
}
```

---

## E3. `'private' modifier cannot be used in an extension` — after file split

**Minimal repro**: split an extension that referenced a `private` property
from its parent type into a new file. Build fails on the platform Swift
compiles first (often macOS).

**Audit**: `git diff HEAD~1 --stat -- '*.swift'` — any file rename or addition
is suspect. Then in the moved file:

```bash
rg -n 'private\s+(var|let|func)' <moved-file>
```

Any `private` member referenced from the original file is now inaccessible.

**Fix**: promote to `internal` (or `fileprivate` if the extension stays in the
original file). See `swift-file-splitting` skill.

---

## E4. Runtime crash on tvOS after `canImport(UIKit)` guard

**Minimal repro**:

```swift
#if canImport(UIKit)
import UIKit
struct MyView: View {
    var body: some View {
        Button("Tap") {
            UIImpactFeedbackGenerator(style: .medium).impactOccurred()
        }
    }
}
#endif
```

Compiles on tvOS, but `UIImpactFeedbackGenerator` is unavailable; running on
tvOS Simulator the app crashes on tap.

**Audit**: same as E1 — `audit-platform-guards.sh` flags this co-location.

**Fix**: tighten the guard to `#if os(iOS)`. Replaces compile-time-permissive
guard with strict per-OS guard.

---

## E5. `Ambiguous use of '...'` — platform-specific overloads

**Minimal repro**: a type has two overloads visible — one from UIKit, one from
AppKit — and the call site is inside a Mac Catalyst conditional that pulls
both in.

**Audit**: check the import list in the failing file.

```bash
rg -n '^import (UIKit|AppKit)' <file>
```

If both appear inside the same `#if` branch, the compiler sees ambiguous
overloads.

**Fix**: add explicit type annotation at the call site, OR partition the
overloaded code into per-framework files.

---

## E6. macOS-only `Static method 'page' requires ...`

**Minimal repro**:

```swift
TabView { /* ... */ }
    .tabViewStyle(.page)  // macOS: error
```

**Audit**:

```bash
rg -n 'tabViewStyle\(\.page' --type swift
```

Every match must be gated `#if !os(macOS)`.

**Fix**: branch the style per platform.

```swift
TabView { /* ... */ }
#if os(macOS)
.tabViewStyle(.automatic)
#else
.tabViewStyle(.page)
#endif
```

---

## E7. Catalyst window collapses on launch

**Minimal repro**: ship a Catalyst app with no `.defaultSize(...)` on its
`WindowGroup`. On first launch the window appears with an unusable small size.

**Audit**:

```bash
rg -n 'WindowGroup\b' --type swift
rg -n 'defaultSize\b' --type swift
```

Each `WindowGroup` for a Catalyst-supported scheme should pair with a
`.defaultSize` (gated for Catalyst / macOS).

**Fix**:

```swift
WindowGroup { ContentView() }
#if targetEnvironment(macCatalyst) || os(macOS)
.defaultSize(width: 1200, height: 800)
#endif
```

See `references/catalyst.md`.

---

## E8. `.fullScreenCover` not found on macOS

**Minimal repro**:

```swift
view.fullScreenCover(isPresented: $show) { ModalContent() }
```

**Audit**:

```bash
rg -n 'fullScreenCover' --type swift
```

Each match must be gated `#if !os(macOS)` or paired with a `.sheet` branch.

**Fix**: branch per platform.

```swift
view
#if os(macOS)
.sheet(isPresented: $show) { ModalContent() }
#else
.fullScreenCover(isPresented: $show) { ModalContent() }
#endif
```

---

## Standardized Error Output Format

When invoking xcodebuild from a wrapper script, emit one line per failure in
this shape so downstream tooling can grep:

```
APPLE-MP-FAIL <platform> <error-class> <file>:<line>: <message>
```

Example:

```
APPLE-MP-FAIL tvOS E4-canImport-runtime Haptics.swift:14: UIImpactFeedbackGenerator unavailable on tvOS
APPLE-MP-FAIL macOS E2-no-member Toolbar.swift:22: ToolbarItemPlacement has no member topBarLeading
```

`scripts/audit-platform-guards.sh` follows this format on output for static
audit hits.
