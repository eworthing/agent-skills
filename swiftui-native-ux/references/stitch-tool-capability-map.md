# Stitch Tool Capability Map

Stitch integrations may expose different tool names depending on whether the workflow uses:

- official Google Stitch MCP
- Stitch SDK
- third-party MCP server
- local proxy
- Antigravity workflow
- Claude Code / Cursor / Gemini CLI / Codex / OpenCode integration

Do not assume exact tool names.

## Required Runtime Behavior

Before invoking Stitch tools, discover available MCP tools or inspect the configured server documentation.

Map available tools to capabilities:

| Capability | Possible Names / Shapes |
|---|---|
| Create project | `create_project`, `createStitchProject`, `project_create` |
| Generate screen from text | `generate_screen`, `generate_screen_from_text`, `create_screen`, `screen_generate` |
| Edit screen | `edit_screen`, `update_screen`, `revise_screen` |
| Generate variants | `generate_variants`, `create_variants`, `variant_generate` |
| Fetch screen code | `get_screen_code`, `getHtml`, `screen_code`, `fetch_code` |
| Fetch screen image | `get_screen_image`, `getImage`, `screen_image`, `fetch_image` |
| Fetch project metadata | `get_project`, `project_context`, `list_screens` |
| Fetch design context | `get_design_dna`, `get_design_context`, `design_tokens`, `generate_design_md` |

## Rules

1. Discover tools first.
2. Prefer screenshot/image plus code/metadata when available.
3. Never rely only on generated HTML for review.
4. Never copy HTML/CSS structure into SwiftUI.
5. If only image output is available, critique visually and ask for a concise design rationale.
6. If only code output is available, parse for anti-patterns but do not port structure.
7. If no fetch tool exists, ask the user to paste/export the Stitch result.

## Capability-Based Workflow

Use this order:

1. create or select project
2. generate screen or variants
3. fetch image/screenshot
4. fetch code/HTML if available
5. fetch design metadata if available
6. review
7. revise
8. extract visual DNA
9. update DESIGN.md / DESIGN-swiftui.md
10. translate to SwiftUI

## Failure Handling

If a Stitch MCP call fails:

- Do not invent the result.
- Report the missing capability.
- Continue with available artifacts.
- Ask for exported screenshot/code only if needed.

## Paste-Export Fallback

If MCP discovery returns no matching tools for any of fetch-screen-code / fetch-screen-image / fetch-project-metadata, stop calling tools entirely. Ask the user for any of:

- a screenshot file or URL
- exported HTML
- a Stitch project share link
- a plain-text screen description

The review rubric in `stitch-output-review.md` works against any of these input shapes. Image-only critique is explicitly allowed — note that as a limitation in the review output rather than blocking on it.
