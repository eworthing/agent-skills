# SwiftData Migrations

Full recipes deferred from `SKILL.md`. The core skill owns the stale-entity
gotcha and **Pattern 1 (delete-and-regenerate)**; this file owns the two gated
seed variants and the user-content schema-migration path.

## Contents

- Scope
- Shared helpers
- Pattern 2 — Version-gated
- Pattern 3 — Hash-gated
- User-Content Migration (VersionedSchema + SchemaMigrationPlan)
- Testing the upgrade path

## Scope

- **Bundled/seed data** (read-only template content in the app binary): use one
  of the three prefill patterns. Pattern 1 is inline in `SKILL.md`; Patterns 2
  and 3 are below.
- **User-created content** (data the user owns): never delete-and-regenerate.
  Evolve the schema with `VersionedSchema` + `SchemaMigrationPlan`.

## Shared helpers

Patterns 2 and 3 both delegate to these. Define them once; they mirror the
delete/insert halves of Pattern 1.

```swift
@MainActor
func deleteAllBundledItems(in modelContext: ModelContext) {
    let bundledSource = BundledSource.bundled.rawValue
    let descriptor = FetchDescriptor<BundledItemEntity>(
        predicate: #Predicate { $0.sourceRaw == bundledSource }
    )
    guard let existing = try? modelContext.fetch(descriptor) else { return }
    for entity in existing {
        modelContext.delete(entity)
    }
}

@MainActor
func insertFreshBundledItems(into modelContext: ModelContext) {
    for item in bundledItems {
        modelContext.insert(makeEntity(from: item))
    }
}

/// Stable across launches: sort keys and encode deterministically.
func hashOfBundledDefinitions() -> String {
    bundledItems
        .map(\.stableFingerprint)   // your deterministic per-item string
        .sorted()
        .joined(separator: "|")
        .hashValue
        .description
}
```

## Pattern 2 — Version-gated

Regenerate only when a hand-maintained integer is bumped. Avoids work on every
launch.

```swift
@MainActor
func prefillBundledItemsIfNeeded(modelContext: ModelContext) {
    let currentVersion = 2  // bump when bundled structure changes
    let key = "bundledItemsVersion"
    guard UserDefaults.standard.integer(forKey: key) < currentVersion else { return }

    deleteAllBundledItems(in: modelContext)
    insertFreshBundledItems(into: modelContext)
    try? modelContext.save()
    UserDefaults.standard.set(currentVersion, forKey: key)
}
```

Trade-off: humans must remember to bump the integer. Easy to forget — which is
what Pattern 3 removes.

## Pattern 3 — Hash-gated

Hash the bundled definitions; regenerate when the hash drifts. Preferred for
teams that forget to bump versions.

```swift
@MainActor
func prefillBundledItemsIfNeeded(modelContext: ModelContext) {
    let currentHash = hashOfBundledDefinitions()
    let storedHash = UserDefaults.standard.string(forKey: "bundledItemsHash")
    guard currentHash != storedHash else { return }

    deleteAllBundledItems(in: modelContext)
    insertFreshBundledItems(into: modelContext)
    try? modelContext.save()
    UserDefaults.standard.set(currentHash, forKey: "bundledItemsHash")
}
```

Trade-off: the hash must be stable across launches — sort keys and encode
deterministically (see `hashOfBundledDefinitions()` above).

## User-Content Migration (VersionedSchema + SchemaMigrationPlan)

When the data belongs to the user, deleting and regenerating loses their work.
Instead, describe each schema version and how to move between them, then hand
the plan to the container.

**1. Freeze each schema as a `VersionedSchema`.**

```swift
enum SchemaV1: VersionedSchema {
    static var versionIdentifier = Schema.Version(1, 0, 0)
    static var models: [any PersistentModel.Type] { [Item.self] }

    @Model final class Item {
        var name: String = ""
        init(name: String) { self.name = name }
    }
}

enum SchemaV2: VersionedSchema {
    static var versionIdentifier = Schema.Version(2, 0, 0)
    static var models: [any PersistentModel.Type] { [Item.self] }

    @Model final class Item {
        var givenName: String = ""
        var familyName: String = ""
        init(givenName: String, familyName: String) {
            self.givenName = givenName
            self.familyName = familyName
        }
    }
}
```

**2. Describe the migration with a `SchemaMigrationPlan`.**

- `.lightweight` handles purely additive/renaming changes SwiftData can infer.
- `.custom` runs `willMigrate` / `didMigrate` for transforms it can't (here,
  splitting `name` into `givenName` / `familyName`).

```swift
enum ItemMigrationPlan: SchemaMigrationPlan {
    static var schemas: [any VersionedSchema.Type] { [SchemaV1.self, SchemaV2.self] }
    static var stages: [MigrationStage] { [migrateV1toV2] }

    static let migrateV1toV2 = MigrationStage.custom(
        fromVersion: SchemaV1.self,
        toVersion: SchemaV2.self,
        willMigrate: { context in
            for old in try context.fetch(FetchDescriptor<SchemaV1.Item>()) {
                let parts = old.name.split(separator: " ", maxSplits: 1)
                context.insert(SchemaV2.Item(
                    givenName: parts.first.map(String.init) ?? old.name,
                    familyName: parts.count > 1 ? String(parts[1]) : ""
                ))
                context.delete(old)
            }
            try context.save()
        },
        didMigrate: nil
    )
}
```

For a purely additive change (new optional property), swap the whole stage for
`MigrationStage.lightweight(fromVersion:toVersion:)` — no closures needed.

**3. Wire the plan into the container.**

```swift
let container = try ModelContainer(
    for: SchemaV2.Item.self,
    migrationPlan: ItemMigrationPlan.self
)
```

Heavy migrations should run off the main actor — drive `willMigrate` work from a
`ModelActor`; defer actor mechanics to `swift-concurrency`.

Apple docs:
[VersionedSchema](https://developer.apple.com/documentation/swiftdata/versionedschema),
[SchemaMigrationPlan](https://developer.apple.com/documentation/swiftdata/schemamigrationplan),
[MigrationStage](https://developer.apple.com/documentation/swiftdata/migrationstage).

## Testing the upgrade path

A passing fresh install proves nothing — the bug lives in the *transition*.
Reproduce it:

1. Check out the **previous** release, build, run, create/seed data, quit.
2. Without wiping the store, check out the **new** build, run.
3. Confirm the migrated data is present and correct. If it isn't, the migration
   stage — not the fresh path — is where to look.

Last verified: 2026-07-04.
