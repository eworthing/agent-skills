# iOS 27 / 26.4 MusicKit additions (diagnostics)

Two MusicKit surfaces added in the 2026 OS cycle are failure-prone enough to
warrant diagnostic coverage in an iOS app. Everything else demonstrated at
WWDC 2026 (session 254) — `ApplicationMusicPlayer` / `SystemMusicPlayer`,
`MusicSubscription`, `.musicSubscriptionOffer` (including
`MusicSubscriptionOffer.Options` and its `messageIdentifier`),
`MusicCatalogResourceRequest`, authorization — is **pre-existing**
(`.musicSubscriptionOffer` and `MusicSubscriptionOffer.Options` are iOS 15+, not
new; the session re-teaches them rather than introducing them). This file covers
only the two genuinely new/failure-prone items.

Surface re-verified against canonical DocC **2026-07-14**: `PickableMusicItem` is
the *only* Beta symbol in the whole MusicKit framework, and `findEquivalents` is
the only other 2026-cycle addition — so these two are the complete new surface, not
a sample of it.

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

Four failure modes:

1. **`@MainActor` only.** The modifier is `@MainActor @preconcurrency`. Present
   it from main-actor context; driving `isPresented` off the main actor does
   nothing (or traps).
2. **Empty selection on cancel.** `selection` is a
   `MusicItemCollection<Selection>`, **not** an optional. On cancel or no-pick
   it is an **empty collection**, not `nil`. Handle the empty case; never
   force-unwrap `selection.first`. Single-select is just a one-element
   collection.
3. **The binding is yours, and it persists — don't assume replace-semantics.**
   `selection` is a collection you own across presentations, not a fresh result
   handed back per sheet. Apple's own sample treats it as accumulating: it diffs
   counts across changes rather than reading a new selection —

   ```swift
   .onChange(of: selectedSongs) { oldValue, newValue in
       let delta = newValue.count - oldValue.count
       print("You selected \(delta) new tracks!")
   }
   ```

   So a stale collection is still populated the next time you present the picker.
   Clear or pre-populate it deliberately, and derive "what did the user just pick"
   from a diff rather than assuming the picker replaced the contents. (Observed
   from the documented sample's shape — Apple does not spell the semantics out,
   so verify against your own seed before depending on it.)
4. **`PickableMusicItem` conforms to `Song`, `Track`, `MusicVideo` only** — not
   `Album`, not `Playlist`. You cannot bind `selection` to `Album`/`Playlist`;
   picking a container yields its tracks. This is a compile-time / design
   constraint, not a runtime bug. (Note the contrast with `MusicPlaylistAddable`,
   where `Album` *does* conform — see `library-playlists.md`. Pickable ≠ addable.)

**Availability.** iOS / iPadOS / visionOS **27.0+, Beta** — for both
`musicPicker(...)` and `PickableMusicItem` (verified against canonical DocC
2026-07-14).

**Not available on Mac Catalyst, macOS, tvOS, or watchOS.** The DocC availability
array lists those three platforms and no others. That omission is real rather than
a documentation gap: `findEquivalents` below *does* list Mac Catalyst explicitly,
so DocC does surface Catalyst when an API supports it. Do not assume a Mac target
reaches this picker via Catalyst — it does not exist there. (`apple-multiplatform`
remains the skill for macOS/Catalyst MusicKit deltas generally, but it has no
picker story to tell.)

Gate with `if #available(iOS 27, *)`. visionOS 27 shares the API; this skill stays
iOS-scoped. Because the API is **Beta**, re-check availability against live DocC
before relying on it — beta metadata shifts between seeds.

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
