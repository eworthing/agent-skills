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
