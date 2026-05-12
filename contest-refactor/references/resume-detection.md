# Resume Detection

Loaded by SKILL.md Step -1 as the first action of every `/contest-refactor` invocation. Defines the full state machine for fresh-run vs resume-after-halt vs mid-Step-3-interrupt routing.

The branches in SKILL.md Step -1 are short pointers; the load-bearing logic lives here.

## Resume Precedence Matrix

Checked top-down, **first match wins**. Apply this matrix immediately after Step -1 step 1 (parse user flags); the matched row determines all subsequent Step -1 work.

| # | Precondition | Action |
|---|---|---|
| 1 | `--reset` flag set | Archive `CURRENT_REVIEW.md` to `REVIEW_HISTORY.md` with divider `--- HALT_<state> reset by user (UTC <ts>) ---`; delete `CURRENT_REVIEW.json`; **delete `LOOP_STATE.json` if present**; reset loop counter to 1; remove any `<!-- loop_cap: N -->` directive; **keep `findings_registry.json` and `REVIEW_HISTORY.json`**. Emit reset confirmation per [halt-handoff.md § Reset handoff](halt-handoff.md). Proceed to Step 0.5 (Provider detection). |
| 2 | `LOOP_STATE.json` present AND `last_checkpoint_at > 24h` ago | Orphan: emit `--reset` recommendation handoff (do not auto-resume). Tell user: "found mid-loop checkpoint older than 24h — likely orphaned. Re-invoke with `--reset` to discard, or commit/stash any in-flight work first." |
| 3 | `LOOP_STATE.json` present AND `loop` field disagrees with `CURRENT_REVIEW.json.loop` | Inconsistent state: emit `--reset` recommendation handoff. Tell user: "checkpoint says loop X but CURRENT_REVIEW says loop Y — inconsistent. Re-invoke with `--reset`." |
| 4 | `LOOP_STATE.json` present AND `CURRENT_REVIEW.json` absent | Bad state: emit `--reset` recommendation handoff. Tell user: "checkpoint present without review artifact — partial state. Re-invoke with `--reset`." |
| 5 | `LOOP_STATE.json` present AND `CURRENT_REVIEW.json.state == "CONTINUE"` | Mid-Step-3 interrupt: route to § Resume from LOOP_STATE.json below. |
| 6 | `LOOP_STATE.json` present AND `CURRENT_REVIEW.json.state ∈ HALT_*` | Leftover post-halt: commit completed before halt was emitted in some prior interrupted resume cycle. Delete `LOOP_STATE.json` (cleanup), then proceed to row 7. |
| 7 | `CURRENT_REVIEW.json.state ∈ HALT_*` | Drift handling per § Drift handling (steps 4, 4a, 4b). |
| 8 | `CURRENT_REVIEW.json` present AND `state == "CONTINUE"` AND no `LOOP_STATE.json` | Treat as interrupted between loops (clean state; commit landed but next loop never started). Dispatch loop N+1 immediately. |
| 9 | No prior artifacts | Fresh run; proceed to Step 0.5 (Provider detection) → 0.6 (Bootstrap) → Step 0 (Context Discovery). |

## Step 0.5 — Provider detection

Detect provider from environment variables per [provider-adapters.md § Detection](provider-adapters.md):

- `provider: "claude_code"` iff `CLAUDECODE=1`.
- `provider: "codex"` iff `CODEX_HOME` non-empty AND `CLAUDECODE` unset.
- `provider: "opencode"` iff `OPENCODE_SESSION` non-empty AND `CLAUDECODE` unset AND `CODEX_HOME` unset.
- 2+ provider env vars set → error, require `--provider <name>` flag.
- Otherwise → `provider: "unknown"`. Set `spawn_isolation: "inline"` (Loop Isolation skipped).
- User flag `--provider <name>` overrides detection unconditionally.

Resolve `loop_model` and `reviewer_model` from provider-adapters.md per-provider table, with override precedence: `--loop-model`/`--reviewer-model` user flag > `CONTEST_REFACTOR_LOOP_MODEL`/`CONTEST_REFACTOR_REVIEWER_MODEL` env > provider default. Record `*_source` ∈ {`default`, `env_override`, `user_flag`} for each.

These values get written to top-level CURRENT_REVIEW.json by every loop (G19 enforces presence).

## Step 0.6 — Registry + REVIEW_HISTORY.json bootstrap

If `REVIEW_HISTORY.md` exists but `findings_registry.json` does not → **bootstrap registry**: parse archived loops, fuzzy-match findings against themselves to infer recurrences, write `findings_registry.json` with `registry_schema_version: 3` (current; previous bootstraps wrote v2 — both legal per G29), stable IDs assigned, full occurrence chains. One-time per repo; cost ~5-10 minutes of subagent time.

If `REVIEW_HISTORY.md` exists but `REVIEW_HISTORY.json` does not → **bootstrap-json**: lossy reverse-parse archived loops to a best-effort `REVIEW_HISTORY.json` with per-loop entries marked `schema_version: 1`. Some fields may be null. One-time per repo.

Both bootstraps run in the main agent and are skipped on subsequent invocations.

## Drift handling (matrix row 7, prior state was a HALT_*)

If state ∈ {`HALT_SUCCESS`, `HALT_STAGNATION`, `HALT_LOOP_CAP`, `HALT_DRY_RUN`}:

- **Compute drift**: `git log --oneline <halt_commit_sha>..HEAD`. Halt commit sha is the most recent commit whose message starts with `loop N:`. If `HEAD == halt_commit_sha`, no drift; else codebase moved.
- **No drift** → emit the state's user-facing handoff per [halt-handoff.md](halt-handoff.md) with the menu options. Wait for user to pick an option (auto-resume only via `--reset` or `--cap`).
- **Drift detected** → continue to step 4a + 4b.

### Step 4a — Match completed handoff actions (main agent)

Read `halt_handoff.expected_actions[]` from prior `CURRENT_REVIEW.json`. For each action, scan commits in `git log <halt_sha>..HEAD` per `match_kind` (`all_of` / `any_of` / `no_drift_expected`). Record matches in `re_validation_context.prior_handoff_actions_taken[]`.

### Step 4b — Re-validate + compose why_halt_persists (main agent)

Run a fresh Step-1 critic pass (in main agent, not loop subagent) against current source. Branch on result:

- Fresh pass returns `[STATE: CONTINUE]` with non-empty backlog → emit "drift + new findings" handoff; resume loop dispatch starting at loop N+1.
- Fresh pass returns same `[STATE: HALT_STAGNATION]` subtype → record `re_validated_at_sha: <HEAD>` in `CURRENT_REVIEW.json`; compose `why_halt_persists` from the new critic's verdict_explanation, the matched expected_actions list, and any new findings vs prior loop. Inline into the drift handoff template.
- Fresh pass returns `[STATE: HALT_SUCCESS]` → emit success handoff.

If the prior halt was `HALT_DRY_RUN` (--dry-run set on prior invocation):
- The current invocation's flag is authoritative. If the user re-invoked WITHOUT `--dry-run`, the dry-run state is absent regardless of the artifact. Skip drift comparison; dispatch loop N+1 (or loop N execution if Step 2 plan still represents current state). No `--reset` required.
- If the user re-invoked WITH `--dry-run` again, treat as a re-plan: continue from CURRENT_REVIEW.json's Improvement Backlog into a fresh Step 1 → Step 2 cycle and emit a new HALT_DRY_RUN.

## Resume from LOOP_STATE.json (matrix row 5)

Read `LOOP_STATE.step_started`, `step_completed`, `commit_attempted_sha`. Branch:

### Case A — `step_completed == 11 AND LOOP_STATE.json still present`

Step 11.f (delete) was interrupted. Verify HEAD subject matches G22 pattern (`loop <N>: ...; finding F<n> (stable_id F-<NNN>) <status> [registry: ...]`):
- Match → delete `LOOP_STATE.json` and proceed to loop N+1 dispatch (Continuation Discipline).
- No match → anomaly: emit `--reset` recommendation handoff.

### Case B — `step_started == 11 AND commit_attempted_sha non-null AND step_completed < 11`

Commit landed; step 11.e (`step_completed` write) or 11.f (delete) was interrupted. Verify `HEAD == commit_attempted_sha`:
- Match → write `step_completed: 11` to `LOOP_STATE.json` (bookkeeping only) then delete `LOOP_STATE.json`; proceed to loop N+1.
- No match → anomaly: HEAD moved unexpectedly between the post-commit checkpoint and now. Emit `--reset` recommendation handoff.

### Case C — `step_started == 11 AND commit_attempted_sha null`

Commit was attempted but interrupted before HEAD updated (`git commit` did not return). Verify HEAD did NOT advance (still at prior loop's commit, i.e., one of: the prior loop's commit_sha, the bootstrap base, or any pre-loop sha):
- Clean → redo step 11.c (`git commit`) onward. Artifacts already on disk from earlier sub-steps are idempotent (commit just re-snapshots the staged files).
- HEAD moved unexpectedly → emit `--reset` recommendation handoff.

### Case D — `step_started > step_completed` (any k in 1..10)

Step `step_started` was interrupted mid-execution. Replay step `step_started` from the beginning. The idempotency rules in SKILL.md Step 3 sub-step 4 (Step 6 reviewer is stateless and the existing `implementation_review` is honored on resume; Step 9 archive uses divider marker dedup; Step 10 registry write uses `idempotency_key` per pending entry) guarantee no duplication.

### Case E — `step_started == step_completed` (any k in 0..10)

Clean boundary between sub-steps. Continue at sub-step k+1.

After successful resume completion of loop N (i.e., reaching the natural `LOOP_STATE.json` delete in step 11.f), the loop continues per Continuation Discipline (no synthetic halt; loop N+1 dispatches normally).

## Notes on behavior across resume

- `--reset` preserves `findings_registry.json` and `REVIEW_HISTORY.json` so cross-loop oscillation detection survives resets. Only `CURRENT_REVIEW.{md,json}` and `LOOP_STATE.json` are cleared.
- A user manually deleting `LOOP_STATE.json` between loops is equivalent to row 8 (clean state; loop N+1 dispatches). Safe.
- A user manually editing `LOOP_STATE.json` is undefined behavior — the matrix's `--reset` recommendation rows (2, 3, 4) should catch most tampered states.
- The Step 0.5 (Provider) and Step 0.6 (Bootstrap) sub-steps are idempotent; re-running them on resume is a no-op when the registry/history files are already current.
