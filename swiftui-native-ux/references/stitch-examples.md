# Stitch Brief Examples

Five worked examples of Apple-native Stitch briefs. Use as patterns when filling out `templates/stitch-apple-native-brief.md`.

## Example 1: iPhone Settings Screen

```
Create a high-fidelity native iOS settings screen concept.

Platform:
Target iOS 26. Design for native SwiftUI implementation.

Screen:
Account Settings.

User goal:
Review account details, update preferences, and safely sign out.

Native Apple structure:
Use NavigationStack with a standard Form. Use grouped sections with short section headers.

Content hierarchy:
1. Account identity row with avatar, name, and email.
2. Preferences section with toggles.
3. Privacy and notification navigation rows.
4. Destructive sign-out section.

Primary action:
Sign Out, displayed as destructive red text in its own final Form section.

States to represent:
Loaded, loading account details, offline account details unavailable, sign-out confirmation.

iPhone behavior:
Compact Form layout. Standard 44pt minimum touch targets. No custom cards.

Accessibility:
Support Dynamic Type, VoiceOver row labels, Increase Contrast, Differentiate Without Color, light and dark mode.

Liquid Glass:
Only standard navigation bar behavior. No glass content rows.

Hard exclusions:
No custom web input fields. No heavy drop-shadow cards. No custom tab bar. No hamburger menu. No Material Floating Action Button.

Generate 3 variants:
1. Conservative native.
2. Dense but readable.
3. Expressive but still Apple-native.
```

## Example 2: iPad Collection/Detail Screen

```
Create a high-fidelity native iPadOS app screen concept.

Platform:
Target iPadOS 26. Design for native SwiftUI implementation.

Screen:
Document Library.

User goal:
Browse document categories, select a document, and inspect metadata.

Native Apple structure:
Use NavigationSplitView. Leading sidebar for categories. Detail column for selected document list or preview. Inspector for metadata.

Content hierarchy:
1. Sidebar category list.
2. Main document collection/detail area.
3. Inspector metadata and actions.
4. Empty state when no category or document is selected.

Primary action:
New Document in the top trailing toolbar.

Secondary actions:
Search, sort, share, edit metadata.

States to represent:
Loaded, empty library, no selection, loading documents, sync error.

iPhone behavior:
Collapse to NavigationStack with category list first, then document list, then detail.

iPad behavior:
Use regular width intentionally. Do not stretch an iPhone screen.

Accessibility:
Support Dynamic Type, VoiceOver selection state, keyboard navigation, Increase Contrast, Reduce Transparency.

Liquid Glass:
Allowed only for navigation/toolbar surfaces.

Hard exclusions:
No hamburger menu. No web sidebar styling. No dashboard grid as primary iPhone structure. No right rail chatbot. No custom tab bar.

Generate 3 variants:
1. Conservative native split view.
2. Dense iPad productivity layout with inspector.
3. Expressive but still Apple-native.
```

## Example 3: Playback / Control Screen With Liquid Glass

```
Create a high-fidelity native iOS playback control screen concept.

Platform:
Target iOS 26. Design for native SwiftUI implementation.

Screen:
Live Playback Controls.

User goal:
Trigger audio quickly and confidently during a live event.

Native Apple structure:
Use NavigationStack with a bottom toolbar/accessory control surface. Main content should be an opaque list or grid of playable items depending on width.

Content hierarchy:
1. Current playback status.
2. Large primary transport controls.
3. Queue or sound list.
4. Emergency stop control.
5. Route/device status.

Primary action:
Play or trigger selected sound. Make it large, reachable, and obvious.

Secondary actions:
Stop, fade out, skip, route selection, volume.

States to represent:
Ready, playing, paused, route unavailable, offline library, error loading sound, emergency stop active.

iPhone behavior:
Single-column. Large touch targets. Critical stop control reachable and visually distinct.

iPad behavior:
Use split view or side panel for library/queue while keeping transport controls persistent.

Accessibility:
Support VoiceOver labels for playback state, Dynamic Type, Reduce Motion, Reduce Transparency, Increase Contrast, and Differentiate Without Color.

Liquid Glass:
Use Liquid Glass only for bottom transport/accessory surface and navigation layer. Use opaque backgrounds for sound rows and dense text.

Hard exclusions:
No glass content cards. No glass-on-glass. No decorative gradient blob background. No tiny gray status text. No hover-only controls. No dashboard card grid on iPhone.

Generate 3 variants:
1. Conservative native playback.
2. Dense iPad-aware control room.
3. Expressive but still Apple-native.
```

## Example 4: Empty-State-Heavy iPhone Screen

```
Create a high-fidelity native iOS app screen concept.

Platform:
Target iOS 26. Design for native SwiftUI implementation.

Screen:
Empty Project Library.

User goal:
Understand that no projects exist yet and create the first project.

Native Apple structure:
Use NavigationStack. Use an empty state in the content area with clear title, explanation, and primary action.

Content hierarchy:
1. Navigation title: Projects.
2. Empty state symbol.
3. Plain-language explanation.
4. Primary Create Project action.
5. Secondary Import Project action.

Primary action:
Create Project in the top trailing toolbar and repeated as a prominent empty-state button.

States to represent:
Empty, loading projects, import failed, permission denied for file import.

iPhone behavior:
Centered but not landing-page-like. Avoid hero section. Keep text concise.

iPad behavior:
If regular width, show empty library in detail area with optional sidebar placeholder.

Accessibility:
Dynamic Type must not truncate. VoiceOver order should read title, explanation, primary action, secondary action. Support Reduce Motion and Increase Contrast.

Liquid Glass:
Navigation only. Empty state content must be opaque and readable.

Hard exclusions:
No website hero CTA. No decorative gradient blob. No glass card. No custom navigation bar. No Material FAB.

Generate 3 variants:
1. Conservative native empty state.
2. More instructional but still compact.
3. Expressive but still Apple-native.
```

## Example 5: AI-Assisted Feature Without Right Rail

```
Create a high-fidelity native iOS/iPadOS app screen concept.

Platform:
Target iOS 26 and iPadOS 26. Design for native SwiftUI implementation.

Screen:
AI-assisted document review.

User goal:
Read a document summary, ask follow-up questions, and apply suggested edits.

Native Apple structure:
On iPhone, use NavigationStack with the AI assistant in a native sheet. On iPad, use NavigationSplitView with an inspector for the assistant.

Content hierarchy:
1. Main document summary.
2. Suggested edits.
3. Assistant interaction.
4. Apply/reject actions.
5. Error and loading states for AI response.

Primary action:
Apply selected suggestion.

Secondary actions:
Ask follow-up, reject suggestion, regenerate summary.

States to represent:
Loaded summary, AI thinking/loading, AI error, no suggestions, suggestion selected, offline unavailable.

iPhone behavior:
Assistant appears as a draggable sheet. Text input respects keyboard and safe area.

iPad behavior:
Assistant appears in inspector, not a web-style right rail. Main document remains readable.

Accessibility:
VoiceOver must distinguish document content from assistant suggestions. Dynamic Type must preserve readable content. Do not rely on color alone for suggestion status.

Liquid Glass:
Allowed only for sheet/inspector chrome or toolbar. Main text surfaces must be opaque.

Hard exclusions:
No right-rail chatbot on iPhone. No floating chat FAB. No web sidebar. No tiny gray text. No hover-only controls. No glass content cards.

Generate 3 variants:
1. Conservative native assistant sheet.
2. Dense iPad inspector workflow.
3. Expressive but still Apple-native.
```
