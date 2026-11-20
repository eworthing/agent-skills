# Capture channels

Open this when choosing or running a capture channel. Names, device lists and commands for the project come from the profile's `channels` block; this file holds the generic procedure. Every channel ends with the pixel checks in [verify-from-pixels.md](verify-from-pixels.md).

## Simulator

Best for home-app fixtures at native pixels. Competitor apps usually cannot install on a simulator.

- **Preconditions:** the simulator is listed under `channels.simulator.sims` in the profile. Never touch simulators the profile forbids (for example a gate's "... Copy" devices): shutting one down mid-run fails someone else's run.
- **Drive:** use the profile's capture channel command, which sets up the disposable fixtures. Do not hand-build fixtures in the app.
- **Capture:** `xcrun simctl io <udid> screenshot --type=png <out.png>` returns native pixels.
- **Status bar:** `xcrun simctl status_bar <udid> override --time <ISO 8601 with milliseconds>`. `--time 9:41` leaves the date live, so use a full timestamp.
- **Appearance:** `xcrun simctl ui <udid> appearance dark` or `light`, only on profile-listed simulators. Confirm from the pixels afterwards.
- **Proves:** the home app's UI under fixtures and controlled responses. **Cannot prove:** live account data, real playback, native-device scale. Note any profile caveat (for example silent playback from a fake transport) in `conditions`; never switch transports to get sound.

## Physical iPhone or iPad via XCUITest

- **Preconditions:** the profile's `channels.device_xcuitest.helper` names a committed test class and run command. If it says `none` or the file does not exist, treat this channel as unavailable: record the blocker (`hardware` or `other`, clearable by `owner`), and never write product or test code yourself.
- **Owner steps:** the owner unlocks the device, confirms it is idle, and switches device appearance. Ask, wait, confirm from the pixels.
- **Drive:** the helper launches the other app by bundle ID (`XCUIApplication(bundleIdentifier:)`). Tap helpers return a Bool; that Bool must gate the capture, or a failed tap produces a duplicate frame.
- **System alerts:** springboard alerts are visible to the runner. Never accept one unless the invoker authorised that exact prompt for this run.
- **Landscape:** device framebuffers are portrait-shaped, so a landscape frame arrives rotated. Rotate it losslessly and say so in `conditions`.
- **Proves:** native installed-app UI at device pixels (tier A). **Cannot prove:** anything behind a sign-in or paywall you may not pass.

## iPhone Mirroring

- **When:** only when the profile (`channels.mirroring.allowed`) or the invoker says the owner approved it for this run. Otherwise this channel is closed.
- **Why it is a window capture:** native device capture is impossible, because Mirroring needs the phone locked and a locked framebuffer is black.
- **Capture:** the Mirroring window at 2x (profile `channels.mirroring.window_pixels` gives the expected size). Write "Mirroring window" in `conditions`; `crop_intent` is `window-with-title-bar` unless you crop to the screen.
- **Never** click links shown in the mirrored app. Owner prompts (appearance, unlock) stay with the owner.
- **Proves:** installed-app UI as the phone rendered it, at window scale. **Cannot prove:** native pixel dimensions.

## Mac

- **Surfaces:** native Mac build, or an iPad or iPhone app running on the Mac. Keep them distinct in `platform_variant` and `layout_variant`.
- **Window capture:** find the window ID, then `screencapture -l <windowID> -o -x <out.png>` (window only, no shadow, no sound), then `sips -s format png <out.png> --out <fixed.png>`. The raw PNG's iCCP chunk is rejected by the ledger's decoder, so re-encode before registering.
- **iPad apps on Mac** render at the profile's scale. Set the window to the profile's device-size points (`channels.mac.ipad_on_mac_window_points`) through accessibility, not by dragging; verify the capture's pixels against `expected_pixels`. A frame showing a column count no real iPad shows means the window was not at device size.
- **Phone-only apps** keep their fixed window. Record the window points and pixels in `conditions`.
- **Owner steps:** system appearance changes, permission dialogs, local-network prompts.
- **Label:** every on-Mac capture of an iPad or iPhone app is non-native (tier C): `platform_variant`, `layout_variant`, a NOT NATIVE note, and a coverage row kept open for the real-device recapture.
- **Proves:** the layout and behaviour of that app on the Mac. **Cannot prove:** native iPad or iPhone rows (touch targets, scale, rotation).

## Public stills and demos

- Store listing images and official demos are tier D `public-still` or `official-demo` evidence: valid, always labelled, never counted as a device capture.
- **Record:** the asset URL (HTTPS, the listing asset itself), pixel size, SHA-256, region and date accessed, and whether a bezel or overlay is present (`crop_intent: store-art-bezel` when the bezel is in the image).
- **Download** only from the listing URL the invoker or profile gives. Keep the downloaded bytes unmodified; crop through the manifest's `crop`, never by editing the original.
- **Appearance:** leave `unspecified` when the image does not show it. Do not infer it from the store's page theme.
- **Proves:** the visible UI at that moment. **Cannot prove:** build, runtime behaviour, other orientations or devices.

## Choosing

Prefer, in order: the profile's simulator for home-app cases; the device helper for installed competitor apps when a committed helper exists; the Mac for apps with a Mac or iPad-on-Mac edition; Mirroring only with owner approval; public stills last and always labelled. Where a channel is unavailable, close the row with the right disposition (`blocked` with a blocker class) rather than substituting a weaker channel silently.
