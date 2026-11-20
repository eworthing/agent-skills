# Manifest and naming

Open this when writing capture metadata, a manifest, filenames or coverage rows. Authority for the format is the tool README's "Bulk registration", "Data contract" and "Blocker classes" sections (path in the profile's `tool.readme`); this file is the working checklist.

## Manifest shape

```json
{
  "description": "<lane> session YYYY-MM-DD, <pass name>",
  "captures": [
    {"image": "originals/<file>.png", "metadata": {"capture_id": "...", "case_id": "...", "app": "..."}},
    {"image": "originals/<file>.png", "crop": [0, 64, 1816, 1262], "metadata": {"...": "..."}}
  ],
  "coverage": [{"priority": "P1", "app": "...", "case_id": "...", "device": "...", "orientation": "...",
                "layout_variant": "...", "appearance": "...", "disposition": "captured",
                "evidence_id": "...", "next_action": "..."}],
  "notes": [{"author": "<capture author>", "author_kind": "agent", "kind": "observation",
             "target": {"type": "capture", "capture_id": "..."}, "text": "..."}]
}
```

Image paths resolve against the manifest's directory. `crop` is `[x, y, width, height]` in original pixels; the original bytes are never edited. One manifest per pass: `add` re-validates every image on each call and is slow per capture.

## Capture metadata fields

| Field | Rule |
| --- | --- |
| `capture_id` | Required; the profile's pattern; stable; includes app slug, device, orientation or window class, case, and appearance when the ledger pattern does |
| `case_id` | Required; must exist in `cases.json`; the case the frame actually shows, not the one intended |
| `app` | Required; exact registry name (match by bundle ID, never by file name) |
| `device` | Required; ledger spelling (for example `iPhone`, `iPad`, `Mac`) |
| `device_model` | Model and identifier, for example `iPad (10th generation) (iPad13,18)` |
| `orientation` | Required; `Portrait`, `Landscape`, or the ledger's not-applicable spelling for Mac |
| `appearance` | `light`, `dark` or `unspecified`; from the pixels, not the setting. An app that forces light in a dark system is `light`, and `conditions` says so |
| `evidence_kind` | Required; `installed-app`, `fixture`, `public-still`, `official-demo`, `archived-simulator` |
| `capture_build` | Required; app version and build from the device or plist; `unknown` only with a reason |
| `os` | Installed and fixture captures; the OS of the device that rendered the frame |
| `layout_variant` | Installed and fixture captures; ledger spelling; `iPad-on-Mac ...` or `iPhone-on-Mac ...` for on-Mac runs |
| `platform_variant` | Required for on-Mac runs: `iPad app on Mac (Designed for iPad)` or `iPhone app on Mac (Designed for iPhone)` |
| `captured_at` | ISO 8601 with UTC offset, the real capture time (file time). Never invent one |
| `title` | One line naming the visible state, quoting a visible label |
| `source`, `destination` | Where the flow started and where its result goes; `Not applicable (<reason>)` when none |
| `conditions` | Channel, driver (XCUITest helper, Mirroring, computer use), rotation applied, covers dismissed, account and fixture state, authorisations granted for this run, "No owner interaction" or what the owner did, window points and pixels for Mac |
| `pixels_per_point` | 3 for 3x phones; 2 for iPad, Retina Mac windows and Mirroring windows; omit for store art |
| `crop_intent` | `bare-screen`, `window-with-title-bar` or `store-art-bezel` |
| `comparison` | `[{case_id, grade, reason}]`; grade is `exact`, `partial` or `adjacent`, with a reason |
| `original_url` | HTTPS listing asset URL, public stills only |

For on-Mac captures also add one note per capture: kind `observation`, tag `not-native`, text "NOT NATIVE: iPad app on Mac; recapture on a real device before relying on it". The viewer derives its recapture filter from `platform_variant` and `layout_variant`; the note makes it visible in note filters.

## Filenames and capture IDs

Take the filename and capture-ID patterns from the profile's `id_patterns`. A neutral example of a filename: `<app-slug>-<device>-<orientation>-<case-slug>-<appearance>.png`, for instance `example-app-ipad-landscape-catalog-results-dark.png`. Rules:

- The name and the metadata must agree. `check` raises `appearance-label` when an ID or title says Dark and the `appearance` field says Light. Fix the metadata or the capture ID before registering, never the original bytes.
- A short visible label may be appended when it helps locate the screen.
- Never reuse an ID. A re-take gets a new ID; the earlier frame moves to `<session>/superseded-*/`.

## Vocabulary

Copy exact spellings of `device`, `orientation`, `layout_variant` and `platform_variant` from existing rows (`sc status` and the viewer facet lists show them; the profile's `vocabulary` field says where they are listed). Rows close only on exact strings: `n/a` and `Not applicable` are different strings, as are `native device` and `native installed app`, and a split spelling silently leaves rows open. `check` reports `vocabulary-near-duplicate` when it sees one.

## Coverage rows

- The key is the six fields app, case_id, device, orientation, layout_variant, appearance. A row whose key already exists replaces it, so run `sc snapshot` first when replacing.
- A `captured` row needs a matching app, case, device, orientation and layout, and, for explicit Light and Dark rows, the same appearance. Public and archived captures close only their own reference variants.
- An `equivalent` row points to a representative capture in another orientation, with verified equivalence.
- Every row that is not `captured` needs a `next_action`.
- A `blocked` row needs `blocker_class` (`hardware`, `paywall`, `account`, `crash`, `owner-action`, `declined`, `other`), `blocker_clearable_by` (`owner`, `agent`, `none`) and a `next_action`. Blocker fields are rejected on `captured` and `equivalent` rows, so clear them when a row closes.
- `unavailable` rows carry evidence that the app lacks the feature, platform, orientation or appearance (for example "app forces light"), cited in `next_action` or a note.
- Missing variants are never silent: every requested matrix row ends as `captured`, `pending`, `blocked`, `unavailable`, `equivalent` or `out-of-scope`.

## Notes

Notes are append-only. A note whose ID is already registered with identical content is skipped; the same ID with different content rejects the manifest. To change a note, give the new one a new ID and `supersedes: "<earlier id>"`; never edit the earlier note. Give notes a `created_at` so re-running the manifest is safe.

## Before registering

Run `sc register --manifest <path> --dry-run` and read every reject. Then `sc snapshot`, then register, then `sc validate` and `sc check --all`, and compare counts with the pre-run numbers.
