# Example: CURRENT_REVIEW.md (loop 3, Apple stack)

```
### Discovery (first loop only — re-emitted for clarity)
- Source roots: BenchHypeKit/Sources/, BenchHype/
- Test command: cd BenchHypeKit && swift test
- Build command: ./build_install_launch.sh ios --skip-preflight
- ADRs found: ADR-0007 (ports & adapters), ADR-0011 (no-MVVM)
- Domain terms (CLAUDE.md): AppState, EditingState, InstanceID, TileCueResolver, CueTransport

### Verdict & State
Promising, but immature
System Flag: [STATE: CONTINUE]

### Scorecard (1-10)
- Architecture quality: 8.5 | UP | Adapter relocation in commit 137c171; SpotifyPort.swift now has 2 adapters (live + fake)
- State management and runtime ownership: 9.0 | SAME | AppState single-writer; reducer-only mutation upheld
- Domain modeling: 8.5 | UP | CueTransport.playbackTransport eliminates last duplicated switch (Cue.swift:88)
- Data flow and dependency design: 8.5 | SAME | DAG holds; no new cycles
- Framework/platform best practices: 9.0 | UP | phaseAnimator pulse landed (commit 13a94dc)
- Concurrency and runtime safety: 9.5 | UP | assumeIsolated bridges documented; no unbound Task remaining
- Code simplicity and clarity: 8.5 | DOWN | New IdleTimerPort closure seam added — deletion test passes (callers concentrate timer policy), but adds one indirection
- Test strategy and regression resistance: 8.0 | SAME | Reducer tests assert state, not call sequence; some legacy mock-style tests remain in BoardEditingTests
- Overall implementation credibility: 8.5 | UP | Build green, no compiler warnings, swift test 0 failures

### Top Structural Finding
- **What is wrong:** `BoardPlayerView+Helpers` re-implements sequence cursor with `%` operator, breaking `playOnce` exhaustion.
- **Architectural test failed:** Interface-as-test-surface — view bypasses `TileCueResolver.resolve(tile:in:)` and computes its own cursor, so reducer tests cannot exercise this path.
- **Dependency category:** in-process
- **Evidence:** BoardPlayerView+Helpers.swift:42-58, TileCueResolver.swift:14
- **Severity:** Serious deduction — gotcha called out in CLAUDE.md, regression risk on transport invariants
- **ADR conflicts:** none
- **Minimal Correction Path:** Replace inline `%` cursor with `state.resolvedCuesByTileID[tile.id]` lookup. Delete BoardPlayerView+Helpers cursor extension entirely.
- **Blast Radius:**
  - change: BoardPlayerView+Helpers.swift, BoardPlayerView.swift
  - avoid: TileCueResolver.swift, AppSnapshot+Project.swift, reducer

### Simplification Check
- Structurally necessary: removes second cursor-resolution path, satisfies interface-as-test-surface (resolver is the surface)
- New seam justified: n/a — collapsing a duplicate, not adding one
- Helpful simplification: BoardPlayerView+Helpers shrinks from ~120 lines to ~60
- Should NOT be done: do not extract a "BoardPlayerSequenceService" protocol — one adapter only, fails two-adapter rule
- Tests after fix: delete BoardPlayerHelpersTests.testCursorWraps (tests internal helper, past the interface). Add BoardsViewStateTests.testPlayOnceExhaustionAtSequenceEnd (tests the resolver-driven projection)

### Improvement Backlog
1. Inline cursor reimplementation in BoardPlayerView+Helpers (above).
2. Remove last unbound `Task { }` in OnboardingDraftCoordinator.swift:31 — store handle, cancel on transition.
3. Collapse `startupPhase + startupFailure` into `enum RootShellState` (Hard Rule #3 violation, surfaced loop 1, deferred).

### Loop Counter
Loop 3 of 10
```

CURRENT_REVIEW.json mirrors the structured fields per `references/output-format.md`.

---

## Inline-mode CONTINUE transition (worked example)

Inline mode (no Loop Isolation subagent) requires the agent to re-enter Step 1 immediately after committing loop N. The only legal close-out of an inline run is a HALT_* handoff or a `user_decision` open question. Hard gate G20 in [validation.md](../references/validation.md) enforces this; the patterns below show what compliance looks like.

### Right (continues silently to next loop)

```
[Loop 1: Critic → Architect → Execution → tests green → commit acbcd48]
[Agent re-reads CURRENT_REVIEW.json → state: "CONTINUE", loop: 1, loop_cap: 10, backlog: [F2, F3, F5]]
[G20 fires: continuation mandatory]
[Agent emits one-line progress: "loop 1: collapse repository-theater seam in OrderIntake — F1 resolved (commit acbcd48)"]
[Agent re-enters Step 1 for loop 2 — same turn, no user-facing close-out]
[Loop 2: ... → commit 7f3e1a2]
[Loop 3: ... → commit b21e8c4]
[Loop 4: Critic emits HALT_STAGNATION (no_progress); writes halt_handoff.text per template]
[Agent reads halt_handoff.text aloud verbatim — first user-facing close-out of the run]
```

### Wrong (the failure G20 prevents)

```
[Loop 1: Critic → Architect → Execution → tests green → commit acbcd48]
[Agent emits user-facing summary: "Loop 1 committed at acbcd48; tests pass; backlog has 3 items..."]
[Agent yields turn]   ← G20 violation: state was "CONTINUE", backlog non-empty, no HALT_* and no user_decision
```

The wrong pattern is tempting because the loop completed cleanly: green tests, clean diff, useful commit. The natural close-out point in normal English is right here. But the protocol's contract is that an inline run terminates only on a HALT_*. Without G20 enforcement, agents drift toward the natural prose stopping point and the user has to manually re-invoke `/contest-refactor` for every subsequent loop — defeating the autonomous-loop premise of the skill.

If the user actually wants a single-loop run, they pass `--cap 1`; this exits via `HALT_LOOP_CAP` after loop 1 with the proper handoff (which lists "bump cap and resume" as a menu option). Stopping early without any HALT_* never serves the user; it's always a protocol failure.
