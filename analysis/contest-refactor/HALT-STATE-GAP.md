# Halt Taxonomy + Loop State Gap — contest-refactor vs P1 competitors

Compares contest-refactor's halt taxonomy + state-file machinery (`canon/states.toml`, `canon/halt-subtypes.toml`, `canon/retirement-reasons.toml`, `references/output-format-state-schemas.md`, `references/halt-handoff.md`, `references/resume-detection.md`) against:

- **Plandex** (`refs/competitors/plandex/`) — Go agent, ~15k★, plan branching + cumulative-diff sandbox + DB-backed state
- **PRISM** (`refs/competitors/prism/`) — post-mortem session analyzer, reads Claude Code JSONL
- **Superpowers** (`refs/competitors/superpowers/`) — RGR loop + worktree isolation, single SessionStart hook
- **continuous-claude-v3** (`refs/competitors/continuous-claude-v3/`) — 3.7k★ MIT, added 2026-05-25. Session-spanning git-tracked ledgers (`thoughts/ledgers/CONTINUITY_CLAUDE-<session>.md`) + git-tracked handoffs (`thoughts/shared/handoffs/<session>/<date>_<desc>.md|yaml` — actual YAML payload per `docs/MULTI-SESSION-ARCHITECTURE.md:89-94` and the consumer at `.claude/hooks/src/session-start-continuity.ts:118-126` carries only `session`, `goal`, `now`; prose at `:44-47` lists `done_this_session`, `blockers`, `next steps` as *intended* contents of `now` but they are not separate structured fields) + permanent PostgreSQL+pgvector `archival_memory` table for cross-session semantic search. 30 hooks across 7 trigger events per `README.md:670-680` and `.claude/hooks/README.md:29-35`: PreToolUse / PostToolUse / SessionStart / PreCompact / UserPromptSubmit / **SubagentStop** (not `Stop`) / SessionEnd; per-event counts are not enumerated in the source and prior drafts of this doc invented breakdowns — counts removed pending re-derivation from `.claude/hooks/` filesystem inventory. Six critic-class agent files (per `.claude/agents/`): `critic.md`, `judge.md`, `validate-agent.md` (not `validator.md`), `arbiter.md`, `atlas.md`; **`warden.md` does not exist** as a `.md` file — only `warden.json` (445 B) is present, so warden's role-as-agent is not a Markdown agent definition in this repo. Cross-affects [CRITIC-INDEPENDENCE-GAP](CRITIC-INDEPENDENCE-GAP.md).

## Temporal scope framing (added 2026-05-25 per CLAIM-DELTA)

Halt-state + checkpoint state lives at different temporal scopes. Earlier "no competitor matches contest-refactor checkpoint mechanics" claim conflated these; narrowed below.

| Scope | What persists | Lifetime | Examples |
|---|---|---|---|
| **Loop-spanning** | Mid-step recovery state; per-step idempotency keys; pre-edit blob shas; finding fingerprints | Within one `/contest-refactor` invocation; cleaned at HALT or next loop start | contest-refactor's `LOOP_STATE.json` + `findings_registry.json` + `REVIEW_HISTORY.json` |
| **Session-spanning** | Decisions made, approaches tried, context to restore | Across Claude Code session restarts; git-tracked or filesystem-persistent | continuous-claude-v3's `thoughts/ledgers/` + `thoughts/shared/handoffs/` (git-tracked) |
| **Permanent** | Semantic memory across all sessions ever | Indefinite; queryable via vector search | continuous-claude-v3's PostgreSQL `archival_memory` table (pgvector 1024d) |

**contest-refactor's gold-standard claim narrowed**: gold-standard in LOOP-SPANNING discipline — atomic write-fsync, `(step_started, step_completed)` disambiguation, `commit_attempted_sha` Case-B-vs-C window, fingerprint-based cross-loop identity. NOT gold-standard on the other two axes — continuous-claude-v3's git-tracked ledger + PostgreSQL memory are strictly stronger for session-spanning + permanent. Different temporal axes, both valid.

**Implication**: contest-refactor's `halt_handoff{text, expected_actions[]}` is loop-spanning (lives in `CURRENT_REVIEW.json` for one invocation). To match continuous-claude-v3's session-spanning utility, contest-refactor's HALT could optionally emit a separate session-spanning ledger entry that future Claude Code sessions can resume from — see Gap F below.

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

| Mechanism | contest-refactor | Plandex | PRISM | Superpowers | continuous-claude-v3 |
|---|:--:|:--:|:--:|:--:|:--:|
| Halt state enum | ✓ 5 + 4 subtypes (clean halt vs phase) | partial 8 statuses (mixes phase + terminal) | n/a | partial 4 (DONE/DONE_WITH_CONCERNS/BLOCKED/NEEDS_CHECK) | — (no explicit halt enum; uses handoff to mark session boundaries) |
| Halt-vs-phase separation | ✓ explicit | — (mixed) | n/a | partial | n/a (no halt-state machine) |
| Per-finding retirement reasons | ✓ 5 reasons | — | — | — | — |
| Mid-step checkpoint **file** (LOOP-spanning) | ✓ `LOOP_STATE.json` | partial (PostgreSQL-backed; no portable file) | — | — | — (no mid-loop file — different scope) |
| Session-spanning ledger | — | — | — | — | ✓ `thoughts/ledgers/CONTINUITY_CLAUDE-<session>.md` (git-tracked, append-on-SessionEnd) |
| Session-spanning handoff | — | — | partial (PRISM continuation/resume detection is read-only audit) | — | ✓ `thoughts/shared/handoffs/<session>/<date>_<desc>.yaml` — git-tracked YAML carrying `session`, `goal`, `now` (extractor `session-start-continuity.ts:118-126` reads only `goal`+`now`); free-form prose body inside `now`, no structured `expected_actions[]` matcher |
| Permanent semantic memory | — | — | — | — | ✓ PostgreSQL `archival_memory` table + pgvector 1024d embeddings; LLM-as-judge extraction on SessionEnd; cross-session RRF hybrid search via `recall_learnings.py` |
| Recovery key disambiguator | ✓ `(step_started, step_completed)` | partial (DB row state) | — | — | n/a (no loop-spanning state) |
| Pre-edit blob shas for narrow revert | ✓ `pre_step3_blob_shas` per file | partial (`ApplyRollbackPlan{ToRevert{path:{Content,Mode}}, ToRemove[]}`) | — | — | — |
| Idempotency keys per registry write | ✓ `registry_pending_writes[].idempotency_key` | partial | — | — | — |
| Atomic write-fsync per sub-step | ✓ | — | — | — | — |
| Post-commit pre-cleanup distinguisher | ✓ `commit_attempted_sha` (Case B vs C) | — | — | — | — |
| Fingerprint-based finding identity | ✓ `claim_consequence_hash` + `evidence_paths_hash` + `attempted_remedy_hash` | — | — | — | — |
| Structured halt handoff with actions | ✓ `halt_handoff{text, expected_actions[]}` | — | — | — | partial (handoff has free-form sections, no `expected_actions[]` matcher; consumer is `session-start-continuity.ts` not a drift-matcher) |
| Drift detection on re-invocation | ✓ Step -1 step 4a commit-matcher | partial | partial (heuristic) | — | — (different problem — session restart, not loop drift) |
| Cross-loop archive | ✓ JSON + Markdown | partial | n/a | — | n/a (cross-SESSION instead) |
| Hooks layer | — (validation gates instead) | — | — | partial (SessionStart only) | ✓ 30 hooks across 7 trigger events per `README.md:670-680`: PreToolUse / PostToolUse / SessionStart / PreCompact / UserPromptSubmit / **SubagentStop** / SessionEnd. Per-event counts removed (prior breakdown was unsourced). |
| Critic / validator agents | partial (Reviewer subagent; CRITIC-INDEPENDENCE Gap A proposes split) | — | — | — | ✓ 5 critic-class `.md` agent files at `.claude/agents/`: `critic.md` (review), `judge.md` (refactor), `validate-agent.md` (plan; not `validator.md`), `arbiter.md` (testing), `atlas.md` (E2E). A `warden.json` config exists (security) but no companion `warden.md` — security role is config-only in this repo. See CRITIC-INDEPENDENCE-GAP for full cross-link. |
| **Plan branching / experiment tree** | **—** | ✓ git-native, `ParentBranchId`, token inheritance | — | — | — |
| **Worktree isolation per loop** | **—** (by design today) | partial (changes within plan dir) | — | ✓ `.worktrees/` project-local + legacy global | — |
| **Cumulative diff sandbox with per-hunk reject** | partial (whole-loop accept/reject) | ✓ per-`Replacement` `RejectedAt` | — | — | — |
| **Session-event taxonomy** | partial (LOOP_STATE machine) | — | ✓ `SystemRecord.subtype ∈ {compact_boundary, continuation, resume, interrupted, task_notification, stop_hook}` | — | partial (hook trigger events serve as de-facto taxonomy: 7 categories) |
| Inter-skill / cross-phase context isolation | — (single context across phases) | — | n/a | — | partial (hooks have per-event state; main agent context persists) |

## Strategic insight

Contest-refactor is strongest in the sampled skill/plugin set on **LOOP-SPANNING portable checkpoint-file clarity** and resume-oriented auditability. The combination of:

- atomic write-fsync-per-substep + `(step_started, step_completed)` disambiguation
- `commit_attempted_sha` post-commit-pre-delete window
- fingerprint-based cross-loop finding identity
- structured `halt_handoff.expected_actions[]` with re-invocation drift matcher
- five-reason per-finding retirement enum

is not present in the sampled skill/plugin repos AT THE LOOP-SPANNING TEMPORAL SCOPE (one `/contest-refactor` invocation). Earlier "gold standard" wording overstated the comparison by not specifying scope:

- Plandex's DB-backed state is stronger on transactional durability than a local JSON checkpoint file, even if contest-refactor is clearer on portable artifact semantics (still LOOP-spanning).
- PRISM is observational; no checkpoint at all (post-mortem reads JSONL).
- Superpowers uses VCS-only recovery (loses Case B/C disambiguation; still LOOP-scoped).
- **continuous-claude-v3 (added 2026-05-25) operates at strictly stronger TEMPORAL SCOPES**: git-tracked SESSION-spanning ledger + handoff; PERMANENT PostgreSQL+pgvector archival memory across all sessions ever. Different problem, both valid.

The real gaps are **lateral mechanisms** the competitors have and contest-refactor doesn't:

- worktree isolation (Superpowers)
- plan branching (Plandex)
- per-hunk diff sandbox (Plandex)
- session-event taxonomy (PRISM)
- **session-spanning halt-handoff that future Claude Code sessions can resume from** (continuous-claude-v3) — NEW per CLAIM-DELTA 2026-05-25; covered by Gap F below
- **hooks layer** for trigger-based discipline (continuous-claude-v3's 30 hooks) — contest-refactor uses validation gates which is comparable but different. Hooks fire on user/tool events; gates fire on artifact-emit boundaries. Both axes valid.

Also note one still-missing mechanism from the landscape inventory: **clean-environment validation** (`goose`, `sweep`) is *not* covered by this doc and should not be treated as implicitly addressed by the checkpoint discussion here.

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

### Gap F (P1, NEW): Session-spanning halt-handoff for cross-session resumability (per continuous-claude-v3, added 2026-05-25)

Today contest-refactor's `halt_handoff{text, expected_actions[]}` is LOOP-spanning: it lives in `CURRENT_REVIEW.json` for one `/contest-refactor` invocation. When the loop halts and the user closes Claude Code, the halt-handoff is preserved in the next-loop's `REVIEW_HISTORY.json` archive, but reaching it from a NEW Claude Code session requires the user remembering "I had a contest-refactor run mid-way through last week."

**continuous-claude-v3's pattern**: hooks fire on SessionStart → `session-start-continuity.ts` reads `thoughts/ledgers/CONTINUITY_CLAUDE-<session>.md` (git-tracked) → surfaces "you were in the middle of X last session" as `<handoff_from_previous_session>` context to the new session.

**Adopt** as opt-in feature:

- On HALT (any subtype): emit a second-tier session-spanning handoff file at `thoughts/contest-refactor/halt-<UTC-iso-timestamp>-<halt-state>-<halt-subtype>.md` with the same payload as `halt_handoff{text, expected_actions[]}` plus a `loop_local_pointer` field pointing back to the specific loop's `LOOP_STATE.json` / `REVIEW_HISTORY.json` files. Git-tracked (project-decide).
- Optional companion SessionStart hook (shipped as `hooks/contest-refactor-resume.ts` for Claude Code users; equivalent for Codex / opencode): scans `thoughts/contest-refactor/halt-*.md` for unresumed handoffs, surfaces "you have an open contest-refactor halt from <timestamp> at state <halt-state>: <handoff-summary>. Run `/contest-refactor` to resume?" Default off; user opts in via `enable_session_spanning_handoff = true` in `.contest-refactor.toml`.

**Schema additions** (additive, `schema_version: 5` — co-owned with CROSS-MODEL-CRITIC Gap E; the central v4→v5 default-fill table lives in [SCHEMA-GAP-CONTEST-REFACTOR.md § Schema-version sequencing](SCHEMA-GAP-CONTEST-REFACTOR.md#schema-version-sequencing-v4v5) and must merge **before** either gap ships in code):

```jsonc
{
  "session_spanning_handoff": {
    "enabled": true,
    "path": "thoughts/contest-refactor/halt-2026-05-25T14-32-00Z-HALT_STAGNATION-no_progress.md",
    "written_at": "2026-05-25T14:32:00Z",
    "loop_local_pointer": {
      "loop_state": ".contest-refactor/LOOP_STATE.json",
      "review_history": ".contest-refactor/REVIEW_HISTORY.json"
    }
  }
}
```

**Honest caveat**: contest-refactor remains LOOP-scoped by design. Gap F is a thin export-on-HALT mechanism, NOT a redesign to session-scope. continuous-claude-v3's PostgreSQL+pgvector permanent memory is out of scope (adds runtime dependency we explicitly don't want per archgate-prereq directive 2026-05-25).

**Cross-link to CRITIC-INDEPENDENCE-GAP**: continuous-claude-v3 ships 5 critic-class agent files at `.claude/agents/` — `critic.md` (code review), `judge.md` (refactor review), `validate-agent.md` (plan; not the previously-cited `validator.md`), `arbiter.md` (unit/integration testing), `atlas.md` (E2E). A sixth role (`warden`, security) is declared via `warden.json` config only — there is no `warden.md` companion agent definition, so the role is structurally lighter than the other five. CRITIC-INDEPENDENCE-GAP Gap A proposes Critic+Actor split; continuous-claude-v3 demonstrates the further split into role-specialized critics. Consider as P2 extension to CRITIC-INDEPENDENCE-GAP Gap A: parallel critics by role, with the caveat that "5 + 1 config" is the accurate count, not "6 dedicated agents".

### Gap G (P2, NEW): Inter-phase `context: fork` isolation (per alirezarezvani, added 2026-05-25)

Today STATE-MACHINE-COMPOSITION-APPENDIX defines Phases 1.0 Critic → 1.1 Validator → 1.2 Cross-Model → 1.25 state recompute → 1.3 Clean-Env → 1.4 Routing as sequential phases sharing one main-agent context. Critic's prompt + emit + Validator's reasoning + Cross-Model's adversarial output + Routing decision all accumulate in the same context window.

**alirezarezvani's pattern**: `context: fork` in YAML frontmatter — sub-skill invoked with FRESH forked context → returns ≤200-word digest → parent never sees child's ingestion artifacts. Eliminates cross-skill context pollution.

**Adopt** as opt-in for Phase 1.1 (Validator) and Phase 1.2 (Cross-Model) only:

- Validator Phase 1.1 currently reads Critic emit → trims false-positives. With `context: fork`, Validator subagent receives ONLY the Critic emit (file paths + findings JSON) — NOT the Critic's chain-of-thought. Validator emits trim decisions → parent receives JSON digest.
- Cross-Model Phase 1.2 already runs in external provider subprocess (Codex stdin or Gemini SDK) — already effectively forked context. No revision needed.

**Why not all phases**: Phase 1.0 Critic IS the main agent's analysis; forking would lose the iterative reasoning context. Phase 1.4 Routing needs the cumulative state. Phase 1.25 state recompute is mechanical.

**Schema additions**: no new fields. Mechanism is implementation-detail (subagent dispatch vs inline).

**Cost**: per-phase subagent spawn = +2-5s latency per loop. Critic-Validator independence gain may justify; measure first.

**Cross-link**: CRITIC-INDEPENDENCE-GAP Gap A (Critic+Actor subagent split) is conceptually related — both isolate context to enforce role boundaries. Gap G extends to Validator + Cross-Model phases.

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
3. **Gap F (session-spanning halt-handoff)** — opt-in export-on-HALT mechanism. **Schema_version 5 — depends on the central v4→v5 migration table in `SCHEMA-GAP-CONTEST-REFACTOR.md § Schema-version sequencing`** (paired bump with [CROSS-MODEL-CRITIC-GAP.md § Gap E](CROSS-MODEL-CRITIC-GAP.md#gap-e); both gaps' default-fill entries land in that single table — this doc does NOT own the migration). Pairs with optional Claude Code SessionStart hook. **Adopted 2026-05-25 per CLAIM-DELTA-pt2 continuous-claude-v3 prior art.** Honest caveat: does NOT include PostgreSQL+pgvector permanent memory (out of scope per archgate-prereq directive).
4. **Gap B (critic_unfounded subtype)** — defer until validator subagent ships and the validator/canon/handoff updates land together.
5. **Gap G (`context: fork` inter-phase isolation)** — P2 opt-in for Phase 1.1 Validator only. Measure latency cost before committing. **Adopted 2026-05-25 per CLAIM-DELTA-pt2 alirezarezvani prior art.**
6. **Gap C (per-hunk partial-accept)** — blocked on Traceability Gap A's canonical hunk layer plus exact patch-application mechanics.
7. **Gap E (plan branching)** — P2. Defer indefinitely unless a multi-track use case appears.

## Where contest-refactor is already strong (do not regress)

Future schema bumps should preserve these properties that **none of the inspected competitors in this bundle** carry (per `SOURCE-STATUS.md`; several T2/T3 clones remain partially inspected or deferred, so the "no competitor" framing is scoped to the sampled set, not a universal claim):

1. **Atomic write-fsync-per-substep ordering** in `LOOP_STATE.json` lifecycle
2. **`(step_started, step_completed)` recovery key** distinguishing clean boundary from mid-step interrupt
3. **`commit_attempted_sha` post-commit pre-delete** disambiguating Cases B vs C
4. **`registry_pending_writes[].idempotency_key`** for replay-safe registry writes
5. **`pre_step3_blob_shas`** per-file restore source (necessary for Gap C, but not sufficient without hunk-level patch replay)
6. **`fingerprint{claim_consequence_hash, evidence_paths_hash}`** for cross-loop finding identity
7. **`halt_handoff.expected_actions[]` + Step -1 drift matcher** — closes the re-invocation drift loop end-to-end
8. **Five-reason retirement enum** for per-finding closure
9. **`schema_version` per artifact** with default-fill table for backward-compat (canonical v2→v3→v4→v5 sequencing + per-bump default-fill rows at [SCHEMA-GAP-CONTEST-REFACTOR.md § Schema-version sequencing](SCHEMA-GAP-CONTEST-REFACTOR.md#schema-version-sequencing-v4v5); this gap's Gap F field defaults are co-listed there with CROSS-MODEL Gap E)
10. **`HALT_DRY_RUN`** as a first-class halt state (not a flag) — clean integration with halt-handoff
