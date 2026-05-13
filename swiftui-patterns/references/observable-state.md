# Observable State Patterns

Portable patterns for SwiftUI state containers built on the Observation framework
(`@Observable`, `@Bindable`). Covers the modern replacements for
`ObservableObject` + `@Published` + `@ObservedObject`, the mutation-routing
discipline that keeps state-driven UIs predictable, undo-snapshot capture,
and error surfacing.

This file is iOS/macOS/tvOS-agnostic. No domain-specific examples.

---

## Headline Gotcha: `@AppStorage` Inside `@Observable` Silently Fails

**The most search-relevant pattern in this file.**

`@AppStorage` does **not** participate in the Observation framework. When you
put it on a property of an `@Observable` class, the property reads/writes
`UserDefaults` correctly, but **SwiftUI views observing that class will never
re-render when the value changes** — even if you mark the property
`@ObservationIgnored`. There is no warning. The view simply stays stale.

```swift
// WRONG — @AppStorage inside @Observable silently fails to trigger view updates.
// Views reading `appearance` will not re-render when it changes.
@Observable
final class Settings {
    @AppStorage("appearance") var appearance: String = "system"
}
```

```swift
// CORRECT — plain stored property + didSet sync to UserDefaults.
// The Observation framework tracks reads/writes of `appearance`, so views update.
@Observable
final class Settings {
    var appearance: String = UserDefaults.standard.string(forKey: "appearance") ?? "system" {
        didSet { UserDefaults.standard.set(appearance, forKey: "appearance") }
    }
}
```

For richer types, encode/decode in `didSet` (e.g. `JSONEncoder` → `Data` →
`UserDefaults.standard.set(_:forKey:)`). The shape of the fix is the same:
**plain stored property, with `didSet` syncing to `UserDefaults`.**

`@AppStorage` is fine when used **directly on a SwiftUI `View`** — it's only
the `@Observable`-class case that breaks. If you need both a class-owned value
and a view that reads `UserDefaults` directly, keep them as separate channels;
do not try to bridge them through `@AppStorage` on the class.

---

## Modern State Container Shape

Use `@Observable` + `@MainActor` + `final class` for SwiftUI state containers.
This is the supported replacement for `ObservableObject` + `@Published`.

```swift
@MainActor
@Observable
final class AppModel {
    var items: [Item] = []
    var selection: Set<Item.ID> = []
    var isLoading: Bool = false
}
```

- **`@Observable`** — opts the class into the Observation framework. Property
  reads are automatically tracked by any SwiftUI view that touches them; writes
  invalidate exactly the views that read them. No `@Published` needed.
- **`@MainActor`** — pins the class to the main actor. SwiftUI updates run on
  main; making the model `@MainActor` lets you mutate it directly from view
  code (e.g. button actions) without `await` ceremony and prevents accidental
  off-main mutation.
- **`final class`** — required for `@Observable`'s macro expansion and avoids
  dynamic-dispatch overhead.

Do **not** use `ObservableObject` / `@Published` / `@StateObject` /
`@ObservedObject` in new code. They still work but have weaker invalidation
granularity (every `@Published` write invalidates every observer, not just the
views that read the changed property).

---

## View Binding: `@Bindable` Over `@ObservedObject`

`@Bindable` is the modern way to get `Binding`s out of an `@Observable` type:

```swift
struct DetailView: View {
    @Bindable var model: AppModel

    var body: some View {
        TextField("Title", text: $model.title)
        Toggle("Enabled", isOn: $model.isEnabled)
    }
}
```

- **`@Bindable var model: ...`** — use when the view receives an `@Observable`
  instance from a parent and needs to project `Binding`s into child controls.
- **`@State private var model = AppModel()`** — use when the view *owns* the
  model (replaces `@StateObject` for `@Observable` types).
- **`@Environment(AppModel.self) private var model`** — use when the model is
  injected via `.environment(model)` higher in the hierarchy.

`@ObservedObject` does not work with `@Observable` types. If you see
`@ObservedObject` in code that's been migrated to `@Observable`, change it to
`@Bindable` (or remove the wrapper entirely if no `Binding`s are needed —
plain `let model: AppModel` is enough to read observed properties).

---

## Mutation Routing: Methods On The Model, Not Views

**Rule of thumb: route mutations through methods on the state object. Never
mutate model state from inside a view body or directly from a button action.**

```swift
// WRONG — view mutates model collections directly.
// Hard to test, no single place to add undo / validation / logging.
struct ToolbarView: View {
    @Bindable var model: AppModel

    var body: some View {
        Button("Delete Selected") {
            for id in model.selection {
                model.items.removeAll { $0.id == id }
            }
            model.selection.removeAll()
        }
    }
}
```

```swift
// CORRECT — view invokes a method; the model owns the mutation logic.
struct ToolbarView: View {
    @Bindable var model: AppModel

    var body: some View {
        Button("Delete Selected") { model.deleteSelected() }
    }
}

@MainActor
@Observable
final class AppModel {
    func deleteSelected() {
        items.removeAll { selection.contains($0.id) }
        selection.removeAll()
    }
}
```

Benefits:
- One place to add undo, validation, persistence, telemetry, error handling.
- The view becomes a thin declarative shell — easier to read, easier to test.
- Multiple call sites stay consistent (no copy-paste mutation logic).

Exception: SwiftUI previews and test fixtures may construct and seed a model
directly. The "no mutation from views" rule applies to production views, not
preview helpers.

---

## Undo Snapshot Capture Pattern

For undo support, capture a snapshot *before* applying a change, apply the
change, then record the snapshot for undo:

```swift
@MainActor
@Observable
final class AppModel {
    private(set) var undoStack: [(action: String, snapshot: Snapshot)] = []

    func performChange() {
        let snapshot = captureSnapshot()           // 1. capture before
        applyChange()                              // 2. mutate
        recordUndo(action: "Perform Change",       // 3. record for undo
                   snapshot: snapshot)
    }
}
```

Three independent steps:

1. **`captureSnapshot()`** — returns a value-type copy of whatever state the
   change might touch. Keep it minimal (only the affected slices) to control
   memory.
2. **Apply the change** — mutate the model's properties.
3. **`recordUndo(action:snapshot:)`** — push the snapshot + a human-readable
   action label onto the undo stack and notify any undo UI.

Keeping these three steps explicit (rather than wrapping the whole thing in a
single `withUndo { }` block) makes it obvious in code review *which* slice of
state is being snapshotted and *when* the snapshot is taken relative to the
mutation. It also lets you skip the snapshot for trivially non-undoable changes
(e.g. transient UI flags).

---

## Error Surfacing: Visual, Not Silent

User-initiated async operations must surface errors visually — a toast,
banner, or alert. Silent `catch` + log strands the user with no feedback.

```swift
// WRONG — error is logged, but the user has no idea anything failed.
func importFile(_ url: URL) async {
    do {
        let data = try await loader.load(url)
        items.append(contentsOf: data)
    } catch {
        Logger().error("Import failed: \(error)")
    }
}
```

```swift
// CORRECT — error is surfaced to the user via the model's error channel,
// which a view binds to and renders as a toast / alert / banner.
func importFile(_ url: URL) async {
    do {
        let data = try await loader.load(url)
        items.append(contentsOf: data)
        presentSuccess("Imported \(data.count) items")
    } catch {
        presentError("Import Failed", error.localizedDescription)
    }
}
```

Rules of thumb:

- **Never `preconditionFailure` for recoverable errors.** A failed CSV import,
  a missing network resource, an out-of-date persisted document — these are
  user-recoverable. Surface them; do not crash.
- **Logging is not surfacing.** Logs are for engineers post-hoc, not for the
  user in the moment. Do both, but never substitute one for the other.
- **Async operations triggered by the user must give the user feedback** —
  success and failure both. Silence after a button tap reads as "the app is
  broken."

---

## Typed Error Taxonomy (Concept)

For models that perform meaningfully different categories of work, define a
**per-domain error type** rather than a single catch-all `enum AppError`.
Each domain error maps cleanly to a user-readable UI surface:

| Domain | Per-domain error type | Typical UI surface |
|---|---|---|
| Export to disk / share | `ExportError` | Destructive toast — "Export Failed: \<reason\>" |
| Import / parse external data | `ImportError` | Info toast or validation summary |
| Persistence (read/write database) | `PersistenceError` | Blocking alert with retry |

```swift
enum ExportError: Error {
    case unsupportedFormat
    case encodingFailed
    case writeFailed(underlying: Error)

    var userMessage: String {
        switch self {
        case .unsupportedFormat:     "This format isn't supported on this platform."
        case .encodingFailed:        "Couldn't encode the document. Try a different format."
        case .writeFailed(let e):    "Couldn't save the file: \(e.localizedDescription)"
        }
    }
}
```

Benefits over `enum AppError`:

- **Exhaustive `switch`** at the call site catches new cases at compile time
  when the error type grows. A catch-all `AppError` swallows new cases
  silently.
- **Each error type knows its UI mapping** — the `userMessage` (or equivalent)
  computed property lives on the error itself, not scattered across views.
- **Errors stay scoped** — an `ImportError` cannot accidentally be thrown from
  an export code path, because the function signature says
  `throws(ImportError)` (or returns `Result<_, ImportError>`).

Keep `Error` conformances minimal — most should be plain `enum`s with
associated `underlying: Error` for wrapping system errors.
