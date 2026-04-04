---
name: quorum-review
description: >
  Multi-provider consensus review system (v3). Orchestrates anonymous quorum
  reviews for plans, specs, and code diffs with canonical issue IDs,
  conservative merges, and an independent verifier.
---

# Quorum Review — Multi-Provider Consensus (v3)

Use this skill when you need a panel of 3+ reviewers to review a plan, spec, or
code diff and reach a ledger-derived verdict rather than a raw vote count.

## What it does

- Launches multiple reviewer CLIs through `run_review.py`
- Keeps reviewers anonymous in shared context
- Tracks canonical blocking and non-blocking issue IDs in a ledger
- Merges only semantically equivalent issues
- Verifies surviving blockers with an external verifier outside the panel
- Derives the final verdict from the ledger, not from reviewer tallies

The host agent revises the artifact between rounds; the orchestrator does not
edit the artifact itself.

## Invocation

```bash
python3 scripts/run_quorum.py \
  --reviewers "claude:sonnet,gemini:pro,codex" \
  --plan-file <artifact-file> \
  --quorum-id <id> \
  --round 1 \
  [--mode plan|spec|code] \
  [--threshold unanimous|super|majority] \
  [--on-failure fail-closed|fail-open|shrink-quorum] \
  [--verifier provider:model] \
  [--max-rounds 5] \
  [--skip-verification] \
  [--sequential]
```

Notes:

- `--plan-file` is the artifact input path. In `code` mode, point it at a code
  diff or patch file.
- `--mode` defaults to `plan`; `spec` uses the same tribunal path as `plan`.
- `--verifier` must be an external provider:model pair. If omitted, the
  orchestrator auto-selects a verifier outside the panel.
- `--max-rounds` has a hard cap of 5.

## Modes

| Mode | Purpose | Prompt flavor |
|------|---------|---------------|
| `plan` | Default plan review | Plan/spec contract |
| `spec` | Backward-compatible alias for plan-style review | Plan/spec contract |
| `code` | Review a code diff/change | Code contract with file/line or hunk anchors |

## Review contract

First-round reviewer prompts always include:

- `### Reasoning`
- `### Blocking Issues`
- `### Non-Blocking Issues`
- `### Confidence`
- `### Scope`
- a final `VERDICT: APPROVED` or `VERDICT: REVISE` line

For code reviews, each issue should include an anchor line naming a file path
and either a line range or diff hunk. For plan/spec reviews, anchors can point
to plan sections and line ranges.

If a `REVIEW.md` file is present, its contents are appended to the review
contract as project-specific guidance.

## Round flow

1. **Round 1** — independent parallel review.
2. **Ledger build** — canonical IDs are assigned and issue metadata is stored.
3. **Merge** — only equivalent issues merge; related/distinct and conflicts are
   recorded as relations only.
4. **Rounds 2+** — anonymous cross-critique with compressed later rounds and
   blind mode.
5. **Verification** — surviving blockers are checked by an external verifier.
6. **Verdict** — APPROVED or REVISE is derived from surviving blocking issues.

Round 1 verdicts are based on the raw independent ledger; merge results are
persisted for later rounds.

## Cross-critique

In rounds 2+, reviewers respond to each open issue before their updated review:

- `[AGREE BLK-001]`
- `[DISAGREE BLK-001] reason`
- `[REFINE BLK-001] revised text`
- `[B-NEW] description`
- `[N-NEW] description`

Use anonymous labels (`Reviewer A/B/C`) when sharing prior-round reviews.
Hidden role labels never appear in the shared deliberation context.

## Merge and verification

- Only `EQUIVALENT` pairs merge.
- `RELATED_DISTINCT` and `CONFLICT` only add relations.
- `UNCERTAIN` is logged and left alone.
- Every merge decision is appended to `merge-log.jsonl`.
- Independent verification sees the artifact, blocker ID, anchor, and summary
  only.
- Invalidated blockers are excluded from the final verdict.

## Role packs

- `plan` / `spec`: Skeptic, Constraint Guardian, User Advocate,
  Integrator-minded reviewer
- `code`: Correctness reviewer, Security reviewer, Maintainability reviewer,
  Performance/operability reviewer

## Temp files

The orchestrator writes reviewer prompts, reviews, session metadata, the merged
ledger, deliberation context, tally JSON, and merge logs under the configured
`--tmpdir`. The ledger lives at `qr-${QUORUM_ID}-ledger.json` and the merge log
at `qr-${QUORUM_ID}-merge-log.jsonl`.

## Examples

Plan review:

```bash
python3 scripts/run_quorum.py \
  --reviewers "claude:sonnet,gemini:pro,codex" \
  --plan-file /tmp/plan.md \
  --quorum-id demo1 \
  --round 1 \
  --mode plan
```

Code review with an external verifier:

```bash
python3 scripts/run_quorum.py \
  --reviewers "claude:sonnet,gemini:flash,codex" \
  --plan-file /tmp/change.patch \
  --quorum-id demo2 \
  --round 1 \
  --mode code \
  --verifier copilot:gpt-5.4
```

## Migration notes from v2.4

- Plan/spec review still works, but `spec` is now a first-class mode alias.
- Code review is new and uses anchors for file/line or diff hunk references.
- Verification is now independent from the review panel.
- Merge handling is conservative: only equivalent issues merge; related issues
  stay linked.
- Invalidated blockers no longer drive a REVISE verdict.

