# Source Architecture

Use this reference when maintaining the skill, evaluating evidence, or deciding where guidance belongs.

## Core Principle

Strong rules need strong sources.

Weak sources can still be useful, but they become lenses, examples, or anti-patterns rather than hard law.

## Skill Structure

This skill should remain modular.

Recommended structure:

```text
swiftui-native-ux/
  SKILL.md
  references/
  workflows/
  data/
  scripts/
  templates/
```

`SKILL.md` is the routing brain.

References are knowledge.

Workflows are repeatable capabilities.

Data files are searchable rule stores.

Scripts support search, validation, and installation.

Templates support multi-agent packaging.

## Source Of Truth

Maintain one source-of-truth skill directory.

Example:

```text
src/swiftui-native-ux/
```

Agent-specific folders should be generated or symlinked from source when possible:

```text
.claude/skills/swiftui-native-ux/
.codex/skills/swiftui-native-ux/
.gemini/skills/swiftui-native-ux/
.opencode/skills/swiftui-native-ux/
```

Do not manually maintain divergent copies.

## Evidence Tiers

### Tier 1: Platform Authority

Use for hard platform rules and API defaults.

Sources:

- Apple Human Interface Guidelines
- Apple Developer documentation
- WWDC sessions
- Apple sample code

Use for:

- navigation containers
- platform behavior
- accessibility APIs
- SwiftUI APIs
- Liquid Glass behavior
- system control usage
- platform conventions

Skill weight: canonical.

### Tier 2: Empirical Research

Use to justify why the skill must be opinionated and why raw LLM output needs critique.

Sources:

- UICoder
- CrowdGenUI
- AlignUI
- Anderson/Shah/Kreminski as supporting homogenization evidence only

Use for:

- LLM UI genericness
- preference grounding
- inconsistency
- model-level homogenization
- why reject/prefer rules matter

Important correction:

Anderson/Shah/Kreminski is not UI-specific evidence. Use it to explain broader LLM homogenization, not as proof about SwiftUI UI quality. For UI-specific claims, prefer UICoder, CrowdGenUI, and AlignUI.

### Tier 3: Practitioner Taste Lenses

Use for critique passes, examples, and judgment vocabulary.

Sources:

- Sebastiaan de With
- Christian Selig
- Federico Viticci
- Marco Arment
- John Gruber
- Michael Tsai
- Sheri Byrne-Haber
- Maggie Appleton
- Geoffrey Litt
- Philip Davis
- Katherine Yeh

Use for:

- physicality
- restraint
- iPad power-user expectations
- legibility skepticism
- accessibility nuance
- AI affordance critique
- SwiftUI as design/prototyping medium
- skill architecture

Skill weight: lens, not law.

### Tier 4: Translated Web And Design-System Sources

Use only after stripping web assumptions.

Sources:

- Refactoring UI
- Brad Frost / Atomic Design
- Jenifer Tidwell
- Material Design
- Tailwind
- shadcn/ui
- Dribbble / Behance
- SaaS dashboard guides
- landing-page advice
- cross-platform UI prompt packs

Borrow:

- hierarchy principles
- design-token discipline
- pattern vocabulary
- component decomposition
- critique framing

Reject:

- Tailwind implementation
- Material FAB
- dashboard default
- hero/CTA marketing structure
- hover-only affordances
- card-grid gravity
- fantasy UI

## Normalized Confidence Scale

5 = canonical or directly evidenced
4 = strong and useful, but not canonical
3 = useful with translation or limited scope
2 = situational or inspirational
1 = avoid except as negative example

## Ranked Source Table

| Rank | Source                                    | Type                       | Use                                                              | Limits                                              | Confidence |
| ---: | ----------------------------------------- | -------------------------- | ---------------------------------------------------------------- | --------------------------------------------------- | ---------: |
|    1 | Apple HIG                                 | Apple-native               | Platform conventions, navigation, accessibility, materials       | Sometimes prescriptive without explaining tradeoffs |          5 |
|    2 | Apple Developer docs                      | Apple-native/API           | SwiftUI APIs, Liquid Glass, Observation, SwiftData, navigation   | Docs can require current SDK context                |          5 |
|    3 | WWDC design sessions                      | Apple-native/current       | iOS 26 design system, Liquid Glass, controls                     | Promotional framing                                 |          5 |
|    4 | Apple SwiftUI sample code                 | Apple-native/API           | Navigation/state structure, split-view patterns                  | Sample scope may be narrow                          |          5 |
|    5 | UICoder / CrowdGenUI / AlignUI            | AI/UI research             | Why LLM UI output needs strong preference grounding              | Does not cover every coding-agent workflow          |          5 |
|    6 | Nielsen Norman Group / Nielsen heuristics | UX critique                | Usability heuristics, legibility skepticism, critique vocabulary | Conservative bias                                   |          5 |
|    7 | Don Norman                                | Critique framework         | Affordances, signifiers, feedback, constraints                   | Foundational, not SwiftUI-specific                  |          5 |
|    8 | Bruce Tognazzini                          | Interaction principles     | Latency, autonomy, defaults, Fitts' Law, discoverability         | Older but still useful                              |          4 |
|    9 | Luke Wroblewski                           | Mobile product judgment    | Thumb reach, content priority, mobile-first pruning              | Old specific stats should not be cited              |          4 |
|   10 | Federico Viticci                          | iPad expert lens           | iPad windowing, keyboard/pointer expectations, power-user fit    | Commentary, not API authority                       |          4 |
|   11 | Sebastiaan de With                        | Visual/native craft        | Physicality, restraint, tactile feel                             | Practitioner lens                                   |          4 |
|   12 | Sheri Byrne-Haber                         | Accessibility lens         | Dark mode nuance, halation, user-choice framing                  | Verify exact claims before hard citation            |          4 |
|   13 | Maggie Appleton / Geoffrey Litt           | AI interaction design      | Scoped AI affordances, avoid bolted-on chat panels               | Conceptual, not SwiftUI-specific                    |          4 |
|   14 | Refactoring UI                            | Visual hierarchy           | Developer-friendly hierarchy and restraint                       | Web/Tailwind implementation must be rejected        |          3 |
|   15 | Jenifer Tidwell                           | Pattern language           | Naming patterns and interaction vocabulary                       | Cross-platform, needs Apple translation             |          3 |
|   16 | Brad Frost                                | Design systems             | Component decomposition mindset                                  | Web origin, loosely maps to SwiftUI                 |          3 |
|   17 | Christian Selig / indie Apple craft       | Craft calibration          | Native gestures plus delight                                     | Inspirational, not formal evidence                  |          3 |
|   18 | Philip Davis                              | SwiftUI design/prototyping | Small previewable views, SwiftUI as design medium                | Verify specific claims before ranking higher        |          3 |
|   19 | Katherine Yeh                             | AI workflow                | Skills as capability layer, references as knowledge              | Workflow precedent, not design authority            |          3 |
|   20 | NextLevelBuilder ui-ux-pro-max            | Structural precedent       | Modular package/distribution ideas                               | Strong web bias, negative taste example             |          2 |
|   21 | Material / shadcn / Tailwind              | Contrast sources           | Useful as anti-pattern detectors                                 | Do not port visual grammar into SwiftUI             |          2 |
|   22 | Dribbble / Behance                        | Inspiration                | Rare craft spark                                                 | Mostly fantasy UI                                   |          1 |

## Source Placement Rule

Apple sources define platform behavior.

Research sources explain model failure modes.

Practitioner sources provide lenses.

Web sources provide translated concepts or anti-patterns.

The skill turns all of them into small, enforceable reject/prefer rules.

## What Belongs In SKILL.md

Only always-on rules that affect nearly every task:

- native structure before styling
- critique before generation
- reference routing
- hard rejections
- default workflow
- output contract

Do not put long source summaries in `SKILL.md`.

## What Belongs In References

References contain focused knowledge:

- iPhone layout
- iPad layout
- navigation
- visual hierarchy
- accessibility
- Liquid Glass
- anti-web-smells
- critique rubric
- generation output format
- expert lenses

Keep each reference compact and operational.

## What Belongs In Workflows

Workflows contain repeatable processes:

- generate new screen
- critique existing SwiftUI
- adapt iPhone to iPad
- rewrite web UI native
- polish visual hierarchy
- audit accessibility

Workflows should tell the agent what to do in order.

## What Belongs In Data

Future searchable data files should store:

- rule IDs
- triggers
- prefer/reject pairs
- severity
- source IDs
- reference file mapping

Example schema:

```csv
rule_id,category,trigger,prefer,reject,severity,source_ids,reference_file
NAV001,navigation,collection detail app,NavigationSplitView on regular width,stretched NavigationStack on iPad,reject,APPLE_HIG;VITICCI,navigation-patterns.md
WEB001,anti_web,hero header in app screen,List/Form/native grouped section,marketing hero section,reject,APPLE_HIG;REF_UI_TRANSLATED,anti-web-smells.md
GLASS001,liquid_glass,text over material,opaque or tinted readable surface,thin text over glass,reject,APPLE_LG;BYRNE_HABER,liquid-glass.md
```

## Demoted Claims

Do not say:

- macOS 27 is current
- Anderson/Shah/Kreminski proves LLMs generate generic UI
- NavigationSplitView is mandatory for all iPad apps
- ObservableObject is forbidden
- every primary action gets a keyboard shortcut
- every screen must have five previews
- absolute font sizes are always forbidden

Say:

- macOS 26 Tahoe is current baseline
- Anderson/Shah/Kreminski supports broader homogenization
- use NavigationSplitView for collection/detail and hierarchy
- prefer Observation for new UI state
- repeated document/app commands on iPad/Mac should get keyboard shortcuts
- generated reusable screens should include relevant preview variants when practical
- prefer semantic Dynamic Type; explicit font sizes require justification

## Maintenance Rule

When adding a rule, include:

- trigger
- prefer
- reject
- severity
- source tier
- file placement

If the rule cannot be stated as a decision, it probably belongs in research notes, not the skill.
