---
name: swiftdata-persistence
description: >-
  SwiftData patterns and gotchas for `@Model` entities, `ModelContext`,
  `ModelContainer`, `FetchDescriptor`, `@Query`, migrations, and cascade-delete
  relationships on iOS, macOS, and tvOS. Use when adding `@Model` properties,
  updating bundled seed data, debugging "data not showing", "stale entity", or
  "images-show-placeholder-after-upgrade" issues, working with ModelContext /
  ModelContainer / FetchDescriptor / @Query, mutating entities off the main
  actor with a ModelActor, applying `@Attribute(.unique)` / `#Unique` / `#Index`,
  implementing seed-data or `VersionedSchema` / `SchemaMigrationPlan` migrations,
  preventing orphan entities, or auto-saving entities on a timer.
allowed-tools:
  - Read
  - Bash
  - Glob
---

# SwiftData Persistence Skill

## Contents

- Purpose
- When to Use
- Do NOT Use For
- Sibling Skills — Defer When
- Critical Gotcha: Stale Bundled Entities
- Seed-Data Migration Patterns
- ModelContainer Setup
- ModelContext Access in Views
- Concurrency & Threading
- FetchDescriptor Patterns
- @Query Patterns
- Entity Relationships and Cascade Delete
- Debugging Stale Entities
- Typed Persistence Errors
- SwiftData API Availability
- Constraints
- References

## Purpose

SwiftData stores [`@Model`](https://developer.apple.com/documentation/swiftdata/model())
entities in a persistent store managed by `ModelContainer`. Entities outlive
code — when bundled "seed" definitions in source change, the existing on-disk
entities **do not** automatically update. This skill documents that gotcha plus
the supporting patterns needed to ship and debug SwiftData-backed features
safely.

> Code examples assume `import SwiftData`; view examples add `import SwiftUI`,
> and `Logger` needs `import os`.

## When to Use

- Adding or renaming properties on a `@Model` type
- Updating bundled seed/template data shipped inside the app
- Debugging "images show placeholders", "new field is nil", "works fresh, broken on upgrade"
- Writing or reading `FetchDescriptor` / `@Query` queries
- Setting up `ModelContainer` at the app entry point
- Mutating entities off the main actor (background import/export) via a `ModelActor`
- Implementing seed-data or `VersionedSchema` migrations or cascade-delete relationships
- Adding auto-save on a periodic timer

## Do NOT Use For

- CloudKit sync (`.modelContainer(for:..., cloudKitDatabase:)` — separate concern)
- Core Data interop / store conversion (user-content migration **is** in scope — see [`references/migrations.md`](references/migrations.md))

## Sibling Skills — Defer When

This skill owns SwiftData persistence — `@Model`, `ModelContext`,
`ModelContainer`, `FetchDescriptor`, `@Query`, migrations, and cascade-delete.
Adjacent skills own neighboring territory; defer to them rather than
re-deriving here. If both apply, this skill leads on the persistence decision
and the sibling fills in the mechanism.

- Actor isolation, `Sendable`, data-race and Swift 6 concurrency mechanics behind
  `ModelActor` and off-main `ModelContext` ownership → `swift-concurrency`.
- `@Observable` data flow, `@Query`-driven view invalidation / update storms,
  Instruments `.trace` analysis of fetch-heavy views → `swiftui-expert-skill`.
- Cross-platform availability gating (`#if os(...)`, version floors for `#Index`
  / `ModelActor`) across iOS / macOS / tvOS → `apple-multiplatform`.

---

## Critical Gotcha: Stale Bundled Entities

**Symptom set** — agents and users report these in this order:

- Images show placeholders despite the correct asset name in source
- A new field on `@Model` returns `nil` even though seed code sets it
- The app works on a fresh install but is broken after upgrade
- Reverting source doesn't fix it — the entity on disk is stale

**Root cause.** SwiftData persists entities. When the *source* of a bundled
entity changes (a new property, a different `imageUrl`, a renamed field), the
*persisted* entity from a previous app launch still holds the old values. A
naive prefill that only inserts when the entity is missing will never observe
the change.

**Lead-with-this fix.** For read-only bundled data, delete-and-regenerate on
every launch (Pattern 1 below), or gate it by version/hash. Never assume "if it
exists, it's correct".

---

## Seed-Data Migration Patterns

*Bundled data* is the read-only template/seed content shipped in the app binary
(managed by `prefillBundledItemsIfNeeded`) — distinct from user-created content,
whose path is `VersionedSchema` + `SchemaMigrationPlan` ([`references/migrations.md`](references/migrations.md)).

Pick one strategy — all three assume read-only template content (<100 entities):

| Strategy | When | Trade-off |
|---|---|---|
| **1. Delete-and-regenerate** | Small dataset, changes during development | Runs every launch |
| **2. Version-gated** | Regenerate only on a bumped integer | Humans forget to bump |
| **3. Hash-gated** | Auto-detect drift by hashing the definitions | Hash must be launch-stable |

Pattern 1 is inline below (the canonical gotcha fix); the gated variants 2 & 3,
with their shared helpers, live in [`references/migrations.md`](references/migrations.md).

### Pattern 1 — Delete-and-Regenerate

Wipes existing bundled entities and re-inserts from the current source-of-truth.

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
            modelContext.insert(makeEntity(from: item))
        }

        try modelContext.save()
    } catch {
        Logger().error("Prefill failed: \(error)")
    }
}
```

**Appropriate for:** read-only template/demo data, small datasets (<100), data
whose source-of-truth is always in code. **Not** for user-created content, large
datasets, or complex ordered-relationship migration (see Constraints).

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

Inject via the environment. Do not store the context in a long-lived reference
outside SwiftUI's lifecycle.

```swift
struct LibraryView: View {
    @Environment(\.modelContext) private var modelContext
    @Query private var items: [BundledItemEntity]
    // ...
}
```

## Concurrency & Threading

Mutate entities only on the actor that owns their `ModelContext`. There are two
correct homes for a context, not one:

- **Main context → `@MainActor`.** The `@Environment(\.modelContext)` context is
  main-actor-isolated. All the mutating examples in this skill are `@MainActor`
  because they operate on it — that is correct, not a workaround.
- **Background context → a `ModelActor`.** For off-main work (bulk import,
  export, heavy migration), use a
  [`ModelActor`](https://developer.apple.com/documentation/swiftdata/modelactor)
  (iOS 17+) — an actor-isolated context. Never pass a `ModelContext` or its
  entities across actor boundaries; re-fetch by `PersistentIdentifier` there.

```swift
@ModelActor
actor BundledImporter {
    func importItems(_ items: [BundledSource]) throws {
        for item in items {
            modelContext.insert(makeEntity(from: item))
        }
        try modelContext.save()   // saves on the actor's own context
    }
}

// Call site — construct with the shared container, await across the boundary.
let importer = BundledImporter(modelContainer: container)
try await importer.importItems(bundledItems)
```

Actor isolation, `Sendable`, and Swift 6 data-race mechanics behind this belong
to `swift-concurrency` — defer there for the "why".

---

## FetchDescriptor Patterns

Use `FetchDescriptor` for imperative fetches (outside a view, or inside a
`ModelActor`); prefer `@Query` (next section) for view-driven fetches.

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

## @Query Patterns

`@Query` is the SwiftUI-native fetch: it re-runs and re-renders the view
automatically when matching data changes. Filter and sort in the property
wrapper for a static query.

```swift
@Query(
    filter: #Predicate<BundledItemEntity> { $0.sourceRaw == "bundled" },
    sort: \.createdAt, order: .reverse
)
private var items: [BundledItemEntity]
```

For a **dynamic** predicate (search text, a selected category), build the query
in the view's `init` — a plain `@Query` property can't read `init` parameters.

```swift
struct FilteredList: View {
    @Query private var items: [BundledItemEntity]

    init(search: String) {
        _items = Query(
            filter: #Predicate { $0.title.localizedStandardContains(search) },
            sort: \.title
        )
    }
}
```

---

## Entity Relationships and Cascade Delete

Declare cascade on the parent so deleting the parent removes its children. This
prevents orphans and the "ghost row" bugs they cause.

```swift
@Model
final class BundledItemEntity {
    @Relationship(deleteRule: .cascade)
    var children: [ChildEntity] = []
}
```

Always delete through the parent — never delete a child while the parent still
references it via a non-optional relationship.

```swift
@MainActor
func deleteItem(_ entity: BundledItemEntity, in modelContext: ModelContext) {
    modelContext.delete(entity)   // children removed via cascade rule
    do {
        try modelContext.save()
    } catch {
        Logger().error("Delete failed: \(error)")
    }
}
```

---

## Debugging Stale Entities

Checklist when a user reports "data not showing" or "wrong values after upgrade":

1. **Verify source.** Open the bundled-definitions Swift file. Are the values you expect actually present?
2. **Inspect persisted state.** Pause in Xcode and `po` the entity — compare on-disk values to source.
3. **Fresh-install test.** Delete the app, reinstall, retry. If the bug disappears, it is stale entities — apply a migration pattern above. (Note: a passing fresh install does **not** prove the upgrade path — see Constraints.)
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

---

## Typed Persistence Errors

Wrap persistence failures in a custom error type so callers branch on the
failure instead of catching opaque `Error`. The migration and auto-save
examples log-and-continue for brevity; production save paths should surface a
typed error.

```swift
enum PersistenceError: Error {
    case saveFailed(underlying: Error)
    case prefillFailed(underlying: Error)
}

func save(_ modelContext: ModelContext) throws {
    do {
        try modelContext.save()
    } catch {
        throw PersistenceError.saveFailed(underlying: error)
    }
}
```

Auto-save on a timer follows the same swallow-and-log discipline — full example
in [`references/modern-apis.md`](references/modern-apis.md).

---

## SwiftData API Availability

Version floors for the newer SwiftData surface; each row links Apple's page for
drift-checking. The body teaches only `ModelActor` (Concurrency) and
`@Attribute(.unique)` — the rest carry a pointer to
[`references/modern-apis.md`](references/modern-apis.md). `@Attribute(.unique)`
(iOS 17) makes a colliding insert upsert-in-place — handy for seed dedup;
compound uniqueness needs `#Unique` (iOS 18).

| API | Floor | What it's for | Apple Docs |
|---|---|---|---|
| `@Attribute(.unique)` | iOS 17 | Single-attribute uniqueness / upsert key | [Attribute](https://developer.apple.com/documentation/swiftdata/attribute(_:originalname:hashmodifier:)) |
| `ModelActor` | iOS 17 | Actor-isolated context for off-main reads/writes | [ModelActor](https://developer.apple.com/documentation/swiftdata/modelactor) |
| `VersionedSchema` + `SchemaMigrationPlan` | iOS 17 | Versioned user-content schema migration | [SchemaMigrationPlan](https://developer.apple.com/documentation/swiftdata/schemamigrationplan) |
| `#Unique` | iOS 18 | Compound uniqueness across attributes | [Unique(_:)](https://developer.apple.com/documentation/swiftdata/unique(_:)) |
| `#Index` | iOS 18 | Single/compound indexes to speed predicate fetches & sorts | [Index(_:)](https://developer.apple.com/documentation/swiftdata/index(_:)-74ia2) |
| History tracking (`fetchHistory` / `deleteHistory`) | iOS 18 | Query/prune persistent transaction history (sync, undo) | [fetchHistory(_:)](https://developer.apple.com/documentation/swiftdata/modelcontext/fetchhistory(_:)) |
| Custom `DataStore` | iOS 18 | Back a model with non-default storage (JSON, server mirror) | [DataStore](https://developer.apple.com/documentation/swiftdata/datastore) |
| Model inheritance (`@Model`) | iOS 26 | Subclass `@Model` types for shared attributes | [Model()](https://developer.apple.com/documentation/swiftdata/model()) |
| `ResultsObserver` | iOS 27 (beta) | Observable fetch results (with sectioning) outside a view | [ResultsObserver](https://developer.apple.com/documentation/swiftdata/resultsobserver) |
| `HistoryObserver` | iOS 27 (beta) | Observe remote/CloudKit history changes via `eventCounter` | [HistoryObserver](https://developer.apple.com/documentation/swiftdata/historyobserver) |

iOS 27 rows are **beta** floors (may shift before GA); 17/18/26 are GA. Last verified: 2026-07-04.

## Constraints

- **Never** assume bundled data auto-updates on app upgrade — pick a migration pattern.
- **Always** use delete-and-regenerate (or a version/hash gate) for bundled content.
- **Never** apply delete-and-regenerate to user-created content — it destroys user data. Use `VersionedSchema` + `SchemaMigrationPlan` instead ([`references/migrations.md`](references/migrations.md)). This is the single rule the whole skill guards.
- **Always** test the upgrade path — fresh-install green does not prove it. Install the old build, then the new one, and confirm the data survives.
- **Never** mutate a `ModelContext` or its entities across actor boundaries — main context on `@MainActor`, background work in a `ModelActor`.
- **Use typed errors** (custom `enum: Error`) for all persistence operations — opaque `Error` hides the recovery path.

## References

- [`references/migrations.md`](references/migrations.md) — version/hash-gated seed variants (with shared helpers) + user-content `VersionedSchema` / `SchemaMigrationPlan` walkthrough
- [`references/modern-apis.md`](references/modern-apis.md) — worked patterns for the iOS 18–27 surface (`#Unique` / `#Index`, history tracking, model inheritance, `ResultsObserver`, custom `DataStore`) + the auto-save task
