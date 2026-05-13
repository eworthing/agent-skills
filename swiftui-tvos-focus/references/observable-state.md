# `@AppStorage` Inside `@Observable` — Silent-Failure Gotcha

The single state-container gotcha unique enough to repeat outside the
general SwiftUI state-management reference. For general
`@Observable` + `@MainActor` + `@Bindable` patterns, mutation routing,
undo snapshots, and error surfacing, see the authoritative
`swiftui-expert-skill` `references/state-management.md`.

## Symptom

`@AppStorage` does **not** participate in the Observation framework. When
declared on a property of an `@Observable` class, the property
reads/writes `UserDefaults` correctly, but **SwiftUI views observing
that class will never re-render when the value changes** — even if the
property is marked `@ObservationIgnored`. There is no compiler warning
and no runtime diagnostic. The view simply stays stale.

```swift
// WRONG — @AppStorage inside @Observable silently fails to trigger view updates.
// Views reading `appearance` will not re-render when it changes.
@Observable
final class Settings {
    @AppStorage("appearance") var appearance: String = "system"
}
```

## Fix

Plain stored property + `didSet` syncing to `UserDefaults`:

```swift
// CORRECT — Observation tracks reads/writes of `appearance`, so views update.
@Observable
final class Settings {
    var appearance: String =
        UserDefaults.standard.string(forKey: "appearance") ?? "system" {
        didSet { UserDefaults.standard.set(appearance, forKey: "appearance") }
    }
}
```

For richer types, encode/decode in `didSet` (e.g. `JSONEncoder` → `Data`
→ `UserDefaults.standard.set(_:forKey:)`). The shape is the same: plain
stored property, `didSet` syncing the new value to `UserDefaults`.

## When `@AppStorage` Is Still Safe

`@AppStorage` works correctly when applied **directly on a SwiftUI
`View`**:

```swift
struct AppearancePicker: View {
    @AppStorage("appearance") private var appearance: String = "system"

    var body: some View {
        Picker("Appearance", selection: $appearance) {
            Text("System").tag("system")
            Text("Light").tag("light")
            Text("Dark").tag("dark")
        }
    }
}
```

Only the `@Observable`-class case breaks. If a class-owned value and a
view both need the same `UserDefaults` key, keep them as separate
channels — the class uses plain property + `didSet`; the view uses
`@AppStorage` directly. Do not try to bridge them through `@AppStorage`
on the class.

## Detection

Grep for the anti-pattern across a project:

```bash
rg -l '@Observable' --glob '*.swift' | xargs rg -l '@AppStorage'
```

Any file in the intersection is suspect. Verify the `@AppStorage` is on
a `View` (safe) and not on a property of the `@Observable` class
(broken).
