# Stitch Design Handoff Workflow

Use this workflow when handing a SwiftUI screen brief off to Google Stitch (or any Stitch MCP / SDK / Antigravity integration) for visual variants, then translating accepted ideas back into native SwiftUI.

## Purpose

Use Google Stitch for visual ideation only. Do not use Stitch as the source of truth for SwiftUI architecture, navigation, state, persistence, accessibility correctness, or implementation structure.

## Non-Negotiable Rules

These are the 10 rules the rest of this workflow enforces. They are echoed in `references/stitch-output-review.md` as automatic rejection conditions.

1. Never translate Stitch HTML/CSS structure directly into SwiftUI view hierarchy.
2. Use Stitch output as visual evidence only.
3. The SwiftUI agent owns containers, navigation, state, accessibility, and platform correctness.
4. Stitch must not choose the app architecture.
5. Stitch must not choose persistence model, SwiftData/Core Data model, reducer/effect architecture, or navigation ownership.
6. Stitch must not override Apple HIG, SwiftUI-native navigation structure, or accessibility requirements.
7. If Stitch returns web/Material/Tailwind/SaaS patterns, reject or revise before implementation.
8. Prefer native Apple containers over arbitrary custom layouts.
9. Prefer semantic SwiftUI structures over pixel-perfect copies.
10. Validate every accepted design against an Apple-native rubric before code generation.

Rule 1 is the critical rule. Rules 4–6 are house-rule sharpenings of HIG. See `references/stitch-output-review.md` for the rubric and severity scheme.

## Workflow Overview

1. Gather product and screen context.
2. Define native SwiftUI structure locally before contacting Stitch.
3. Select platform constraints.
4. Compile a short Apple-native Stitch brief.
5. Append hard exclusions.
6. Ask Stitch for variants.
7. Fetch Stitch output using available MCP or SDK tools.
8. Review output against Apple-native rubric.
9. Request focused revisions if needed.
10. Extract visual DNA only.
11. Update DESIGN.md or DESIGN-swiftui.md.
12. Translate into native SwiftUI using standard containers.

## Step 1: Define Native Structure First

Before prompting Stitch, decide the native structure:

- Use `TabView` for flat peer sections.
- Use `NavigationStack` for linear drill-down.
- Use `NavigationSplitView` for iPad collection/detail.
- Use `List` or `Form` for scannable content, settings, and grouped controls.
- Use `sheet` for bounded modal tasks.
- Use `inspector` for secondary editing on iPad/macOS-style layouts.
- Use toolbars for primary navigation actions.
- Use confirmation dialogs for destructive choices.
- Use native search placement where appropriate.

Do not ask Stitch to invent the structure from scratch. See `references/navigation-patterns.md` for the container decision table.

## Step 2: Keep Prompts Short and Plain

Stitch generally behaves better when prompts are direct and focused.

Prefer:

- One screen at a time.
- One layout goal at a time.
- One or two refinements per edit.
- Plain language.
- Concrete exclusions.

Avoid:

- Huge all-app prompts.
- Dense XML-like instruction blocks.
- Contradictory style requests.
- Asking for architecture and visual design in the same prompt.

## Step 3: Generate Variants

Ask for 3 variants by default:

1. Conservative native.
2. Dense iPad-aware.
3. Expressive but still Apple-native.

Variants must differ structurally or behaviorally, not merely by color.

Use `templates/stitch-apple-native-brief.md` as the starting template. See `references/stitch-examples.md` for 5 worked example briefs and `references/stitch-handoff-format.md` for the canonical format.

## Step 4: Fetch Output

**Discover first, then call.** Do not assume any Stitch MCP server is installed or which tool names it exposes. Most agent environments do not have a Stitch MCP at all; the most common path here is the paste-export fallback below.

### 4a. Discovery

1. List currently available MCP tools (in Claude Code: inspect the `mcp__*` tool surface; in other agents, list configured MCP servers).
2. Match each tool against the capability table in `references/stitch-tool-capability-map.md`. The names there are illustrative possibilities, not a canonical contract — match by *capability* (create project / generate screen / fetch image / fetch code / fetch metadata), not by literal string.
3. Note the actual MCP tool prefix the agent runtime uses (Claude Code wraps server tools as `mcp__<server>__<tool>` — call the wrapped name, not the bare name from the capability table).

### 4b. If a Stitch MCP server is available

Fetch any combination of:

- screenshot/image (preferred for review)
- HTML/CSS/code (parse for anti-patterns, do not port structure)
- design metadata
- screen description
- project or screen context

Prefer image plus code/metadata when both exist. Never rely solely on generated HTML for review.

### 4c. Paste-export fallback (most common path)

If discovery returns no matching capabilities for fetch-screen-image / fetch-screen-code / fetch-project-metadata — or if no Stitch MCP server is configured at all — stop calling tools entirely and ask the user for any of:

- a screenshot file or URL
- exported HTML
- a Stitch project share link
- a plain-text screen description

The review rubric in `references/stitch-output-review.md` works against any of these input shapes. Image-only critique is explicitly allowed; note that as a limitation in the review output rather than blocking on it.

## Step 5: Review Before Implementation

Review Stitch output using `references/stitch-output-review.md`.

Fast-fail if the design contains:

- Material Floating Action Button
- hamburger menu on iPhone
- custom tab bar
- custom navigation bar
- dashboard grid as primary iPhone structure
- hero CTA inside app workflow
- glass content cards
- glass-on-glass
- decorative gradient blob background
- tiny gray essential text
- hover-only affordances
- iPad that is just stretched iPhone
- right-rail chatbot on iPhone

The full machine-readable rejection table lives in `data/stitch-negative-constraints.csv`.

## Step 6: Revise in Focused Loops

When revising, ask for one or two changes at a time.

Example:

Bad:
"Make this more native, more accessible, less web, better colors, fix iPad, add empty state."

Good:
"Remove the bottom-right Floating Action Button. Place the Add action in the top trailing navigation bar. Keep the rest of the layout unchanged."

See `references/stitch-negative-prompts.md` for 5 validation experiments showing the revise loop in action.

## Step 7: Extract Visual DNA Only

Allowed to extract:

- color palette
- typography hierarchy
- spacing rhythm
- visual density
- icon direction
- grouping style
- empty/error/loading visual treatment
- tone and mood
- useful layout inspiration

Must discard:

- DOM hierarchy
- CSS class structure
- absolute positioning
- web breakpoints
- Tailwind utility structure
- React component structure
- custom navigation chrome
- hover states
- web dashboard layout assumptions

## Step 8: Translate to SwiftUI

Implement with native SwiftUI structures. Do not copy Stitch layout literally.

Examples:

- Web sidebar on iPad → `NavigationSplitView`
- Web card list → `List` / `ScrollView` with semantic sections
- Floating Add button → toolbar `Button`
- Right rail assistant → iPad `inspector`, iPhone `sheet`
- Dashboard tiles on iPhone → single-column list or grouped sections
- Glass card → opaque grouped background
- Web modal → SwiftUI `sheet`

For the iPad side, cross-reference `references/ipad-layout.md`. For Liquid Glass placement, defer to `references/liquid-glass.md`. For project tokens, defer to the `swiftui-design-tokens` sibling skill.

## Output Contract

When completing a Stitch workflow, return:

1. Brief sent to Stitch.
2. Variants requested.
3. Review findings.
4. Rejected patterns, if any.
5. Accepted visual ideas.
6. SwiftUI-native translation plan.
7. DESIGN.md / DESIGN-swiftui.md changes.
8. Implementation guidance.

## Critical Rule

Never translate Stitch HTML/CSS structure directly into SwiftUI view hierarchy.

Use Stitch output as visual evidence only. The SwiftUI agent owns containers, navigation, state, accessibility, and platform correctness.

## Failure Conditions

Restart this workflow if:

- the SwiftUI translation reads as a DOM tree
- the iPhone screen reverted to a dashboard grid
- the iPad screen is only a stretched iPhone layout
- Liquid Glass appears on content surfaces or dense text
- accessibility coverage shrank vs the existing screen
- the user cannot identify the primary action within a glance
