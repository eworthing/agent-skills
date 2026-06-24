# Loop 5 — `concurrency` dimension (run invoked with `--strictness aggressive`)

**Actor report (`loop_result`):** *"Tightened the audio-session teardown so the lease releases on the main actor. Proposing `concurrency` → 9.5 with one accepted residual: `deinit` cannot `await`, so teardown hops to the main actor unbound — a Swift language constraint, microsecond-bounded and idempotent, covered by a focused test. iOS suite green (1,204 tests)."*

This run was invoked with `--strictness aggressive`, recorded in the artifact below.

## CURRENT_REVIEW.json (excerpt)

```json
{
  "strictness": "aggressive",
  "loop": 5,
  "scorecard": {
    "concurrency": {
      "score": 9.5,
      "delta": "UP",
      "residual_blocking_10": "AudioSessionConfigurator.Lease.deinit cannot await teardown",
      "residual_disposition": "accepted",
      "residual_rationale_or_backlog_ref": "Swift language constraint: `deinit` cannot `await` (AudioSessionConfigurator.swift:88). Teardown is an idempotent main-actor hop, microsecond-bounded; covered by AudioSessionConfiguratorLeaseDeinitTests.testDeinitReleasesSession."
    }
  }
}
```

## Diff

```diff
--- a/Sources/Soundboard/AudioSessionConfigurator.swift
+++ b/Sources/Soundboard/AudioSessionConfigurator.swift
@@
     deinit {
-        session.deactivate()
+        Task { @MainActor in session.deactivate() }
     }
```

The residual disposition is `accepted`, and its `residual_rationale_or_backlog_ref` cites a named language constraint, a concrete `file:line`, and a covering test. It carries no `residual_expires` date.
