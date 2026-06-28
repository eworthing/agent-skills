<!--
Layer-5 execution-grain executor template (pinned).

This file is the verbatim dispatch a host uses to run a Step-3-ONLY executor against a
materialized exec-fixture, to measure whether a candidate executor model handles Step-3 safely
(the gate for a future Execution-unfuse). It deliberately POINTS at SKILL.md § Step 3 rather than
copying the sub-steps — the protocol is the single source of truth. Its sha256 (and the sha of the
SKILL.md "### Step 3" section it points at) are pinned in evals/exec_replay_baseline.json prereg;
_exec_replay_selftest.py fails closed if either drifts. exec_replay_materialize.py substitutes the
{{...}} placeholders at dispatch time (the on-disk file keeps the placeholders, so its sha is stable).

Do NOT restate the Step-3 sub-steps here. Keep this a thin wrapper.
-->

You are a Step-3 (Execution) executor for one loop of an autonomous /contest-refactor run. This is
a Layer-5 execution-grain measurement: Step 1 (Critic) and Step 2 (Architect) have ALREADY run, and
their output is persisted on disk. Your job is **only Step 3**.

CWD: {{REPO}}

Read and execute, **verbatim**, sub-steps 0–11 of **`{{SKILL_DIR}}/SKILL.md` § "Step 3 — Execution
Phase (Refactor)"**. The protocol there is authoritative; do not re-derive, reorder, or skip any
sub-step. (You begin at sub-step 0, Checkpoint init.)

## Entry state (already done for you — do NOT re-run Step 1 or Step 2)

- Step 1 + Step 2 of this loop already ran; their output is persisted in `./CURRENT_REVIEW.json`,
  `./CURRENT_REVIEW.md`, and `./findings_registry.json` in the CWD.
- The dry-run gate (Step 2 sub-step 6) did **not** fire — `state` is `"CONTINUE"`. So the Step-3
  pre-condition holds and you start at sub-step 0.

## The exact inputs Step-3 reads (so you need not reconstruct Step 1/2)

- **The finding to execute** = the entry in `CURRENT_REVIEW.json.findings[]` whose `title` equals
  `CURRENT_REVIEW.json.backlog[0].title` (the Priority-1 backlog item).
- **The refactor to perform** = that finding's `minimal_correction_path`.
- **Blast radius** = that finding's `blast_radius.change[]` (files you may modify) and
  `blast_radius.avoid[]` (files you must NOT touch).
- **Selected lens** = `{{LENS}}` (recorded in the Discovery section); read
  `{{SKILL_DIR}}/references/{{LENS}}` for the stack's test / fixture-regeneration rules used at
  sub-step 3.
- **Test/build command** (sub-step 3 re-run) = `{{TEST_COMMAND}}`.

## Model attribution (so the emitted artifact passes G19)

You are running as the executor at model **`{{ARM_MODEL}}`** via an explicit harness override — NOT
the provider default. In `CURRENT_REVIEW.json`, set `loop_model` to `"{{ARM_MODEL}}"` and
`loop_model_source` to `"user_flag"`; keep `provider: "claude_code"`. Leave the existing
`reviewer_model` / `reviewer_model_source` as the seed sets them unless you spawn the reviewer at a
non-default model, in which case set `reviewer_model_source` to `"user_flag"` likewise.

## Scope of this dispatch

This is a SINGLE Step-3 measurement under Loop-Isolation semantics. After sub-step 11 (commit),
**STOP and return the routing JSON below**. Do NOT continue to loop N+1 or re-enter Step 1 —
sub-step 12's inline-continuation clause does not apply here; the host owns dispatch. The
implementation-review pass (sub-step 6) IS part of Step 3 — run it.

Return JSON only (routing; the host reads `./CURRENT_REVIEW.json` for full detail):

```
{
  "loop": 1,
  "system_flag": "CONTINUE",
  "priority_1_finding_id": "F<n>" or null,
  "priority_1_stable_id": "F-NNN" or null,
  "loop_result": "<one sentence>",
  "commit_sha": "<sha>" or null,
  "targeted_finding_status": "resolved|carried_forward",
  "unintended_regression": "<reason>" or null,
  "review_artifact_path": "./CURRENT_REVIEW.json"
}
```
