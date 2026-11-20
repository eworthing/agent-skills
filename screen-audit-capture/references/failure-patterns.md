# Failure patterns

Open this when a capture looks wrong, a run stalls, or registration rejects. Each row: symptom, cause, fix, and what to record. When none fits, record the symptom plainly in `<session>/session-log.md`, register nothing from that frame, and continue with the next case.

| Symptom | Cause | Fix and record |
| --- | --- | --- |
| App did not launch, or sits on onboarding, a coach mark, a trial nag or a "rate us" prompt | First launch, expired state, launch hang | Relaunch once. Dismiss a non-permission cover with its close control. If the process hung after sign-in, quit and relaunch the app. Record covers dismissed in `conditions`. A sign-in gate is a blocker (`account`, `owner`) |
| Frame identical or near-identical to the previous one | A tap helper returned false (element not found) but the run captured anyway | Make the helper's Bool gate the capture. Re-query the element. Never register the frame; note the step in the log |
| Permission or system alert in the frame (springboard alert, macOS permission dialog) | First access to media library, Apple Music, microphone, local network | Stop. Record `blocker_class: owner-action`, `blocker_clearable_by: owner` and the exact prompt text, unless the invoker authorised that prompt for this run. Then the owner or the authorised step clears it, and the log quotes the authorisation |
| Landscape frame is portrait-shaped | A device framebuffer is always portrait | Lossless rotation; verify text reads upright; say "rotated 90 degrees, pixel-preserving" in `conditions` |
| Black frames from a physical iPhone | Device locked (Mirroring requires it) | Use Mirroring-window capture only with owner approval; otherwise blocker `hardware`, clearable by `owner` |
| Mac frame shows more tile columns than any real iPad | Window not at device size | Resize to the profile's points through accessibility; retake; move wrong-size frames to `superseded-not-device-size/` |
| Frame registered as Dark but the app renders Light | The app forces a theme | Register the observed appearance. `conditions` states the system setting. The other mode's row gets `unavailable` with that evidence |
| File name says "dark", metadata says light | Renamed late | `check` reports `appearance-label`. Fix the metadata or capture ID before registering; never change the original bytes |
| Sheet closed before the capture | Race between action and screenshot | Wait for the element, not a sleep; retake |
| Playing state with no sound, or a frozen 0:00 | Home-app fixtures use a fake transport (profile note) | Expected. Say "silent fixture playback" in `conditions`. Never switch transports to get sound |
| Row stays open after a captured frame | Vocabulary mismatch (`n/a` versus `Not applicable`, `native device` versus `native installed app`) | Copy the exact spelling from existing rows. `check` reports `vocabulary-near-duplicate` |
| `add` is slow per capture | Each call re-validates every image | Use one `register` manifest per pass |
| Registration rejected for a duplicate note ID | Re-registering a changed note | Give it a new ID with `supersedes`; never edit the earlier note |
| `build` refuses the output folder | Leftover assets from an earlier build | Use a fresh, empty directory; keep the previous build |
| iCCP or decoder rejection on registration | Raw Mac window PNG carries a rejected colour-profile chunk | Re-encode with `sips -s format png`; keep the original and register the re-encoded file, noting it in `conditions` |
| Gate or test simulator shut down mid-run | Used a simulator the profile forbids (a gate's copy) | Stop using it. Never touch the gate's simulators; use the profile's capture simulators. Report it |
| A crash of the app or test host, or a "quit unexpectedly" dialog | Helper or app trap | Stop; do not rerun. Report the crash report path if the profile names a lister. Never dismiss the dialog or change crash-reporter settings: that is owner-only |
| Wrong case captured (screen shows another state) | Drove to the wrong state or the app redirected | Do not register under the intended case. Register under the case it shows, or discard to `superseded-*` with a reason |
| Capture of a case the app cannot do | Feature missing on this platform, build or orientation | Close the row `unavailable` with evidence, or `out-of-scope` with the reason; never leave it silent |
| Helper named in the profile does not exist | Profile out of date or helper never committed | Treat the channel as unavailable, record the blocker, and do not write helper or test code yourself |
