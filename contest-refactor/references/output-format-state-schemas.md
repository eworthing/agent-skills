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
  "loop": 3,                                    // int. Must equal CURRENT_REVIEW.json.loop. Mismatch routes to --reset (Resume Precedence Matrix row 5).
  "step_started": 7,                            // int 1..11. Sub-step whose work has begun.
  "step_completed": 6,                          // int 0..11. Highest sub-step fully on disk. See § Idempotency for replay semantics.
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
  "pre_step3_blob_shas": {                      // populated at Step 3 sub-step 0 (pre-edit). path → blob sha; null = untracked. Narrow-revert source: `git checkout <sha> -- <path>` per recorded sha, `git rm --cached <path>` per null.
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
  "commit_message_draft": null,                 // populated at 11.a; subject line for `git commit`.
  "implementation_review": null,                // verbatim copy of CURRENT_REVIEW.json.implementation_review after step 6. Honored on resume (reviewer stateless; do not re-spawn).
  "commit_attempted_sha": null                  // populated at 11.d post-commit, pre-11.f-delete. Disambiguates Case B vs Case C in resume-detection.md.
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
        {
          "loop": 1,
          "loop_local_id": "F3",
          "status": "open",
          "sha": "<observation_sha>",
          "fingerprint": {
            "claim_consequence_hash": "sha256:abcd...",
            "evidence_paths_hash": "sha256:1234..."
          },
          "attempted_remedy_hash": "sha256:beef..."
        },
        {
          "loop": 3,
          "loop_local_id": "F3",
          "status": "fixed_by_user",
          "sha": "c066b0b",
          "fingerprint": {
            "claim_consequence_hash": "sha256:abcd...",
            "evidence_paths_hash": "sha256:1234..."
          },
          "attempted_remedy_hash": "sha256:beef..."
        },
        {
          "loop": 5,
          "loop_local_id": "F2",
          "status": "rejected_attempt",
          "sha": "<resolution_sha>",
          "reviewer_reason": "<one sentence>",
          "idempotency_key": "loop5-F-007-rejected_attempt",
          "fingerprint": {
            "claim_consequence_hash": "sha256:abcd...",
            "evidence_paths_hash": "sha256:1234..."
          },
          "attempted_remedy_hash": "sha256:beef..."
        },
        {
          "loop": 7,
          "loop_local_id": "F2",
          "status": "unresolvable",
          "sha": "<retirement_sha>",
          "fingerprint": {
            "claim_consequence_hash": "sha256:abcd...",
            "evidence_paths_hash": "sha256:1234..."
          },
          "attempted_remedy_hash": "sha256:beef...",
          "retirement": {
            "reason": "unresolvable",
            "rationale": "Two rejected attempts at loops 3 and 5; identical Source paths and identical attempted Remedy. Mechanically retired."
          }
        }
      ]
    }
  ]
}
```

Occurrence `status` enum: `open` (still in backlog) | `resolved` (loop's reviewer approved a fix) | `fixed_by_user` (user resolved between loops) | `rejected_attempt` (reviewer rejected the loop's attempted fix; do not drop, the audit chain needs it) | `unresolvable` (per-finding retirement per [method.md § Step 1.6](method.md); the finding is mechanically stuck via Branch A 3-way hash equality or Branch B 2-way hash equality + intervening `resolved`. Skipped for Priority-1 selection while the latest occurrence matches the retiring basis).

### Fingerprint + retirement occurrence fields (PR 1)

Every occurrence emitted at `schema_version >= 2` carries:

- `fingerprint.claim_consequence_hash` — SHA-256 of the normalized Claim + Consequence fields.
- `fingerprint.evidence_paths_hash` — SHA-256 of the sorted, normalized `evidence[]` list.
- `attempted_remedy_hash` — SHA-256 of the normalized Remedy field.

When `status == "unresolvable"`, the occurrence also carries:

- `retirement.reason` — value from `canon/retirement-reasons.toml`.
- `retirement.rationale` — non-empty free-text audit string (validator checks presence, not content).

### Fingerprint algorithm (canonical, owned by `scripts/_fingerprint.py`)

The Actor and Critic call `scripts/_fingerprint.py` when emitting findings; `scripts/validate-artifact.py` imports the same module and recomputes. Single owner prevents algorithm drift; G31 enforces stored hashes equal recomputed hashes.

`normalize(text)` steps (order matters):

1. `None` or non-string → empty string.
2. Lowercase.
3. Strip markdown emphasis characters: `*`, `_`, backticks.
4. Collapse all whitespace runs (newlines, tabs, multiple spaces) to a single space.
5. Strip leading/trailing whitespace.

Hash inputs (each hash returns `"sha256:" + hex_digest`):

- `claim_consequence_hash = SHA-256( normalize(title) "\n" normalize(why_it_matters) "\n" normalize(what_is_wrong) "\n" normalize(why_weakens_submission) )`
- `evidence_paths_hash = SHA-256( "\n".join(sorted(normalize(item) for item in evidence)) )` — note the **sorting**; reordering `evidence[]` does not change the hash.
- `attempted_remedy_hash = SHA-256( normalize(minimal_correction_path) )`

Evidence Chain mapping is the same as in `method.md` § The Evidence Chain: Claim = `title` + `why_it_matters` + `what_is_wrong`; Source = `evidence`; Consequence = `why_weakens_submission`; Remedy = `minimal_correction_path`.

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

## Incident retro feed (--incidents flag)

When the user invokes `/contest-refactor --incidents <path>`, Step 0 reads the file at `<path>` and surfaces its contents to Method Step 3 (architecture review). Purpose: codify hindsight as foresight — past incidents become evidence the current architecture either prevents, mitigates, or still permits.

**Schema (JSON, schema_version 1)**:

```jsonc
{
  "schema_version": 1,
  "incidents": [
    {
      "id": "INC-001",                          // string, unique per file
      "date": "2026-04-15",                     // ISO-8601 date (UTC)
      "summary": "string",                      // 1-2 sentence what-happened
      "severity": "Cosmetic|Noticeable|Serious|Likely Disqualifier",  // optional; same canon as findings
      "affected_paths": ["Sources/Foo/Bar.swift", "..."],  // source files involved
      "root_cause": "string|null",              // post-mortem conclusion, if known
      "preventable_by": "string|null",          // architectural pattern that would have prevented it
      "incident_url": "string|null",            // optional link to bug tracker / postmortem doc
      "user_impact": "string|null"              // optional 1-line user-visible consequence
    }
  ]
}
```

**Loading**:
- Path is resolved relative to CWD if not absolute.
- File must parse as JSON with `schema_version: 1`. Other versions → emit warning, treat as absent.
- Empty `incidents[]` is legal (warns "no incidents to cross-reference").
- File missing or unreadable → emit warning ("--incidents path not found: <path>; proceeding without incident context"), continue Step 0 normally.

**Usage in Method Step 3**:
For each incident, cross-reference `affected_paths` against the current source tree:
- Does the file still exist? If renamed/moved, update the trail.
- If `preventable_by` is set, does the codebase now embody that pattern? Or does the anti-pattern persist?
- If the same architectural shape that allowed the incident is still present, surface as a Noticeable-or-worse finding citing the incident id + date + summary.

This is a **discovery aid**, not a hard gate. Incidents that have been architecturally addressed produce no finding; incidents whose enabling pattern persists become high-confidence findings (real-world precedent beats theoretical concern).

**Skeleton implementation**: the flag, the schema, and the Step 3 sub-bullet are wired; production parsing logic + per-stack incident-pattern matching is deferred until a user supplies an incident corpus to test against.

If REVIEW_HISTORY.md exists at first invocation but REVIEW_HISTORY.json does not, Step -1 step 0.6 reverse-parses to a best-effort .json with each entry marked `schema_version: 1`. Lossy; some fields may be null.
