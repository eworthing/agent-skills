# Internal Reorder (SDK 27): `reorderable()` vs DropDelegate

For **same-app** drag-to-reorder on SDK 27 targets, use `reorderable()` /
`reorderContainer(for:)` instead of a hand-rolled `DropDelegate` reorder chain.
The rest of the parent skill (priority routing, payload extraction) remains for
*external* pasteboard payloads; when reorder coexists with external drop handlers,
the parent skill's priority rules still govern the external targets.

SDK 27 adds first-class drag-to-reorder for **any** container (`List`,
`LazyVStack`, `LazyVGrid`, stacks, custom layouts) — no longer `List`-only.

**Availability:** iOS / macOS / watchOS / visionOS 27; **tvOS unavailable**. The
examples reference SDK-27-only symbols, so they require the **Xcode 27 SDK to
compile**; use `if #available(iOS 27, *)` to support older deployment targets, and
keep the existing `#if !os(tvOS)` gate.

## Two cooperating modifiers

`.reorderable()` goes on the `ForEach` (it's declared on `DynamicViewContent`);
`.reorderContainer(for:move:)` goes on the container. The full label set is
`reorderContainer(for:isEnabled:move:)` — `isEnabled:` defaults to `true` and is
the built-in per-container enable gate (no need to conditionally omit the modifier).
The `move` closure receives a `ReorderDifference` you apply to your own data:

```swift
ScrollView {
    LazyVGrid(columns: columns) {
        ForEach(stickers) { StickerView($0) }
            .reorderable()
    }
    .reorderContainer(for: Sticker.self) { difference in
        difference.apply(to: &stickers)   // mutate your @State collection
    }
}
```

`apply(to:)` is **your** helper, not SDK-provided (the SDK ships no `apply` on
`ReorderDifference`). Implement it from the type's public members:

- `difference.sources: [Item.ID]` — the items being moved.
- `difference.destination.position` — a `ReorderDifference.Destination.Position`
  enum with exactly two cases: `.before(id)` (insert ahead of that item) and
  `.end` (append).
- `difference.destination.collectionID` — which collection, for the multi-collection
  overloads (below).

So `apply(to:)` moves `difference.sources` within your collection to the slot named
by `difference.destination.position`.

## Overloads

- `Item` must be `Identifiable` for the `for:` overload (keys on `\.id`); otherwise
  use `reorderContainer(for:itemID:)` with a key path.
- **Sections / multiple collections:** tag each `ForEach` with
  `.reorderable(collectionID:)` and declare the id type on the container with
  `reorderContainer(for:in:)`; route via `difference.destination.collectionID`.

Verified label sets (Xcode 27.0, build 27A5194q): `reorderContainer(for:isEnabled:move:)`,
`reorderContainer(for:in:isEnabled:move:)`, `reorderContainer(for:itemID:isEnabled:move:)`,
`reorderContainer(for:itemID:in:isEnabled:move:)`.

## Customizing beyond plain reorder

`reorderContainer(for:)` **already acts as a drag container and drop destination**,
so plain reorder works with no extra drop code. Customize only when needed:

| Need | Add |
|---|---|
| Same-app reorder | `reorderable()` + `reorderContainer(for:)` (nothing else) |
| Custom drag payload / drag-out to other apps | `.dragContainer(for:)` on the container (a bare `.draggable` does **not** customize it) |
| Drop one item onto another (combine) | `.dropDestination(for:isEnabled:)` on each child |
| Accept a drop at the reorder position | `.dropDestination(for:)` on container + `session.reorderDestination(for:)` |
| Accept **external** pasteboard payloads | the parent skill's `DropDelegate` priority architecture |

`session.reorderDestination(for:in:)` is declared on `DropSession` and returns a
`ReorderDifference.Destination?` — the reorder slot the drop currently targets, or
`nil`. The `in:` collection-id argument defaults to the single-collection identifier.

## Critical overload pitfall

For drop-to-combine use the void overload
`dropDestination(for:isEnabled:) { items, session in … }`, and put the per-item
predicate in `isEnabled:` (SwiftUI calls the closure only when it's true; it draws
the target/gap for you). Do **not** use the legacy
`dropDestination(for:) { … } isTargeted: { … }` overload — it reports hover state
for custom feedback, returns `Bool`, and does **not** gate combining. Picking it is
the common mistake.
