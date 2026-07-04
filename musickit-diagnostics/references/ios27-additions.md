# iOS 27 / 26.4 MusicKit additions (diagnostics)

Two MusicKit surfaces added in the 2026 OS cycle are failure-prone enough to
warrant diagnostic coverage in an iOS app. Everything else demonstrated at
WWDC 2026 (session 254) — `ApplicationMusicPlayer` / `SystemMusicPlayer`,
`MusicSubscription`, `.musicSubscriptionOffer`, `MusicCatalogResourceRequest`,
authorization — is **pre-existing** (`.musicSubscriptionOffer` is iOS 15+, not
new). This file covers only the two genuinely new/failure-prone items.

## Contents

- [Music Picker (iOS 27)](#music-picker-ios-27)
- [`findEquivalents` partial results (26.4+)](#findequivalents-partial-results-264)

## Music Picker (iOS 27)

`musicPicker(isPresented:title:selection:)` presents a system sheet for
picking catalog/library music. Genuinely new in the iOS 27 cycle.

```swift
@MainActor @preconcurrency
func musicPicker<Selection>(
    isPresented: Binding<Bool>,
    title: Text? = nil,
    selection: Binding<MusicItemCollection<Selection>>
) -> some View where Selection : PickableMusicItem
```

Three failure modes:

1. **`@MainActor` only.** The modifier is `@MainActor @preconcurrency`. Present
   it from main-actor context; driving `isPresented` off the main actor does
   nothing (or traps).
2. **Empty selection on cancel.** `selection` is a
   `MusicItemCollection<Selection>`, **not** an optional. On cancel or no-pick
   it is an **empty collection**, not `nil`. Handle the empty case; never
   force-unwrap `selection.first`. Single-select is just a one-element
   collection.
3. **`PickableMusicItem` conforms to `Song`, `Track`, `MusicVideo` only** — not
   `Album`, not `Playlist`. You cannot bind `selection` to `Album`/`Playlist`;
   picking a container yields its tracks. This is a compile-time / design
   constraint, not a runtime bug.

**Availability.** iOS / iPadOS / Mac Catalyst 27.0+ (also visionOS 27 —
metadata only; not a support target here). **No native macOS** — a Mac target
reaches the picker only via Mac Catalyst, and **no tvOS / watchOS**. Gate with
`if #available(...)`. For the native-macOS story, see the `apple-multiplatform`
skill; this skill stays iOS-scoped.

## `findEquivalents` partial results (26.4+)

`.findEquivalents` on a catalog resource request maps IDs to the **current
storefront** (region + clean/explicit variants). Shipped in **26.4** on all
platforms — **not** an iOS 27 API.

```swift
var request = MusicCatalogResourceRequest<Song>(matching: \.id, memberOf: songIDs)
request.options = [.findEquivalents]
let response = try await request.response()

// CORRECT: the response may omit IDs unavailable in this storefront.
let songs = songIDs.compactMap { response.item(for: $0) }   // not .map
```

**The trap: silent partial results, no thrown error.** The response is **not
guaranteed to contain every requested ID**. `response.item(for: id)` returns
`nil` for any ID that has no equivalent in the current storefront, and the call
**does not throw** for missing items — it throws only the usual
`MusicDataRequest.Error` on transport/auth failure. So:

- Do **not** assume `response.items.count == requestedIDs.count`.
- Iterate with `compactMap` / nil-checks, never force-unwrap `item(for:)`.
- A shorter-than-expected result with no error is the storefront mismatch, not
  a bug in your code.

## Sources

- [WWDC 2026 session 254 — Integrate MusicKit into your app](https://developer.apple.com/videos/play/wwdc2026/254/)
- [`musicPicker(isPresented:title:selection:)`](https://developer.apple.com/documentation/swiftui/view/musicpicker(ispresented:title:selection:))
- [`PickableMusicItem`](https://developer.apple.com/documentation/MusicKit/PickableMusicItem)
- [`MusicCatalogResourceRequestOption.findEquivalents`](https://developer.apple.com/documentation/MusicKit/MusicCatalogResourceRequestOption/findEquivalents)
