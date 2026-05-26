# Halt Handoff

When the loop terminates, the subagent emits two things to main:

1. **JSON** for routing (per `references/trust-model.md` Loop Isolation subagent return contract).
2. **User-facing handoff text** the main agent reads aloud to the user when reporting the halt.

The handoff is **plain language**. It explains *why* the loop stopped, *what* remains, and *what the user can do next*. Halts without handoff text leave the user staring at a flag with no path forward.

This file defines the handoff for each halt state and subtype.

## Contents

- [Schema (PR 4, schema_version >= 2)](#schema-pr-4-schema_version--2)
- [HALT_SUCCESS](#halt_success)
- [HALT_STAGNATION](#halt_stagnation)
- [HALT_DRY_RUN (schema_version >= 3)](#halt_dry_run-schema_version--3)
- [HALT_LOOP_CAP](#halt_loop_cap)
- [Re-validation handoff (on drift)](#re-validation-handoff-on-drift)
- [Reset handoff](#reset-handoff)

## Schema (PR 4, schema_version >= 2)

At schema_version >= 2, the handoff is emitted as a structured `halt_handoff` object (per [output-format-json.md § halt_handoff](output-format-json.md#halt_handoff-object-pr-4-schema_version--2)) with `text` (user-facing prose) and `expected_actions[]` (HandoffAction objects matching the menu options in the handoff text).

For each menu option in the handoff templates below, the loop subagent emits a corresponding HandoffAction with:
- `action_id`: kebab-case derived from the menu option's verb + object (e.g., menu "Split file X" → `action_id: "split-file-x"`)
- `description`: the menu option's user-facing text
- `match_keywords`: substrings that would appear in a commit subject if the user took this action (e.g., `["split", "X"]`)
- `match_paths`: file paths that would appear in the commit's changed files (when the menu option references specific paths)
- `match_kind`: `all_of` if `match_paths` non-empty (default); `any_of` if keyword-only fallback; `no_drift_expected` if the action is "accept halt; no commits expected"

Step -1 step 4a (next invocation, on drift) reads `expected_actions[]` from prior CURRENT_REVIEW.json and matches commits in the drift range against each action.

At schema_version 1, only the prose `halt_handoff_text` is emitted; no structured action matching.

## Retirement precedence

Per-finding retirement (Step 1.6 in [method.md](method.md)) fires **before** whole-loop stagnation. A loop may not emit `HALT_STAGNATION / oscillation` while any eligible Serious-or-worse finding is unretired. Sequence each loop:

1. Apply Step 1.6 retirement rules to each registry occurrence. Any finding mechanically eligible (Branch A 3-way hash equality, or Branch B 2-way hash equality + intervening `resolved`) gets `status: "unresolvable"` plus a `retirement` block.
2. After retirement transitions, check whether `HALT_STAGNATION / oscillation` still applies. The Step 1.6 retirement may have removed the oscillating finding from the Priority-1-eligible pool, so the loop may now continue with the next backlog item instead of halting.
3. If `HALT_STAGNATION / oscillation` is still warranted (every remaining Serious-or-worse finding cannot be made Priority 1), emit it with `halt_handoff.remaining_serious_findings_disposition[]` per G30.

A retired finding surfaces in user-visible loop output via the "Retired finding" template:

```
**Retired finding:** F-007 marked `unresolvable` after rejected attempts in loops 3 and 5. Continuing with 4 eligible backlog items.
```

Emit one such line per finding that transitioned to `unresolvable` in this loop. The per-loop archive header in `REVIEW_HISTORY.md` (PR 5 compression) also lists the loop's retirement transitions; see [output-format-markdown.md § Per-loop archive format](output-format-markdown.md#per-loop-archive-format-pr-5-schema_version--2).

---

## HALT_SUCCESS

Triggered when every scorecard category reaches 10, OR 9.5+ with `accepted` residual disposition (per `architecture-rubric.md` Score Anchors).

### Subagent records
- `system_flag: "HALT_SUCCESS"`
- `unresolved_reason: null`
- `halt_subtype: null`

### Handoff template

```
Loop N ended at HALT_SUCCESS — every scorecard category is at 10 or 9.5+ with an
accepted residual. The codebase meets the contest target.

Final scorecard: <list dimensions and scores from CURRENT_REVIEW.json>

Accepted residuals (won't be revisited unless you ask):
  - <category>: <residual_blocking_10> — <residual_rationale>
  ...

Next step options:
  (a) Tag the commit and move on.
  (b) Spot-check one accepted residual — say "verify <category>" and I'll re-read
      the cited source.
  (c) Reset and run again from current source — type "/contest-refactor --reset"
      (useful if the codebase has changed materially since this halt).
  (d) Deep-reset (purge) — type "/contest-refactor --purge" for a preview, then
      "/contest-refactor --purge --confirm" to execute. Wipes findings_registry
      + REVIEW_HISTORY on top of --reset's scope, making the next loop run as
      if first-installed. Backup created automatically; see Purge Preview
      handoff for full semantics.
```

---

## HALT_STAGNATION

Triggered when the loop cannot make further progress under the rubric. Four distinct subtypes — each means something different to the user.

### Subagent records
- `system_flag: "HALT_STAGNATION"`
- `halt_subtype: "no_progress" | "oscillation" | "user_decision" | "no_backlog"`
- `unresolved_reason: <subtype-specific explanation>`

### Subtype: `no_progress`

**Condition**: 3 consecutive loops with no scorecard category UP, AND remaining backlog items don't pass Simplify Pressure Test.

**What it means in plain language**: The loop hit a structural wall. The remaining issues exist but every proposed fix either fails the deletion test, fails Unified Seam Policy, or would add ceremony (costume layer / fake-clean reward). Continuing would over-engineer without raising scores.

#### Handoff template

```
Loop N ended at HALT_STAGNATION (subtype: no_progress).

What this means: I've made N loops and the scorecard hasn't moved up in the last
3. The remaining backlog items don't pass the Simplify Pressure Test — every
proposed fix either fails the deletion test, would add a costume layer, or only
polishes the surface without changing structure. Forcing more loops would
over-engineer without raising scores.

Current scorecard: <list dimensions and scores>

Remaining backlog (carried forward):
  - <Priority 1 finding ID + title> — <one-line why it stopped me>
  ...

Next step options:
  (a) Accept the halt — current source is contest-grade-enough. The remaining
      items are local polish, not winnable structural findings.
  (b) Resolve manually — fix the blocking finding outside the loop (e.g., make
      a product/ownership decision, change a contract), then re-invoke
      /contest-refactor. I'll re-validate and resume.
  (c) Scope down — re-invoke as "/contest-refactor --scope <dir>" to refactor
      only one module that may have winnable structural moves.
  (d) Reset and try a different angle — "/contest-refactor --reset" archives
      this halt and starts fresh from current source.
  (e) Deep-reset (purge) — "/contest-refactor --purge --confirm" if you want to
      additionally wipe findings_registry + REVIEW_HISTORY (no cross-loop
      oscillation memory). Useful when prior findings are no longer relevant
      and you want a truly first-time critic walk.
```

### Subtype: `oscillation`

**Condition**: Same finding reappears as Priority 1 twice after a "fix". Indicates the fix didn't actually resolve the smell — it relocated it or surface-polished it.

#### Handoff template

```
Loop N ended at HALT_STAGNATION (subtype: oscillation).

What this means: Finding F<id> ("<title>") came back as Priority 1 after a
prior loop claimed to fix it. The fix didn't resolve the smell — it relocated
or surface-polished it. Continuing would loop on the same fake fix.

The fix attempted: <loop M loop_result.what_changed>
Why it didn't stick: <subagent's analysis from current CURRENT_REVIEW.md>

Next step options:
  (a) Resolve manually — the finding needs human judgment about the right fix.
      Read CURRENT_REVIEW.md finding F<id>; decide on a structural change; then
      re-invoke /contest-refactor.
  (b) Demote the finding — if you accept the residual, edit CURRENT_REVIEW.md
      to mark F<id> as accepted residual (per Score Anchors), then re-invoke.
  (c) Reset — "/contest-refactor --reset".
  (d) Deep-reset (purge) — "/contest-refactor --purge --confirm" (additionally
      wipes findings_registry + REVIEW_HISTORY).
```

### Subtype: `user_decision`

**Condition**: Top Structural Finding requires product/ownership decision the loop cannot make (per Guardrails "Stop on ambiguity").

#### Handoff template

```
Loop N ended at HALT_STAGNATION (subtype: user_decision).

What this means: The blocking finding requires a decision I can't make
unilaterally. It's not a code question; it's a product/ownership question.

The question: <subagent's open_question_for_user>

Context (from CURRENT_REVIEW.md F<id>):
  - <one-paragraph summary>

Next step: answer the question, then re-invoke /contest-refactor with the answer
in your message. I'll resume the loop with your answer as the resolved decision.
```

### Subtype: `no_backlog`

**Condition**: `[STATE: CONTINUE]` with empty Improvement Backlog while not at 9.5+ after Residual Accounting Pass/G23. Every score below 9.5 names a source-backed blocker that keeps the dimension's 9-anchor unmet and cannot honestly become a backlog item or accepted residual. If a dimension's 9-anchor is met and the only leftovers are Cosmetic for contest, ADR-carved-out, framework-constrained, or SPT-failing candidates, this subtype is illegal for that dimension; those leftovers are accepted residuals and should normally produce `HALT_SUCCESS`.

#### Handoff template

```
Loop N ended at HALT_STAGNATION (subtype: no_backlog).

What this means: Scorecard is at <X>/10 average — not at 9.5+ — and the
remaining blockers keep one or more dimensions below the 9-anchor. I cannot
generate a backlog item that passes the evidence chain or Simplify Pressure
Test, and the blockers are not acceptable residuals.

Current scorecard: <list>

Residual accounting:
  - <category>: <blocker> — why it is not backlog-worthy and not accepted

Next step options:
  (a) Accept the halt — the rubric and the codebase don't agree on what's left
      to fix; trust the rubric's silence.
  (b) Inspect manually — read CURRENT_REVIEW.md and ask "why isn't <concern>
      flagged?" I'll re-check that specific area.
  (c) Switch lens — if the wrong lens was selected (e.g., Generic on a Swift
      codebase), re-invoke as "/contest-refactor --force-lens <name>".
  (d) Reset — "/contest-refactor --reset".
  (e) Deep-reset (purge) — "/contest-refactor --purge --confirm" if you want
      to drop findings_registry + REVIEW_HISTORY too.
```

---

## HALT_DRY_RUN (schema_version >= 3)

Triggered when `--dry-run` was set on the current invocation; the loop ran Step 0 + Step 1 + Step 2 (planning) and halted at the Step 2 dry-run gate before Step 3 execution. The flag is **invocation-scoped, not persisted** — re-invoking without `--dry-run` executes Step 3 normally.

### Subagent records

- `system_flag: "HALT_DRY_RUN"`
- `halt_subtype: null`
- `unresolved_reason: null`
- `dry_run: true` (audit-only field in CURRENT_REVIEW.json; not read by next invocation)

### What gets emitted at halt

- `## Loop N Plan (dry-run)` section appended to `CURRENT_REVIEW.md` containing the Step 2 execution plan (file change list, files-not-to-touch list, blast radius bound).
- `CURRENT_REVIEW.json` mirrors with `state: "HALT_DRY_RUN"` and `dry_run: true`.
- No `loop_result`. No `implementation_review`. No commit (the dry-run state itself does not commit; the user re-invokes to execute).

### Handoff template

```
Loop N ended at HALT_DRY_RUN — --dry-run was set on this invocation, so I ran
Step 0 (Discovery), Step 1 (Critic), and Step 2 (Architect plan) but stopped
before Step 3 (Execution). No code changes. No commit.

Targeted Priority-1 finding: F<id> — <title>

The plan I would execute (in CURRENT_REVIEW.md "Loop N Plan (dry-run)" section):
  Files to change: <comma-separated list>
  Files NOT to touch: <comma-separated list>
  Blast radius: bounded to the change list above
  Expected scorecard impact: <one line>

Next step options:
  (a) Execute the plan — re-invoke "/contest-refactor" (no flag). The --dry-run
      flag is invocation-scoped; absence of the flag means execute. No --reset
      needed.
  (b) Re-plan with a different target — edit the Improvement Backlog in
      CURRENT_REVIEW.md to promote a different finding to Priority 1, then
      re-invoke "/contest-refactor --dry-run" to see the new plan.
  (c) Abort — leave the dry-run state on disk; nothing was changed.
```

### Notes

- **No --reset required to execute**: the dry-run flag is held in invocation memory only. The artifact's `dry_run: true` field is audit-only — it records the last loop's invocation flag but does not gate the next invocation. Re-invoking without `--dry-run` proceeds to Step 3 immediately.
- **G9 backlog purity** still applies: the Step 2 plan must derive from the existing Improvement Backlog (Priority-1 finding); no new concerns introduced at the dry-run gate.
- **G21 / G23 untouched**: HALT_SUCCESS criteria and residual accounting are not relevant to HALT_DRY_RUN (no scoring claim is made beyond carry-forward). [validation.md G23 § HALT_DRY_RUN bypass](validation.md) makes this explicit.
- **Bootstrap sibling files required at HALT_DRY_RUN emit time** (`schema_version >= 2`): the validator's required-artifact check is state-agnostic, so `REVIEW_HISTORY.json`, `REVIEW_HISTORY.md`, and `findings_registry.json` must already exist on disk when HALT_DRY_RUN is emitted. Step -1 (Resume / Discovery) sub-step 0.6 covers this — empty/seed stubs are written before the first Critic emit. A loop that halts at HALT_DRY_RUN without those siblings will fail `validate-artifact.py --mode strict` on `[required-artifact]`, not on any HALT_DRY_RUN-specific rule.

---

## HALT_LOOP_CAP

Triggered when loop counter reaches cap (default 10; override via env var or directive).

### Subagent records
- `system_flag: "HALT_LOOP_CAP"`
- `halt_subtype: null`
- `unresolved_reason: "loop counter reached cap of <N>"`

### Handoff template

```
Loop N ended at HALT_LOOP_CAP — I made <N> loops, the configured maximum.

Progress so far: <delta from loop 1 scorecard to loop N scorecard, summarized>

Current Priority 1 (carried forward):
  - F<id>: <title> — <one-line why>

Next step options:
  (a) Bump cap and resume — "/contest-refactor --cap <N+5>" continues from here.
  (b) Accept current state — <N> loops landed substantial improvements; current
      source is the new baseline.
  (c) Reset — "/contest-refactor --reset".
```

---

## Re-validation handoff (on drift)

When Resume Detection finds the codebase has moved past the prior halt sha, the main agent runs a fresh Step-1 critic pass and emits one of three results.

### Drift + fresh pass returns CONTINUE with new backlog

```
Detected <K> commit(s) since the prior HALT (<halt_sha>..HEAD). I re-ran a fresh
critic pass against current source.

New Priority 1 finding: F<id> — <title>

The prior halt is no longer current; resuming the loop with the new finding.
```

### Drift + fresh pass returns same HALT_STAGNATION subtype

```
Detected <K> commit(s) since the prior HALT (<halt_sha>..HEAD). I re-ran a fresh
critic pass against current source.

Prior handoff actions detected as completed:
  - <action_id>: addressed by commit <sha> ("<commit subject>") — matched via <kind>
  - <action_id>: no commits in range; matches "no_drift_expected"
  (or "none of the prior expected_actions matched commits in the drift range" if 0 matched)

Result: same halt — HALT_STAGNATION (<subtype>). Recorded re_validated_at_sha
<HEAD> in CURRENT_REVIEW.json so we don't re-revalidate against this same state.

Why the halt persists: <why_halt_persists from main agent's re-validation pass>

<emit the subtype's standard handoff template>
```

The "Prior handoff actions detected" list comes from `re_validation_context.prior_handoff_actions_taken[]` (PR 4, schema_version >= 2), populated by Step -1 step 4a. The "Why the halt persists" sentence comes from `re_validation_context.why_halt_persists`, composed by the main agent in Step -1 step 4b after the fresh critic pass.

### Drift + fresh pass returns HALT_SUCCESS

```
Detected <K> commit(s) since the prior HALT (<halt_sha>..HEAD). I re-ran a fresh
critic pass against current source.

Result: HALT_SUCCESS — the changes since the halt brought every scorecard
category to 10 or 9.5+ with accepted residuals.

<emit HALT_SUCCESS standard handoff template>
```

---

## Reset handoff

When user invokes `/contest-refactor --reset` or selects a reset option from a halt menu, main agent performs the reset and emits this confirmation:

```
Reset complete. Archived prior CURRENT_REVIEW.md to REVIEW_HISTORY.md with
divider "--- HALT_<state> reset by user (UTC <timestamp>) ---". Cleared
CURRENT_REVIEW.json. <if LOOP_STATE.json was present: Deleted LOOP_STATE.json
(orphaned mid-Step-3 checkpoint discarded).> Loop counter reset to 1.
Removed any <!-- loop_cap: N --> directive.

Preserved across reset: findings_registry.json + REVIEW_HISTORY.json
(cross-loop oscillation detection survives the reset).

Starting fresh from current source. Running Step 0 Discovery now.
```

For a destructive deep-reset that ALSO wipes `findings_registry.json` + `REVIEW_HISTORY.{md,json}` (run-as-if-first-time-ever), see [Purge Preview handoff](#purge-preview-handoff) and the `--purge` flag.

## Purge Preview handoff

When user invokes `/contest-refactor --purge` (without `--confirm`), main agent emits this preview handoff. **No files are modified.** Purpose: let the user see exactly what would be deleted + the backup path before committing to the destructive action.

```
Purge preview (NO FILES CHANGED).

Re-invoke with /contest-refactor --purge --confirm to execute. The
following files would be moved from this working directory into a
timestamped backup directory and then removed from the working tree:

<list each present file from the target set>
  - CURRENT_REVIEW.json
  - CURRENT_REVIEW.md
  - REVIEW_HISTORY.json
  - REVIEW_HISTORY.md
  - findings_registry.json
  <if LOOP_STATE.json present: also LOOP_STATE.json>
  <if LOOP_STATE.json.deleting present: also LOOP_STATE.json.deleting>

Backup destination (computed at confirmation time):
  .contest-refactor-backup-<UTC-timestamp>/

Audit ledger:
  PURGE_LOG.jsonl  (one JSON Lines entry appended per purge)

Differences vs --reset:
  - --reset archives CURRENT_REVIEW.md to REVIEW_HISTORY.md and KEEPS
    findings_registry.json + REVIEW_HISTORY.json (cross-loop oscillation
    detection survives).
  - --purge MOVES findings_registry.json + REVIEW_HISTORY.{md,json} into
    the backup dir, making the next loop run as if the skill were
    first-installed.

Recovery: the backup directory contains every moved file byte-for-byte.
You may restore manually with `cp <backup>/* .` or delete the backup when
no longer needed.

<if CURRENT_REVIEW.json.state == "CONTINUE": warn user>
WARNING: current loop state is CONTINUE, not a HALT_*. Executing
--purge --confirm will discard the in-flight finding(s) targeted by
the active loop plus all prior findings_registry oscillation history.
This is usually NOT what you want mid-loop. Consider:
  - Letting the loop reach its next halt before purging
  - Using --reset (preserves findings_registry) if you only want a
    clean restart from current source
  - Proceeding with --purge --confirm only if you genuinely want
    "first-time" critic behavior with no in-flight context

Suggestion: add `.contest-refactor-backup-*` to .gitignore if not
already present, so backup directories don't pollute commits.
PURGE_LOG.jsonl is intentionally tracked in git as a team-visible
audit trail of when purges happened.
```

## Purge Complete handoff

When `scripts/purge.sh` exits 0 (success), main agent emits this confirmation and proceeds to Step 0.5 (Provider detection) as a fresh Loop 1.

```
Purge complete.

Backup: <path>
Files moved:
  <enumerate moved files>

Audit entry appended to PURGE_LOG.jsonl:
  <tail -1 of the file, pretty-printed>

Loop counter reset to 1. findings_registry.json + REVIEW_HISTORY.json
absent — Step 1.5 will bootstrap a fresh registry; Step 1.7 anchor-check
is Loop-1-exempt.

Suggestion: add `.contest-refactor-backup-*` to .gitignore if not
already present.

Starting fresh from current source. Running Step 0 Discovery now.
```

## Purge Partial-Failure handoff

When `scripts/purge.sh` exits 3 (partial failure: some files moved, some failed), main agent emits this handoff and **does NOT proceed to Step 0.5**. The user must complete reconciliation before the next loop runs.

```
Purge PARTIAL FAILURE — workspace in inconsistent state.

Backup: <path>
Successfully moved into backup:
  <enumerate MOVED list>

Failed to move (still in CWD):
  <enumerate FAILED list>

Error log (per-file OS error):
  <backup>/.purge-errors.log

Deterministic 5-step reconciliation (no manual JSON editing — the script
owns the audit log):

1. Inspect <backup>/.purge-errors.log to identify the OS error per
   failed file (permission denied, disk full, file busy, etc.).

2. Fix the underlying error:
   - chmod for permission errors
   - free disk space for disk-full
   - close processes for file-busy
   - etc.

3. Manually move each failed file into the backup dir:
     mv -v ./CURRENT_REVIEW.json "$BACKUP_DIR/"
     mv -v ./LOOP_STATE.json    "$BACKUP_DIR/"
     <one command per FAILED entry>

4. Run the helper script in recovery mode. It verifies no target files
   remain in CWD and appends a valid `purge_partial_recovery` JSONL
   entry to PURGE_LOG.jsonl:
     bash "$SKILL_DIR/scripts/purge.sh" --recover --backup-dir "<path>"
   Exit 0 → reconciled. Exit 1 → script names the offending file still
   in CWD; repeat steps 3-4 for that file.

5. Re-invoke /contest-refactor (no --purge needed; workspace is now
   equivalent to a successful purge).
```

## Purge Total-Failure handoff

When `scripts/purge.sh` exits 1 (total failure: mkdir backup-dir failed before any mv fired), main agent emits this handoff. **No files were moved; state is untouched.**

```
Purge TOTAL FAILURE — state untouched.

Could not create backup directory:
  <path>

Underlying error (from script stderr):
  <error message>

Common causes:
  - Insufficient permissions on the current working directory.
  - Disk full.
  - Read-only filesystem.
  - Path collision with an existing file (not directory) at the
    intended backup name.

Fix the root cause, then re-invoke:
  /contest-refactor --purge --confirm

Same flags, same intent — safe to retry.
```

## Purge Precondition-Error handoff

When `scripts/purge.sh` exits 2 (precondition error: bad args, backup-dir already exists, etc.), or when the agent itself cannot resolve `$SKILL_DIR`, main agent emits this handoff.

```
Purge PRECONDITION ERROR.

<one of:>

  - Backup directory already exists: <path>
    The path collided (theoretically impossible at second-resolution but
    can happen on rapid repeat invocations). Re-invoke with --confirm;
    the agent will compute a fresh timestamped path.

  - SKILL_DIR could not be resolved.
    Searched: ~/.claude/skills/contest-refactor, ~/.codex/skills/...,
    ~/.config/opencode/skills/..., ~/.agents/skills/..., and
    ~/.gemini/antigravity-cli/skills/contest-refactor — none found.
    Set SKILL_DIR explicitly in your environment to the directory
    containing the contest-refactor SKILL.md, then re-invoke.

  - scripts/purge.sh not found at $SKILL_DIR/scripts/purge.sh.
    The skill installation may be incomplete. Re-install or pull latest.

  - Unknown flag passed to scripts/purge.sh: <flag>
    This indicates an internal version mismatch between SKILL.md and
    scripts/purge.sh. Re-install or pull latest.

State untouched. Fix the precondition and re-invoke.
```
