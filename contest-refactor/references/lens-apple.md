# Review Lens: Apple / SwiftUI

Apply when discovered stack contains `Package.swift`, `*.xcodeproj`, `*.xcworkspace`, or Swift sources dominate.

This lens specializes the meta-rules in `method.md` and the score anchors in `architecture-rubric.md` for Swift/iOS. Counts do not score in either direction. Penalize duplicate-authority architecture; reward small honest architecture.

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

## Hidden State Machines (Apple-flavored)

- Multiple booleans/optionals jointly encoding one logical state.
- loading/error/empty/content/retry/selection modeled as independent flags rather than honest state model.
- Duplicated state across view, domain, service, cache, persistence layers.
- Navigation/presentation state that can drift out of sync with domain state.
- Async flows that can leave UI in invalid intermediate combinations.

Penalize state models permitting impossible combinations. Recommend explicit state-machine formalization only where it removes real ambiguity — do not force enum-heavy modeling everywhere.

## Ownership (Apple-flavored)

Map actual writers. Do not infer ownership from access control alone.

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

### Authority-Map test-surface cross-check (mandatory before scoring test_strategy ≥ 9)

A passing test count is not test strategy. Before scoring `test_strategy` ≥ 9, walk the Authority Map produced in this same loop:

1. For each concern with `verdict: Single and clear`, identify at least one test file that exercises that concern's mutation paths through its Interface (not through internal helpers).
2. For each concern with `verdict: Split and ambiguous`, the test gap is part of the finding — note it in the finding, not in test_strategy.
3. For each shell-level seam (`AppRuntime`, `RootScene`, `ScenePhase` mirror, URL guard, app-launch composition), verify a direct test file exists. App-shell coverage gaps are common; "1500 tests pass" with zero `AppRuntimeTests.swift` is a Noticeable weakness, not a 9.5 score.
4. For every contest-relevant feature flow flagged in the Feature-flow choreography audit above, verify a feature-surface test exists (sheet present/dismiss, bulk-import cancel, source-choice branch). Missing = test_strategy ceiling at 8.

Aggregate count → test_strategy is a fake-clean reward. Surface coverage → test_strategy is honest evidence.

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
