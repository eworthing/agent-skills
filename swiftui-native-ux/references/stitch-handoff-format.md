# Stitch Apple-Native Handoff Format

Use this format when creating a prompt for Stitch. Keep the prompt short enough to remain focused. Prefer one screen per prompt.

The reusable template lives at `templates/stitch-apple-native-brief.md`. This file is the spec the template implements.

## Required Brief Sections

Every brief must carry, in order:

1. Platform — iOS 27 / iPadOS 27, native SwiftUI implementation, Apple-native interaction and layout patterns.
2. Screen, user goal, and task topology.
3. Native Apple structure — chosen locally before prompting, per `references/navigation-patterns.md`.
4. Content hierarchy — primary, secondary, supporting metadata, then state content.
5. Primary action with placement; secondary actions.
6. States to represent — loaded, empty, loading, error, permission, offline, selection, editing, as relevant.
7. iPhone behavior — compact, single column, reachable, safe areas, no dashboard grid.
8. iPad behavior — regular width used intentionally, split view / inspector / multi-pane where useful, never a stretched iPhone layout.
9. Accessibility — Dynamic Type, VoiceOver order, Reduce Motion, Reduce Transparency, Increase Contrast, Differentiate Without Color, light and dark mode.
10. Liquid Glass scope — navigation layers, toolbars, floating controls, accessory surfaces only; opaque fallback for Reduce Transparency.
11. Hard exclusions — the hard-reject tier of `references/anti-web-smells.md`, phrased as "No ..." lines.
12. A request for 3 variants: conservative native, dense iPad-aware, expressive but still Apple-native.

The exclusion list does the heavy lifting: `deviceType` alone does not constrain Stitch to Apple HIG (see `workflows/stitch-design-handoff.md` Step 4b).

## Prompting Notes

Prefer plain language. Avoid giant prompts. If Stitch omits components or drifts, revise one or two issues at a time.

Do not ask Stitch for SwiftUI code unless the user explicitly requests exploratory pseudocode. Even then, treat the code as disposable.

For the iPad section, cross-link to `references/ipad-layout.md` when the brief involves split view, inspector, or multi-window behavior. The handoff format does not duplicate those rules.
