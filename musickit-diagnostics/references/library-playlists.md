# Library Playlist Creation (MusicLibrary)

Creating a playlist in the user's Apple Music library — so it appears
under **Library → Playlists** in the Music app — uses MusicKit's
`MusicLibrary` wrapper around the Apple Music API endpoints
[Create a New Library Playlist](https://developer.apple.com/documentation/applemusicapi/create-a-new-library-playlist)
and [Add Tracks to a Library Playlist](https://developer.apple.com/documentation/applemusicapi/add-tracks-to-a-library-playlist).
This is **different** from `MusicLibrary.shared.add(_:)` (which adds a
single item to the library) and from `ApplicationMusicPlayer.queue =
[...]` (which only plays in-app and does not persist anywhere).

The general `musickit` skill covers basic `MusicLibrary.shared.add(_:)`.
This file covers the playlist-creation path specifically, plus the
failure modes that recur there.

## Contents

- [API choice (iOS 16+)](#api-choice-ios-16)
- [The catalog-identifier rule](#the-catalog-identifier-rule)
- [Failure walkthrough: empty identifier set + -7013](#failure-walkthrough-empty-identifier-set---7013)
- [Pre-call checklist](#pre-call-checklist)
- [Post-success handoff](#post-success-handoff)

## API choice (iOS 16+)

```swift
import MusicKit

func saveSelectionToLibrary(name: String, songs: [Song]) async throws -> Playlist {
    // 1. Create the empty playlist in the user's library.
    let playlist = try await MusicLibrary.shared.createPlaylist(
        name: name,
        description: nil,
        authorDisplayName: nil
    )

    // 2. Add each song one by one. Song, Track, and Album all conform to
    //    MusicPlaylistAddable — the failure below is a *runtime* empty
    //    identifier set, not a compile-time conformance gap. Pass
    //    catalog-fetched Songs (see below).
    for song in songs {
        try await MusicLibrary.shared.add(song, to: playlist)
    }

    return playlist
}
```

Requirements (same as catalog search):

- `MusicAuthorization.request()` must have returned `.authorized` before this method runs
- The device user must be signed into Apple Music with an active subscription
- iOS 16 or later

There may be a short delay (a few seconds) before the new playlist
appears in the Music app's Library → Playlists. That is normal — the API
returns success once the create call commits server-side, but the Music
app's local cache refreshes asynchronously.

## The catalog-identifier rule

`MusicLibrary.shared.add(_:to:)` accepts any `MusicPlaylistAddable` — per
Apple's own conformance list that's `Album`, `MusicVideo`, `Playlist`,
`Playlist.Entry`, `Song`, **and `Track`**. Conformance is **not** the issue;
a populated identifier set is. The rule is about *provenance*, not the
Swift type: pass items that trace back to a catalog fetch. That includes a
`Song` from `MusicCatalogSearchRequest` **and** a `Track` obtained via a
catalog `Album`'s `.tracks` relationship — both carry a populated
`MPIdentifierSet` because both originate from the catalog. There is no need
to unwrap a `Track` into a `Song` before adding it; `Track` is a first-class,
directly-addable item, not a lesser stand-in for `Song`.

Passing the **bare `Album` container itself** (or any hand-built item)
instead of its resolved contents is what fails in the field-observed
incident this section is sourced from. Apple's own docs don't document
*why* — `Album` is a listed `MusicPlaylistAddable` conformer, so this isn't
a conformance gap, and the exact mechanism behind the empty-identifier-set
log is not publicly documented. Treat it as an observed, not documented,
failure mode and prefer resolved items:

```swift
// CORRECT — Song from a direct catalog search:
var request = MusicCatalogSearchRequest(term: query, types: [Song.self])
let response = try await request.response()
for song in response.songs {
    try await MusicLibrary.shared.add(song, to: playlist)
}

// ALSO CORRECT — Track from a catalog Album's tracks relationship.
// No need to unwrap to Song first; Track conforms to MusicPlaylistAddable
// and carries its own populated identifier set here because `album` itself
// came from the catalog.
let detailedAlbum = try await album.with(.tracks)
guard let tracks = detailedAlbum.tracks else { return }
for track in tracks {
    try await MusicLibrary.shared.add(track, to: playlist)
}

// WRONG (observed, not documented): passing the Album container itself.
// Album does conform to MusicPlaylistAddable, so this isn't a compile-time
// error — but in field testing it silently no-op'd with an empty
// MPIdentifierSet log. Apple doesn't document why; prefer the resolved
// Song/Track items above instead of relying on this working.
try await MusicLibrary.shared.add(album, to: playlist)
```

**Why.** A library playlist entry needs a valid catalog or library
identifier. `Song` and `Track` instances that trace back to a catalog
fetch (a direct search, or a relationship fetch off a catalog-sourced
parent) carry a populated `MPIdentifierSet`. Items **not** fetched from a
catalog request — hand-constructed from `title`/`artistName` display
strings, or the `Album` container passed directly instead of its resolved
tracks — have an empty identifier set, even when their fields look fine to
a human reader. The framework will log

```
No catalogID, libraryID, or deviceLocalID was found from underlying
identifier set <MPIdentifierSet EMPTY>. A MusicIdentifierSet with empty
string, for type ... Album
```

and the add silently does nothing.

## Failure walkthrough: empty identifier set + -7013

Two error signatures appear together when this fails:

1. Console: `No catalogID, libraryID, or deviceLocalID was found …  MPIdentifierSet EMPTY … type … Album`
2. Catch block: `ICError Code=-7013 "Client is not entitled to access account store"`

Three root causes, ranked by frequency:

**1. Passing the bare container (most common).** Code is passing an
`Album` (or a hand-built item) directly instead of its resolved contents.
Fix: either search with `types: [Song.self]` and iterate `response.songs`,
or fetch `album.with(.tracks)` and iterate its `tracks` — add each `Song`
or `Track` individually. Both are catalog-sourced and equally valid; there
is no need to convert a `Track` into a `Song`.

**2. Simulator.** Library playlist creation and account-store touches do
not work reliably on the iOS Simulator regardless of code correctness.
Fix: run on a physical device with the same bundle ID, signed into Apple
Music.

**3. Bundle ID without MusicKit capability.** The bundle ID being
installed on the device is not registered with MusicKit in your Apple
Developer account. Fix: see `bundle-id-setup.md`.

A third symptom sometimes shows up next to these: `applicationQueuePlayer
_establishConnectionIfNeeded timeout [ping did not pong]`. That points
at audio session contention — typically a Speech-framework recording tap
still active. Fix: see `speech-coexistence.md`. The save itself usually
still succeeded; only the immediately-following playback failed.

## Pre-call checklist

Run through these in order before suspecting an SDK bug:

1. **Authorization** — `MusicAuthorization.request()` returned `.authorized` and the result is stored in a view-model flag (e.g. `isAuthorized`) gating the save button.
2. **Source items are catalog-sourced `Song` or `Track` instances** — either from `MusicCatalogSearchRequest(types: [Song.self])` directly, or from a catalog `Album`'s resolved `.tracks` relationship. Not the bare `Album` container itself. Not constructed from display strings. Not from `MusicLibraryRequest` either (those are library items; they have a `libraryID` but no `catalogID` — the API can usually still add them, but mixing sources is a frequent source of empty-identifier-set logs).
3. **Real device, not Simulator.**
4. **Bundle ID registered with MusicKit capability** (`bundle-id-setup.md`).
5. **Device signed into Apple Music** with an active subscription. Confirm in Settings → Music.
6. **Speech recognizer stopped** before this call runs, if the app also captures voice input (`speech-coexistence.md`).

If all six are green and the call still fails, inject the diagnostic
snippet from `error-codes.md` to capture the exact domain/code.

## Post-success handoff

After a successful save, **do not block the success UX with playback
errors**. If you call `ApplicationMusicPlayer.shared.play()` right after
saving and it returns `MPMusicPlayerControllerErrorDomain` error 1, that
is a separate hiccup (see `error-codes.md`). The save already worked.

Pattern for handing the user off to the Music app:

```swift
let playlist = try await saveSelectionToLibrary(name: name, songs: songs)
statusMessage = "Playlist “\(name)” added to your library."

// Optional: try in-app playback, but don't error-out the save UX if it fails.
do {
    ApplicationMusicPlayer.shared.queue = .init(for: playlist)
    try await ApplicationMusicPlayer.shared.play()
} catch {
    // Append a non-blocking hint; the save itself succeeded.
    statusMessage += " Open the Music app to play it."
}

// Open the Music app's library so the user sees the new playlist.
// Apple does not support deep links to a specific library playlist; this
// URL goes to Library, where the new playlist appears under Playlists.
if let url = URL(string: "music://music.apple.com/library") {
    await UIApplication.shared.open(url)
}
```

Two URL details that trip people up:

- `music://music.apple.com/library` opens the Music app's library tab. This is the closest you can get programmatically.
- Deep-linking to a *specific* user-library playlist by ID is **not supported**. The Apple Music URL scheme only exposes catalog playlists and the library root.
