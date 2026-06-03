---
name: musickit-diagnostics
description: >-
  Diagnose and fix iOS MusicKit runtime failures: ICError codes (-8200,
  -8102, -7007, -7013, -7010), "Could not access Apple Music", "Failed to
  request developer token", MusicLibrary playlist creation failures ("No
  catalogID, libraryID" / "Client is not entitled"), CreateRecordingTap
  "nullptr == Tap()" crashes, and applicationQueuePlayer timeouts. Use
  when MusicKit search or playback throws, when MusicLibrary.createPlaylist
  or add(_:to:) silently fails, when Speech + ApplicationMusicPlayer
  coexist in one app, when code requests a developer token on iOS
  (anti-pattern — no such API), when action buttons fire before
  MusicAuthorization.request() returns .authorized, when search returns
  "unknown error", or when a bundle ID lacks MusicKit capability in the
  Apple Developer portal. Pairs with the general `musickit` skill for
  setup/auth/search/playback basics. iOS only — defer macOS/tvOS specifics
  to `apple-multiplatform` and `apple-tvos`.
allowed-tools:
  - Read
  - Glob
  - Grep
---

# MusicKit Diagnostics (iOS)

**Dependencies:** native Apple frameworks only (MusicKit, AVFoundation, StoreKit, Speech). No Python / pip / Swift Package dependencies required.

## Contents

- Scope
- Routing map (when to use this vs. `musickit`)
- Diagnostic-first protocol
- Error-code quick table
- iOS anti-patterns
- Simulator vs device
- Post-fix verification checklist
- Skip this skill when
- Related skills
- References

## Scope

This skill is **iOS-only** and **troubleshooting-focused**. It diagnoses
runtime failures in apps that already use MusicKit — error codes, library
playlist creation pitfalls, Speech + ApplicationMusicPlayer audio session
conflicts, bundle ID registration gaps, and iOS-specific anti-patterns.

For framework basics (setup, `MusicAuthorization.request()` happy path,
`MusicCatalogSearchRequest`, `MusicSubscription`, `ApplicationMusicPlayer`,
queue manipulation, Now Playing, remote command center), use the general
`musickit` skill. This skill points back to it where appropriate rather
than duplicating that content.

For macOS / Mac Catalyst MusicKit deltas, use `apple-multiplatform`.
For tvOS MusicKit availability gaps, use `apple-tvos`.

## Routing map

Find the symptom; jump to the relevant section or reference file.

| Symptom | Go to |
|---------|-------|
| You have an error but no NSError domain/code yet | [Diagnostic-first protocol](#diagnostic-first-protocol) |
| You have a domain + code (e.g. `ICErrorDomain -8200`) | [Error-code quick table](#error-code-quick-table) → [references/error-codes.md](references/error-codes.md) |
| "Failed to request developer token" appears anywhere | [iOS anti-patterns](#ios-anti-patterns) → §1 |
| "Search failed: Could not access Apple Music" | [iOS anti-patterns](#ios-anti-patterns) → §2 (auth gate) |
| "unknown error" surfaced to user | [iOS anti-patterns](#ios-anti-patterns) → §3 (fallback msg) |
| `MusicLibrary.createPlaylist` / `add(_:to:)` silently fails | [references/library-playlists.md](references/library-playlists.md) |
| "No catalogID, libraryID … MPIdentifierSet EMPTY" in console | [references/library-playlists.md](references/library-playlists.md) → Song-only rule |
| `CreateRecordingTap: nullptr == Tap()` crash | [references/speech-coexistence.md](references/speech-coexistence.md) |
| `applicationQueuePlayer _establishConnectionIfNeeded timeout` | [references/speech-coexistence.md](references/speech-coexistence.md) |
| Song list auto-scrolls / cycles by itself | [iOS anti-patterns](#ios-anti-patterns) → §5 |
| `MPMusicPlayerControllerErrorDomain` error 1 after a successful save | [references/error-codes.md](references/error-codes.md) → that section |
| Bundle ID in install log not in Apple Developer Identifiers | [references/bundle-id-setup.md](references/bundle-id-setup.md) |
| Catalog search works on device but not Simulator | [Simulator vs device](#simulator-vs-device) |

## Diagnostic-first protocol

Read this before applying any fix from the table below, *unless* you
already have an NSError `domain` and `code` in hand.

MusicKit errors are routed by domain and code, not by description. The
default `localizedDescription` is frequently empty or "unknown error".
Guessing at fixes wastes iterations. Add this one-time diagnostic to
every catch block around a MusicKit call:

```swift
} catch {
    let ns = error as NSError
    var msg = "Diagnostic: domain=\(ns.domain) code=\(ns.code) "
    msg += "description=\(error.localizedDescription)"
    if let underlying = ns.userInfo[NSUnderlyingErrorKey] as? NSError {
        msg += " | underlying: domain=\(underlying.domain) code=\(underlying.code)"
    }
    await MainActor.run { errorMessage = msg }
}
```

Run the failing flow once. Read the captured `domain` + `code`. Look it
up in the table below. Apply the targeted fix. Then **remove the
diagnostic** — it is a debugging probe, not production telemetry.

Apply this snippet around every: `MusicCatalogSearchRequest.response()`,
`ApplicationMusicPlayer.play()`, `MusicLibrary.shared.createPlaylist(...)`,
and `MusicLibrary.shared.add(_:to:)`.

Full per-field rationale and per-code deep dives live in
[references/error-codes.md](references/error-codes.md).

## Error-code quick table

| Domain | Code | Meaning | One-line fix | Long form |
|--------|------|---------|--------------|-----------|
| `ICErrorDomain` | **-8200** | Simulator / token failure | Run on a real iPhone or iPad. | [error-codes.md](references/error-codes.md#icerrordomain--8200--simulator--token-failure) |
| `ICErrorDomain` | **-8102** (underlying **-7007**) | Privacy acknowledgement required | User must open the Music app and accept the privacy/terms prompt. | [error-codes.md](references/error-codes.md#icerrordomain--8102-underlying--7007--privacy-acknowledgement) |
| `ICErrorDomain` | **-7010** | Listener / cloud auth | Re-run `MusicAuthorization.request()`, run on device, confirm `.authorized` before any call. | [error-codes.md](references/error-codes.md#icerrordomain--7010--listener--cloud-auth) |
| `ICErrorDomain` | **-7013** | Account-store entitlement | Run on device + bundle ID must have MusicKit capability in Apple Developer. | [error-codes.md](references/error-codes.md#icerrordomain--7013--account-store-entitlement) + [bundle-id-setup.md](references/bundle-id-setup.md) |
| `MPMusicPlayerControllerErrorDomain` | **1** | Post-save playback hiccup | Don't show a blocking dialog if the save itself succeeded; degrade to a non-blocking hint. | [error-codes.md](references/error-codes.md#mpmusicplayercontrollererrordomain-1--post-save-playback-hiccup) |

## iOS anti-patterns

Five named anti-patterns that recur in MusicKit code. Each has a WRONG
example and the CORRECT fix.

### 1. Developer token on iOS

There is **no developer-token API on native iOS**. MusicKit's automatic
developer-token generation (enabled by the MusicKit App Service for your
bundle ID) is opaque to app code; the framework attaches the token to
catalog requests on your behalf after `MusicAuthorization.request()`
returns `.authorized`.

Code that "requests a developer token" — JWTs, server fetches, hand-built
auth headers — comes from MusicKit JS / web or from server-API patterns
and **does not belong in an iOS app**. It cannot work; it can crash.

```swift
// WRONG: iOS does not expose this. Crashes or surfaces
// "Failed to request developer token".
func fetchDeveloperToken() async throws -> String { ... }

// CORRECT: nothing to do. Just authorize.
let status = await MusicAuthorization.request()
guard status == .authorized else { return }
// Catalog/playback calls work from here.
```

If you find a "developer token" reference in Swift code: grep the project
for `developer`, `token`, `DeveloperToken`, `developerToken` and delete
every reference. Do not "fix" the developer-token call site; remove it.

### 2. Action button enabled before authorization

If "Build Playlist" / "Create and Play" / "Search" fires before
`MusicAuthorization.request()` returns `.authorized`, users see "Could
not access Apple Music" (or worse — a crash from the unauthorized call).

```swift
// WRONG: button always enabled; auth is lazy
Button("Build Playlist") { Task { await build() } }

// CORRECT: button disabled until authorized; auth requested on appear
Button("Build Playlist") { Task { await build() } }
    .disabled(!viewModel.isAuthorized)

// In the view:
.onAppear { Task { await viewModel.requestAuthorization() } }
```

The view-model property (`isAuthorized` or similar) must be set to
`true` only when `MusicAuthorization.request()` returns `.authorized`,
and every search/playback path must check it before firing.

### 3. Raw `error.localizedDescription` shown to user

MusicKit errors often have empty or generic `localizedDescription`.
Surfacing "" or "unknown error" to the user is useless. Fall back to a
message that points at the real check.

```swift
} catch {
    let raw = error.localizedDescription
    let isGeneric = raw.isEmpty || raw.lowercased().contains("unknown")
    let fallback = "Could not access Apple Music. " +
        "Check Settings → Music and sign in with an Apple Music subscription."
    await MainActor.run {
        errorMessage = isGeneric ? fallback : "Search failed: \(raw)"
    }
}
```

Apply this **alongside** the diagnostic from the protocol above — the
diagnostic captures the real domain/code for the developer; the fallback
gives the user something actionable.

### 4. `Album` (or constructed items) passed to library-playlist add

`MusicLibrary.shared.add(_:to:)` requires items with a valid catalog or
library identifier. `Album` instances and items constructed from display
strings have empty identifier sets; the add silently fails and logs

```
No catalogID, libraryID, or deviceLocalID was found …
MPIdentifierSet EMPTY … type … Album
```

```swift
// WRONG: Album type, or items built from title/artist strings
try await MusicLibrary.shared.add(album, to: playlist)

// CORRECT: Song from catalog search
var request = MusicCatalogSearchRequest(term: query, types: [Song.self])
let response = try await request.response()
for song in response.songs {
    try await MusicLibrary.shared.add(song, to: playlist)
}
```

Full walkthrough: [references/library-playlists.md](references/library-playlists.md).

### 5. Auto-scrolling song list

The generated UI sometimes adds a `ScrollViewReader` that scrolls to the
current item, or a timer/animation that cycles through the list. Users
read this as "the app is broken — it keeps jumping". They did not ask
for it.

```swift
// WRONG: auto-scroll on every track change
ScrollViewReader { proxy in
    List(songs) { song in SongRow(song: song).id(song.id) }
        .onChange(of: currentSong) { _, new in
            withAnimation { proxy.scrollTo(new.id) }
        }
}

// CORRECT: plain static list, user scrolls manually
List(songs) { song in SongRow(song: song) }
```

Show the current track in the player UI. Do not move the list. If the
user wants to find the current song, they will scroll.

## Simulator vs device

The iOS Simulator does **not** reliably support several MusicKit features
that work on real devices:

- **Catalog search.** Often fails with `ICErrorDomain -8200`.
- **Library playlist creation** (`MusicLibrary.shared.createPlaylist`, `add`). Often fails with `ICErrorDomain -7013`.
- **Account-store access** generally.

If a MusicKit call works on device and fails identically every time on
Simulator with one of those codes, that is the cause — not your code.
Run on hardware. If a call fails on device, the bundle ID may not be
registered with MusicKit capability — see
[references/bundle-id-setup.md](references/bundle-id-setup.md).

## Post-fix verification checklist

After any fix, walk these six preconditions end-to-end on a real device:

1. **Real device, not Simulator.** Use Run on iPhone / iPad.
2. **Authorization** — App calls `MusicAuthorization.request()` on screen appear (`.onAppear` or `.task`). User taps **Allow** when the system prompt appears.
3. **Music app privacy accepted** — On the device, open the built-in Music app, sign in if asked, accept any privacy/terms prompt. Satisfies the -8102 / -7007 path.
4. **Apple Music subscription active** — Settings → Music shows an active Apple Music subscription (or trial). Required for catalog access.
5. **Network reachable** — Wi-Fi or cellular.
6. **Bundle ID registered with MusicKit capability** — see [references/bundle-id-setup.md](references/bundle-id-setup.md).

If any one of these is red, the call will fail in a predictable way
covered above. If all six are green and the call still fails, re-add the
diagnostic and capture a new `domain` + `code`.

**Before merging:** remove any stale diagnostic code left in catch blocks —
the diagnostic from the protocol above is for debugging, not production
telemetry.

## Skip this skill when

These questions belong to the general `musickit` skill, not here:

- "How do I authorize MusicKit?" → general `musickit` skill, Authorization section.
- "How do I search the catalog?" → general `musickit` skill, Catalog Search section.
- "How do I set up Now Playing / Lock Screen / Remote Commands?" → general `musickit` skill.
- "How do I check the user's subscription?" → general `musickit` skill, Subscription Checks.
- "How do I build a queue from an album?" → general `musickit` skill, Queue Management.
- "I want to add basic SwiftUI integration around an `ApplicationMusicPlayer`" → general `musickit` skill → references/musickit-patterns.md.

This skill takes over when those happy-path patterns are in place and a
specific failure mode surfaces.

## Related skills

- **`musickit`** (general) — Framework basics: setup, authorization, catalog search, subscriptions, `ApplicationMusicPlayer`, queue, Now Playing, remote commands. Always reach for this first; reach for `musickit-diagnostics` when something specific is failing.
- **`swift-concurrency`** — `ApplicationMusicPlayer` is `@MainActor`; `MusicCatalogSearchRequest.response()` is `async throws`. If you have actor-isolation warnings or `Sendable` issues around MusicKit types, consult this skill.
- **`swiftui-expert-skill`** — View-model patterns for the `isAuthorized` gate from anti-pattern §2 (`@Observable` properties, `.onAppear` vs `.task`, button disabling).
- **`apple-multiplatform`** — macOS / Mac Catalyst MusicKit deltas (not iOS-specific failures).
- **`apple-tvos`** — tvOS MusicKit availability gaps; some MusicKit APIs are not available or behave differently on tvOS.

## References

Apple documentation:

- [MusicKit framework overview](https://developer.apple.com/documentation/musickit/)
- [Using Automatic Developer Token Generation for Apple Music API](https://developer.apple.com/documentation/musickit/using-automatic-token-generation-for-apple-music-api) — explicit confirmation that iOS does **not** require a developer token in app code
- [Playlist](https://developer.apple.com/documentation/musickit/playlist)
- [Playlist.Entry](https://developer.apple.com/documentation/musickit/playlist/entry)
- [Create a New Library Playlist](https://developer.apple.com/documentation/applemusicapi/create-a-new-library-playlist)
- [Add Tracks to a Library Playlist](https://developer.apple.com/documentation/applemusicapi/add-tracks-to-a-library-playlist)

Internal references (this skill):

- [references/error-codes.md](references/error-codes.md) — Per-code deep dives + diagnostic snippet + fallback messaging
- [references/library-playlists.md](references/library-playlists.md) — `MusicLibrary.createPlaylist` + `add(_:to:)` patterns and failures
- [references/speech-coexistence.md](references/speech-coexistence.md) — AVAudioEngine tap discipline; speech-then-playback flow
- [references/bundle-id-setup.md](references/bundle-id-setup.md) — Apple Developer portal registration for MusicKit capability
