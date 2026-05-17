---
name: swiftui-native-ux
description: >-
  Use when designing, building, reviewing, or restructuring SwiftUI screens for
  iPhone or iPad — picking between TabView, NavigationStack, or
  NavigationSplitView; deciding empty/detail pane states; adapting iPhone
  layouts to iPad; deciding sheet vs inspector vs sidebar vs pinned pane;
  rewriting a screen that "doesn't feel native" or feels like a
  web/React/Material/Tailwind/dashboard port; restructuring settings, home,
  list/detail, or now-playing screens; or auditing a SwiftUI view for Dynamic
  Type, VoiceOver, Reduce Transparency, Liquid Glass, or visual hierarchy.
  Trigger on SwiftUI UI questions targeting iOS/iPadOS (any version, including
  iOS 26), Apple-native look and feel, iPad multi-pane decisions,
  sheet/inspector/popover choice, accessibility review of a SwiftUI screen, or
  asking what's "wrong" with an iPhone/iPad screen. Skip for pure backend,
  data modeling, networking, macOS-only AppKit, UIKit-only layout, or
  non-Apple platforms.
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - Glob
---

# SwiftUI Native UX

Design, generate, critique, and revise SwiftUI interfaces so they feel native to Apple platforms instead of like React, Tailwind, Material, or SaaS dashboards ported into SwiftUI.

This skill is a capability layer, not a design textbook. Keep the always-on core small. Load references and workflows only when the task needs them.

## Quick Decision Tree

Pick a workflow before reading the rest of this file.

- Asked to generate a new screen or component → `workflows/generate-new-screen.md` (+ `references/generation-output-format.md`).
- Reviewing existing SwiftUI code or a screenshot → `workflows/critique-existing-swiftui.md` (+ `references/critique-rubric.md`).
- iPhone layout that needs an iPad version → `workflows/adapt-iphone-to-ipad.md` (+ `references/ipad-layout.md`).
- SwiftUI screen that smells like React / Tailwind / Material / SaaS dashboard → `workflows/rewrite-web-ui-native.md` (+ `references/anti-web-smells.md`).
- Screen "works but looks bland / generic / noisy" → `workflows/polish-visual-hierarchy.md` (+ `references/visual-hierarchy.md`).
- Accessibility / Dynamic Type / VoiceOver / Reduce Motion concerns → `workflows/audit-accessibility.md` (+ `references/accessibility.md`).
- Liquid Glass question (where it belongs, where it doesn't) → `references/liquid-glass.md`.
- Choosing between TabView / NavigationStack / NavigationSplitView / sheet / inspector → `references/navigation-patterns.md`.

## Target Baseline

Assume new code targets:

- iOS 26
- iPadOS 26
- macOS 26 Tahoe when Mac-class behavior matters
- Xcode 26
- Swift 6.2
- SwiftUI
- Observation
- SwiftData where appropriate
- NavigationStack
- NavigationSplitView
- TabView
- Liquid Glass with restraint

Do not use macOS 27 as the current baseline. Mention it only as future-looking rumor or compatibility planning.

## When To Use

Use this skill when the task involves:

- creating or rewriting SwiftUI screens
- reviewing SwiftUI UI code
- adapting iPhone UI to iPad
- choosing navigation structure
- improving visual hierarchy
- making UI more Apple-native
- reducing generic AI-generated UI
- removing web, Tailwind, React, Material, or dashboard residue
- using Liquid Glass
- auditing accessibility, Dynamic Type, motion, transparency, localization, or VoiceOver order
- generating previews or state variants for UI

Do not use this skill for backend architecture, data modeling alone, networking alone, or non-UI code unless the UI contract is affected.

## Sibling Skills — Defer When

This skill owns iPhone and iPad SwiftUI native UX. Several adjacent skills own neighboring territory; defer to them rather than re-deriving here. If both apply, this skill leads on the design decision and the sibling fills in the API or platform detail.

- tvOS focus engine, focus-ring clipping on tvOS, `.onExitCommand` Menu dismissal, tvOS settle delays → `apple-tvos`.
- Cross-platform Apple compatibility, `#if os(...)` vs `#if canImport(...)`, Mac Catalyst sidebar / NSToolbar placement, `TabView .page` vs `.automatic` per platform → `apple-multiplatform`.
- SwiftUI hangs, hitches, view-update storms, `_printChanges()`, Instruments `.trace` analysis, performance-as-correctness → `swiftui-expert-skill`.
- `fileExporter`, `Transferable`, `ShareLink`, sandbox entitlements, "fileExporter does nothing on macOS" silent failure → `swiftui-file-export`.
- `@Model`, `ModelContext`, `ModelContainer`, `FetchDescriptor`, cascade-delete relationships, SwiftData migrations, bundled seed data → `swiftdata-persistence`.
- `DropDelegate`, `.onDrop`, drop-priority routing, NSItemProvider extraction, Chrome image drag (`public.tiff` / `public.html` / `public.url`) → `swiftui-drag-drop`.
- `async`/`await`, `@MainActor`, `Sendable`, actor isolation, "capture of self with non-sendable type" warnings → `swift-concurrency`.
- Project-specific design-token conventions (named spring/timed motion tokens, project Palette, repo-prescriptive button-style table) → `swiftui-design-tokens`.
- `function_body_length` / `type_body_length` / `file_length` / `cyclomatic_complexity` SwiftLint violations and justified `// swiftlint:disable:next` rationale → `swift-linting`.
- Splitting a Swift file approaching the `file_length` limit while preserving visibility and build correctness → `swift-file-splitting`.
- XCUITest UI automation, accessibility-identifier contracts for tests, `.xctestrun` selective execution, "Executed 0 tests" → `xctest-ui-testing`.
- Swift Testing (unit tests with `@Test`/`#expect`, parameterized tests, traits and tags) → `swift-testing-expert`.
- Input validation, path traversal, URL allowlists, CSV sanitization, AI prompt sanitization, iOS Data Protection — security review of the inputs that feed the UI → `ios-security-hardening`.
- Visual regression / screenshot analysis against project tokens, glass-on-glass auto-detection in batch → `visual-audit`.
- React / Tailwind / shadcn / Next.js / generic web UI work — this skill does not handle web stacks → `ui-ux-pro-max`.

When the task fits one of the rows above more squarely than it fits this skill's iPhone/iPad design scope, hand off and stop. When the task is mostly design but needs one detail from a sibling (e.g. a Liquid Glass screen with a fileExporter button), use both: this skill drives the screen shape; the sibling fills the detail.

## Always Apply

- Prefer native Apple containers before custom UI.
- Choose navigation structure before styling.
- Use `NavigationStack` for linear drill-down flows.
- Use `NavigationSplitView` for collection/detail layouts when width supports it.
- Use `TabView` for flat top-level app sections.
- Use sheets for bounded tasks.
- Use inspectors for secondary editing on iPad and Mac.
- Treat iPhone and iPad as different presentations of the same task.
- Keep content readable before making it glassy.
- Use Liquid Glass for controls, navigation, tab bars, sidebars, toolbars, and accessory surfaces.
- Reject Liquid Glass as decorative content-card or full-screen background treatment.
- Express hierarchy through layout, grouping, typography, system materials, semantic color, and native containers.
- Prefer semantic typography, Dynamic Type, system colors, SF Symbols, localization-safe layout, and accessibility variants.
- Prefer Observation for new SwiftUI UI state, but allow legacy `ObservableObject` when justified.
- Prefer SwiftData for simple local Apple-platform persistence, but do not override an existing persistence architecture.
- Reject hero sections, dashboard grids, hamburger menus, Material FABs, Tailwind spacing reflexes, right-rail AI panels, hover-only affordances, decorative gradient blobs, and custom navigation chrome when native containers fit.
- Critique before generating.
- Self-review generated UI against the rubric before final output.

## Hard Rejections

Reject these unless the user explicitly asks for them and the tradeoff is documented:

- custom tab bars when `TabView` fits
- custom navigation bars when `NavigationStack` or `NavigationSplitView` fits
- custom back buttons that break edge-swipe navigation
- hamburger menus on iPhone
- Material Floating Action Buttons
- dashboard grids on iPhone
- hero sections inside app workflows
- decorative gradient backgrounds carrying hierarchy
- glass-on-glass
- thin or ultra-light text over translucent material
- hover-only affordances on touch UI
- icon-only buttons without accessibility labels
- arbitrary Tailwind-style spacing such as `.padding(11)` or `.padding(15)`
- hard-coded tiny body text
- fixed-height rows that break Dynamic Type
- forced dark mode without a user setting
- networking or persistence side effects inside `View.body`

## Source Use Policy

Apple sources define platform behavior.

Research sources explain model failure modes.

Practitioner sources provide lenses.

Web sources provide translated concepts or anti-patterns.

Do not treat all sources as equal. A practitioner blog can sharpen judgment, but it should not overrule Apple platform behavior. A web design system can teach hierarchy, but it must not leak Tailwind, Material, or SaaS-dashboard structure into SwiftUI.

## Load References As Needed

- Native Apple feel: `references/apple-native-design.md`
- iPhone layout: `references/iphone-layout.md`
- iPad layout: `references/ipad-layout.md`
- Navigation decisions: `references/navigation-patterns.md`
- Visual polish: `references/visual-hierarchy.md`
- Accessibility: `references/accessibility.md`
- Liquid Glass: `references/liquid-glass.md`
- Web residue: `references/anti-web-smells.md`
- Review scoring: `references/critique-rubric.md`
- Generated code contract: `references/generation-output-format.md`
- Expert critique passes: `references/expert-lenses.md`
- Evidence tiers and source policy: `references/source-architecture.md`

## Load Workflows As Needed

- New screen generation: `workflows/generate-new-screen.md`
- Existing UI critique: `workflows/critique-existing-swiftui.md`
- iPhone to iPad adaptation: `workflows/adapt-iphone-to-ipad.md`
- Web-style UI rewrite: `workflows/rewrite-web-ui-native.md`
- Visual hierarchy polish: `workflows/polish-visual-hierarchy.md`
- Accessibility audit: `workflows/audit-accessibility.md`

## Default Workflow

1. Identify the user goal.
2. Identify platform and device context.
3. Identify task topology: flat tabs, linear drill-down, collection/detail, editor, capture, or settings.
4. Critique current/requested design before generating.
5. Choose native Apple structure.
6. Define core states: empty, loading, content, error, offline/permission where relevant.
7. Define accessibility risks.
8. Define iPhone and iPad behavior separately.
9. Produce SwiftUI component breakdown.
10. Generate or revise code.
11. Self-review against `critique-rubric.md`.
12. Remove decorative elements that do not carry meaning, structure, navigation, or feedback.

## Output Contract

When generating UI, provide:

- Native structure choice and reason.
- State model and state coverage.
- Component breakdown.
- SwiftUI code.
- Preview matrix when practical.
- Accessibility notes.
- Anti-web-smell self-review.
- Any tradeoffs or justified deviations.

When critiquing UI, provide:

- High-level verdict.
- Rubric scores.
- Severe issues first.
- Concrete fixes.
- Optional rewrite plan.
- Code only when asked or clearly useful.

## Tone Of Review

Be direct. Prefer small, concrete rules. Avoid theory dumps.

Use reject/prefer pairs.

Example:

Prefer:
`List { Section { ... } }` with native row affordances.

Reject:
Custom card grids for scannable iPhone content.

## Evidence Discipline

Use Apple HIG, Apple Developer documentation, WWDC sessions, and Apple sample code as primary authority.

Use expert practitioners as critique lenses.

Use AI/LLM research to justify anti-generic rules.

Use web/design-system sources only after translating away React, Tailwind, Material, SaaS dashboards, and landing-page assumptions.

When evidence is weak, write the rule as a heuristic, not a fact.
