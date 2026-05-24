# Output Format — Persistent state schemas

JSON schemas for the cross-loop persistent state files: `LOOP_STATE.json` (mid-Step-3 checkpoint), `findings_registry.json` (cross-loop finding identity), `REVIEW_HISTORY.json` (per-loop archive), plus the Fuzzy-match rules used by Method Step 1.5 + Step -1 bootstrap to map findings to registry entries.

The per-loop schemas (`CURRENT_REVIEW.json`, embedded objects, validation rules) live in [output-format-json.md](output-format-json.md); the markdown spec in [output-format-markdown.md](output-format-markdown.md); artifact index in [output-format.md](output-format.md).

## Contents

- [LOOP_STATE.json schema (own track, schema_version: 1)](#loop_statejson-schema-own-track-schema_version-1)
- [findings_registry.json schema](#findings_registryjson-schema)
- [Fuzzy-match rules (Method Step 1.5 + bootstrap)](#fuzzy-match-rules-method-step-15--bootstrap)
- [REVIEW_HISTORY.json schema](#review_historyjson-schema)

## LOOP_STATE.json schema (own track, schema_version: 1)

Mid-Step-3 checkpoint artifact. Created at Step 3 sub-step 0; updated before/after every Step 3 sub-step (`step_started` written pre-work, `step_completed` written post-work, both fsynced); deleted at Step 3 sub-step 11.f after the loop's commit lands. Resume routing in [resume-detection.md § Resume from LOOP_STATE.json](resume-detection.md) keys off `(step_started, step_completed, commit_attempted_sha)`.

```jsonc
{
  "schema_version": 1,
  "loop": 3,                                    // int. Must equal CURRENT_REVIEW.json.loop. Mismatch routes to --reset (Resume Precedence Matrix row 3).
  "step_started": 7,                            // int 1..11. The Step 3 sub-step whose work has begun but not yet completed.
  "step_completed": 6,                          // int 0..11. The highest Step 3 sub-step whose work is fully on disk and idempotent-safe. step_started > step_completed = mid-step interrupt; replay required.
  "started_at": "2026-05-12T14:30:22Z",         // ISO-8601 UTC. When the loop's Step 3 began.
  "last_checkpoint_at": "2026-05-12T14:31:05Z", // ISO-8601 UTC. Updated on every checkpoint write. > 24h old at resume time = orphan (Resume Precedence Matrix row 2).
  "artifacts_written": [                        // array of paths (relative to repo root) modified or created since loop's Step 3 began. Used to verify expected on-disk state during resume.
    "CURRENT_REVIEW.md",
    "CURRENT_REVIEW.json",
    "BenchHypeKit/Sources/BenchHypeApplication/Reducer/AppReducer+Workflow.swift"
  ],
  "changed_paths": [                            // copy of loop_result.changed_paths once Step 3 step 4 has run (the diff is final at that point). Empty before step 4.
    "BenchHypeKit/Sources/BenchHypeApplication/Reducer/AppReducer+Workflow.swift"
  ],
  "pre_step3_blob_shas": {                      // populated at Step 3 sub-step 0 BEFORE any edit. Maps path → blob sha (or null if path was untracked at sub-step 0). Restore source for narrow revert: `git checkout <blob-sha> -- <path>` per file with a recorded sha; `git rm --cached <path>` for null entries (untracked-then-created files). Guarantees revert restores the pre-loop state of those files even when the user's working tree had unstaged edits in them at loop start (though the dirty-tree precondition in Step 0 should prevent that case).
    "BenchHypeKit/Sources/BenchHypeApplication/Reducer/AppReducer+Workflow.swift": "9b2a13c4...",
    "BenchHypeKit/Tests/AppReducerWorkflowTests.swift": null
  },
  "registry_pending_writes": [                  // array of mutations queued for findings_registry.json but not yet flushed. Each entry carries idempotency_key for replay-safe re-write at resume.
    {
      "stable_id": "F-007",
      "occurrence": {"loop": 3, "loop_local_id": "F3", "status": "resolved", "sha": "<pending>"},
      "idempotency_key": "loop3-F-007-resolved"
    }
  ],
  "commit_message_draft": null,                 // populated at Step 3 sub-step 11.a; null before. The draft commit subject line that will be passed to `git commit`.
  "implementation_review": null,                // verbatim copy of CURRENT_REVIEW.json.implementation_review once Step 3 step 6 completes; null before. Honored on resume (reviewer is stateless; re-spawning is wasteful when verdict already in hand).
  "commit_attempted_sha": null                  // populated at Step 3 sub-step 11.d AFTER `git commit` succeeds and BEFORE LOOP_STATE.json delete in 11.f. Distinguishes "commit landed but cleanup interrupted" (Case B in resume-detection.md) from "commit interrupted before HEAD updated" (Case C).
}
```

### Lifecycle

1. **Init** (Step 3 sub-step 0): write with `step_started: 1, step_completed: 0`, populated `pre_step3_blob_shas`, empty arrays, `null` for review/commit fields. fsync.
2. **Per-sub-step k in {1..11}**:
   - 2a. Write `step_started: k`. fsync.
   - 2b. Execute sub-step k's body.
   - 2c. Write `step_completed: k`. fsync. Also update `last_checkpoint_at`.
3. **Sub-step 11 commit detail**:
   - 11.a. Write `commit_message_draft: <subject>`. fsync.
   - 11.b. Write `step_started: 11`. fsync.
   - 11.c. `git commit`.
   - 11.d. On commit success, write `commit_attempted_sha: <new HEAD>`. fsync.
   - 11.e. Write `step_completed: 11`. fsync.
   - 11.f. Delete `LOOP_STATE.json` (atomic rename to `.json.deleting` then unlink).
4. **Resume entry**: see [resume-detection.md § Resume from LOOP_STATE.json](resume-detection.md) Cases A-E.

### Idempotency requirements (replay-safe)

The pair `(step_started, step_completed)` is the recovery key:
- `step_started == step_completed` → clean boundary; resume continues at sub-step k+1.
- `step_started > step_completed` → step `step_started` was interrupted mid-execution; replay it.

Per-step idempotency:
- Step 6 (Implementation Review): reviewer is stateless. If `implementation_review` is non-null on resume, honor the existing verdict; do not re-spawn.
- Step 9 (archive): `REVIEW_HISTORY.md` append checks for existing `--- Loop N (UTC <ts>) ---` divider before appending. `REVIEW_HISTORY.json.loops[]` append uses `(loop, schema_version)` as dedup key.
- Step 10 (registry write): each `registry_pending_writes[]` entry's `idempotency_key` is checked against `findings_registry.json.entries[].occurrences[].idempotency_key`; replay skips entries already present.
- Step 11 (commit): `commit_attempted_sha` populated post-commit-pre-delete distinguishes Cases B and C in resume routing.

## findings_registry.json schema

External file at repo root. Created on first loop or via Step -1 step 0.6 bootstrap; persisted across loops; committed alongside CURRENT_REVIEW.{md,json} + REVIEW_HISTORY.{md,json}. Never embedded in CURRENT_REVIEW.json — referenced by `findings_registry_path`.

```jsonc
{
  "registry_schema_version": 3,        // int. Independent of CURRENT_REVIEW.json schema_version. v3 (this revision) accepts an optional `idempotency_key` per occurrence (used by Step 3 step 10 replay-safe writes, see § LOOP_STATE.json).
  "next_serial": 8,                    // int. Monotonically incremented as new stable_ids are assigned.
  "entries": [
    {
      "stable_id": "F-007",            // string, regex ^F-\d{3,}$
      "title": "Oversized workflow file (>800 LOC)",
      "category_hint": "file-length",  // string, free-form taxonomy hint
      "primary_file": "BenchHypeKit/Sources/BenchHypeApplication/Reducer/AppReducer+Workflow.swift",
      "primary_evidence_lines": [1, 661],  // [start, end]
      "test_failed": "Shallow module",     // enum, same as findings[].test_failed
      "severity": "Cosmetic for contest",  // enum, same as findings[].severity
      "first_seen_loop": 1,
      "first_seen_sha": "<sha>",
      "last_seen_loop": 7,
      "occurrences": [
        {"loop": 1, "loop_local_id": "F3", "status": "open", "sha": "<observation_sha>"},
        {"loop": 3, "loop_local_id": "F3", "status": "fixed_by_user", "sha": "c066b0b"},
        {"loop": 5, "loop_local_id": "F2", "status": "rejected_attempt", "sha": "<resolution_sha>", "reviewer_reason": "<one sentence>", "idempotency_key": "loop5-F-007-rejected_attempt"}
      ]
    }
  ]
}
```

Occurrence `status` enum: `open` (still in backlog) | `resolved` (loop's reviewer approved a fix) | `fixed_by_user` (user resolved between loops) | `rejected_attempt` (reviewer rejected the loop's attempted fix; do not drop, the audit chain needs it).

Occurrence `sha` semantics:
- `status == "resolved"` → resolution commit sha (the loop's commit that landed the fix; matches `Step 3 step 11` commit_sha for that loop).
- `status == "fixed_by_user"` → the user's commit sha that resolved the finding between loops (typically detected via Step -1 step 4a drift matching).
- `status == "rejected_attempt"` → the loop's commit sha (committing review artifacts only, no code change; the attempted-fix code was reverted in Step 3 step 6).
- `status == "open"` → the head sha at observation time (i.e., the parent of the loop's commit; equivalent to `git rev-parse HEAD~1` from the loop's commit perspective). For loop 1 with no prior commit, this is the sha of the most recent commit before `/contest-refactor` was invoked.

`first_seen_sha` always uses the observation-time sha (per the `open` rule), so it answers "what was the codebase state when this finding was first noticed."

## Fuzzy-match rules (Method Step 1.5 + bootstrap)

A candidate finding matches a registry entry iff `entry.last_seen_loop >= N - 3` AND **either**:

- **(M1) Title proximity**: case-insensitive cosine similarity of word-bag(title) >= 0.6.
- **(M2) Strong tuple**: same `primary_file` AND same `test_failed` AND same `severity` AND `|candidate.primary_evidence_lines.start - entry.primary_evidence_lines.start| <= 50`.

If 2+ entries match the candidate via M2 and 0 via M1 → emit `open_question_for_user` in loop return JSON; halt at HALT_STAGNATION subtype `user_decision`. Do not silently pick one.

## REVIEW_HISTORY.json schema

Mirrors REVIEW_HISTORY.md as a structured archive. Each loop's complete CURRENT_REVIEW.json is appended to the top-level `loops[]` array on Step 3 step 8.

```jsonc
{
  "schema_version": 3,
  "loops": [
    { /* full CURRENT_REVIEW.json snapshot for loop 1, schema_version: 1 if pre-migration */ },
    { /* full CURRENT_REVIEW.json snapshot for loop 2, schema_version: 2 */ },
    { /* full CURRENT_REVIEW.json snapshot for loop 3, schema_version: 3 (mixed-version loops[] entries are legal — each carries its own schema_version) */ }
  ]
}
```

Compression rules for the markdown archive live in [output-format-markdown.md § Per-loop archive format](output-format-markdown.md#per-loop-archive-format-pr-5-schema_version--2); they apply only to REVIEW_HISTORY.md. REVIEW_HISTORY.json keeps full per-loop fidelity for downstream tooling.

If REVIEW_HISTORY.md exists at first invocation but REVIEW_HISTORY.json does not, Step -1 step 0.6 reverse-parses to a best-effort .json with each entry marked `schema_version: 1`. Lossy; some fields may be null.
