# Review Lens: Apple / SwiftUI

Apply when discovered stack contains `Package.swift`, `*.xcodeproj`, `*.xcworkspace`, or Swift sources dominate.

This lens specializes the meta-rules in `method.md` and the score anchors in `architecture-rubric.md` for Swift/iOS. Counts do not score in either direction. Penalize duplicate-authority architecture; reward small honest architecture. Findings produced here must follow The Evidence Chain from `method.md`: Claim → Source → Consequence → Remedy.

## Contents

- [SwiftUI Discipline](#swiftui-discipline)
- [Concurrency & Runtime Safety](#concurrency--runtime-safety)
- [Cross-platform compile correctness](#cross-platform-compile-correctness)
- [Hidden State Machines (Apple-flavored)](#hidden-state-machines-apple-flavored)
- [Ownership (Apple-flavored)](#ownership-apple-flavored)
- [Tests / Regression Resistance (Apple-flavored)](#tests--regression-resistance-apple-flavored)
- [Accessibility audit](#accessibility-audit)
- [Incremental Test Scoping](#incremental-test-scoping)
- [Useful Metrics](#useful-metrics)
- [Apple-specific Core Questions](#apple-specific-core-questions)

## SwiftUI Discipline

- SwiftUI state separate from domain state. `@Observable`, `@State`, `@Bindable`, `@Environment` have clear write rules.
- Persisted SwiftData `@Model` state separate from runtime state. SwiftData mutations originate behind clear persistence seams.
- Navigation has one owner. Presentation has one owner.
- `@Environment` injection used honestly, not as a service-locator costume.
- SwiftUI views thin and declarative, not informal controllers.
- UIKit and SwiftUI live behind clear seams when they perform durable side effects.
- Domain policy does not import or depend on SwiftUI, UIKit, SwiftData, StoreKit, AVFoundation, third-party SDK types, or other platform framework types.
- Lifecycle seams explicit.
- Previews and fixtures supported by design but not used as proof of quality.
- Do not reward MVVM, repositories, coordinators, or protocol abstraction unless they reduce ambiguity or coupling per the architectural tests in `architecture-rubric.md`.
- **Collection identity (correctness, not perf).** `ForEach` / `List` over **dynamic or reorderable** data needs identity that is stable, outlives the view, and is not derived from mutable content. (`.indices` / offset is acceptable for genuinely static content — not a blanket ban.) Unstable identity on dynamic data is a `state_management` finding, not a style nit.
- **Stable workflow identity** (canon smell — `architecture-rubric.md`). Apple telltale: `.onMove` / `.onDelete` hand the reducer raw `IndexSet` offsets from a *filtered/sorted* projection, which do not index the stored collection. Resolve offsets to durable IDs in the view, or validate the exact ordered slice at the write authority.
- **Passed-value ownership.** Declaring a parent-passed value as `@State` / `@StateObject` captures the initial value and ignores later parent updates — a bug **only when continued parent synchronization is expected**. Seeding a local editable draft from a passed value is legitimate; flag only on evidence the child is expected to track the parent. (`state_management`.)
- **Invalidation problems need evidence.** Surface an over-invalidation finding only from a **demonstrated** source — Instruments, `Self._printChanges()`, a measured hot path — not from heuristics. Do not assert that passing an `@Observable` object broadens invalidation (the Observation framework tracks only the properties a view actually reads), and do not turn `AnyView`, non-unary rows, or missing `Equatable` into blanket findings. Map a demonstrated case to `framework_idioms`.
- **Unstable shaped output** (canon smell — `architecture-rubric.md`). Apple telltales: iterating `Dictionary` / `Set` `.values` into rows, sorting by a non-unique display label with no tie-breaker, or resolving child data before applying the selected scope — surfaces as flaky SwiftUI snapshots and wrong-row continuity. Shape once at the projection boundary with a durable tie-breaker (`id`, explicit order, sequence).
- **Workflow time in presentation** (canon smell — `architecture-rubric.md`). Apple telltales: SwiftUI `.task`, `Timer`, `Task.sleep`, `.onReceive` are fine for animation, debounce, or ephemeral UI dismissal — not for durable domain clocks. Move the clock to a coordinator / reducer effect / clock-injected policy; a view may render the deadline (`TimelineView`) but must not own expiry.

## Concurrency & Runtime Safety

Investigate:
- `@MainActor` use on UI-affecting state
- actor isolation correctness
- task lifetime tied to correct lifecycle owner
- task ownership (no unbound `Task { }` in adapter or application code)
- cancellation behavior explicit and correct
- reentrancy hazards
- fire-and-forget tasks that mutate state
- racing async flows
- overwritten state
- wrong lifecycle attachment
- `Sendable` and cross-actor usage

Counts do not score. High or low @MainActor / async / actor count is not itself a finding.

TSAN findings, compiler concurrency warnings, Non-Sendable warnings are serious evidence; map each to source and behavior.

Unstructured `Task` usage needs ownership proof. Treat unclear concurrency as architecture weakness, not implementation footnote.

**Reservation after suspension** (canon smell — `architecture-rubric.md`). Apple telltale: Swift actor methods are reentrant across every `await` — a call parked at `await pricing.quote(...)` lets another call enter and pass the same guard. Reserve/mark before the first suspension, or move check+claim into one actor-isolated / transactional / unique-constraint authority after it.

### Continuation-bridge delegate audit (mandatory when adapter uses `withCheckedThrowingContinuation` + timeout)

`CheckedContinuation` guarantees single-resume, **not** single-side-effect. A delegate body that fires after a timeout or cancellation has already resumed the continuation can still execute its other state writes. Pattern is contest-relevant whenever an SDK delegate writes auth/session/connection state alongside the resume.

For every adapter file matching `rg -l "withCheckedThrowingContinuation|CheckedContinuation" Sources/`:

1. Find the `signIn` / `connect` / `authorize` / equivalent entry point. Identify the timeout or cancellation path that resumes the continuation.
2. Open the delegate extension (often `+Delegate.swift`). Read every delegate method that writes adapter state.
3. **Failure pattern**: delegate body has unconditional state mutations followed by a nil-coalesced `continuation?.resume()`. Late-fire after timeout still mutates state.
4. **Honest pattern**: delegate body gates on a per-attempt token (`UUID`, generation counter) before any state write — the same token the timeout clears.
5. **Also check `signOut` / `disconnect` paths**: do they cancel the in-flight continuation? If not, the user can sign out during a sign-in window and silently re-authenticate.

Severity calibration: a real observable state flip after timeout = Noticeable weakness minimum. The `CheckedContinuation` single-resume guarantee is not a defense; it covers exactly one line.

### Feature-flow choreography audit (mandatory for every contest-relevant user-facing feature)

A contest-grade architecture cannot have one important workflow switch ownership model depending on which branch the user picked. For each feature directory under `Sources/<App>*Feature/`:

1. Enumerate the user-flow entry points (sheets, screens, top-level views).
2. For each entry point, walk every branch — file picker / SDK source / direct entry / wizard / etc.
3. Tag each branch's choreography: **reducer-owned** (intent → reducer arm → effect), **executor-owned** (workflow executor mediates), **view-owned** (view calls ports/builds drafts directly, then dispatches a single intent).
4. **Failure pattern**: more than one choreography model inside one feature for the same business job (e.g. local bulk import is reducer/workflow-owned but Spotify bulk assembles drafts in the view body before a terminal `.batchSaveX` dispatch).
5. **Honest pattern**: one choreography boundary per workflow family. All branches reach the same seam at the same shape.

Multi-choreography in one feature = Serious deduction (locality + leverage failure). Recommend extracting a feature-specific context (`AddSoundContext`) instead of a god-bag context (`LibraryScreenContext`) that exposes raw ports plus the entire dispatch helper surface.

### Sheet / binding symmetry audit

A SwiftUI `Binding(get:set:)` whose `get` arm reads multiple state slots must have a `set` arm that unwinds every slot it can read. Asymmetric present/dismiss = the sheet can present from one truth and dismiss to another, leaving stale presentation state that re-presents.

For every `Binding(get:` in scene/root/feature shell files:

1. List every state slot the `get` arm checks (e.g. `bulkAddSoundSession != nil OR libraryDraft.cue.existingID == nil`).
2. List every state slot the `set` arm mutates on dismiss.
3. **Failure pattern**: `set` arm clears one slot via `if-else`, leaving the other slot intact when both were truthful. Sheet immediately re-presents.
4. **Failure pattern**: `set` arm dispatches a feature-specific cancel intent (`.editing(.cancelBulkAddSound)`) that doesn't reach the actual workflow cancellation path (`.workflow(.cancelBulkImport)`).
5. **Honest pattern**: one dedicated reducer-facing `dismissAddSoundSheet` action that clears every slot the `get` arm reads, in the right order, through the authority that owns each.

Asymmetric sheet binding for a contest-relevant feature = Serious deduction (state ownership credibility hit).

### Failure modes & observability (Apple-flavored)

Apple repos load only `lens-apple.md` (plus always-included `lens-security.md`); `lens-generic.md` is **not** in the Apple load set. So this subsection inlines the five generic failure-mode categories alongside Apple-specific bullets. (Canonical detailed detection rules per language live in [lens-generic.md § Failure modes & observability](lens-generic.md#failure-modes--observability) for non-Apple stacks.)

**Generic categories (always check on every loop)**:
1. **Silent-swallow audit** — Swift hits: `try?`, `catch { }`, `_ = try`, `as? T` that drops the error. Each needs an inline rationale (comment, log, compensating return).
2. **Retry/backoff policy** — every external-call path (network, disk, IPC, subprocess) needs an explicit retry policy or a documented "// no retry: <reason>" comment.
3. **Error-context preservation** — catch blocks must wrap (`throw .wrapped(original: err, ...)`), log with breadcrumb (`logger.error("...", error: err, file: #file, line: #line)`), or re-throw verbatim. Strip-and-rethrow loses provenance.
4. **Observability at adapter boundaries** — every port crossing network/disk/IPC emits telemetry on entry/success/failure. Missing telemetry on user-visible paths is a `credibility` finding.
5. **Panic-recovery on executors** — background executors (effect pumps, job queues, task pools) must wrap unit-of-work execution with panic-recovery that logs and either restarts or marks-failed.

**Then layer these Apple-specific concerns**:

1. **URLSession background config.** Any `URLSession(configuration: .background(withIdentifier:))` requires `URLSessionDelegate.urlSession(_:task:didCompleteWithError:)` implementation. App suspended mid-transfer continues background; result lands at delegate, not the completion handler. Missing delegate = silent dropped results. Hits: `grep -rn 'URLSessionConfiguration.background' Sources/`.
2. **AVAudioEngine start/stop pairing.** Every `engine.start()` must pair with `engine.stop()` in error-path AND happy-path AND `deinit`. Engine left running across a fatal node-graph error leaks the audio session and the engine resources. Hits: `grep -rn 'AVAudioEngine\(\)\|engine.start(' Sources/`. Watch for `try?` on `engine.start()` followed by no failure handling.
3. **MusicKit auth fail vs downgrade.** `MusicSubscription.subscriptionUpdates` can emit `.fetchFailed` (transient, retryable) or a confirmed-downgrade (`canPlayCatalogContent: false`). Treating these as the same path silently locks users out on transient failures. Pattern: separate `.fetchFailed` → retry-with-backoff vs `canPlayCatalogContent == false` → user-facing subscription prompt. Hits: `grep -rn 'MusicSubscription\|subscriptionUpdates\|canPlayCatalogContent' Sources/`.
4. **`Task { @MainActor in }` in `deinit` (HR-9 carve-out).** Swift `deinit` cannot `await`; the standard pattern fires-and-forgets a cleanup Task on MainActor. Audit: every `deinit` containing `Task { @MainActor in ... }` must document why (resource that ONLY the deinitee can release; cancellation that ONLY MainActor can perform). Undocumented uses = HR-12 violation (mislabels compliance as carve-out).
5. **`os_log` redaction.** `os_log("%@", userInput)` is public by default — user data appears in Console.app + sysdiagnose dumps. Sensitive interpolation must use `%{private}@` or `%{public}@` explicitly (the absence of the modifier is a violation). Hits: `grep -rn 'os_log\|Logger().' Sources/` — every `%@` site needs explicit privacy annotation.

## Cross-platform compile correctness

contest-refactor moves and splits code (Replace-don't-layer; inlining). On Apple multi-platform targets that is the exact trigger for a refactor that compiles on one platform and breaks another — and a single-platform test run (e.g. iOS Simulator) will not catch it. (Provenance / deeper recipes: the `apple-multiplatform` skill.)

**Three distinct gating mechanisms — do not conflate:**

- `#if canImport(UIKit)` answers *module importability*. It is **true on tvOS and Mac Catalyst too**, so it does not prove a given symbol exists.
- `#if os(iOS)` answers *which target OS compiles the code* — i.e. per-OS SDK symbol presence. A UIKit symbol the tvOS SDK lacks (e.g. `UIImpactFeedbackGenerator`) is gated here, not by `canImport`.
- `#available` / `@available` answers *API-version availability within an OS* (deployment-target gating).

Using `canImport(UIKit)` to gate a symbol the tvOS SDK lacks is a correctness bug — the guard passes on tvOS and the build breaks at the symbol. The correct guard is `#if os(...)`; runtime version differences use `#available`.

**File-split visibility hazard (a direct refactor risk).** `fileprivate` members are file-scoped; `private` members are reachable from same-file extensions of the same type (Swift 4+). Moving a type or extension into a new file can therefore lose access to either — a plain compile break, platform-independent in mechanism. It often *appears* on only one platform because the moved code sits behind `#if os()`, has different target membership, or only some targets are built in CI. When a refactor splits or relocates Swift code, confirm visibility holds across the affected targets.

**Discover the declared target matrix first.** "All platforms" means the project's **affected declared targets** — read the schemes, `Package.swift` `platforms:`, and project target list. Audit and verify only what the project ships, not every theoretical Apple OS or OS version.

**Illustrative, non-exhaustive divergence traps** (verify against the project's current SDK + deployment targets — these shift between SDK releases, so treat them as smoke, not fixed rules): toolbar placements `.topBarLeading` / `.topBarTrailing` (absent on macOS), `.tabViewStyle(.page)` (absent on macOS), `.fullScreenCover` (absent on macOS), `@Environment(\.editMode)` (iOS-family only), haptics and drag-receiving (absent on tvOS).

**Scoring — via existing Severity Anchors, no new gate.** A confirmed compile failure on a supported target is a **Likely disqualifier** (a core property — "it builds" — is broken on a primary flow) and blocks 9.5 acceptance until fixed. A refactor that touches multi-platform or `#if`-gated code but leaves an applicable target **unverified** is a **Serious deduction** (unresolved risk) until the Actor produces the compile evidence required by [method.md Meta-Rule 4](method.md#meta-rules-apply-everywhere). Do not invent a gate on the *presence of a "cross-platform note"* — a documentation proxy is gameable and is itself a fake-clean reward.

## Hidden State Machines (Apple-flavored)

- Multiple booleans/optionals jointly encoding one logical state.
- loading/error/empty/content/retry/selection modeled as independent flags rather than honest state model.
- Duplicated state across view, domain, service, cache, persistence layers.
- Navigation/presentation state that can drift out of sync with domain state.
- Async flows that can leave UI in invalid intermediate combinations.
- State with no authority (canon smell — `architecture-rubric.md`): map writers *and* readers before treating a mutable field as an owner; a field with write sites but no application/test read site is not one.
- Causal runtime context (canon smell — `architecture-rubric.md`): completion/error/progress events for an existing record must resolve from the record's captured request/context, not mutable ambient "current" selection. Current-selection *commands* are fine when they validate identity/version at the write authority.

Penalize state models permitting impossible combinations. Recommend explicit state-machine formalization only where it removes real ambiguity — do not force enum-heavy modeling everywhere.

## Ownership (Apple-flavored)

Map actual writers. Do not infer ownership from access control alone.
For every mutable property you treat as runtime-significant, map both writers and readers (see canon smell *state with no authority*); a field with write sites but no application/test read site is not an owner — delete it, emit the fact through the existing stream, or move it to the type that decides behavior.
For adapter seams, compare the Interface output contract with facts the adapter receives from the external SDK/system: a promised downstream value dropped to `nil`/zero/empty/placeholder is *adapter output contract incompleteness* (canon smell) — publish the fact or narrow the Interface.

Treat as smoke (confirm before findings):
- global mutable state
- `static var` state
- public mutable properties
- broad internal mutation
- singleton mutation
- shared mutable references

Reducer-style shared state may be valid, but it must still have clear write rules.

## Tests / Regression Resistance (Apple-flavored)

Check:
- deterministic business-logic tests (no `Thread.sleep`, `Task.sleep`, polling without cancellation)
- async tests prove ordering without sleeps
- explicit failure paths
- one source of truth
- diagnosable runtime behavior
- previews / fixtures / tests reinforce design (do not bypass it)
- old low-level waste tests removed

Treat Interface as test surface. Tests should use real Interfaces, assert outcomes, survive refactor, avoid implementation-mirroring.

Coverage is proxy, not proof. Absence of tests on stateful domain, reducer, persistence, networking, async runtime Modules is a serious regression-resistance concern. Name the untested Interface and explain why it should be testable.

Flag sleeps, timing hacks, unowned time, randomness, UUIDs only when they harm determinism. Do not add injection ceremony without need.

### Recorded-fixture mismatch in Step 3 (regenerate vs revert)

`swift-snapshot-testing` `.dump` / golden fixtures encode *expected* output. When a Step 3 refactor *intentionally* changes that output (added a row, renamed a label, reordered a section), the fixture test fails because the recording is stale — not because the build broke. Per [SKILL.md Step 3 sub-step 3], before reverting confirm the **only** failures are these recorded mismatches and the diff is exactly your intended change, then regenerate and re-run:

- `SNAPSHOT_TESTING_RECORD=all swift test --filter <SuiteName>` regenerates the affected `.dump`s; then re-run the suite **without** the env var to confirm green.
- Scope the `--filter` to the suite whose recordings you meant to change — a blanket regenerate can mask a real regression in an unrelated snapshot.
- The `.dump` serializes the model, not the rendered view — a diff that touches model fields you did not intend to change is a regression signal, not a stale recording; revert.

If any non-snapshot test fails, or the snapshot diff includes output you did **not** intend to change, treat it as a real break and revert. Regeneration never launders a behavior regression green.

### Authority-Map test-surface cross-check (mandatory before scoring test_strategy ≥ 9)

A passing test count is not test strategy. Before scoring `test_strategy` ≥ 9, walk the Authority Map produced in this same loop:

1. For each concern with `verdict: Single and clear`, identify at least one test file that exercises that concern's mutation paths through its Interface (not through internal helpers).
2. For each concern with `verdict: Split and ambiguous`, the test gap is part of the finding — note it in the finding, not in test_strategy.
3. For each shell-level seam (`AppRuntime`, `RootScene`, `ScenePhase` mirror, URL guard, app-launch composition), verify a direct test file exists. App-shell coverage gaps are common; "1500 tests pass" with zero `AppRuntimeTests.swift` is a Noticeable weakness, not a 9.5 score.
4. For every contest-relevant feature flow flagged in the Feature-flow choreography audit above, verify a feature-surface test exists (sheet present/dismiss, bulk-import cancel, source-choice branch). Missing = test_strategy ceiling at 8.

Aggregate count → test_strategy is a fake-clean reward. Surface coverage → test_strategy is honest evidence.

## Accessibility audit

User-facing iOS code without accessibility considerations is shipping with a deferred-cost class of bugs. Every contest-relevant Apple lens loop must run this audit once and surface gaps as findings (`framework_idioms` dimension hit; `test_strategy` ceiling at 9 if a11y surfaces have no test).

1. **VoiceOver labels.** Every tappable view (`Button`, `.onTapGesture`, `Toggle`, `Picker`, custom gesture handlers) must have a non-empty `.accessibilityLabel(_:)`. Decorative `Image` views must declare `.accessibilityHidden(true)`. Smoke check: `grep -rn 'onTapGesture\|Button(action:\|gesture(' Sources/ | wc -l` should approximately equal `grep -rn 'accessibilityLabel(' Sources/ | wc -l` (within 2x); gross mismatch is a finding.
2. **Dynamic state semantics.** Custom controls whose value changes (sliders, knobs, segmented selectors, custom toggles) need `.accessibilityValue(_:)` (current value as text) and `.accessibilityHint(_:)` (what happens on activation). VoiceOver users hear the value AND the action, not just the label.
3. **Dynamic Type.** Hardcoded font sizes (`Font.system(size: 12)`) lock layout — fails Dynamic Type. Prefer `Font.system(.body)`, `Font.system(.headline)`, etc. (text-style family scales with user preference). Hits: `grep -rn 'Font\.system(size:\|\.font(\.system(size:' Sources/`. Each hit needs justification (icon font, tabular numerics, etc.) or is a finding.
4. **Color-only state.** State communicated only through color (red = error, green = success) is invisible to color-blind users. Every color-conveyed state needs a non-color affordance: label text, SF Symbol, position, or shape change. Audit: locate every `.foregroundStyle(.red)` / `.foregroundStyle(.green)` / `.background(Color.X)` site; trace whether a non-color signal exists in the same view.
5. **Focus order.** Custom containers (`HStack`/`VStack` with mixed interactive + decorative children, custom collection views) need deterministic focus order. Verify via the Accessibility Inspector in Xcode (Simulator → Hardware → Accessibility Inspector) — focus walks elements in a predictable order. Random / row-major-then-jump = a finding.
6. **Reduce Motion / Reduce Transparency / Increase Contrast.** Animations gated on `accessibilityReduceMotion`; backdrop materials gated on `accessibilityReduceTransparency`; thin stroke weights gated on `accessibilityDifferentiateWithoutColor` where structural. Hits: `grep -rn '@Environment(\\.accessibility' Sources/` — count must be > 0 for any app shipping animations or backdrop materials.

A11y findings are `framework_idioms` dimension (platform best practices); persistent gaps drop `test_strategy` ceiling at 9 (a11y surfaces are testable via `XCUIElement.staticTexts[<label>]` accessor patterns — no test = surface-coverage gap).

## Incremental Test Scoping

Used when `--test-filter <pattern>` is set on the invocation. Step 0 records `test_scope: "incremental"` and `test_filter: "<pattern>"` in CURRENT_REVIEW.json discovery (first loop only). Per-stack patterns:

- XCTest: `swift test --filter <ModuleTests>.<TestClass>/<testMethod>`
- Module-level: `swift test --filter <ModuleTests>`
- Package-level: `cd <pkg_dir> && swift test --filter <pattern>`
- xcodebuild equivalent: `xcodebuild test -only-testing:<Target>/<Class>/<Method>`

Trade-off: incremental misses regressions outside `<pattern>`. G21 in [validation.md](validation.md) requires a full-suite reverify before HALT_SUCCESS when any prior loop in REVIEW_HISTORY ran incremental.

## Useful Metrics

When available:
- SwiftLint findings (force unwraps, force casts, large types, cyclomatic complexity, broad access control, unused code — these matter; line length / trailing whitespace / formatting preferences do not)
- Taylor reports
- complexity reports
- Sonar duplication / coverage reports
- xcodebuild test output
- xccov coverage reports
- compiler diagnostics
- TSAN reports
- grep counts
- SwiftSyntax counts

Map every metric to source + behavior. Reject metric-only findings. Large explicit code may be honest; small split code may be worse. Raw framework calls in infrastructure are not automatic issues; domain policy leaking frameworks is.

## Apple-specific Core Questions

1. Would experienced Swift/iOS engineers respect this as high-quality?
2. Does code use Swift, SwiftUI, platform frameworks idiomatically?
3. Is concurrency handled correctly, explicitly, testably?
4. Do previews/fixtures/tests reinforce architecture rather than bypass it?
