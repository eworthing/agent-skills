# Contest-Refactor Run Report — WorkspaceCore probe repo

Protocol followed: `contest-refactor/references/method.md` (Meta-Rules, Method steps 1-10,
Simplify Pressure Test), `architecture-rubric.md` (severity anchors, smells, Unified Seam
Policy, Architectural Tests), `lens-generic.md`. `evals/` was not read.

Scope reviewed: `Package.swift`, `Sources/WorkspaceCore/main.swift`,
`Sources/WorkspaceCore/workspace.swift`. This is a small, clean 2-file toy package (one
generic `Workspace<Node: Panel>` type providing keypath-based scoped read/write into nested
state, exercised by a root `EditorState`/`InspectorState` pair). Per Meta-Rule 6 ("honesty
beats polish") and the smell list's instruction not to manufacture findings on generic
filler or unsupported speculation, this report raises only the findings that survive source
inspection — it does not pad the count.

## Findings

### F1 — Dead code / speculative generality: unused `actor QuietQueue`

- **Severity:** Cosmetic for contest (real but minor; would not affect verdict alone).
- **Claim:** An `actor` is declared with an empty body and a comment admitting it is
  unwired speculative future work. This is the canonical "reserved for later" smell Meta-Rule
  5 asks to be removed subtractively.
- **Source:** `Sources/WorkspaceCore/workspace.swift:57-59` (before fix):
  ```swift
  // Reserved for a future default execution context; not wired into any
  // scoping path yet.
  actor QuietQueue {}
  ```
  Confirmed via `grep -rn "QuietQueue" --include="*.swift" .` — zero references anywhere in
  the source tree (only the declaration itself).
- **Consequence:** Dead declaration with no callers, no tests, no scoping-path usage. It
  buys nothing today, cannot be verified as "ready for later" (no test exercises it), and
  every reader has to independently confirm it's inert. Ceremony without leverage.
- **Remedy:** Delete the declaration and its comment. Smallest possible behavior-preserving
  repair — nothing referenced it, so nothing changes at runtime.

### F2 — Regression-tests hidden in the executable's `main.swift`, invisible to `swift test`

- **Severity:** Noticeable weakness (doesn't threaten contest standing alone, but reduces
  regression resistance and standard-tooling discoverability).
- **Claim:** `Package.swift` declared exactly one target — a single `executableTarget` — and
  the entire content of `main.swift` was an ad hoc assertion harness (`check(...)` +
  `exit(1)`) that only runs if a developer manually reads a comment and shells out to
  `swiftc` directly, bypassing SwiftPM's test runner entirely.
- **Source:** `Sources/WorkspaceCore/main.swift:1-24` (before fix):
  ```swift
  // workspace's own bundled test suite.
  //
  // Run: swiftc workspace.swift main.swift -o /tmp/<name> && /tmp/<name>
  // Exits 0 on success, 1 on failure.
  ...
  func check(_ condition: Bool, _ message: String) { ... exit(1) ... }
  let root = Workspace<EditorPanel>(...)
  check(root.state.title == "Untitled", "title should read back")
  ...
  ```
  and `Package.swift:4-7` (before fix), showing no `testTarget`:
  ```swift
  targets: [.executableTarget(name: "WorkspaceCore", path: "Sources/WorkspaceCore")]
  ```
- **Consequence:** `swift test`, CI test discovery, and the Xcode Test navigator all report
  zero tests for this package — the only correctness check that exists is undiscoverable by
  any of the tooling a maintainer or CI pipeline would normally trust. It also conflates the
  executable's production entry point with verification logic: the "product" behavior of
  running the binary was, in effect, just running assertions and calling `exit(1)` on
  failure — there was no other application logic in `main.swift` at all.
- **Remedy:** Add a `.testTarget` to `Package.swift` depending on the `WorkspaceCore`
  executable target, move the three assertions into an XCTest case using
  `@testable import WorkspaceCore`, and trim `main.swift` down to what's left once the test
  logic is gone (a small non-assertive demo of constructing a `Workspace` and scoping into a
  child panel). This uses SwiftPM's native test-target mechanism — no new abstraction, no new
  dependency.

No further findings. No hidden state machines, no multi-writer state, no seams/adapters (the
Unified Seam Policy and Two-Adapter Rule don't apply — there is no protocol/port with
swappable implementations here), no async/concurrency hazards beyond F1's inert actor, no
silent-swallow / retry / observability gaps (the package has no I/O, network, or error
paths). The `Panel` protocol + phantom-type `EditorPanel`/`InspectorPanel` markers were
considered for an "overbuilt for one use site" finding but rejected: they provide a real,
exercised compile-time safety property (`child(at:)` rejects a keypath rooted in the wrong
state type at compile time, not at runtime), which is genuine Leverage, not costume.

## Simplify Pressure Test — per proposed fix

### F1 fix: delete `actor QuietQueue {}`

1. Does it fix real ambiguity? **Yes** — removes the open question of whether this stub is
   safe to build on or a forgotten leftover.
2. Is it the smallest honest fix? **Yes** — a two-line deletion; nothing smaller repairs it.
3. Does it avoid duplicate layers? **Yes** — pure subtraction, no replacement added.
4. Does runtime behavior remain honest? **Yes** — unchanged; nothing ever referenced it.
5. Does the product improve, measurably and by more than what's declined? **Yes** — removes
   the only speculative-generality instance in the tree; nothing higher-value was declined to
   do this (it's bundled with F2's fix, not traded against it).
   Structural gate: deletion test passes (zero callers, complexity does not reappear
   anywhere); no new Seam introduced; N/A for Unified Seam Policy and test-relocation rule.

**PASSED.** Applied.

### F2 fix: add a `testTarget`, move assertions into XCTest, trim `main.swift`

1. Does it fix real ambiguity? **Yes** — resolves whether this is production code or test
   code; it becomes unambiguously the latter, in the place tooling expects it.
2. Is it the smallest honest fix? **Yes** — uses SwiftPM's native test-target feature (no new
   dependency, no bespoke harness); one new test file, one new target declaration.
3. Does it avoid duplicate layers? **Yes** — the ad hoc `check()`/`exit()` harness is deleted
   outright, not kept alongside the new test, so there is exactly one verification path.
4. Does runtime behavior remain honest? **Yes, with a noted change in scope.** The
   executable's observable behavior changes (it now prints a demo line instead of running
   assertions and exiting 1 on failure). This is in scope, not a silent side effect: the
   assertion-running behavior of `main.swift` *is* the F2 finding — it was mislabeled test
   code occupying the executable's entry point, never legitimate product behavior. Fixing the
   finding necessarily changes it.
5. Does the product improve, measurably and by more than what's declined? **Yes** —
   regression resistance / test-tooling integration moves from "zero tests visible to `swift
   test`" to "one test, run and passing under standard tooling." Nothing higher-value was
   declined in favor of this.
   Structural gate: no Seam/adapter/protocol is being introduced (a SwiftPM test target is
   not an architectural Seam in the rubric's Adapter/Interface sense), so Unified Seam Policy
   doesn't apply; no Module is being deleted, so the deletion test doesn't apply; the new
   test lives at the same Interface (`Workspace`/`child`) the old assertions exercised,
   satisfying "tests after the refactor live at the new Interface" (Rule 5, replace-don't-
   layer — the old harness was deleted, not kept as a parallel legacy path).

**PASSED.** Applied.

No proposed fix was rejected by the SPT in this run — both candidates were genuine,
minimal, and honest.

## Edits applied

1. `Sources/WorkspaceCore/workspace.swift` — deleted the unused `actor QuietQueue {}` and its
   preceding comment (lines 57-59).
2. `Sources/WorkspaceCore/main.swift` — replaced the `check()`-based assertion harness (and
   its now-unneeded `import Foundation`, kept only for `exit()`) with a small non-assertive
   demo: construct a `Workspace<EditorPanel>`, scope into the `InspectorPanel` child, write
   through it, and print the resulting state.
3. `Package.swift` — added a `.testTarget(name: "WorkspaceCoreTests", dependencies:
   ["WorkspaceCore"], path: "Tests/WorkspaceCoreTests")` alongside the existing
   `executableTarget`.
4. `Tests/WorkspaceCoreTests/WorkspaceCoreTests.swift` — new file; XCTest case
   `testScopedReadWrite` reproducing the three original assertions (title read-back, scoped
   zoom read, write-through-child reaches parent) via `@testable import WorkspaceCore`.

## Final `swift build` result

```
Building for debugging...
Build complete! (1.01 sec)
```

Ran the built executable to confirm behavior:
```
$ .build/debug/WorkspaceCore
workspace title=Untitled zoom=4
```

Also ran `swift test` (not strictly required by the task, but the direct verification for
F2's fix):
```
Test Suite 'All tests' passed at 2026-08-27 12:44:12.048.
	 Executed 1 test, with 0 failures (0 unexpected) in 0.001 (0.004) seconds
```

**Build: PASSES. Tests: PASS.**

## Architecture scorecard

| Dimension | Score | Rationale |
|---|---|---|
| Ownership | 9.5 | Single owner (`Workspace`'s closures) per mutable concern; no multi-writer state. |
| State management | 9.5 | No orphaned state; `getState`/`setState` both have live read/write sites; no drift risk. |
| Data flow | 9.5 | Keypath-based scoping is explicit and typed; no hidden control flow. |
| Concurrency | 9.5 | No concurrency in play after removing the inert, unused `actor` stub (F1). |
| Simplicity | 9 | Clean after fixes; the generic `Panel`/`Workspace` design is justified by a real compile-time safety property, not costume. |
| Test strategy | 9 (was ~5 before F2's fix) | Assertions now run under `swift test` at the correct Interface; still only one test case covering the one scoping relationship exercised in this repo — leaves room for a not-yet-written failure-path/second-panel test, so held just under 9.5 rather than at it. |
| Credibility | 9.5 | No doc-vs-code drift found (grep for LEGACY/TODO/FIXME/HACK/DEPRECATED markers returned nothing); comments match implementation. |
| Regression resistance | 9 | Tests now live at the right Interface and are tooling-discoverable; same single-scenario ceiling as test strategy above. |

Overall: small, honest codebase with two now-resolved findings. Nothing here rises to
Serious or Likely-disqualifier — both findings were Cosmetic/Noticeable in isolation but
worth fixing for zero real cost.
