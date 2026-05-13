---
name: swiftdata-persistence
author: eworthing
description: >-
  SwiftData patterns and gotchas for `@Model` entities, `ModelContext`,
  `ModelContainer`, `FetchDescriptor`, migrations, and cascade-delete
  relationships on iOS, macOS, and tvOS. Use when adding `@Model` properties,
  updating bundled seed data, debugging "data not showing", "stale entity",
  or "images-show-placeholder-after-upgrade" issues, working with
  ModelContext / ModelContainer / FetchDescriptor, implementing seed-data
  migrations, preventing orphan entities, or auto-saving entities on a timer.
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - Glob
---

# SwiftData Persistence Skill

## Purpose

SwiftData stores `@Model` entities in a persistent store managed by
`ModelContainer`. Entities outlive code — when bundled "seed" definitions
in source change, the existing on-disk entities **do not** automatically
update. This skill documents that gotcha plus the supporting patterns
needed to ship and debug SwiftData-backed features safely.

## When to Use

- Adding or renaming properties on a `@Model` type
- Updating bundled seed/template data shipped inside the app
- Debugging "images show placeholders", "new field is nil", "works fresh, broken on upgrade"
- Writing or reading `FetchDescriptor` queries
- Setting up `ModelContainer` at the app entry point
- Implementing seed-data migrations or cascade-delete relationships
- Adding auto-save on a periodic timer

## Do NOT Use For

- Schema migrations across `VersionedSchema` releases (use Apple's `SchemaMigrationPlan` docs)
- CloudKit sync (`.modelContainer(for:..., cloudKitDatabase:)` — separate concern)
- Core Data interop / store conversion
- User-created content migrations (delete-and-regenerate **destroys user data**)

---

## Critical Gotcha: Stale Bundled Entities

**Symptom set** — agents and users report these in this order:

- Images show placeholders despite the correct asset name in source
- A new field on `@Model` returns `nil` even though seed code sets it
- The app works on a fresh install but is broken after upgrade
- Reverting source doesn't fix it — the entity on disk is stale

**Root cause.** SwiftData persists entities. When the *source* of a bundled
entity changes (a new property, a different `imageUrl`, a renamed field),
the *persisted* entity from a previous app launch still holds the old
values. A naive prefill that only inserts when the entity is missing will
never observe the change.

**Lead-with-this fix.** For read-only bundled data, delete-and-regenerate
on every launch (or guarded by version/hash — see below). Never assume
"if it exists, it's correct".

---

## Seed-Data Migration Patterns

Pick one. All three assume the bundled data is read-only template content
(<100 entities) — none are safe for user-created data.

### 1. Delete-and-Regenerate (simplest)

Use when the dataset is small and changes during development. Wipes
existing bundled entities and re-inserts from current source-of-truth.

```swift
@MainActor
func prefillBundledItemsIfNeeded(modelContext: ModelContext) {
    do {
        let bundledSource = BundledSource.bundled.rawValue
        let descriptor = FetchDescriptor<BundledItemEntity>(
            predicate: #Predicate { $0.sourceRaw == bundledSource }
        )
        let existing = try modelContext.fetch(descriptor)

        // DELETE all existing bundled entities
        for entity in existing {
            modelContext.delete(entity)
        }

        // INSERT fresh from current definitions
        for item in bundledItems {
            let entity = makeEntity(from: item)
            modelContext.insert(entity)
        }

        try modelContext.save()
    } catch {
        Logger().error("Prefill failed: \(error)")
    }
}
```

**Appropriate for:** read-only template/demo data, small datasets (<100),
data whose source-of-truth is always in code.

**Never use for:** user-created content (loses data!), large datasets
(performance), or data with complex relationships requiring careful
ordered migration.

### 2. Version-Based (regenerate only on bump)

Avoids work on every launch by gating the regenerate on a stored integer.

```swift
@MainActor
func prefillBundledItemsIfNeeded(modelContext: ModelContext) {
    let currentVersion = 2  // bump when bundled structure changes
    let key = "bundledItemsVersion"
    guard UserDefaults.standard.integer(forKey: key) < currentVersion else { return }

    deleteAllBundledItems(in: modelContext)
    insertFreshBundledItems(into: modelContext)
    UserDefaults.standard.set(currentVersion, forKey: key)
}
```

Trade-off: humans must remember to bump the integer. Easy to forget.

### 3. Hash-Based (auto-detect changes)

Hash the bundled source definitions; regenerate when the hash drifts.

```swift
@MainActor
func prefillBundledItemsIfNeeded(modelContext: ModelContext) {
    let currentHash = hashOfBundledDefinitions()
    let storedHash = UserDefaults.standard.string(forKey: "bundledItemsHash")
    guard currentHash != storedHash else { return }

    deleteAllBundledItems(in: modelContext)
    insertFreshBundledItems(into: modelContext)
    UserDefaults.standard.set(currentHash, forKey: "bundledItemsHash")
}
```

Trade-off: hash must be stable across launches (sort keys, encode
deterministically). Preferred for teams that forget to bump versions.

---

## ModelContainer Setup

Set up the container once at the `@main` app entry, attach with
`.modelContainer(_:)`, and never instantiate ad-hoc containers in views.

```swift
@main
struct YourApp: App {
    let container: ModelContainer

    init() {
        do {
            container = try ModelContainer(
                for: BundledItemEntity.self, ChildEntity.self
            )
        } catch {
            fatalError("ModelContainer failed: \(error)")
        }
    }

    var body: some Scene {
        WindowGroup {
            ContentView()
        }
        .modelContainer(container)
    }
}
```

## ModelContext Access in Views

Inject via the environment. Do not store the context in a long-lived
reference outside SwiftUI's lifecycle.

```swift
struct LibraryView: View {
    @Environment(\.modelContext) private var modelContext
    @Query private var items: [BundledItemEntity]
    // ...
}
```

---

## FetchDescriptor Patterns

### Basic

```swift
let descriptor = FetchDescriptor<BundledItemEntity>()
let all = try modelContext.fetch(descriptor)
```

### Filtered with `#Predicate`

```swift
let source = BundledSource.bundled.rawValue
let descriptor = FetchDescriptor<BundledItemEntity>(
    predicate: #Predicate { $0.sourceRaw == source }
)
```

### Sorted with `SortDescriptor`

```swift
let descriptor = FetchDescriptor<BundledItemEntity>(
    sortBy: [SortDescriptor(\.createdAt, order: .reverse)]
)
```

### Limited

```swift
var descriptor = FetchDescriptor<BundledItemEntity>()
descriptor.fetchLimit = 10
```

---

## Auto-Save Pattern

Run a `@MainActor` task that wakes on a 30-second interval and saves only
when `hasChanges` is true. Throws are swallowed with a log — auto-save
should never crash the app.

```swift
@MainActor
private func startAutoSaveTask(modelContext: ModelContext) -> Task<Void, Never> {
    Task { @MainActor in
        while !Task.isCancelled {
            try? await Task.sleep(for: .seconds(30))
            guard modelContext.hasChanges else { continue }
            do {
                try modelContext.save()
            } catch {
                Logger().error("Auto-save failed: \(error)")
            }
        }
    }
}
```

---

## Entity Relationships and Cascade Delete

Declare cascade on the parent so deleting the parent removes its children.
This prevents orphans and the "ghost row" bugs they cause.

```swift
@Model
final class BundledItemEntity {
    @Relationship(deleteRule: .cascade)
    var children: [ChildEntity] = []
}
```

Always delete through the parent — never delete a child while the parent
still references it via a non-optional relationship.

```swift
@MainActor
func deleteItem(_ entity: BundledItemEntity, in modelContext: ModelContext) {
    modelContext.delete(entity)   // children removed via cascade rule
    try? modelContext.save()
}
```

---

## Debugging Stale Entities

Checklist when a user reports "data not showing" or "wrong values after upgrade":

1. **Verify source.** Open the bundled-definitions Swift file. Are the values you expect actually present?
2. **Inspect persisted state.** Pause in Xcode and `po` the entity — compare on-disk values to source.
3. **Fresh-install test.** Delete the app, reinstall, retry. If the bug disappears, it is stale entities — apply a migration pattern above.
4. **Add load-time logging.** Print entity values when prefill runs; diff against source to confirm drift.

### Delete app data during development

```bash
# iOS Simulator — uninstall just your app (preferred, narrowly scoped)
xcrun simctl uninstall <device-id> <your.bundle.id>

# iOS Simulator — nuke ALL simulator app data (destructive — wipes every app, not just yours)
xcrun simctl shutdown all
rm -rf ~/Library/Developer/CoreSimulator/Devices/*/data/Containers/Data/Application/*/Documents/*

# macOS sandbox — your app only
rm -rf ~/Library/Containers/<your.bundle.id>/Data/Documents/*
```

Prefer `simctl uninstall` over the broad `rm -rf` — the broad form deletes
every other simulator app's data on the machine.

---

## Constraints

- **Never** assume bundled data auto-updates on app upgrade — pick a migration pattern.
- **Always** use delete-and-regenerate (or version/hash gate) for bundled content.
- **Always** test the upgrade path — fresh-install green does not prove anything.
- **Never** mutate `@Model` entities outside a `@MainActor` context.
- **Use typed errors** (custom `enum: Error`) for all persistence operations — opaque `Error` hides the recovery path.
- **Never** apply delete-and-regenerate to user-created content. Pick `VersionedSchema` + `SchemaMigrationPlan` instead.
