# Verify from the pixels

Open this after every capture, before the frame enters a manifest. A file on disk, a passing helper or a log line is not a captured screen. Do each check on the image file itself and log the result in one line per frame.

## Expected pixels

Look up the expected pixel size for the device model, orientation and channel in the profile (`expected_pixels`, and `channels.mac.expected_pixels` for Mac windows). A frame whose size is not in the set is refused: do not register it, move it to `<session>/superseded-not-device-size/` (or the closest `superseded-*` name) and log why.

## Per-image checklist

1. **Pixel size.** `magick identify -format '%w %h' <png>` (or `sips -g pixelWidth -g pixelHeight <png>`) equals the expected size.
2. **Orientation.** Width greater than height means landscape. A portrait-shaped landscape frame from a device framebuffer is rotated with `magick <in> -rotate 90 <out>` (or `-rotate -90`, whichever makes text upright). Never resample. Re-open the result and check that the status bar and text read upright. Write "rotated 90 degrees, pixel-preserving" in `conditions`.
3. **Appearance.** `magick <png> -colorspace Gray -format '%[fx:mean]' info:`. Below about 0.35 suggests dark; above about 0.6 suggests light. Between those, or when the result contradicts the requested appearance, look at the image and record what the app shows. The recorded `appearance` is what the pixels show, not what was requested.
4. **State.** Open the image with the image tool and write one line naming the screen, the visible title and the case-defining element. It must match the case's `task` text in `cases.json`; name the `case_id` only after this line. Check the edges for covers: keyboard, coach mark, nag, permission sheet, banner, "rate us" prompt.
5. **Duplicates and no-change.** `shasum -a 256 <png>` across the session and against the ledger (`check` reports `identical-frame` for the same bytes and crop). Compare with the previous frame: `magick compare -metric AE -fuzz 1% a.png b.png null: 2>&1`. Zero or near-zero changed pixels after a tap means the tap did nothing: a tap helper probably returned false and the run captured anyway.
6. **Black or blank.** A mean luminance near 0, or a single colour, means a locked device, a hidden window or a screen not yet drawn. Do not register it.
7. **Decoder.** The registration dry run is the decoder check. An iCCP rejection is fixed by re-encoding with `sips -s format png <in> --out <fixed>`; keep the original too.

## Reading the image

Open the image with the image tool and describe it before judging it. If you cannot see images (only a path or an error comes back), stop and say so: pixel checks that need eyes are not done, and nothing from this frame may be registered as verified.

## What to log

One line per frame in `<session>/session-log.md`:

`<file> | <case_id> | <one-line screen description> | size ok, orientation ok, appearance <light|dark> (mean 0.xx), no cover, unique`

A frame that fails any item is not registered; log which item failed and what was done (retaken, moved to `superseded-*`, blocker recorded). In the hand-back, count only frames that passed as verified, and say how many were refused.

## Black-box limits

Mean luminance and pixel compare are lexical checks: they catch gross errors, not a wrong screen that looks plausible. The one-line description is the real check, so never skip it because the numbers pass.
