# Stitch Apple-Native Handoff Format

Use this format when creating a prompt for Stitch. Keep the prompt short enough to remain focused. Prefer one screen per prompt.

The reusable template lives at `templates/stitch-apple-native-brief.md`. This file is the spec the template implements.

## Template

```
Create a high-fidelity native iOS/iPadOS app screen concept.

Platform:
- Target iOS 26 and iPadOS 26.
- Design for native SwiftUI implementation.
- Use Apple-native interaction and layout patterns.

Screen:
- [screen name]

User goal:
- [what the user is trying to accomplish]

Task topology:
- [linear drill-down / settings form / collection-detail / playback controls / creation flow / review flow]

Native Apple structure:
- [NavigationStack / NavigationSplitView / TabView / List / Form / sheet / inspector / toolbar]

Content hierarchy:
1. [primary content]
2. [secondary content]
3. [supporting metadata]
4. [empty/error/loading state content]

Primary action:
- [action]
- Placement: [top trailing toolbar / bottom toolbar / prominent row / sheet confirmation]

Secondary actions:
- [actions and placement]

States to represent:
- Loaded
- Empty
- Loading
- Error
- Permission denied
- Offline, if relevant
- Selection state, if relevant
- Editing state, if relevant

iPhone behavior:
- Compact width.
- One primary column.
- No dashboard grid as primary structure.
- Controls must be reachable and touch-friendly.
- Respect safe areas and keyboard.

iPad behavior:
- Use regular-width space intentionally.
- Prefer NavigationSplitView for collection/detail.
- Use inspector for secondary metadata or AI assistance when appropriate.
- Do not simply stretch the iPhone layout.

Accessibility:
- Support Dynamic Type.
- Support VoiceOver reading order.
- Support Reduce Motion.
- Support Reduce Transparency.
- Support Increase Contrast.
- Support Differentiate Without Color.
- Work in light and dark mode.
- Avoid tiny gray essential text.
- Avoid fixed-height text containers.

Liquid Glass:
- Use only for navigation layers, toolbars, tab bars, floating controls, and accessory surfaces.
- Do not use Liquid Glass for content cards, list rows, dense text, ordinary settings, dashboard tiles, or full-screen backgrounds.
- Provide an opaque fallback for Reduce Transparency.

Hard exclusions:
- No Material Floating Action Button.
- No hamburger menu on iPhone.
- No custom tab bar.
- No custom navigation bar.
- No dashboard card grid on iPhone.
- No hero CTA section inside app workflow.
- No glass content cards.
- No glass-on-glass.
- No decorative gradient blob background.
- No tiny gray essential text.
- No hover-only affordances.
- No right-rail AI assistant on iPhone.
- No Tailwind/SaaS/dashboard visual grammar.

Generate 3 variants:
1. Conservative native.
2. Dense iPad-aware.
3. Expressive but still Apple-native.

For each variant, briefly explain:
- hierarchy
- density
- interaction model
- accessibility considerations
- what changed from the base structure
```

## Prompting Notes

Prefer plain language. Avoid giant prompts. If Stitch omits components or drifts, revise one or two issues at a time.

Do not ask Stitch for SwiftUI code unless the user explicitly requests exploratory pseudocode. Even then, treat the code as disposable.

For the iPad section, cross-link to `references/ipad-layout.md` when the brief involves split view, inspector, or multi-window behavior. The handoff format does not duplicate those rules.
