# Stitch Tool Capability Map

Verified against the official Google Stitch MCP at `https://stitch.googleapis.com/mcp` on 2026-05-17 (server `StatelessServer` / protocol `2025-06-18`). 14 tools exposed.

Third-party MCP servers, the Stitch SDK, local proxies, or Antigravity wrappers may rename or omit tools. Always discover at runtime; match by **capability**, not literal string.

## MCP tool naming in agent runtimes

Agent runtimes wrap server tools with a prefix. In Claude Code the wrapped form is `mcp__stitch__<tool>` (e.g. `mcp__stitch__generate_screen_from_text`). The names in the table below are the **server-side** names — your runtime exposes the wrapped form.

## Required Runtime Behavior

1. **List the MCP tools your runtime actually exposes.** If none look Stitch-related, jump to the paste-export fallback in `workflows/stitch-design-handoff.md` Step 4c.
2. Match each available tool to a capability below by behavior, not exact string. Tool authors may rename.
3. Verify the tool's input schema before calling — enums in particular drift between releases.

## Canonical tool list (official Google Stitch MCP, 14 tools)

### Project management

| Tool | Annotation | Required inputs | Purpose |
|---|---|---|---|
| `list_projects` | read-only | — | List all accessible Stitch projects. Optional `filter`. |
| `get_project` | read-only | `name` | Retrieve project details by name. |
| `create_project` | destructive | — | Create a new project. Optional `title`. |

### Screen reading

| Tool | Annotation | Required inputs | Purpose |
|---|---|---|---|
| `list_screens` | read-only | `projectId` | List all screens in a project. |
| `get_screen` | read-only | `name`, `projectId`, `screenId` | Retrieve a single screen including its Asset (image) and Design data. |

### Screen generation and revision

| Tool | Annotation | Required inputs | Purpose |
|---|---|---|---|
| `generate_screen_from_text` | destructive | `projectId`, `prompt` | Generate a new screen from a text brief. Returns `outputComponents` array containing Screen, Asset, Design, optionally DesignSuggestion. Optional `deviceType`, `modelId`, `designSystem`. |
| `edit_screens` | destructive | `projectId`, `selectedScreenIds`, `prompt` | Revise existing screens with a focused prompt. Use for one or two changes at a time per the workflow revise loop. |
| `generate_variants` | destructive | `projectId`, `selectedScreenIds`, `prompt`, `variantOptions` | Generate variants of existing screens. `variantOptions.variantCount` is 1-5 (default 3). |

### Design system

| Tool | Annotation | Required inputs | Purpose |
|---|---|---|---|
| `list_design_systems` | read-only | — | List all design systems for a project. Takes `projectId`. |
| `upload_design_md` | destructive | `projectId`, `designMdBase64` | Upload a DESIGN.md file as base64. |
| `create_design_system` | destructive | `designSystem` | Create a design system from a structured `designSystem` payload. |
| `create_design_system_from_design_md` | destructive | `projectId`, `selectedScreenInstance` | Generate a design system from a previously uploaded DESIGN.md. |
| `update_design_system` | destructive | `name`, `projectId`, `designSystem` | Update an existing design system. |
| `apply_design_system` | destructive | `projectId`, `selectedScreenInstances`, `assetId` | Apply a design system to a list of screens. |

## Critical enums (verified)

### `deviceType`

```
DEVICE_TYPE_UNSPECIFIED | MOBILE | DESKTOP | TABLET | AGNOSTIC
```

**Gotcha (house rule):** there is no iOS-specific or iPadOS-specific value. `MOBILE` covers iPhone *and* Android phones; `TABLET` covers iPad *and* Android tablets. Stitch will happily produce Material / Tailwind / web-card output at `MOBILE`. The Apple-native guardrails in your brief (`templates/stitch-apple-native-brief.md`) and the rubric in `stitch-output-review.md` carry the entire load — `deviceType` alone does not constrain Stitch to Apple HIG. Always pair `MOBILE` with the iPhone exclusion list; always pair `TABLET` with the iPad exclusion list.

### `modelId`

```
MODEL_ID_UNSPECIFIED | GEMINI_3_PRO | GEMINI_3_FLASH (deprecated) | GEMINI_3_1_PRO
```

Omit unless you have a reason — the server picks the current best. Avoid `GEMINI_3_FLASH` (deprecated).

### `variantOptions.creativeRange` (for `generate_variants`)

```
CREATIVE_RANGE_UNSPECIFIED | REFINE | EXPLORE | REIMAGINE
```

Map to workflow stage:

- **REFINE** — Step 6 focused revise loop ("remove the FAB, place Add in toolbar"). Subtle refinements close to the original.
- **EXPLORE** — Step 3 default variants. Balanced exploration. Stitch default.
- **REIMAGINE** — only when current direction is fundamentally wrong and you want a clean break.

### `variantOptions.aspects`

```
LAYOUT | COLOR_SCHEME | IMAGES | TEXT_FONT | TEXT_CONTENT
```

Useful for the workflow's "extract visual DNA only" step. To explore palette without disturbing layout, pass `aspects: ["COLOR_SCHEME"]`. To explore typography pairings, `aspects: ["TEXT_FONT"]`. Empty array means Stitch may vary any aspect (the default).

### `variantOptions.variantCount`

`1-5`. Default `3`. Matches the workflow's "3 variants by default" guidance — no override needed.

## Output shape

`generate_screen_from_text` and `generate_variants` return `outputComponents`, an array containing any of:

- `Screen` — structured screen definition with components, regions, bounding boxes
- `Asset` — generated image (this is what you review visually)
- `Design` — structured design metadata
- `DesignSuggestion` — additional design directions
- `DesignSystem` — generated or referenced design system
- `DesignTheme` — color mode, fonts, color variant
- `File` — supporting files
- `PrototypeLink` — prototype URLs
- `Question` / `QuestionsAsked` — clarification questions Stitch wants the user to answer
- `ProgressUpdate` / `ProgressUpdates` — long-call progress

Plus `projectId` and `sessionId`. The image and the structured data come back together — there is no separate "fetch image" call.

## Rules

1. **Discover tools first.** Listed tool names are verified as of 2026-05-17; treat as the contract, but re-list at runtime if anything fails.
2. **Prefer the Asset (image) for visual review.** The Design / DesignSuggestion structured data is useful for extracting tokens but should not be ported as-is into SwiftUI view hierarchy.
3. **Never copy DesignSystem structure straight into SwiftUI.** Use it as input to `design-md-swiftui.md` token guidance, then write SwiftUI extensions.
4. **For revisions, prefer `edit_screens` with REFINE-style language over `generate_variants`** — the latter generates fresh, the former preserves what works.
5. **If a tool fails with a timeout**, the operation may still complete server-side. Re-run `get_screen` before retrying generation.
6. **If no Stitch MCP server is configured at all**, ask the user to paste/export the Stitch result (screenshot file, exported HTML, project share link, or plain-text description). The review rubric works against any input shape.

## Capability-Based Workflow

Use this order:

1. `list_projects` or `create_project` (or pick a known `projectId`)
2. `generate_screen_from_text` for first pass, or `generate_variants` for further variants
3. Read `outputComponents` Asset for the image; Design/DesignSystem for tokens
4. `edit_screens` with REFINE-style prompts for focused revisions
5. Review per `references/stitch-output-review.md`
6. Extract visual DNA (palette, typography, density, hierarchy)
7. Update `DESIGN.md` / `DESIGN-swiftui.md` (use `upload_design_md` if syncing back to Stitch)
8. Translate to SwiftUI — native containers, no DOM porting

## Failure Handling

If a Stitch MCP call fails:

- Do not invent the result.
- Report the missing capability or error.
- For timeouts: call `get_screen` to check whether the server completed anyway.
- Continue with available artifacts.
- Ask the user to paste/export only if recovery isn't possible.

## Paste-Export Fallback

If MCP discovery returns no Stitch tools at all (e.g. project doesn't have the server enabled, the user disabled it, or there is no Stitch MCP installed), stop calling tools entirely and ask the user for any of:

- a screenshot file or URL
- exported HTML
- a Stitch project share link
- a plain-text screen description

The review rubric in `stitch-output-review.md` works against any of these input shapes. Image-only critique is explicitly allowed — note that as a limitation in the review output rather than blocking on it.
