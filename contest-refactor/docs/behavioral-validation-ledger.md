# Behavioral validation ledger

## 2026-08-25 — item 14 reviewer risk-boundary cue (no ship)

Fresh-context, host-dispatched review experiment: 20 `spawn_agent` calls on
`gpt-5.6-luna` at medium effort — five repetitions per arm per fixture. There
was no shell runner. For each call, the host supplied one fixture only, required
the reviewer to compare that fixture's `base/` and `head/` as the whole diff,
and prohibited inspection of the live repository diff.

- **Control protocol:** `git show HEAD:contest-refactor/references/implementation-reviewer.md`.
- **Treatment protocol:** the current worktree
  `contest-refactor/references/implementation-reviewer.md` at experiment time,
  including the proposed Honesty-check cue.
- **Risk fixture:** `contest-refactor/evals/reviewer-cases/missing-invariant-evidence-1/`.
- **Discovery lens:** `lens-apple.md`.

Every sample returned only this reviewer JSON contract:

```json
{
  "verdict": "approved" | "rejected" | "conditional",
  "reason": "<one sentence>",
  "checks": {"reality": "passed" | "failed" | "skipped", "honesty": "passed" | "failed" | "skipped", "regression": "passed" | "failed" | "skipped"},
  "regressions": ["<file:line finding>", "..."],
  "conditions": ["<file:line fix>", "..."]
}
```

The risk score records the verdict and whether the new Honesty cue routed the
result before Regression. The benign score treats any non-`approved` verdict
caused by its explicit `internal` marker as a false positive.

### Benign fixture (durable inline form)

Targeted finding `F1`: `ProgressMath.percent(completed:total:)` divides by zero
when `total` is zero (`Sources/ProgressMath.swift:3`), so the minimal fix returns
zero for `total <= 0` and adds the regression assertion. Its
`loop_result.risk_boundary_evidence` is null. The same diff makes default
top-level `internal` explicit; Swift's default top-level access is `internal`,
so this is semantically identical and demonstrably crosses no visibility
boundary.

```diff
--- base/Sources/ProgressMath.swift
+++ head/Sources/ProgressMath.swift
@@
-struct ProgressMath {
+internal struct ProgressMath {
     static func percent(completed: Int, total: Int) -> Int {
-        (completed * 100) / total
+        guard total > 0 else { return 0 }
+        return (completed * 100) / total
     }
 }
--- base/Tests/ProgressMathTests.swift
+++ head/Tests/ProgressMathTests.swift
@@
 @Test func percentOfCompletedWork() {
     #expect(ProgressMath.percent(completed: 1, total: 4) == 25)
 }
+
+@Test func emptyTotalReportsZero() {
+    #expect(ProgressMath.percent(completed: 0, total: 0) == 0)
+}
```

| Fixture | Definition | Control | Treatment |
|---|---|---|---|
| risk-bearing | `evals/reviewer-cases/missing-invariant-evidence-1`: removes class-level `@MainActor` with only reasoning evidence | 5/5 rejected at Regression; Honesty passed | 5/5 non-approved: 2/5 conditional through the new Honesty cue; 3/5 the same Regression rejection as control |
| benign visibility-adjacent | `public`/`internal`-only change that demonstrably crosses no boundary | 5/5 approved | 5/5 approved; zero false positives |

The control already detected the risk-bearing case in every repetition, so the
treatment added no correctness lift and only split routing in two of five runs.
Per the writing-skills micro-test rule, the Honesty cue is not shipped. The
existing Regression risk-boundary check remains the single source for this family;
this record does not add a mechanical gate.
