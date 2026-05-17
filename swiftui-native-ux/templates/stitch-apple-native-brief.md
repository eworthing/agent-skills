# Stitch Apple-Native Brief Template

Substitute the `{{PLACEHOLDER}}` tokens before sending to Stitch. The format spec lives at `references/stitch-handoff-format.md`; worked examples at `references/stitch-examples.md`.

```
Create a high-fidelity native iOS/iPadOS app screen concept.

Platform:
- Target iOS 26 and iPadOS 26.
- Design for native SwiftUI implementation.
- Use Apple-native layout, interaction, accessibility, and navigation patterns.

Screen:
- {{SCREEN_NAME}}

User goal:
- {{USER_GOAL}}

Task topology:
- {{TASK_TOPOLOGY}}

Native Apple structure:
- {{NATIVE_STRUCTURE}}

Content hierarchy:
1. {{PRIMARY_CONTENT}}
2. {{SECONDARY_CONTENT}}
3. {{SUPPORTING_CONTENT}}

Primary action:
- {{PRIMARY_ACTION}}
- Placement: {{PRIMARY_ACTION_PLACEMENT}}

Secondary actions:
- {{SECONDARY_ACTIONS}}

States to represent:
- Loaded: {{LOADED_STATE}}
- Empty: {{EMPTY_STATE}}
- Loading: {{LOADING_STATE}}
- Error: {{ERROR_STATE}}
- Permission/offline if relevant: {{PERMISSION_OR_OFFLINE_STATE}}

iPhone behavior:
- Compact one-column layout.
- Reachable controls.
- Respect safe areas and keyboard.
- No dashboard grid as primary structure.

iPad behavior:
- Use regular-width space intentionally.
- Prefer split view, inspector, or multi-pane behavior when useful.
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
- Use only for navigation layers, tab bars, toolbars, floating controls, and accessory surfaces.
- Do not use Liquid Glass for content cards, list rows, dense text, ordinary settings, dashboard tiles, or full-screen backgrounds.
- Include an opaque fallback for Reduce Transparency.

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
