# Contest Refactor Review — Loop 1

### Discovery

- Source roots: `BenchHypeKit/Sources/BenchHypeSettingsFeature` — **SCOPED RUN**: this scorecard and every finding is a claim about that subtree only, not the repository.
- Test command: `./scripts/run_local_gate.sh --quick` (human-pinned floor in the verify-trust store)
- Build command: `./scripts/run_local_gate.sh --targeted` (AGENTS.md Definition of Done for any Swift source change; stricter than the pin — discrepancy recorded in discovery.notes)
- ADRs found: ADR-0001 (reject transport parity tests, accepted); ADR-0003 (transition modes — duck-match and device-volume fade, accepted, 4 amendments)
- Domain terms (CONTEXT.md): Transition Mode, Fade, Duck, Duck-Veil, Duck-Match Envelope, Volume Ramp, True Fade, Fade Duration, AppState, EditingState, NavigationState, PlaybackState, InstanceID, CueTransport, CueKind
- Selected lens: Apple (+ always-included security and efficiency lenses)

### Loop Counter

Loop 1 of 10 (cap)

### System Flag

[STATE: HALT_DRY_RUN]

---

## Contest Verdict

Good app, but not top-tier yet.

Scoped claim: the Settings feature subtree is a small, honest, reducer-disciplined surface — 1,853 lines, zero stored adapter state, zero unstructured Tasks, single dispatch path, documented ADR-consistent Apple Music copy. What holds it below the 9.5 bar is view-side derivation of display state at three sites that the repo's own projection contract already rules out, an untested control-to-intent mapping on the main settings screen, and a composition interface whose defaults let a correct-looking call render lying copy.

## Scorecard (1-10)

Ground truth this loop: ./scripts/run_local_gate.sh --quick and the project-authoritative ./scripts/run_local_gate.sh --targeted both exited 0. Quick: format/lint/shell/boundaries (108 rules)/starter-sound compliance and 3,396 tests. Targeted: the same checks, build ok, iPhone 7/7, iPad 8/8, macOS 8/8 UI tests, split validation clean. No score increase is claimed because this is a dry-run with no source diff; no attestation wrapper event is citable.

- Architecture quality: 9.5 | SAME | `SettingsScreenContext.swift:5-41` (value-type context, closure-injection seam with documented features-narrow rationale surviving the deletion test). Residual blocking 10: permissive defaults + parallel availability fields on the public composition interface (queued, F2).
- State management and runtime ownership: 9.0 | SAME | Writers map to one dispatch path (`SettingsScreenContext.swift:116-125`); view @State is presentation-only and symmetric (`DiagnosticsView.swift:51-57` clears `pendingCleanup` on both dialog arms). 9-anchor unmet: derived display state lives in views at three sites (F1) and one runtime fact is split across two manually-coupled fields (F2) — both named in the backlog.
- Domain modeling: 9.0 | SAME | Pickers use display names carried on the types (`AppearanceMode`/`TapAction`/`TransitionMode` `.displayName` at call sites, e.g. `SettingsScreenContent.swift:90-91`); `OutputDestination.isWireless` on the type (`Route.swift:30`). 9-anchor unmet: a second interpretation of the domain enum `OutputDestination` (case→display-string) lives in a feature view (`DiagnosticsView.swift:81-89`) — the repo's Hard Rule 4 says the type owns it (F1).
- Data flow and dependency design: 9.5 | SAME | One-way: projection in → render → `dispatcher.dispatch(intent)` out; destinations arrive by injected closure, no ambient port reach (`SettingsScreenContent.swift:224-245`). Residual blocking 10: the diagnostic trace gate is a string-keyed `UserDefaults` channel duplicated at three modules instead of flowing through the typed seam — accepted: forced by the `features-no-adapter-imports` rule and mechanically gate-checked (`scripts/check_boundaries.sh:1195-1208`, `applemusic-trace-key-sync`; gate green this run).
- Framework / platform best practices: 9.5 | SAME | `Form` with documented macOS rationale (`SettingsScreenContent.swift:19-21`); `#if os(macOS)` used for symbol-presence gating, never `canImport` misuse (`SettingsScreenContent.swift:394-400`, `+AppleMusic.swift:71-77`); native `fileImporter`/`fileMover`/`ShareLink`; iOS 26 `neutralValue:` slider with VoiceOver parity (`SettingsScreenContent.swift:295-306`). Residual blocking 10: `AnyView`-erased destination closures (`SettingsScreenContext.swift:38-41`) — accepted: type erasure is forced by the features-narrow rule; friction-proof is the rule itself and the documented `nil`-row behavior.
- Concurrency and runtime safety: 10 | SAME | G25 walked: zero `CheckedContinuation`/`withCheckedThrowingContinuation` occurrences in scope (grep-listed), so no delegate audit applies; no unstructured `Task` (README's "never wrap dispatch in Task" claim verified true); `@MainActor` value-type context; `.task` refreshes are view-lifecycle-scoped (`DiagnosticsView.swift:42-45`) and reducer-guarded against re-entry (`DiagnosticsReducer.swift:15-23`). No behavior-preserving improvement identifiable: the subtree holds no async lifetime of its own to restructure.
- Code simplicity and clarity: 9.5 | SAME | 1,853 lines, no protocol soup, no repository theater, one 15-line visibility facade (`SettingsScreen.swift`) that earns its keep. Residual blocking 10: the F1 view-side label trio (≈28 lines removable to their owners) (queued, F1).
- Test strategy and regression resistance: 8.5 | SAME | Snapshot coverage for Paywall/Diagnostics/Help/StarterLicenses + `AppBuildInfo` pure-fn tests + projection tests (`SettingsViewStateTests.swift`) + app-level paywall UI test (`PaywallUITests.swift:10-48`). 9-anchor unmet: no direct test at the surface binding the 16 settings controls to their intents — `UITestIdentifiers.Settings` playback identifiers (`UITestIdentifiers.swift:93` transitionModePicker et al.) have zero consumers in any test target; mutating a `settingBinding` keyPath pair (swap `\.defaultFadeInSeconds`↔Out at `SettingsScreenContent.swift:311/316`) passes every current test (F4).
- Overall implementation credibility: 9.5 | SAME | Doc-vs-code sweep re-run in scope: README rule claims hold; the trace-key comment's gate claim verified real (above); `AppBuildInfo` doc comments match code. Residual blocking 10: the render-rule comment block (`SettingsScreenContent+AppleMusic.swift:12-24`) describes a reachable "available + entitlement nil → Authorize" cold-start branch that the app's own wiring (`RootScene.swift:341` derives availability from entitlement non-nilness) makes unreachable — code and doc disagree (queued with F2; per AGENTS.md the doc is treated as binding and the conflict reported here).

## Authority Map

- Concern: Settings edits (draft → persisted prefs)
  - Owner: `EditingState.settingsDraft`, reducer-side
  - Allowed writers: `SettingsScreenContext.applySettingsChange` intents only (`SettingsScreenContext.swift:120-125`)
  - Readers: `SettingsViewState` projection → `settingBinding` get arm (`:54-62`); reducer; persistence effect
  - Persistence seam: `.editing(.saveSettingsDraft)` → application
  - Async mutation entry points: none in feature (synchronous dispatch)
  - Verdict: Single and clear
- Concern: Apple Music availability + entitlement display
  - Owner: split — `context.appleMusicAvailable` (composer-supplied, defaulted) vs `SettingsViewState.appleMusicEntitlement` (projection); `RootScene.swift:341` manually derives one from the other
  - Allowed writers: app shell (uncoordinated with the render rule in `+AppleMusic.swift:12-24`)
  - Readers: `appleMusicSection` branches
  - Persistence seam: none
  - Async mutation entry points: injected closures
  - Verdict: Split and ambiguous (Finding F2)
- Concern: Backup operation state
  - Owner: `BackupState.phase` (reducer)
  - Allowed writers: backup intents/outcomes
  - Readers: `BackupSettingsView` + its `statusMessage` (Finding F1 — the read-site *interpretation* is in the view)
  - Persistence seam: backup effects (application)
  - Async mutation entry points: none in feature
  - Verdict: Single and clear
- Concern: Diagnostics storage/integrity phases and cleanup staging
  - Owner: application `DiagnosticsState` phases; `pendingCleanup` is view-staged *payload*
  - Allowed writers: reducer guards re-entry (`DiagnosticsReducer.swift:15-34`); view stages filenames
  - Readers: `DiagnosticsView`; the delete authority re-validates each name (sanitize + containment + live reference-set pass, `CuesFileStore.swift:175-192`)
  - Persistence seam: `DiagnosticsPort`
  - Async mutation entry points: `.task` refresh intents (lifecycle-scoped)
  - Verdict: Single and clear (stale-snapshot risk defused at the write authority, UI documents it)
- Concern: Apple Music trace-logging gate
  - Owner: `UserDefaults` key, no state-model owner
  - Allowed writers: `DiagnosticsView` @AppStorage toggle
  - Readers: `BenchHypeAppleMusic/BoundedRelease.swift:24`, `AppleMusicPlaylistTracksView.swift:18`
  - Persistence seam: UserDefaults (deliberate; documented)
  - Async mutation entry points: none
  - Verdict: Single and clear — string-literal triplication enforced by named gate `applemusic-trace-key-sync` (verified live in `scripts/check_boundaries.sh:1195-1208`)

## Strengths That Matter

- Deletion-authority pattern done right: the destructive orphan cleanup routes a view-staged filename list to an authority that re-derives the live referenced set and re-checks containment per name (`CuesFileStore.swift:184-192`) — the snapshot staleness the UI admits (`DiagnosticsView.swift:60`) cannot become a wrong delete.
- `EntitlementSlice.proUpgradeButtonTitle` states the repo's own projection contract at its site of enforcement ("Projection-owned so the view stays render-only", `AppSnapshot.swift:210-212`) — and F1 is judged against that in-repo standard, not an imported one.
- Composition seam honesty: destination closures are injected precisely so this feature never imports `BenchHypeLiveFeature`, with the `nil` degradation behavior documented at the property (`SettingsScreenContext.swift:34-41`) — a seam encoding platform-isolation policy that survives the deletion test.
- A11y is not bolt-on here: custom gain slider gets `accessibilityValue` matching the visual readout (`SettingsScreenContent.swift:306`), combined-label rows, explicit generic-icon-vs-badge brand rules (`+AppleMusic.swift:170-174`), touch-target minimums on caption links (`StarterSoundLicensesView.swift:38-42`).

## Findings

### Finding #1: Derived display state — enum-to-user-text mapping — lives in feature views at three sites

**Why it matters** — the repo's own Hard Rule 5 and the in-source projection contract ("views render-only") put derived display state in `*ViewState` projections, and Hard Rule 4 puts domain-enum interpretation on the enum; three view-side switches violate that pattern at once, and the class was already swept and fixed elsewhere twice (F-001, F-008/F-009 in the registry).

**What is wrong** — `DiagnosticsView` resolves the domain enum `OutputDestination` and application enum `InterruptionState` to user-facing labels; `BackupSettingsView` resolves `BackupPhase` to status copy. The copy is product messaging owned by the projection/state layer, shaped at read-site instead of owner-site.

**Evidence** — `BenchHypeKit/Sources/BenchHypeSettingsFeature/DiagnosticsView.swift:81-97` (`routeDestinationLabel`, `interruptionLabel`); `BenchHypeKit/Sources/BenchHypeSettingsFeature/BackupSettingsView.swift:112-125` (`statusMessage`); the enum's home module already carries policy interpretations (`BenchHypeKit/Sources/BenchHypeDomain/Values/Route.swift:22-41` `isWireless` — the label is the only mapping outside the type); repo precedent for the correct home (`BenchHypeKit/Sources/BenchHypeApplication/Projections/AppSnapshot.swift:210-212`); hotspot scan confirms control-decision density in `statusMessage` (decision_count 5, `CURRENT_REVIEW.json.discovery.hotspot_scan`).

**Architectural test failed** — Replace-don't-layer (the view-local helpers should be deleted; the mapping asserted at the projection interface instead).

**Leverage impact** — every new surface that must report backup/interruption/route status re-derives the strings; today only views can answer them.

**Locality impact** — phase copy edits today touch feature files; tomorrow they touch both, drifting.

**Metric signal, if any** — scanner queues `statusMessage` to the control queue (5 decisions / 11 lines) — corroborating, not deciding.

**Why this weakens submission** — a documented single-owner invariant holding by review in one module but violated in the reviewed subtree is a locality and credibility leak, scored Noticeable because it is contained and no drift has been demonstrated live.

**Severity** — Noticeable weakness

**ADR conflicts** — none

**Minimal correction path** — move the three mappings to their owners, strings byte-identical: `displayName: String` computed on `OutputDestination` (its home, `BenchHypeDomain/Values/Route.swift` — Hard Rule 4's prescribed canonical form); label fields on `DiagnosticsViewState` for the interruption case (its home projection, `SettingsViewState.swift`); `statusMessage: String?` computed on `BackupState.phase`'s owning type (`BenchHypeApplication/State/BackupState.swift`). Delete the three view functions; extend `SettingsViewStateTests`/existing snapshot tests to assert the relocated strings. No new seam, no new protocol.

**Blast radius** — change: `BenchHypeKit/Sources/BenchHypeSettingsFeature/DiagnosticsView.swift`, `BackupSettingsView.swift`; `BenchHypeKit/Sources/BenchHypeDomain/Values/Route.swift`; `BenchHypeKit/Sources/BenchHypeApplication/State/BackupState.swift`, `Projections/SettingsViewState.swift`; `BenchHypeKit/Tests/BenchHypeSettingsFeatureTests/SettingsViewStateTests.swift`, `DiagnosticsViewSnapshotTests.swift`. Avoid: `AppReducer+Editing.swift`, `SettingsDraft`, persistence effects, `PlaybackReducer` — no behavior, serialization, or ordering change.

### Finding #2: The context interface's permissive defaults plus parallel availability fields let a correctly-compiling call render lying copy

**Why it matters** — Hard Rule 3 signal: two fields (`appleMusicAvailable`, `state.appleMusicEntitlement`) must agree, but nothing keeps them in agreement except a derivation at one call site; the defaults (`= false`, `= {}`) turn a forgotten wire-up into a silently wrong UI instead of a compile error.

**What is wrong** — `SettingsScreenContext` exposes `appleMusicAvailable: Bool = false` plus two no-op default closures; the render rule (`+AppleMusic.swift:12-24`) claims "available && entitlement nil → Authorize (cold-start)" is reachable, but `RootScene.swift:341` derives `appleMusicAvailable` from `entitlement != nil`, making the branch unreachable and the two fields a manually-synchronized pair — code and doc disagree on the invariant (AGENTS.md: treat the doc as binding, report the conflict; reported, here).

**Evidence** — `BenchHypeKit/Sources/BenchHypeSettingsFeature/SettingsScreenContext.swift:10-26` (defaults); `:31-33` (three parallel fields); `BenchHypeKit/Sources/BenchHypeSettingsFeature/SettingsScreenContent+AppleMusic.swift:12-24` (render rule); `BenchHype/BenchHype/RootScene.swift:338-346` (manual coupling at the only production construction site); `BenchHypeKit/Tests/BenchHypeSettingsFeatureTests/DiagnosticsViewSnapshotTests.swift` (second construction site, relies on defaults).

**Architectural test failed** — n/a — different category (impossible-state representability, not a seam-removal claim)

**Leverage impact** — every future call site must re-learn the derivation rule to wire this struct honestly.

**Locality impact** — the availability fact is owned jointly by the caller, the context, and the view's branching logic.

**Metric signal, if any** — none

**Why this weakens submission** — a public composition interface whose lying states are reachable and whose doc and wiring disagree about which states exist is a credibility and state-ownership weakness; Noticeable because both current sites wire honestly and the damage is latent, not live.

**Severity** — Noticeable weakness

**ADR conflicts** — none

**Minimal correction path** — replace the triad with one sum type (`enum AppleMusicAccess { case unavailable; case available(authorize: @MainActor () -> Void, refresh: @MainActor () -> Void) }`) and drop the defaults; two construction sites update. Blocked for execution until the owner adjudicates the render-rule conflict above (which side is the invariant?) — this is an unconditional AGENTS.md stop-and-ask, not coverable by the Hard Rule 3/4 safe harbor.

**Blast radius** — change: `SettingsScreenContext.swift`, `SettingsScreenContent+AppleMusic.swift`, `BenchHype/BenchHype/RootScene.swift`, `DiagnosticsViewSnapshotTests.swift`. Avoid: entitlement adapter, playback chain.

### Finding #3: `DiagnosticsView` is public with zero cross-module consumers

**Why it matters** — repeat of the `api-surface-scope` class the registry already retired twice (F-022, F-024): unjustified `public` widens the supported surface of a feature module for no caller.

**What is wrong** — only same-module consumers exist (`SettingsScreenContent.swift:212` NavigationLink) and its own `@testable` snapshot tests; no app-target or cross-module call site survives this loop's grep.

**Evidence** — `BenchHypeKit/Sources/BenchHypeSettingsFeature/DiagnosticsView.swift:8` (`public struct`); repo-wide grep this loop: `DiagnosticsView(` appears only in `SettingsScreenContent.swift` (in-module) and `BenchHypeKit/Tests/BenchHypeSettingsFeatureTests/DiagnosticsViewSnapshotTests.swift` (`@testable import`, so internal is sufficient — precedent: `PaywallView` demoted at `af18aebc` with its snapshot tests still green); `HelpView` public is justified by `BenchHype/BenchHype/BenchHypeApp.swift:92`.

**Architectural test failed** — Deletion test

**Leverage impact** — none gained; a public initializer exposing `SettingsScreenContext` reachability that no external module uses.

**Locality impact** — the supported-surface list overstates reality.

**Metric signal, if any** — none

**Severity** — Cosmetic for contest

**ADR conflicts** — none

**Minimal correction path** — drop `public` from `DiagnosticsView` and its init; the compile matrix is the oracle (same mechanics as `af18aebc`). Fold into Finding 1's loop (same file, one-line).

**Blast radius** — change: `DiagnosticsView.swift`. Avoid: everything else.

### Finding #4: The settings control-to-intent mapping has no test at any surface

**Why it matters** — the 16 controls on the main settings screen are pure `keyPath` bindings; a mis-wire is invisible to every current test, and the screen's own playback identifiers were built for tests that do not exist.

**What is wrong** — `SettingsScreenContent` has no render test in the feature target; no UI test consumes `settings.playback.*` or the tap-action pickers; reducer tests assert intent semantics (`SettingsDraftReducerTests`) but cannot see which control dispatches which keyPath. Mutation check: swapping `\.defaultFadeInSeconds`/`\.defaultFadeOutSeconds` at `SettingsScreenContent.swift:311/316` leaves the full pinned suite green.

**Evidence** — `BenchHypeKit/Sources/BenchHypeSharedUI/UITestIdentifiers.swift:73,93` (identifiers); zero consumers in `BenchHypeKit/Tests/`, `BenchHype/BenchHypeUITests/`, `BenchHype/BenchHypeMacUITests/` this loop (grep for `transitionModePicker|duckingPolicyPicker|settings.playback`); absence of any `SettingsScreenContent*Tests` in `BenchHypeKit/Tests/BenchHypeSettingsFeatureTests/`; binding path `SettingsScreenContext.swift:54-62`.

**Architectural test failed** — Interface-as-test-surface

**Leverage impact** — a settings regression today is caught by no gate; the flow's tests would not survive a view refactor, which is the test-shape signal.

**Locality impact** — none.

**Metric signal, if any** — none

**Severity** — Noticeable weakness

**ADR conflicts** — none (ADR-0001 rejects transport parity tests, not feature-surface tests)

**Minimal correction path** — add one value-differentiated render test for `SettingsScreenContent` in the existing `@testable` snapshot pattern (distinct fade-in/out and gain values in the fed `SettingsViewState` make a keyPath swap change the rendered `.dump` — the slider rows print their value text, `SettingsScreenContent.swift:352-363`). Existing mechanics, no new harness, no new seam.

**Blast radius** — change: new `BenchHypeKit/Tests/BenchHypeSettingsFeatureTests/SettingsScreenContentSnapshotTests.swift`. Avoid: UI test targets, `UITestIdentifiers`, source files.

## Simplification Check

- Structurally necessary: F1 consolidates three enum→display mappings onto their owner types — passes Replace-don't-layer (view helpers deleted, assertions land at the projection interface); F2 removes representable contradiction onto a sum type (Hard Rule 3's prescribed shape, pending the doc conflict's owner decision).
- New seam justified: no — zero new ports, protocols, or wrappers; Hard Rule 10 not approached.
- Helpful simplification: F3's `public` drop is a one-line deletion riding F1's file pass.
- Should NOT be done: adding a `SettingsBinder` protocol to make the binding mapping injectable for F4 (fails Unified Seam Policy — one adapter, no fakes; and a test seam for a value struct that snapshot-render tests reach without it); routing the trace-gate UserDefaults key through the reducer (inverts product-policy cost onto every launch for a diagnostic switch that already has a named gate check).
- Tests after fix: keep `SettingsViewStateTests` and `DiagnosticsViewSnapshotTests` at their current surfaces; relocate the string assertions into `SettingsViewStateTests` (projection interface) and one new `SettingsScreenContentSnapshotTests`; no old tests deleted (none mirror the removed view helpers).

## Improvement Backlog

1. **F-025** — Move the three view-side enum→display mappings to their owner types; delete the view helpers; relocate string assertions to the projection interface; fold F-027's `public` drop into the same pass.
   - why it matters: restores the repo's own single-owner display rule across the subtree and closes the class the registry retired elsewhere.
   - score impact: `state_management +0.5; domain_modeling +0.5`
   - structural / needed for winning
2. **F-028** — Add the value-differentiated `SettingsScreenContent` render test pinning control→value mapping.
   - why it matters: today the settings-edit flow has no test that fails when a control binds the wrong field.
   - score impact: `test_strategy +0.5`
   - structural / needed for winning
3. **F-026** — Collapse `appleMusicAvailable` + two closure params + defaults into one sum type.
   - why it matters: removes the representable lying-composition state; **blocked on the AGENTS.md code-vs-doc stop-and-ask** — the render rule (`+AppleMusic.swift:12-24`) and the app wiring (`RootScene.swift:341`) disagree about whether available-and-nil entitlement is reachable; the doc is binding, so an owner must adjudicate before Step 3 of any loop attempting this.
   - score impact: `architecture_quality +0.5; credibility +0.5`
   - structural / helpful

## Deepening Candidates

1. Candidate module: `SettingsScreenContext` (composition interface).
   - Source friction proven: `RootScene.swift:341` manually derives one public parameter from another projection field to keep the F2 pair consistent.
   - Why the current interface is shallow or misplaced: the caller must know the coupling rule; the type cannot.
   - What behavior should move behind the deeper interface: availability branching becomes one sum-type match at the render site (already partially structured at `+AppleMusic.swift:43-69`).
   - Dependency category: in-process
   - Test surface after the change: the same snapshot tests; construction becomes exhaustive over two states.
   - Smallest first step: owner adjudication of the F2 invariant (backlog item 3), then the enum.
   - What not to do: do not inject a protocol or view-model layer; the struct is the right shape, just modeled as a product.

## Builder Notes

1. **Pattern**: a repo that documents its own rule at one enforcement site (`AppSnapshot.swift:211` "Projection-owned so the view stays render-only") still leaks the rule where no grep reaches — view-side switches returning user-facing strings are the missed shape, and AGENTS.md says the enforcement is partial by design. **Recognize**: `private func … -> String?` whose body is a `switch` over an enum from another module. **Smallest rule**: if a view computes a sentence, a type or projection computes it instead.
2. **Pattern**: permissive defaults on a composition type convert a forgotten wire-up into wrong output instead of a compile error. **Recognize**: `= false` / `= {}` parameters that select user-visible branches. **Smallest rule**: defaults only where every defaulted value is safe in every combination; otherwise make the state a sum type.
3. **Pattern**: "compliance is not clearance, and claims are not checks" — a comment asserting its own duplication is "gate-checked" was verified before filing (real: `scripts/check_boundaries.sh:1195-1208`), which converted a would-be Finding into an accepted residual. **Recognize**: prose citing an enforcement mechanism. **Smallest rule**: open the cited check before trusting or filing it.
4. **Priority-1 accounting** (Backlog Prioritization Pass): P1 moves `state_management` and `domain_modeling` 9.0→9.5. The further-from-target candidate F-028 (8.5) was considered first under criterion 1 and ranks second on expected marginal gain — F-025 moves two dimensions onto the target line at equal severity, while F-028 moves one halfway; neither fails SPT, so severity/gain decides, not the SPT-rejection branch. F-026 would tie on state-ownership merit but is blocked by the doc-conflict stop-and-ask (criterion 0: ranked on merit, blocker named, next actionable item taken).
5. **Scorecard humility check** — (1) `state_management` at 9.0 vs 9.5: the F1 trio is 28 lines and no live drift is demonstrated; a reviewer could read the 9-anchor as met with F1 an accepted residual — this critic scores it unmet because the owner-site violation is the anchor's own criterion ("presentation state separated… writers explicit"), file:line `DiagnosticsView.swift:81`. (2) F2's "Split and ambiguous" Authority Map verdict treats the `RootScene.swift:341` derivation as an invariant the types must not rely on; if availability is defined at build time (compile-time AM support), that line is the single source and only the doc is stale, not the model — uncertainty because both readings fit current source. (3) `concurrency` at 10: the claim is scoped — G25's zero-continuation sweep covers this subtree only; the `.task` refresh pair (`DiagnosticsView.swift:42-45`) could be read as lifecycle-sensitive, and the reducer guard (`DiagnosticsReducer.swift:15`) is out of scope, so its re-entry proof is quoted, not re-derived here.
6. **Execution evidence**: pinned `--quick` run bare this loop (exit 0, 3396 tests) — `scripts/attested_run.py` is absent from the repo so no attestation-ledger event exists to cite; re-verify `--targeted` on any execution loop per AGENTS.md DoD.

## Final Judge Narrative

**Place** — for the scoped subtree: a genuinely disciplined feature surface (single dispatch path, honest seams, verified doc claims, ADR-consistent copy) held back from contest-winning structure by one repeated ownership pattern (display shaping in views, three sites, F-025), an untested control-mapping surface (F-028), and a composition interface with defaults that make lying states reachable (F-026, blocked on an owner call the repo itself mandates). Simplification helped this loop — the two strongest corrections are moves and a deletion, adding no seam; runtime ownership is trustworthy where tested; concurrency is trustworthy and clean; tests currently under-protect the screen they most obviously govern. Future work risk is the opposite of ceremony: the honest fixes are relocations and one sum type, and any proposal that reaches for a `SettingsBinder` protocol is the fake-clean reward to refuse.

## Retired Findings (this loop)

None.

## Loop 1 Plan (dry-run)

**Invocation**: `--dry-run`, scope `BenchHypeKit/Sources/BenchHypeSettingsFeature`, loop 1/10. This plan executes on the next loop, invoked without `--dry-run` (no `--reset` needed).

**Selected target**: P1 = F-025 (stable_id F-025). No tiebreak fired (single highest by expected marginal gain; rationale in Builder Notes item 4).

**Simplify Pressure Test (P1)**: Q1 fixes real ambiguity — yes (three questions, two owners today: the view and its absent projection/type answer "what text does phase/route/interruption show"); Q2 smallest honest fix — yes (byte-identical string relocations, no new types beyond a computed property); Q3 no duplicate owners after — yes (one owner per string, view functions deleted); Q4 runtime honest — yes (rendered text unchanged; verified against current view strings at DiagnosticsView.swift:81-97, BackupSettingsView.swift:112-125); Q5 measurable gain — yes (state_management 9.0→9.5, domain_modeling 9.0→9.5; the defect class becomes structurally impossible at these three sites). Structural gate: no new seam (Unified Seam Policy untouched); deletion test passes for the removed helpers; tests after refactor live at the projection interface (existing `SettingsViewStateTests` + `DiagnosticsViewSnapshotTests`).

**Files to change (Step 3, loop 2)**:

- `BenchHypeKit/Sources/BenchHypeDomain/Values/Route.swift` — add `displayName` computed property to `OutputDestination` (Hard Rule 4 canonical home).
- `BenchHypeKit/Sources/BenchHypeApplication/Projections/SettingsViewState.swift` — add `interruptionLabel` (or equivalent display field) to `DiagnosticsViewState`; assemble from `InterruptionState`.
- `BenchHypeKit/Sources/BenchHypeApplication/State/BackupState.swift` — add `statusMessage: String?` computed on `BackupPhase`.
- `BenchHypeKit/Sources/BenchHypeSettingsFeature/DiagnosticsView.swift` — delete `routeDestinationLabel`/`interruptionLabel`; read projected strings; drop `public` from `DiagnosticsView` (F-027).
- `BenchHypeKit/Sources/BenchHypeSettingsFeature/BackupSettingsView.swift` — delete `statusMessage`; read from state.
- `BenchHypeKit/Tests/BenchHypeSettingsFeatureTests/SettingsViewStateTests.swift` — assert relocated strings (byte-equal to current view outputs) through the projection interface.
- `BenchHypeKit/Tests/BenchHypeSettingsFeatureTests/DiagnosticsViewSnapshotTests.swift` — regenerate only if record serialization changes (expected: it does not; strings move between owners, view tree output is identical).

**Files NOT to touch** (blast radius bounded): `AppReducer*.swift`, `SettingsDraft`, `IntentDispatcher`, `DiagnosticsReducer.swift`, `CuesFileStore.swift`, `RootScene.swift`, `BenchHypeApp.swift`, `PaywallView.swift`, `HelpView.swift`, `SettingsScreenContext.swift` (that file belongs to blocked F-026), `UITestIdentifiers.swift`, all UI test targets.

**AGENTS.md gate discipline for the execution loop**:

- F-025 crosses no stop-and-ask gate: it adds no stored state, no intent/effect/seam; the `OutputDestination.displayName` addition is exactly Hard Rule 4's prescribed move — eligible for the documented `$contest-refactor` safe harbor (docs/contest-refactor-safe-harbor-reference.md, read this loop). At Step 3, record the harbor basis in `finding.evidence` (writer/reader/reducer/projection/documentation/test inventory — current inventory: readers = DiagnosticsView/BackupSettingsView; interpretations = the three view functions + `isWireless` on type + PreflightUseCase severity switch, a different question, stays), `.structurally_necessary`, and the reviewer prompt must carry the quoted harbor addendum. `git status --short --untracked-files=all` must show only the three workflow artifacts at the checkpoint.
- Any behavior-preserving relocation crossing the module-line (feature → application/domain) records `risk_boundary_evidence {boundary_kind: cross_file_visibility, verification: compile_matrix, detail: <affected-target build via ./scripts/run_local_gate.sh --targeted>, mechanically_testable: true}`.
- Gate tier for execution: `./scripts/run_local_gate.sh --targeted` (Swift source change in BenchHypeKit; the pinned `--quick` floor already passed green this loop as ground truth).
- F-026 (backlog P3) may not be attempted autonomously: its precondition is the unconditional code-vs-doc-conflict stop-and-ask — the owner must adjudicate whether `+AppleMusic.swift:12-24`'s cold-start branch is the invariant (then `RootScene.swift:341` is the bug, out of scope) or the stale doc (then the sum type adopts the derivation). If the next non-dry-run loop reaches F-026 as its turn, it must emit HALT_STAGNATION/user_decision with that question, not guess.

**Expected scorecard impact after execution**: `state_management` 9.0→9.5, `domain_modeling` 9.0→9.5, `simplicity` queued→accepted at 9.5, architecture/credibility unchanged (F-026's queue stays until the owner call). Loop 2+ then takes F-028.

**HALT_DRY_RUN notes**: no code changed, no commit, registry updated in memory only (reserved F-025…F-028; on disk `findings_registry.json` stays at next_serial 25 until an execution loop's Step 3 step 10 writes it). Re-invoke without `--dry-run` to execute.

```
loop 1/10 | HALT_DRY_RUN | plan-only (Step 2) | tests green | 861s
```
