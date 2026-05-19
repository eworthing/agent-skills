# Bundle ID + MusicKit Capability Setup

For MusicKit (catalog search, playback, library access) to work, the
**exact bundle ID** installed on the device must be registered as an
**App ID** in your Apple Developer account with the **MusicKit**
capability enabled. The MusicKit framework binds its automatic developer
token to that App ID; if Apple's identifier service does not see the
bundle ID with MusicKit capability, calls fail.

This is the most common cause of `ICErrorDomain -7013` when running on a
real device (with the user correctly signed in to Apple Music). It also
explains "search works in one project but not in another" on the same
device.

## Contents

- [Symptom that points here](#symptom-that-points-here)
- [Option A — Reuse an identifier already enabled (recommended)](#option-a--reuse-an-identifier-already-enabled-recommended)
- [Option B — Register the new bundle ID](#option-b--register-the-new-bundle-id)
- [Verification](#verification)
- [Notes on auto-generated bundle IDs](#notes-on-auto-generated-bundle-ids)

## Symptom that points here

You are looking at this page if:

- The app installs and launches on a real device, but `MusicCatalogSearchRequest.response()` or `MusicLibrary.shared.createPlaylist(...)` fails with `ICErrorDomain` -7013, or
- Search/playback works in one of your projects but not another, on the same device with the same Apple ID, or
- The bundle ID shown in Xcode's install log (or in your IDE's deployment console) is **not** in your Apple Developer **Identifiers** list.

Symptoms that point elsewhere:

- -8200 → see `error-codes.md` (likely Simulator, not bundle ID)
- -8102 / underlying -7007 → see `error-codes.md` (Music-app privacy prompt)
- "Failed to request developer token" → that is iOS anti-pattern code, not a bundle ID problem (see SKILL.md)

## Option A — Reuse an identifier already enabled (recommended)

For multi-project workflows (e.g. spinning up several test apps that all
exercise MusicKit), register **one** identifier with MusicKit and reuse
it across projects. This is faster than registering each new bundle ID.

1. In Apple Developer → Certificates, Identifiers & Profiles → Identifiers, confirm you have an App ID like `com.yourdomain.musickit` with the MusicKit capability enabled. Add one if not.
2. In the project under repair, open project settings.
3. Under **Identity**, set **Bundle Identifier** to that reusable identifier (e.g. `com.yourdomain.musickit`).
4. Save and rebuild. Xcode will refresh provisioning automatically.
5. Reinstall on the device and retry the failing call.

This was the confirmed fix in the originating learnings: switching from
an auto-generated bundle ID to a manually registered MusicKit-enabled
identifier made catalog search return results on the first try.

## Option B — Register the new bundle ID

Use this when you specifically need to keep an auto-generated or
project-specific bundle ID (e.g. for App Store / TestFlight distinct
listings).

1. In Apple Developer → Certificates, Identifiers & Profiles → Identifiers, click **+** to add a new App ID.
2. Choose **App IDs → App**.
3. Bundle ID **Explicit** → enter the exact bundle ID from the install log.
4. Under **Capabilities**, enable **MusicKit**.
5. Save.
6. Rebuild and reinstall the app. Xcode may need to refresh provisioning profiles; sign in / wait / Clean Build Folder as needed.

You must repeat this step for every new bundle ID. If your project
generator produces a fresh bundle ID per build (some IDE tooling does),
prefer Option A.

## Verification

After applying either fix:

1. Confirm the bundle ID in Xcode's project settings (Identity → Bundle Identifier) matches the identifier with MusicKit capability in Apple Developer.
2. Build, install, run on the real device.
3. Inject the diagnostic snippet from `error-codes.md` if the call still fails. A fresh failure with a *different* code (e.g. -8102) means the bundle ID is now fine and a different fix applies.
4. The symptom that confirms the fix: a `MusicCatalogSearchRequest` for a common term (e.g. "the beatles") returns a non-empty `response.songs`.

## Notes on auto-generated bundle IDs

Some agent / IDE tooling generates a unique bundle ID per project (e.g.
`com.vibetree.app1772195763292i59o34o`). Each such ID, by definition, is
**not** in your Apple Developer Identifiers list. With Option B, you
would have to register each one individually. Option A — overriding the
generated ID with a known MusicKit-enabled identifier — is dramatically
less friction for iteration.

Do not assume Apple is rejecting the build outright — the install log
showing "succeeded" with `com.vibetree.app1772195763292i59o34o` only
means provisioning let the binary onto the device. MusicKit's
entitlement check happens later, at the first API call, and fails
silently (or with -7013) when the bundle ID is unknown.
