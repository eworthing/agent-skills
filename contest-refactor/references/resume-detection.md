# Resume Detection

Loaded by SKILL.md Step -1 as the first action of every `/contest-refactor` invocation. Defines the full state machine for fresh-run vs resume-after-halt vs mid-Step-3-interrupt routing.

The branches in SKILL.md Step -1 are short pointers; the load-bearing logic lives here.

## Contents

- [Resume Precedence Matrix](#resume-precedence-matrix)
- [Skill-script path resolution](#skill-script-path-resolution)
- [Step 0.5 — Provider detection](#step-05--provider-detection)
- [Step 0.6 — Registry + REVIEW_HISTORY.json bootstrap](#step-06--registry--review_historyjson-bootstrap)
- [Drift handling (matrix row 9, prior state was a HALT_*)](#drift-handling-matrix-row-9-prior-state-was-a-halt_)
- [Resume the out-of-plan cleanup transaction (matrix row 6c)](#resume-the-out-of-plan-cleanup-transaction-matrix-row-6c)
- [Out-of-plan disposition observation (row 3)](#out-of-plan-disposition-observation-row-3)
- [Resume from LOOP_STATE.json (matrix row 7)](#resume-from-loop_statejson-matrix-row-7)
- [Notes on behavior across resume](#notes-on-behavior-across-resume)

## Resume Precedence Matrix

Checked top-down, **first match wins**. Apply this matrix immediately after Step -1 step 1 (parse user flags); the matched row determines all subsequent Step -1 work.

| # | Precondition | Action |
|---|---|---|
| 1 | `--purge` flag set AND `--confirm` NOT set | Emit Purge Preview handoff per [halt-handoff.md § Purge Preview handoff](halt-handoff.md#purge-preview-handoff). Compute proposed backup path: `.contest-refactor-backup-$(date -u +%Y%m%d-%H%M%S)/`. Enumerate which persistent files are currently present in CWD (the script's exact target set). Do **NOT** modify any files. Exit. |
| 2 | `--purge` flag set AND `--confirm` set | Resolve `$SKILL_DIR` per [§ Skill-script path resolution](#skill-script-path-resolution). Compute `BACKUP_DIR=.contest-refactor-backup-$(date -u +%Y%m%d-%H%M%S)`. Invoke `bash "$SKILL_DIR/scripts/purge.sh" --confirm --backup-dir "$BACKUP_DIR"` from target repo CWD. Script handles: mkdir backup, per-file atomic `mv`, PURGE_LOG.jsonl append, exit-code semantics. Then route on exit code: **0** → emit [Purge Complete handoff](halt-handoff.md#purge-complete-handoff) + reset loop counter to 1 + proceed to Step 0.5. **1** → emit [Purge Total-Failure handoff](halt-handoff.md#purge-total-failure-handoff) (state untouched). **2** → emit [Purge Precondition-Error handoff](halt-handoff.md#purge-precondition-error-handoff). **3** → emit [Purge Partial-Failure handoff](halt-handoff.md#purge-partial-failure-handoff) (state inconsistent; do NOT proceed to Step 0.5; user must run `scripts/purge.sh --recover` after manual reconciliation). If `--reset` is ALSO set, emit a one-line warning that `--reset` is redundant; proceed as `--purge --confirm`. |
| 3 | `--reset` flag set | **If the prior `CURRENT_REVIEW.json.halt_subtype == "user_decision"` and its `halt_handoff.expected_actions[]` names out-of-plan paths, first observe the operator's disposition — see [§ Out-of-plan disposition observation](#out-of-plan-disposition-observation-row-3) — before the rest of this row runs.** Archive `CURRENT_REVIEW.md` to `REVIEW_HISTORY.md` with divider `--- HALT_<state> reset by user (UTC <ts>) ---`; delete `CURRENT_REVIEW.json`; **delete `LOOP_STATE.json` if present**; reset loop counter to 1; remove any `<!-- loop_cap: N -->` directive; **keep `findings_registry.json` and `REVIEW_HISTORY.json`**. Emit reset confirmation per [halt-handoff.md § Reset handoff](halt-handoff.md), including the observed disposition when one was computed. Proceed to Step 0.5 (Provider detection); re-entry always starts from the clean-tree preflight ([startup.md § Step 0](startup.md#step-0--context-discovery-first-loop-only-runs-in-main-agent) sub-step 4b) and a fresh Critic plan — the interrupted Step-3 sub-step is never resumed here; mid-sub-step resume is deliberately not one of the dispositions. For a destructive deep-reset that also wipes `findings_registry.json` + `REVIEW_HISTORY.{md,json}`, use `--purge` (rows 1-2 above). |
| 4 | `LOOP_STATE.json` present AND `last_checkpoint_at > 24h` ago | Orphan: emit `--reset` recommendation handoff (do not auto-resume). Tell user: "found mid-loop checkpoint older than 24h — likely orphaned. Re-invoke with `--reset` to discard, or commit/stash any in-flight work first." |
| 5 | `LOOP_STATE.json` present AND `loop` field disagrees with `CURRENT_REVIEW.json.loop` | Inconsistent state: emit `--reset` recommendation handoff. Tell user: "checkpoint says loop X but CURRENT_REVIEW says loop Y — inconsistent. Re-invoke with `--reset`." |
| 6 | `LOOP_STATE.json` present AND `CURRENT_REVIEW.json` absent | Bad state: emit `--reset` recommendation handoff. Tell user: "checkpoint present without review artifact — partial state. Re-invoke with `--reset`." |
| 6b | `LOOP_STATE.json` present AND `LOOP_STATE.json.phase == "halt_success_panel"` | This is a **mid-panel checkpoint written by main**, not a Step-3 loop checkpoint — rows 7 / 7b / 8 must not touch it: 7 would treat it as a mid-Step-3 interrupt, 7b would re-spawn the whole panel discarding paid-for verdicts, and 8 would delete it as post-halt leftover. Route via the resume router (`scripts/_panel_capability.py resume --checkpoint LOOP_STATE.json --source-rev <sha> --candidate-fingerprint <fp>`, per the shared contract in [provider-adapters.md § panel_certification capability manifest](provider-adapters.md#panel_certification-capability-manifest-v5-panel-authorization)): fails closed on a stale, unsupported, or unreadable `protocol_digest` (launch nothing; fresh v4 Critic candidate); routes drift (`source_rev` / `candidate_fingerprint` changed) to the fresh-Critic path — a stale candidate is never panelled; otherwise resumes only the unresolved staged work, reusing durable held member records from `panel_state`. Must resume correctly whether `CURRENT_REVIEW.json.state` still reads `HALT_SUCCESS_candidate`, has reached `CONTINUE`, or has reached a terminal `HALT_*`. |
| 6c | `LOOP_STATE.json` present AND `LOOP_STATE.json.phase == "out_of_plan_cleanup"` | This is a **mid-cleanup checkpoint written by the loop subagent** (not main, unlike 6b's panel phase) at Step 3 sub-step 6, replacing the normal step_started/step_completed schema — row 7 must never see it (row 7's `CURRENT_REVIEW.json.state == "CONTINUE"` precondition is still true here: `CURRENT_REVIEW.json` is not rewritten to `HALT_STAGNATION` until the checkpoint's `cleanup_subphase` reaches `"committing"`, so without this row row 7 would misroute it as an ordinary mid-Step-3 interrupt and Case D would replay a sub-step that no longer applies). Route to [§ Resume the out-of-plan cleanup transaction](#resume-the-out-of-plan-cleanup-transaction-matrix-row-6c): idempotently finish restoration and the halt commit. **Never** generic Step-3 sub-step replay. |
| 7 | `LOOP_STATE.json` present AND `CURRENT_REVIEW.json.state == "CONTINUE"` | Mid-Step-3 interrupt: route to § Resume from LOOP_STATE.json below. |
| 7b | `CURRENT_REVIEW.json.state == "HALT_SUCCESS_candidate"` (schema_version >= 4; committed candidate, challenge pending) | Main re-enters the **HALT_SUCCESS Challenge** ([halt-verifier.md](halt-verifier.md)) bound to the committed candidate (`run_id` / `source_rev` / `candidate_commit_sha`): re-spawn the challenger; **held** → promote to terminal `HALT_SUCCESS` + commit; **broke** → CONTINUE transition (finding as Priority 1) + dispatch loop N+1; **unavailable** → `HALT_STAGNATION` subtype `verification_blocked`. Do NOT re-run the loop — the candidate is already committed. At `schema_version >= 5` with a v5 panel authorized, re-entering the challenge means re-entering the **panel** — and if a panel checkpoint exists, row 6b already matched; this row's re-spawn applies only when no panel phase was ever created (the v4 path, or v5 before member-1 launch). |
| 8 | `LOOP_STATE.json` present AND `CURRENT_REVIEW.json.state ∈ terminal HALT_*` (HALT_SUCCESS / HALT_STAGNATION / HALT_LOOP_CAP / HALT_DRY_RUN / HALT_EXHAUSTION; not `HALT_SUCCESS_candidate`) | Leftover post-halt: commit completed before halt was emitted in some prior interrupted resume cycle. Delete `LOOP_STATE.json` (cleanup), then proceed to row 9. |
| 9 | `CURRENT_REVIEW.json.state ∈ terminal HALT_*` (not `HALT_SUCCESS_candidate`) | Drift handling per § Drift handling (steps 4, 4a, 4b). |
| 10 | `CURRENT_REVIEW.json` present AND `state == "CONTINUE"` AND no `LOOP_STATE.json` | Interrupted between loops. **First inspect the working tree (`git status --porcelain`) — do not assume it is clean.** Clean, or dirty only in artifact paths → dispatch loop N+1 immediately. **Dirty with source paths → a prior dispatch died after editing source and before writing any artifact; run [trust-model.md § Orphaned working-tree edits from a dead executor](trust-model.md#orphaned-working-tree-edits-from-a-dead-executor) before dispatching**, or the fresh executor silently inherits unverified edits and can commit them. |
| 11 | No prior artifacts | Fresh run; proceed to Step 0.5 (Provider detection) → 0.6 (Bootstrap) → Step 0 (Context Discovery). |

## Skill-script path resolution

The skill ships helper scripts under `scripts/` (`dry-run.sh`, `purge.sh`, `audit-*.sh`). When `/contest-refactor` runs, the agent's CWD is the **target repo** (e.g., `/Users/Shared/git/BenchHype/`), not the skill installation directory. Invoking these scripts requires the agent to resolve the absolute path of the directory containing the currently-loaded `SKILL.md` and export it as `$SKILL_DIR`. All `scripts/*` invocations then take the form `bash "$SKILL_DIR/scripts/<name>.sh"`.

**Resolution precedence (per host agent)** — see [provider-adapters.md § Skill-directory resolution](provider-adapters.md#skill-directory-resolution) for per-provider mechanics. In short, every host CLI provides a way to learn the absolute path of the loaded skill at session start; the agent should consult that mechanism first.

**Fallback search chain** — if `$SKILL_DIR` is unset after provider-specific resolution, search these installation paths in order (first existing wins):

1. `$HOME/.claude/skills/contest-refactor`
2. `$HOME/.codex/skills/contest-refactor`
3. `$HOME/.config/opencode/skills/contest-refactor`
4. `$HOME/.agents/skills/contest-refactor`
5. `$HOME/.gemini/antigravity-cli/skills/contest-refactor`

If none exist, also try `./contest-refactor/scripts/<name>.sh` relative to CWD (covers repo-local checkouts).

If all fail → emit Purge Precondition-Error handoff per [halt-handoff.md § Purge Precondition-Error handoff](halt-handoff.md#purge-precondition-error-handoff) (the same handoff covers any `scripts/*` invocation failure mode, not only purge): "cannot locate scripts/<name>.sh; set SKILL_DIR explicitly in your environment to the directory containing the contest-refactor SKILL.md, then re-invoke."

Set `$SKILL_DIR` once at first action of every invocation (per SKILL.md Step -1 entry directive); subsequent `scripts/*` invocations within the same loop reuse it.

## Step 0.5 — Provider detection

Detect provider from environment variables per [provider-adapters.md § Detection](provider-adapters.md):

- `provider: "claude_code"` iff `CLAUDECODE=1`.
- `provider: "codex"` iff `CODEX_HOME` non-empty AND `CLAUDECODE` unset.
- `provider: "opencode"` iff `OPENCODE_SESSION` non-empty AND `CLAUDECODE` unset AND `CODEX_HOME` unset.
- 2+ provider env vars set → error, require `--provider <name>` flag.
- Otherwise → `provider: "unknown"`. Set `spawn_isolation: "inline"` (Loop Isolation skipped).
- User flag `--provider <name>` overrides detection unconditionally.

Resolve `loop_model` and `reviewer_model` from provider-adapters.md per-provider table:

- If `--premium-dry-run-model <id>` is present, reject simultaneous `--loop-model`, set `loop_model=<id>`, set `loop_model_source: "user_flag"`, set invocation `dry_run=true`, and populate `premium_dry_run: {"model": "<id>", "model_source": "user_flag", "activated_dry_run": true}`.
- Else if `CONTEST_REFACTOR_PREMIUM_DRY_RUN_MODEL` is set, set `loop_model=<id>`, set `loop_model_source: "env_override"`, set invocation `dry_run=true`, and populate `premium_dry_run: {"model": "<id>", "model_source": "env_override", "activated_dry_run": true}`.
- Else resolve the normal loop model with precedence `--loop-model` user flag > `CONTEST_REFACTOR_LOOP_MODEL` env > provider default, and set `premium_dry_run: null`.
- Resolve `reviewer_model` independently with precedence `--reviewer-model` user flag > `CONTEST_REFACTOR_REVIEWER_MODEL` env > provider default.

Record `*_source` ∈ {`default`, `env_override`, `user_flag`} for each. `premium_loop_override` is `true` only when `--allow-premium-loop` is present and the invocation is not dry-run; if the flag appears with `--dry-run` or a dedicated premium dry-run control, warn and record `premium_loop_override: false`.

Before dispatching a loop subagent, apply the premium model budget guard using `canon/premium-models.toml`: if resolved `loop_model` is premium, invocation `dry_run` is false, and `--allow-premium-loop` is absent, stop before spawning. Print the safer commands:

- Dry-run premium planning: `/contest-refactor --premium-dry-run-model <model> --cap 1`
- Normal execution after reviewing the plan: `/contest-refactor` (or the same invocation with the default model controls)
- Explicit full premium override: `/contest-refactor --loop-model <model> --allow-premium-loop --cap 1`

These values get written to top-level CURRENT_REVIEW.json by every loop (G19 enforces provider/model presence; G38 enforces premium-model budget safety).

## Step 0.6 — Registry + REVIEW_HISTORY.json bootstrap

If `REVIEW_HISTORY.md` exists but `findings_registry.json` does not → **bootstrap registry**: parse archived loops, fuzzy-match findings against themselves to infer recurrences, write `findings_registry.json` with `registry_schema_version: 3` (current; previous bootstraps wrote v2 — both legal per G29), stable IDs assigned, full occurrence chains. One-time per repo; cost ~5-10 minutes of subagent time.

If `REVIEW_HISTORY.md` exists but `REVIEW_HISTORY.json` does not → **bootstrap-json**: lossy reverse-parse archived loops to a best-effort `REVIEW_HISTORY.json` with per-loop entries marked `schema_version: 1`. Some fields may be null. One-time per repo.

Both bootstraps run in the main agent and are skipped on subsequent invocations.

## Drift handling (matrix row 9, prior state was a HALT_*)

If state ∈ {`HALT_SUCCESS`, `HALT_STAGNATION`, `HALT_LOOP_CAP`, `HALT_DRY_RUN`, `HALT_EXHAUSTION`}:

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

## Resume the out-of-plan cleanup transaction (matrix row 6c)

Read `LOOP_STATE.cleanup_state` (schema: [output-format-state-schemas.md §
Out-of-plan cleanup phase](output-format-state-schemas.md#out-of-plan-cleanup-phase-out_of_plan_cleanup)).
Branch on `cleanup_subphase`:

- **`"restoring"`** — re-apply restoration for every `planned_paths` entry
  (non-null blob sha ⇒ `git restore --source=HEAD --staged --worktree`;
  `null` ⇒ `git rm --cached --ignore-unmatch` + delete the working-tree
  file). Idempotent: restoring an already-restored path is a no-op. Confirm
  every `unexpected_paths` entry is still present (do not re-verify content —
  a user may already be acting on the disposition mid-crash-window). Once
  confirmed, write `cleanup_subphase: "committing"`, fsync, fall through to
  the next branch.
- **`"committing"`** — check whether the halt commit already landed: compare
  `git log -1 --format=%s HEAD` against `cleanup_state.halt_commit_draft.subject`
  AND confirm `git status --porcelain` has no non-`??` line (untracked `??`
  lines for `unexpected_paths` are expected). Both true → already landed;
  write `cleanup_subphase: "done"`, fsync, delete `LOOP_STATE.json`, present
  the halt handoff. Either false → not landed: rewrite `CURRENT_REVIEW.md`/
  `.json` to the halt shape (idempotent — same content each time), archive to
  `REVIEW_HISTORY.{md,json}` (Step 3 sub-step 9's existing dedup: divider-marker
  for `.md`, `(loop, schema_version)` key for `.json`), flush
  `findings_registry.json` if pending (sub-step 10's `idempotency_key` dedup),
  then `git commit` with `halt_commit_draft.subject`. On success, re-run the
  subject/tree check to confirm, write `cleanup_subphase: "done"`, delete
  `LOOP_STATE.json`.
- **`"done"` with `LOOP_STATE.json` still present** — sub-step-11.f-equivalent
  delete was interrupted (mirrors Case A below). Verify the halt commit via
  the same subject/tree check: match → delete `LOOP_STATE.json`, present the
  handoff; no match → anomaly, emit `--reset` recommendation handoff.

After successful resume completion (`LOOP_STATE.json` deleted), the run is
**terminal** — `HALT_STAGNATION` per Continuation Discipline. No loop N+1
dispatch.

## Out-of-plan disposition observation (row 3)

By the time an operator re-invokes with `--reset`, `LOOP_STATE.json` is
typically already gone — the cleanup transaction above deletes it once the
halt commit lands — so the original `unexpected_paths` list is no longer
available there. It survives in the halt commit's own
`CURRENT_REVIEW.json.halt_handoff.expected_actions[]` instead: the
`delete-out-of-plan-paths` and `adopt-out-of-plan-paths` actions both carry
`match_paths[]` equal to the original `unexpected_paths` (one verb each, same
paths, `match_kind: "all_of"` per the shape rule — non-empty `match_paths`
requires it); `abort-halt` carries empty `match_paths` and
`match_kind: "no_drift_expected"`. None of these are ever matched via the
normal commit-scanning drift path (`--reset` is matched at row 3, strictly
before row 9's drift handling reaches Step 4a) — reading `match_paths` here
is a one-off, structural reuse of the schema, not the field's usual
consumption.

For each path in that `match_paths[]` list, observe current git/filesystem
state — never operator self-report:

- **`committed`** — the path resolves in `git ls-tree HEAD -- <path>` (the
  operator ran the adopt route: added and committed it as new baseline).
- **`removed_or_reverted`** — the path is absent from both the working tree
  and `HEAD`'s tree (the operator ran the delete route).
- **`unverified`** — anything else (still present untracked, present but
  uncommitted, or any state that doesn't cleanly match either of the above).

All observed paths agreeing → that single label is the disposition. Mixed
observations, or any `unverified`, → disposition `unverified` overall.
Include this label in the reset confirmation per [halt-handoff.md § Reset
handoff](halt-handoff.md). This observation is why these three actions
"never surface in `prior_handoff_actions_taken`" (which [§ Step 4a — Match
completed handoff actions](#step-4a--match-completed-handoff-actions-main-agent)
populates only when row 9's drift handling runs): row 3 matches strictly
before row 9 ever gets a chance to, so the disposition is recorded here,
once, at reset time, never accumulated through the ordinary commit-scanning
path.

## Resume from LOOP_STATE.json (matrix row 7)

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

Step `step_started` was interrupted mid-execution. Replay step `step_started` from the beginning. The Step 3 idempotency rules (Step 6 reviewer is stateless and the existing `implementation_review` is honored on resume; Step 9 archive uses divider marker dedup; Step 10 registry write uses `idempotency_key` per pending entry) guarantee no duplication.

### Case E — `step_started == step_completed` (any k in 0..10)

Clean boundary between sub-steps. Continue at sub-step k+1.

After successful resume completion of loop N (i.e., reaching the natural `LOOP_STATE.json` delete in step 11.f), the loop continues per Continuation Discipline (no synthetic halt; loop N+1 dispatches normally).

## Notes on behavior across resume

- `--reset` preserves `findings_registry.json` and `REVIEW_HISTORY.json` so cross-loop oscillation detection survives resets. Only `CURRENT_REVIEW.{md,json}` and `LOOP_STATE.json` are cleared.
- `--purge` (with `--confirm`) does what `--reset` does AND moves `findings_registry.json` + `REVIEW_HISTORY.{md,json}` into a timestamped backup directory. Next loop runs as if first-installed. Backup directory is user-owned; PURGE_LOG.jsonl is the append-only audit trail. No validator gate enforces backup-dir persistence (see [halt-handoff.md § Purge Preview handoff](halt-handoff.md#purge-preview-handoff)).
- A user manually deleting `LOOP_STATE.json` between loops is equivalent to row 10, and safe **when the working tree is clean** — which row 10 now checks rather than assumes. A deleted checkpoint over a tree still carrying a dead executor's source edits is the orphaned-draft case, not a clean interrupt.
- A user manually editing `LOOP_STATE.json` is undefined behavior — the matrix's `--reset` recommendation rows (4, 5, 6) should catch most tampered states.
- The Step 0.5 (Provider) and Step 0.6 (Bootstrap) sub-steps are idempotent; re-running them on resume is a no-op when the registry/history files are already current.
