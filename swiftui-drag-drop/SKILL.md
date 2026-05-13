---
name: swiftui-drag-drop
author: eworthing
description: >-
  SwiftUI drag-and-drop architecture for iOS, iPadOS, and macOS — covers
  DropDelegate vs `.onDrop`, drop-priority routing across overlapping
  handlers, multi-provider payload extraction, NSItemProvider lifecycle
  rules, Chrome image-drag compatibility (`public.tiff` / `public.html` /
  `public.url`), Button drop-attachment pitfalls, and tvOS gating. Use when
  implementing drag-drop, working with DropDelegate, onDrop, NSItemProvider,
  UTType drop types, drop priority, drop handler conflicts, drop validation,
  payload extraction, multi-provider drops, Chrome image drag, image drops,
  internal item moves, drop target highlighting, or fixing "wrong handler
  catches drop" bugs.
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - Glob
  - Grep
---

# SwiftUI Drag & Drop

## Purpose

This skill owns SwiftUI **drop-receiving architecture** — choosing between
`DropDelegate` and `.onDrop(of:isTargeted:perform:)`, routing drops
correctly when multiple handlers overlap on screen, extracting the best
payload from a heterogeneous `[NSItemProvider]`, and respecting Apple's
`NSItemProvider` lifecycle rules.

**Platforms:** iOS 16+, iPadOS 16+, macOS 13+. tvOS has no drop-receiving
API — all receiving code must be platform-gated.

## When to Use

- Implementing a new drop target (card, row, sidebar, background).
- Multiple drop handlers stack on the same hit area and the wrong one wins.
- Drops from Safari succeed but the same drag from Chrome fails.
- An `NSItemProvider` completion handler crashes or doesn't update UI.
- Adding a new payload type (image data, file URL, plain URL, HTML).
- Auditing whether `.onDrop` is attached to the right view.

## Do NOT Use For

- tvOS — no drop receiving exists; skip the feature.
- `Transferable` / `.dropDestination(for:)` model-typed drops where you
  already control both source and destination — that API is simpler and
  doesn't need this skill. Use this skill when you must accept *external*
  pasteboard payloads (browser drags, Finder, Photos).
- macOS `NSPasteboard` paste shortcuts — different surface.

## Architecture: DropDelegate vs `.onDrop`

| Need | Use |
|---|---|
| Single payload type, no UI feedback on enter/exit | `.onDrop(of:isTargeted:perform:)` |
| Custom highlight, hover preview, or per-target validation | `DropDelegate` |
| Multiple overlapping drop handlers with priority | `DropDelegate` (mandatory — `.onDrop` cannot suppress) |
| Need to inspect `DropInfo` before committing | `DropDelegate` |

Once any target on screen needs priority routing, **all** participating
targets must be `DropDelegate`. Mixing `.onDrop` callbacks with
`DropDelegate` makes priority undefined.

## Drop Priority (Winner-Take-All)

When multiple drop handlers cover the same hit area, SwiftUI delivers the
drop to the topmost target whose `validateDrop` returns `true`. Encode
priority by suppressing lower-priority handlers in their own
`validateDrop`:

```
Example priority chain (highest first):
1. Internal-move handler on a leaf view  (e.g. reorder)
2. Image-replace handler on a card
3. Item-create handler on a list row
4. Fallback handler on background / empty space
```

**Critical rule:** suppression belongs in `validateDrop`, **never** in
`performDrop`. Returning `false` from `performDrop` after `validateDrop`
already accepted the drop yields a "ghost" drop (visual accept,
no-op result) and breaks Apple's contract.

The lower-priority handler must read shared targeting state (set by
higher-priority handlers in `dropEntered` / `dropExited`) and reject in
`validateDrop` when a higher-priority sibling is currently targeted.

## DropDelegate Skeleton

Use a small shared targeting model so handlers can suppress each other:

```swift
@MainActor
@Observable
final class DropRouter {
    var imageTargetID: String?     // set by ItemDropDelegate
    var rowTargetID: String?       // set by BinDropDelegate
}
```

### Leaf (highest priority) — image replace on an item

```swift
struct ItemDropDelegate: DropDelegate {
    let itemID: String
    let router: DropRouter
    let acceptedTypes: [UTType]
    @Binding var isTargeted: Bool

    func validateDrop(info: DropInfo) -> Bool {
        info.hasItemsConforming(to: acceptedTypes)
    }

    func dropEntered(info: DropInfo) {
        withAnimation(.easeInOut(duration: 0.15)) { isTargeted = true }
        router.imageTargetID = itemID
    }

    func dropExited(info: DropInfo) {
        withAnimation(.easeInOut(duration: 0.15)) { isTargeted = false }
        if router.imageTargetID == itemID { router.imageTargetID = nil }
    }

    func performDrop(info: DropInfo) -> Bool {
        let providers = info.itemProviders(for: acceptedTypes)
        guard !providers.isEmpty else { return false }
        Task {
            let payload = await DropPayloadExtractor.extract(from: providers)
            await MainActor.run { /* apply payload */ }
        }
        return true   // accept now; finish async
    }
}
```

### Mid-priority — create item on a row, suppressed by leaf

```swift
func validateDrop(info: DropInfo) -> Bool {
    // Always allow internal moves
    if info.hasItemsConforming(to: internalTypes) { return true }
    // Suppress if a higher-priority leaf is currently targeted
    guard router.imageTargetID == nil else { return false }
    return info.hasItemsConforming(to: externalTypes)
}
```

### Fallback — background handler, never internal moves

```swift
func validateDrop(info: DropInfo) -> Bool {
    if info.hasItemsConforming(to: internalTypes) { return false }
    guard router.imageTargetID == nil else { return false }
    guard router.rowTargetID == nil else { return false }
    return info.hasItemsConforming(to: externalTypes)
}
```

## NSItemProvider Lifecycle Rules

These are Apple requirements, not stylistic choices:

1. **Start `NSItemProvider` loading inside `performDrop`** — never in
   `validateDrop` or `dropEntered`. The provider's data isn't guaranteed
   to be available until the drop is performed.
2. **Return `true` from `performDrop` as soon as you've kicked off async
   loading.** Returning `false` cancels the drop animation. The async
   work continues; surface failures via UI state, not the return value.
3. **Hop to `@MainActor` before touching observable state** in
   `loadItem`/`loadDataRepresentation` completion handlers. They run on
   a background queue.
4. **Capture providers by value** — they are reference types but the
   pasteboard backing store may be released; load on a `Task` you own.

```swift
provider.loadDataRepresentation(forTypeIdentifier: UTType.image.identifier) { data, _ in
    guard let data else { return }
    Task { @MainActor in
        model.apply(imageData: data)
    }
}
```

## Payload Extraction Across Providers

A single drop may deliver multiple `NSItemProvider` instances, each
advertising several UTTypes. Don't pick the first match — walk a priority
list and pick the **best** payload across all providers.

```swift
enum DroppedPayload: Sendable {
    case internalID(String)
    case imageData(Data, fileExtension: String?)
    case url(URL)
    case text(String)
}

enum DropPayloadExtractor {
    /// Priority (best → fallback):
    ///   1. internal-move UTType  (own custom type)
    ///   2. public.html           (Chrome — parse for img src, og:image, data: URLs)
    ///   3. public.tiff           (Chrome image drags)
    ///   4. public.image          (Safari, Finder; prefer file URL over data)
    ///   5. public.url            (link drops)
    ///   6. public.file-url       (Finder file drops)
    ///   7. public.plain-text     (last resort)
    static func extract(from providers: [NSItemProvider]) async -> DroppedPayload? {
        // Try each tier in order; return the first tier that yields a payload.
        // Within a tier, try every provider before moving to the next tier.
        ...
    }
}
```

Keep the extractor pure-ish: take `[NSItemProvider]`, return
`DroppedPayload?`. No view-model coupling, no global state. This is the
piece you'll unit-test.

## Chrome / Cross-Browser Image-Drag Compatibility

Browser image drags surface different UTTypes:

| UTType | Safari | Chrome | Firefox | Notes |
|---|---|---|---|---|
| `public.image` | reliable | rare | sometimes | Preferred when present |
| `public.tiff` | sometimes | reliable | sometimes | Chrome's primary image surface |
| `public.html` | reliable | reliable | reliable | Parse for `<img src>`, `srcset`, `og:image`, `data:` URLs |
| `public.url` | reliable for links | unreliable for images | unreliable for images | Often points at the page, not the image |
| `public.file-url` | drag from Finder only | n/a | n/a | |

**Practical rule:** parse `public.html` *before* trying `public.tiff`.
HTML extraction gives you a real image URL you can fetch with proper
caching; the TIFF blob is opaque and large.

A minimal HTML parser only needs to find the first `<img …>` element and
read its `src` (and `srcset`, picking the largest candidate).

## View Attachment: Don't Attach Drops Directly to `Button`

`Button` consumes drop events on some platforms. Attach `.onDrop` to a
wrapper that owns the hit area:

```swift
struct ItemCard: View {
    let item: Item
    @State private var isTargeted = false

    var body: some View {
        Button { open(item) } label: { content }
            .buttonStyle(.plain)
            .contentShape(.rect)                     // explicit hit shape
            #if !os(tvOS)
            .onDrop(
                of: acceptedTypes,
                delegate: ItemDropDelegate(
                    itemID: item.id,
                    router: router,
                    acceptedTypes: acceptedTypes,
                    isTargeted: $isTargeted
                )
            )
            #endif
            .overlay {
                if isTargeted {
                    RoundedRectangle(cornerRadius: 8)
                        .stroke(.tint, lineWidth: 3)
                        .allowsHitTesting(false)     // don't steal hit-testing
                }
            }
    }
}
```

Key points:

- `.contentShape(.rect)` makes the entire frame draggable-onto, not just
  opaque pixels.
- The targeting overlay uses `.allowsHitTesting(false)` so it never
  intercepts subsequent drops.
- Drop attachment lives on the wrapper, not on `Button`'s label.

## Platform Gating

tvOS has no drop-receiving API. Every `.onDrop` and every `DropDelegate`
conformance must be gated:

```swift
#if !os(tvOS)
.onDrop(of: acceptedTypes, delegate: delegate)
#endif
```

Compile a tvOS build locally before declaring drop work done — `#if`
mistakes don't surface in an iOS-only build.

## Debugging Drop Types

When a drop is silently ignored, the registered types almost always
reveal why. Log them at the top of `performDrop`:

```swift
#if DEBUG
let typeIDs = info.itemProviders(for: [.item])
    .flatMap(\.registeredTypeIdentifiers)
print("Drop types:", typeIDs)
#endif
```

Common diagnoses:

- Empty array → drag source didn't promise any UTTypes; usually a custom
  in-app drag that forgot to register a type.
- Only `dyn.…` types → opaque provider with no public conformance;
  unsupported.
- Has `public.html` but no `public.image` → browser drag; route through
  the HTML parser.

## Undo Semantics

- **Replace image (single mutation):** one undo step using your existing
  per-item mutation machinery.
- **Create N items from one drop:** finalize as one atomic undo group.
  Open the group before the first insert, close after the last; do not
  emit one undo step per item.

## Constraints

- `validateDrop` is the only place to encode priority suppression.
- `performDrop` must return `true` if you accept; do async work after.
- Start `NSItemProvider` loading **inside** `performDrop`, not earlier.
- Hop to `@MainActor` before touching observable state in completion
  handlers.
- Background/fallback handlers must reject internal-move UTTypes.
- All drop-receiving code is gated `#if !os(tvOS)`.
- Don't attach `.onDrop` directly to `Button` — use a wrapper with
  `.contentShape(.rect)`.
- The payload extractor should be pure: providers in, payload out, no
  global state.
