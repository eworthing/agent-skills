# Halt Taxonomy + Loop State Gap — contest-refactor vs P1 competitors

Compares contest-refactor's halt taxonomy + state-file machinery (`canon/states.toml`, `canon/halt-subtypes.toml`, `canon/retirement-reasons.toml`, `references/output-format-state-schemas.md`, `references/halt-handoff.md`, `references/resume-detection.md`) against:

- **Plandex** (`refs/competitors/plandex/`) — Go agent, ~15k★, plan branching + cumulative-diff sandbox + DB-backed state
- **PRISM** (`refs/competitors/prism/`) — post-mortem session analyzer, reads Claude Code JSONL
- **Superpowers** (`refs/competitors/superpowers/`) — RGR loop + worktree isolation, single SessionStart hook

## Baseline: contest-refactor today

**Halt taxonomy:**
- 5 states: `CONTINUE | HALT_SUCCESS | HALT_STAGNATION | HALT_LOOP_CAP | HALT_DRY_RUN`
- 4 subtypes (HALT_STAGNATION only): `no_progress | oscillation | user_decision | no_backlog`
- 5 per-finding retirement reasons: `unresolvable | user_decision | outside_scope | unverifiable | superseded`

**State files:**
- `LOOP_STATE.json` — mid-Step-3 checkpoint, `(step_started, step_completed)` recovery key, atomic write-fsync ordering per sub-step, `pre_step3_blob_shas` for narrow revert, `registry_pending_writes[].idempotency_key`, `commit_attempted_sha` for post-commit pre-delete disambiguation
- `findings_registry.json` — cross-loop stable_id + occurrences[] + `fingerprint{claim_consequence_hash, evidence_paths_hash}` + `attempted_remedy_hash`
- `REVIEW_HISTORY.json` + `.md` — per-loop archive

**Halt handoff:** `halt_handoff{text, expected_actions[]}` with `HandoffAction{action_id, description, match_keywords, match_paths, match_kind}`. Step -1 step 4a re-invocation drift matcher reads expected_actions and matches against commits in drift range.

**Loop isolation:** subagent-per-loop, same CWD, commits land on active branch (no worktree isolation by design).

## Gap matrix

Legend: **✓** = present, **partial** = weaker form, **—** = absent, **n/a** = doesn't apply.

| Mechanism | contest-refactor | Plandex | PRISM | Superpowers |
|---|:--:|:--:|:--:|:--:|
| Halt state enum | ✓ 5 + 4 subtypes (clean halt vs phase) | partial 8 statuses (mixes phase + terminal: draft/replying/describing/building/missingFile/finished/stopped/error) | n/a | partial 4 (DONE/DONE_WITH_CONCERNS/BLOCKED/NEEDS_CONTEXT) |
| Halt-vs-phase separation | ✓ explicit | — (mixed) | n/a | partial |
| Per-finding retirement reasons | ✓ 5 reasons | — | — | — |
| Mid-step checkpoint **file** | ✓ `LOOP_STATE.json` | partial (PostgreSQL-backed; no portable file) | — | — |
| Recovery key disambiguator | ✓ `(step_started, step_completed)` | partial (DB row state) | — | — |
| Pre-edit blob shas for narrow revert | ✓ `pre_step3_blob_shas` per file | partial (`ApplyRollbackPlan{ToRevert{path:{Content,Mode}}, ToRemove[]}`) | — | — |
| Idempotency keys per registry write | ✓ `registry_pending_writes[].idempotency_key` | partial (claims idempotent ops) | — | — |
| Atomic write-fsync per sub-step | ✓ | — | — | — |
| Post-commit pre-cleanup distinguisher | ✓ `commit_attempted_sha` (Case B vs C) | — | — | — |
| Fingerprint-based finding identity | ✓ `claim_consequence_hash` + `evidence_paths_hash` + `attempted_remedy_hash` | — | — | — |
| Structured halt handoff with actions | ✓ `halt_handoff{text, expected_actions[]}` | — (CLI prompts only) | — | — |
| Drift detection on re-invocation | ✓ Step -1 step 4a commit-matcher | partial (`ConflictedPaths()` at apply) | partial (heuristic "what is X" + continuation/resume subtype detection) | — |
| Cross-loop archive | ✓ JSON + Markdown | partial (ConvoMessageDescription history) | n/a | — |
| **Plan branching / experiment tree** | **—** | ✓ git-native, `ParentBranchId`, token inheritance | — | — |
| **Worktree isolation per loop** | **—** (by design today) | partial (changes within plan dir) | — | ✓ `.worktrees/` project-local + `~/.config/superpowers/worktrees/$project/` legacy global |
| **Cumulative diff sandbox with per-hunk reject** | partial (whole-loop accept/reject in Step 3 sub-step 6) | ✓ per-`Replacement` `RejectedAt` timestamp | — | — |
| **Session-event taxonomy** | partial (LOOP_STATE machine) | — | ✓ `SystemRecord.subtype ∈ {compact_boundary, continuation, resume, interrupted, task_notification, stop_hook}` | — |
| Hooks layer | — (validation gates instead) | — | — | partial (SessionStart only) |

## Strategic insight

Contest-refactor is strongest in the sampled skill/plugin set on **portable checkpoint-file clarity** and resume-oriented auditability. The combination of:

- atomic write-fsync-per-substep + `(step_started, step_completed)` disambiguation
- `commit_attempted_sha` post-commit-pre-delete window
- fingerprint-based cross-loop finding identity
- structured `halt_handoff.expected_actions[]` with re-invocation drift matcher
- five-reason per-finding retirement enum

is not present in the sampled skill/plugin repos. But the earlier "gold standard" wording overstated the comparison: Plandex's DB-backed state is stronger on transactional durability than a local JSON checkpoint file, even if contest-refactor is clearer on portable artifact semantics. PRISM is observational; Superpowers uses VCS-only recovery (which loses Case B/C disambiguation).

The real gaps are **lateral mechanisms** the competitors have and contest-refactor doesn't: worktree isolation, plan branching, per-hunk diff sandbox, session-event taxonomy. Also note one still-missing mechanism from the landscape inventory: **clean-environment validation** (`goose`, `sweep`) is *not* covered by this doc and should not be treated as implicitly addressed by the checkpoint discussion here.

## P1 GAPS — what to import

### Gap A: Worktree isolation as opt-in mode (Superpowers' pattern)

Contest-refactor commits to active branch by design — UX is "watch it work." But three real cases want isolation:

1. Multi-loop background run while keeping main branch clean
2. Abort + drop all loop commits without manual `git reset --hard`
3. Experimental "what if we tried refactor A vs B" runs

Superpowers' bootstrap is the cleanest:
- Detect already-in-worktree via `GIT_DIR != GIT_COMMON` (skip create if true)
- Prefer native tool (`EnterWorktree`); fall back to `git worktree add` to `.worktrees/` (project-local, gitignored)
- Run baseline tests in worktree before proceeding
- Cleanup is user-decided (merge / PR / keep / discard) — no auto-cleanup on failure

**Adopt as `--worktree` flag** (default off — preserves current UX). But do **not** overload `spawn_isolation`; that field already means `subagent | inline` agent-dispatch mode and is enforced by G19. If worktree mode ships, it needs its own field (for example `execution_workspace: active_branch | worktree`) or pure CLI/runtime state.

Updates:
- `references/trust-model.md § Loop Isolation` — describe worktree mode separately from `spawn_isolation`
- `references/halt-handoff.md` — new HALT_SUCCESS variant that prompts user to merge/PR/keep/discard
- `canon/states.toml` — no change (worktree is isolation mode, not a halt state)

### Gap B: New halt subtype — `critic_unfounded` (pairs with Schema Gap's validator subagent)

Schema Gap analysis recommended a per-finding validator subagent that can reject findings. Today contest-refactor's `no_backlog` subtype only covers "Critic produced no findings." Once a validator exists, a new case appears: **"Critic produced findings but validator rejected them all."**

**Adopt:** `critic_unfounded` subtype — single-source-of-truth canon entry lives in [STATE-MACHINE-COMPOSITION-APPENDIX § canon/halt-subtypes.toml consolidated enum](STATE-MACHINE-COMPOSITION-APPENDIX.md). Per Codex round 1 N3 single-ownership rule, this doc does NOT include a standalone `halt_subtypes = [...]` block.

Plus a new `halt_handoff.md` template for `HALT_STAGNATION/critic_unfounded` explaining which findings the validator rejected and why.

Defer until validator subagent ships (Schema Gap Gap C) **and** the canon / validator codepaths are updated together. This is not just a `canon/halt-subtypes.toml` edit.

### Gap C: Per-hunk partial-accept (Plandex's `RejectedAt` per Replacement)

Today Step 3 sub-step 6 (Implementation Review) is whole-loop accept/reject. Plandex allows per-`Replacement` rejection inside a `PlanFileResult` — the reviewer can keep the rename and drop the type-narrowing change in the same commit. This fits contest-refactor's "smallest behavior-preserving repair" principle better than all-or-nothing.

**Design constraint:** do **not** add `implementation_review.verdict: "partial_accept"` to the committed artifact. The checked schema only allows `approved | rejected | conditional`, and `conditional` is mid-loop only.

If partial accept is ever adopted, keep the final verdict enum unchanged and model hunk decisions as review metadata that drives a selective revert + re-review cycle.

**Sketch** (blocked on Traceability Gap A establishing canonical `hunk_id`):

```jsonc
// CURRENT_REVIEW.json.implementation_review
{
  "verdict": "rejected",         // final committed artifact still uses the existing enum
  "rejected_hunks": [
    {
      "path": "src/Foo.swift",
      "hunk_id": "h2",           // index into the loop's diff
      "rejection_reason": "Type-narrowing change adds Seam without Adapter (Two-adapter rule violation)"
    }
  ]
}
```

`LOOP_STATE.json.pre_step3_blob_shas` already provides the per-file restore source, but that is only half the mechanism. `git checkout <blob-sha> -- <path>` restores the **entire file**. True partial accept requires canonical hunk IDs plus exact patch generation / patch re-application after restore. That is why this gap is blocked on Traceability Gap A's shared hunk layer.

Bigger lift than Gap A; needs hunk-level diff machinery. Defer to a later schema bump unless reviewers are routinely struggling with all-or-nothing today.

### Gap D: Session-event taxonomy from PRISM's SystemRecord.subtype

PRISM classifies session events into `compact_boundary | continuation | resume | interrupted | task_notification | stop_hook`. Contest-refactor's Step -1 Resume Detection already handles most of these implicitly via the Resume Precedence Matrix (Cases A-E), but doesn't tag the resume **class** in the artifact.

**Adopt** as audit-only field in `CURRENT_REVIEW.json`:

```jsonc
{
  "session_resume_class": "drift_re_validation",
  // enum: fresh_start | continuation_same_session | resume_new_session
  //     | mid_step3_resume | drift_re_validation | reset_requested
}
```

Useful when debugging "why did loop 4 behave oddly after loop 3 halted?" — the resume class makes the cause one-line readable. Low-risk additive change.

### Gap E (defer to P2): Plan branching for experimental refactors (Plandex)

Plandex's git-native plan branching (parent tracking, token inheritance) enables "try refactor A on branch X and B on branch Y in parallel, scorecard them, merge winner." For contest-refactor: spawn parallel loop subagents on alternate branches, each picks a different priority-1 backlog item, compare scorecards on HALT, merge winner.

Big lift. Wants:
- Branching protocol in `references/trust-model.md` (or a future dedicated loop-isolation appendix)
- Multi-track `REVIEW_HISTORY.json` (branch keyed)
- Scorecard-compare logic + winner-selection rule
- Auto-merge or human-pick-then-merge

Defer to P2 unless a real use case appears.

## What NOT to import

| Tempting | Why skip |
|---|---|
| Plandex's 8-state mixed status enum | Mixes execution phase (replying/describing/building) with terminal states (finished/stopped/error). Contest-refactor's clean halt-vs-CONTINUE split is the right design — don't regress. |
| Plandex's PostgreSQL-backed state | Overkill for single-user single-host loops. LOOP_STATE.json + git is sufficient and portable. |
| Superpowers' VCS-only recovery model | No `(step_started, step_completed)` disambiguation means you cannot distinguish Case B (commit landed, cleanup interrupted) from Case C (commit interrupted before HEAD updated). Contest-refactor already solves this; don't undo it. |
| PRISM's full session-wide ledger | PRISM is observational across all sessions. Contest-refactor is loop-driven inside one invocation. Adopting full session intelligence would re-implement what `find_registry.json` + `REVIEW_HISTORY.json` already do for its narrower domain. |
| Superpowers' single SessionStart hook for skill bootstrap | Contest-refactor loads skill via `Reference Load Matrix`; hook-based bootstrap conflates protocol load with skill registration. |
| Plandex's `_apply.sh` exec-history replay | Replay-by-re-execution doesn't compose with contest-refactor's per-loop commit discipline. Contest-refactor's `LOOP_STATE.registry_pending_writes[].idempotency_key` is the correct equivalent. |

## Adoption order

1. **Gap D (session_resume_class field)** — one new audit field. No behavioral change. Trivial schema bump.
2. **Gap A (worktree opt-in mode)** — useful, but not self-contained: it needs a separate workspace-mode contract rather than a `spawn_isolation` enum change.
3. **Gap B (critic_unfounded subtype)** — defer until validator subagent ships and the validator/canon/handoff updates land together.
4. **Gap C (per-hunk partial-accept)** — blocked on Traceability Gap A's canonical hunk layer plus exact patch-application mechanics.
5. **Gap E (plan branching)** — P2. Defer indefinitely unless a multi-track use case appears.

## Where contest-refactor is already strong (do not regress)

Future schema bumps should preserve these properties that no competitor has:

1. **Atomic write-fsync-per-substep ordering** in `LOOP_STATE.json` lifecycle
2. **`(step_started, step_completed)` recovery key** distinguishing clean boundary from mid-step interrupt
3. **`commit_attempted_sha` post-commit pre-delete** disambiguating Cases B vs C
4. **`registry_pending_writes[].idempotency_key`** for replay-safe registry writes
5. **`pre_step3_blob_shas`** per-file restore source (necessary for Gap C, but not sufficient without hunk-level patch replay)
6. **`fingerprint{claim_consequence_hash, evidence_paths_hash}`** for cross-loop finding identity
7. **`halt_handoff.expected_actions[]` + Step -1 drift matcher** — closes the re-invocation drift loop end-to-end
8. **Five-reason retirement enum** for per-finding closure
9. **`schema_version` per artifact** with default-fill table for backward-compat
10. **`HALT_DRY_RUN`** as a first-class halt state (not a flag) — clean integration with halt-handoff
