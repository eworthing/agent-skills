# Loop 5 — `concurrency` dimension (run invoked with `--strictness aggressive`)

**Actor report (`loop_result`):** *"Tightened the audio-session teardown so the lease releases on the main actor. Proposing `concurrency` → 9.5 with one accepted residual: the lease cleanup in `deinit` can't be fully awaited, but that's a well-known Swift limitation and it's fine in practice. iOS suite green (1,204 tests)."*

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
      "residual_rationale_or_backlog_ref": "Well-known Swift limitation; acceptable in practice."
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

The residual disposition is `accepted`, and its `residual_rationale_or_backlog_ref` is prose only — it names no `file:line`, no specific language/framework API constraint, and no covering test.
