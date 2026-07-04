# Drop Troubleshooting: "Wrong Handler Catches Drop" & Platform Notes

Depth catalog for the parent skill's inline *Debugging Drop Types* snippet. Start
there (log `registeredTypeIdentifiers` at the top of `performDrop`); come here when
the type log alone doesn't explain the misroute.

## "Wrong handler catches drop" — symptom → cause → fix

| Symptom | Likely cause | Fix |
|---|---|---|
| Drop lands on the background even though it's over a card | `.onDrop` callbacks mixed with `DropDelegate` on overlapping targets — priority is undefined once any target needs routing | Convert **all** participating targets to `DropDelegate`; `.onDrop(perform:)` cannot suppress siblings |
| Higher-priority leaf never wins | Leaf doesn't publish its targeting state, so lower handlers can't detect it | In the leaf's `dropEntered`/`dropExited`, set/clear the shared `DropRouter` field; siblings read it in `validateDrop` |
| Internal reorder gets hijacked by a create/fallback handler | Background/fallback `validateDrop` returns `true` for internal-move UTTypes | Fallback handlers must `return false` when `info.hasItemsConforming(to: internalTypes)` |
| Visual accept, then nothing happens ("ghost drop") | Suppression logic put in `performDrop` (returned `false` after `validateDrop` accepted) | Move all suppression into `validateDrop`; `performDrop` returns `true` whenever it accepts |
| Drop silently ignored on a tappable card | `.onDrop` attached to `Button` (or its label), which consumes the event | Attach the drop to a wrapper with `.contentShape(.rect)`; keep the targeting overlay `.allowsHitTesting(false)` |
| Highlight sticks after the drag leaves | Targeting state cleared only in `performDrop`, not `dropExited` | Clear the router field + local `isTargeted` in `dropExited` (and guard the clear on `== itemID`) |
| Two adjacent targets both highlight | Both set the same shared router field without an identity guard | Guard writes/clears on the specific `itemID`; only clear if the stored id matches |

## macOS-specific notes

- **Finder file drops arrive as promises.** `public.file-url` from Finder is a
  file-URL you can load, but large or iCloud-backed files may resolve lazily — load
  inside `performDrop` on a `Task` you own and surface failures via UI state, never
  block the main thread waiting.
- **`NSPasteboard` paste is a different surface.** Cmd-V / Edit-menu paste does not
  flow through `DropDelegate` at all — it reads `NSPasteboard.general`. If you need
  both drag-drop *and* paste, wire them separately; this skill covers only the drop
  path (see the parent skill's *When Not to Use*).
- **Pointer-precise hit testing.** macOS drags target exact pixels; a card that only
  highlights over its opaque content (not its padding) is usually missing
  `.contentShape(.rect)` on the wrapper.
