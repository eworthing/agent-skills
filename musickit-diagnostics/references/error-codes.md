# MusicKit Error Codes Reference

When a MusicKit call fails on iOS, the framework throws an `Error` whose
default `localizedDescription` is often empty or generic. The real signal
lives on the underlying `NSError`: its `domain`, `code`, and any nested
`NSUnderlyingErrorKey`. Read those before changing code — the fix branches
sharply by code.

## Contents

- [Diagnostic injection (do this first)](#diagnostic-injection-do-this-first)
- [`ICErrorDomain` -8200 — Simulator / token failure](#icerrordomain--8200--simulator--token-failure)
- [`ICErrorDomain` -8102 (underlying -7007) — Privacy acknowledgement](#icerrordomain--8102-underlying--7007--privacy-acknowledgement)
- [`ICErrorDomain` -7010 — Listener / cloud auth](#icerrordomain--7010--listener--cloud-auth)
- [`ICErrorDomain` -7013 — Account-store entitlement](#icerrordomain--7013--account-store-entitlement)
- [`MPMusicPlayerControllerErrorDomain` 1 — Post-save playback hiccup](#mpmusicplayercontrollererrordomain-1--post-save-playback-hiccup)
- ["Unknown error" fallback messaging](#unknown-error-fallback-messaging)

## Diagnostic injection (do this first)

Before guessing at fixes, capture the real error. Cast every MusicKit
`error` to `NSError` and surface `domain`, `code`, `localizedDescription`,
and (if present) the underlying error's domain/code. The agent that wrote
the buggy code should add this once, run the failing flow once, and read
the result.

```swift
} catch {
    let ns = error as NSError
    var msg = "Diagnostic: domain=\(ns.domain) code=\(ns.code) "
    msg += "description=\(error.localizedDescription)"
    if let underlying = ns.userInfo[NSUnderlyingErrorKey] as? NSError {
        msg += " | underlying: domain=\(underlying.domain) code=\(underlying.code)"
    }
    await MainActor.run {
        errorMessage = msg  // or show in alert with a Copy button
    }
}
```

Why each field matters:

- **`domain`** routes the fix. `ICErrorDomain` means MusicKit/iTunes-Cloud; `MPMusicPlayerControllerErrorDomain` means the player path; `NSURLErrorDomain` means network. Different rows in the table below.
- **`code`** narrows it. Within `ICErrorDomain`, -8200 and -7013 are different bugs requiring different fixes.
- **`localizedDescription`** is occasionally informative (especially for `MusicSubscription` errors) but is often empty or "unknown" — do not rely on it alone.
- **`NSUnderlyingErrorKey`** matters for `-8102`: the surface code is generic, the nested `-7007` is what actually points at a fix (privacy acknowledgement).

Apply this snippet to every `catch` around `MusicCatalogSearchRequest.response()`, `ApplicationMusicPlayer.play()`, `MusicLibrary.shared.createPlaylist(...)`, and `MusicLibrary.shared.add(_:to:)`. Remove it once the bug is fixed; it is a one-time diagnostic, not production telemetry.

## `ICErrorDomain` -8200 — Simulator / token failure

**Meaning.** The iOS Simulator cannot reach the catalog token endpoint
reliably. MusicKit's automatic developer-token generation works through the
device's account binding; the Simulator does not have an Apple-Music-signed
account in the same way. Catalog search and catalog playback fail with -8200
and a generic description.

**Fix.** Run on a real iPhone or iPad. Do not chase token configuration in
code — there is no developer-token API to configure on iOS in the first
place (see SKILL.md anti-pattern "Developer token on iOS").

**Verify the fix:** The same build that throws -8200 in Simulator should
return `MusicItemCollection<Song>` populated with results on a signed-in
device with an Apple Music subscription.

## `ICErrorDomain` -8102 (underlying -7007) — Privacy acknowledgement

**Meaning.** "Privacy acknowledgement required." The Apple-ID holder on
this device has not opened the Music app and accepted Apple Music's
privacy/terms prompt. MusicKit refuses to return catalog data for an
unacknowledged account. The surface code is -8102; check
`NSUnderlyingErrorKey` for `-7007` to confirm.

**Fix.** Have the device user:

1. Open the built-in **Music** app
2. Sign in with their Apple ID if prompted
3. Accept any privacy / "Use Apple Music" / terms prompt
4. Return to your app and retry

The acknowledgement is per-device, per-Apple-ID. It persists across app
installs; you only see this on a fresh device or a fresh sign-in.

**Do not** try to swallow -8102 with a retry loop. The framework will
keep returning it until the user satisfies the prompt in the Music app.

## `ICErrorDomain` -7010 — Listener / cloud auth

**Meaning.** Listener or cloud-service authentication failure. Frequently
appears when `MusicAuthorization.request()` was never called, when the
returned status was not `.authorized`, or when the device account changed
between authorization and the failing call.

**Fix.**

1. Confirm `MusicAuthorization.request()` is called on screen appear (e.g. in `.onAppear` or `.task`) and that the resulting status is `.authorized` before any catalog request fires.
2. Re-authorize if the user signed out and back in: `MusicAuthorization.currentStatus` may still be `.authorized` but the underlying account binding broke.
3. Run on device (same as -8200; -7010 can also surface on Simulator).

## `ICErrorDomain` -7013 — Account-store entitlement

**Meaning.** "Client is not entitled to access account store." Appears when
the app tries to touch the iCloud Music Library or create/modify a library
playlist (`MusicLibrary.shared.createPlaylist`, `MusicLibrary.shared.add`)
in a context where the entitlement chain breaks. The two common contexts:

1. **Simulator.** Account-store access is not reliably available in
   Simulator regardless of how the build is signed.
2. **Bundle ID lacking MusicKit capability.** The bundle ID actually
   running on the device is not registered in Apple Developer Identifiers
   with MusicKit enabled. See `bundle-id-setup.md`.

**Fix.**

1. Run on a real device.
2. Verify the bundle ID in the install log matches an App ID registered with MusicKit capability in your Apple Developer account. If it doesn't, set the project's Bundle ID to one that is (see `bundle-id-setup.md` Option A) or register the new one (Option B).
3. Confirm the device user is signed in to Apple Music (Settings → Music).

**Do not** assume -7013 means the user lacks a subscription. The
subscription is checked separately (`MusicSubscription.canPlayCatalogContent`).
-7013 is about the app's entitlement chain, not the user's subscription tier.

## `MPMusicPlayerControllerErrorDomain` 1 — Post-save playback hiccup

**Meaning.** Generic playback failure from
`MPMusicPlayerController` / `ApplicationMusicPlayer.play()`. Often appears
**after** a successful library-playlist save: the playlist was created and
populated, but the immediately-following `player.play()` failed because
the queue is not yet ready, or because the audio session is contested
(see `speech-coexistence.md`).

**Critical UX rule.** Do **not** show a blocking error dialog for this
code after a successful save. The user's primary goal — "create the
playlist in Apple Music" — already succeeded. Surface a non-blocking
status:

```swift
// WRONG: blocking alert obscures the success
alertMessage = "Playback error: \(error.localizedDescription)"
showAlert = true

// CORRECT: keep success message; degrade gracefully
statusMessage = "Playlist added to your library. " +
    "Open the Music app to play it if playback didn't start."
```

Then optionally open the Music app (see `library-playlists.md` →
"Post-success handoff").

**If you need playback in-app to actually work**, ensure no speech
recognizer is holding the audio session — see `speech-coexistence.md`.

## "Unknown error" fallback messaging

MusicKit sometimes throws an error whose `localizedDescription` is empty
or literally the string "unknown error". Showing that raw string to the
user is useless. Use a fallback that points at the actual fix:

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

This pattern applies to search and playback paths alike. Apply it
*alongside* the diagnostic injection above — the diagnostic captures the
real domain/code so you can fix the root cause; the fallback gives the
user something actionable while you debug.
