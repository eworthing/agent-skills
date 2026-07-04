# Modern SwiftData APIs (iOS 18–27)

Worked patterns for the newer SwiftData surface, deferred from `SKILL.md`'s
availability table. Verify every floor against Apple's docs before relying on it;
the iOS 27 rows are **beta**. Last verified: 2026-07-04.

## Contents

- Auto-Save Task
- Uniqueness: `@Attribute(.unique)` and `#Unique`
- Indexes: `#Index`
- History Tracking (iOS 18)
- Model Inheritance (iOS 26)
- ResultsObserver (iOS 27, beta)
- Custom DataStore (iOS 18)

## Auto-Save Task

A `@MainActor` task that wakes on a 30-second interval and saves only when
`hasChanges`. Throws are swallowed with a log — auto-save should never crash the
app.

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

## Uniqueness: `@Attribute(.unique)` and `#Unique`

`@Attribute(.unique)` (iOS 17) enforces uniqueness on a **single** attribute and
turns an insert with a colliding key into an **upsert** (update-in-place) rather
than a duplicate — the clean way to make Pattern 1's seed reinsert idempotent
without a delete pass.

```swift
@Model
final class BundledItemEntity {
    @Attribute(.unique) var slug: String
    var title: String
    init(slug: String, title: String) { self.slug = slug; self.title = title }
}
```

`#Unique` (iOS 18) declares **compound** uniqueness across several attributes,
including combinations:

```swift
@Model
final class Person {
    #Unique<Person>([\.id], [\.givenName, \.familyName])
    var id: UUID
    var givenName: String
    var familyName: String
    init(id: UUID, givenName: String, familyName: String) {
        self.id = id; self.givenName = givenName; self.familyName = familyName
    }
}
```

Docs: [Attribute](https://developer.apple.com/documentation/swiftdata/attribute(_:originalname:hashmodifier:)),
[Unique(_:)](https://developer.apple.com/documentation/swiftdata/unique(_:)).

## Indexes: `#Index`

`#Index` (iOS 18) defines single or compound indexes so `#Predicate` fetches and
sorts on those key-paths stay fast as the store grows. Index the columns you
actually filter/sort on — not every property.

```swift
@Model
final class BundledItemEntity {
    #Index<BundledItemEntity>([\.sourceRaw], [\.sourceRaw, \.createdAt])
    var sourceRaw: String
    var createdAt: Date
    // ...
}
```

Docs: [Index(_:)](https://developer.apple.com/documentation/swiftdata/index(_:)-74ia2).

## History Tracking (iOS 18)

`fetchHistory(_:)` / `deleteHistory(_:)` expose the store's persistent
transaction log — the basis for syncing to a server, computing deltas, or
building undo. Fetch transactions since a saved token, process them, then prune.

```swift
let descriptor = HistoryDescriptor<DefaultHistoryTransaction>()
let transactions = try modelContext.fetchHistory(descriptor)
for tx in transactions {
    for change in tx.changes { /* apply / diff */ }
}
// Prune everything up to the last processed token:
if let token = transactions.last?.token {
    try modelContext.deleteHistory(.before(token))
}
```

Docs: [fetchHistory(_:)](https://developer.apple.com/documentation/swiftdata/modelcontext/fetchhistory(_:)).

## Model Inheritance (iOS 26)

The `@Model` macro supports class inheritance — factor shared attributes into a
base `@Model` and subclass it. Fetching the base type returns instances of all
subclasses; use `#Predicate` type checks to narrow.

```swift
@Model class MediaItem {
    var title: String = ""
    var createdAt: Date = .now
}

@Model final class Movie: MediaItem {
    var runtimeMinutes: Int = 0
}
```

Docs: [Model()](https://developer.apple.com/documentation/swiftdata/model()).

## ResultsObserver (iOS 27, beta)

`ResultsObserver` gives you an `@Observable` collection of fetched models that
stays live — the `@Query` behavior, but usable **outside** a SwiftUI view (view
models, services). Supply a `FetchDescriptor` or inline filter/sort; use `Never`
as the section type when you don't need sectioning.

```swift
let observer = try ResultsObserver<BundledItemEntity, Never>(
    filterBy: #Predicate { $0.sourceRaw == "bundled" },
    sortBy: [SortDescriptor(\.createdAt, order: .reverse)],
    modelContext: context
)
// observer.results updates as the store changes; observe from any @Observable consumer.
```

Its sibling `HistoryObserver` (also iOS 27 beta) watches for remote/CloudKit
history changes via an `eventCounter`. Docs:
[ResultsObserver](https://developer.apple.com/documentation/swiftdata/resultsobserver),
[HistoryObserver](https://developer.apple.com/documentation/swiftdata/historyobserver).

## Custom DataStore (iOS 18)

Adopt the `DataStore` protocol (and `DataStoreBatching` / `HistoryProviding`) to
back a `@Model` with storage other than the default SQLite — a JSON file, an
in-memory cache, or a server mirror — while keeping the `ModelContext` API. This
is advanced; reach for it only when the default store genuinely doesn't fit.

Docs: [DataStore](https://developer.apple.com/documentation/swiftdata/datastore).
