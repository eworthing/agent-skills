---
name: swiftui-native-ux
description: >-
  Use when designing, reviewing, or restructuring SwiftUI screens for iPhone or
  iPad — picking TabView vs NavigationStack vs NavigationSplitView; adapting
  iPhone layouts to iPad; sheet vs inspector vs sidebar vs popover choice;
  rewriting screens with web gravity (React / Tailwind / Material /
  SaaS-dashboard ports); auditing Dynamic Type, VoiceOver, Reduce Transparency,
  Liquid Glass, or visual hierarchy. Also use for Google Stitch or Stitch MCP
  visual variants, DESIGN.md / DESIGN-swiftui.md tokens, or translating Stitch
  design-to-code output to SwiftUI. Trigger on iOS/iPadOS 26–27 SwiftUI
  questions, Apple-native look and feel, or asking what's "wrong" with an
  iPhone/iPad screen. Skip pure backend, data modeling, networking, macOS-only
  AppKit, UIKit-only layout, non-Apple platforms.
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

## Contents

- Quick Decision Tree
- Target Baseline (iOS / iPadOS / SwiftUI versions)
- When To Use
- Sibling Skills — Defer When
- Always Apply
- Hard Rejections
- Source Use Policy
- Default Workflow
- Output Contract
- Tone Of Review (prefer/reject example pairs)

## Quick Decision Tree

Pick a workflow before reading the rest of this file.

- Asked to generate a new screen or component → `workflows/generate-new-screen.md`.
- Reviewing existing SwiftUI code or a screenshot → `workflows/critique-existing-swiftui.md`.
- iPhone layout that needs an iPad version → `workflows/adapt-iphone-to-ipad.md`.
- SwiftUI screen with web gravity (React / Tailwind / Material / SaaS dashboard) → `workflows/rewrite-web-ui-native.md`.
- Screen "works but looks bland / generic / noisy" → `workflows/polish-visual-hierarchy.md`.
- Accessibility / Dynamic Type / VoiceOver / Reduce Motion concerns → `workflows/audit-accessibility.md`.
- Liquid Glass question (where it belongs, where it doesn't) → `references/liquid-glass.md`.
- Handing a screen off to Google Stitch / Stitch MCP, writing DESIGN.md / DESIGN-swiftui.md, or translating Stitch design-to-code output to SwiftUI → `workflows/stitch-design-handoff.md` (it loads its own references as needed: `references/stitch-handoff-format.md`, `references/stitch-output-review.md`, `references/stitch-tool-capability-map.md`, `references/stitch-examples.md`, `references/stitch-negative-prompts.md`, `references/design-md-swiftui.md`).
- Choosing between TabView / NavigationStack / NavigationSplitView / sheet / inspector → `references/navigation-patterns.md`.
- Designing an iPhone-only screen, or checking iPhone density, spacing, and touch targets → `references/iphone-layout.md`.
- Designing or critiquing an iPad layout at regular width (split view, inspectors, selection, keyboard, multiwindow) → `references/ipad-layout.md`.
- Need the baseline for what "native Apple feel" actually means before deciding anything → `references/apple-native-design.md`.
- A critique needs more depth than the rubric alone gives (multiple expert passes) → `references/expert-lenses.md`.
- None of the above, or the request is ambiguous → default to `workflows/critique-existing-swiftui.md` when existing SwiftUI code or a screenshot is in view; otherwise ask one clarifying question before choosing.

## Target Baseline

Assume new code targets iOS 27 / iPadOS 27, macOS 27 when Mac-class behavior matters, Xcode 27, Swift 6.2.

Generation 26 is the prior generation, not the target. When a 27-only API carries the design decision, use it and gate `if #available(iOS 27, *)` for older deployment targets — see `references/navigation-patterns.md`.

## When To Use

Triggers live in this skill's `description` (the single source) — do not restate them here.

Scope boundary: do not use this skill for backend architecture, data modeling alone, networking alone, or non-UI code — **unless the UI contract is affected**.

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
- React / Tailwind / shadcn / Next.js / generic web UI work — this skill does not handle web stacks → `ui-ux-pro-max`.

When the task fits one of the rows above more squarely than it fits this skill's iPhone/iPad design scope, hand off and stop. When the task is mostly design but needs one detail from a sibling (e.g. a Liquid Glass screen with a fileExporter button), use both: this skill drives the screen shape; the sibling fills the detail.

When running the Stitch workflow (`workflows/stitch-design-handoff.md`), this skill owns brief construction, output critique, and SwiftUI translation, but still defers to: `swiftui-design-tokens` for project-specific token application, `swiftui-expert-skill` for final SwiftUI code review and Liquid Glass API depth, and `apple-multiplatform` for any `#if os(...)` gating that comes out of the translation. Do not let Stitch override those skills.

## Always Apply

- Prefer native Apple containers before custom UI.
- Choose navigation structure before styling.
- Treat iPhone and iPad as different presentations of the same task.

Container decisions: `references/navigation-patterns.md`. Glass placement: `references/liquid-glass.md`. Everything else lives in the references the decision tree routes to.

## Hard Rejections

The always-on guardrails. The full rejection inventory — every pattern, severity, native alternative, and the documented-tradeoff escape hatch — lives in `references/anti-web-smells.md`.

Reject unless the escape hatch in `references/anti-web-smells.md` applies:

- custom tab bar or navigation bar when `TabView` / `NavigationStack` / `NavigationSplitView` fits
- hamburger menu on iPhone
- Material Floating Action Button
- dashboard grid as primary iPhone structure
- glass content cards or glass-on-glass
- icon-only buttons without accessibility labels
- networking or persistence side effects inside `View.body`

## Source Use Policy

Do not treat all sources as equal. Rank them:

- **Apple** (HIG, Developer docs, WWDC sessions, sample code) — primary authority; defines platform behavior.
- **Research** (AI/LLM) — explains model failure modes; justifies anti-generic rules.
- **Practitioner** — critique lenses that sharpen judgment, but never overrule Apple platform behavior.
- **Web / design systems** — translated concepts and anti-patterns only, and only after translating away React, Tailwind, Material, SaaS-dashboard, and landing-page assumptions. A web design system can teach hierarchy, but must not leak its structure into SwiftUI.

Stitch sources rank at the tool tier — see `workflows/stitch-design-handoff.md` (Purpose).

When evidence is weak, write the rule as a heuristic, not a fact. For the full evidence-tier ranking and confidence scale, see `references/source-architecture.md`.

## Default Workflow

1. Identify the user goal.
2. Identify platform and device context.
3. Identify task topology: flat tabs, linear drill-down, collection/detail, editor, capture, or settings.
4. Critique current/requested design before generating.
5. Choose native Apple structure per `references/navigation-patterns.md`.
6. Define core states: empty, loading, content, error, offline/permission where relevant.
7. Define accessibility risks.
8. Define iPhone and iPad behavior separately.
9. Produce SwiftUI component breakdown.
10. Generate or revise code.
11. Self-review against `references/critique-rubric.md`, including the reductionist pass — remove decoration that carries no meaning, structure, navigation, feedback, or confidence.

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

Output scaffold: `references/generation-output-format.md`. Critique output: `references/critique-rubric.md` (Required Review Output). Stitch workflow output: `workflows/stitch-design-handoff.md` (Output Contract).

## Tone Of Review

Be direct. Prefer small, concrete rules. Avoid theory dumps.

**Lists vs. card grids (iPhone scannable content)**
- Prefer: `List { Section { ... } }` with native row affordances.
- Reject: Custom card grids for scannable iPhone content.

**Navigation root on iPad**
- Prefer: `NavigationSplitView` when the topology is collection/detail; `TabView` with `.tabViewStyle(.sidebarAdaptable)` when destinations are flat peers — iPadOS 18+ adapts it to a sidebar at regular width.
- Reject: a collection/detail hierarchy stretched across a full-width `NavigationStack`, which slides the whole canvas away on selection. The defect is the topology mismatch, not the container.

**Liquid Glass surfaces**
- Prefer: System-provided `.glassBackgroundEffect()` and toolbar surfaces with Reduce Transparency support.
- Reject: Hand-built blur stacks (custom `Material` + `.opacity` recipes) that ignore Reduce Transparency / Increase Contrast.
