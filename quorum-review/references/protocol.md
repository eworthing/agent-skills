# Quorum Review — Protocol Reference (v3)

This file is the source of truth for `run_quorum.py`, `run_review.py`, and the
review prompts they generate.

## Modes

- `plan` and `spec` share the same tribunal path.
- `code` reviews a code diff/change and requires anchors.
- `--mode` defaults to `plan`.
- `--verifier provider:model` selects the independent verifier; if omitted, the
  orchestrator auto-selects a verifier outside the active panel.

## Review contracts

### Plan/spec

Each reviewer must produce:

```md
### Reasoning
### Blocking Issues
### Non-Blocking Issues
### Confidence
### Scope
VERDICT: APPROVED|REVISE
```

- Blocking and non-blocking issues use canonical labels like `[B1]` and `[N1]`.
- Anchors should be section/line references, e.g. `Section: Step 3 (lines 42-55)`.
- The verdict line must be the last non-empty line.

### Code

Code reviews use the same section structure, but blocking/non-blocking issues
must include an anchor line naming a file path and either a line range or diff
hunk, e.g.:

```md
- [B1] (HIGH) Missing auth check
  Anchor: src/auth/admin.ts (lines 45-52)
```

Accepted anchor keys include `Anchor:`, `Section:`, `File:`, `Path:`, and
`Hunk:`. The parser also preserves line ranges and diff hunk markers when
present.

## Cross-critique

Rounds 2+ use anonymous cross-critique before the updated review:

- `[AGREE BLK-001]` — confirm the issue is valid
- `[DISAGREE BLK-001] reason` — dispute the issue
- `[REFINE BLK-001] revised text` — keep the issue but narrow or clarify it
- `[B-NEW] description` — new blocking issue
- `[N-NEW] description` — new non-blocking issue

Rules:

1. Every open issue must receive exactly one response.
2. Reviewer identities stay anonymous in shared context (`Reviewer A/B/C...`).
3. Hidden role labels never appear in cross-critique context.

## Issue ledger

The ledger is canonical, immutable-by-ID, and stored at
`<TMPDIR>/qr-${QUORUM_ID}-ledger.json`.

### Core shape

```json
{
  "id": "BLK-001",
  "identity": {
    "severity": "blocking",
    "status": "open",
    "round_introduced": 1
  },
  "anchor": {
    "artifact_kind": "code_diff",
    "artifact_path": "src/middleware/auth.ts",
    "anchor_kind": "line_range",
    "anchor_start": 45,
    "anchor_end": 52,
    "anchor_hash": "sha256:..."
  },
  "claim": {
    "summary": "Missing JWT validation on admin route",
    "category": "security",
    "impact": "Unauthorized access possible",
    "evidence_refs": []
  },
  "adjudication": {
    "proposed_by": [1],
    "endorsed_by": [3],
    "refined_by": [],
    "disputed_by": [2],
    "support_count": 2,
    "dispute_count": 1,
    "merged_from": []
  },
  "verification": {
    "status": "pending",
    "verified_by": null,
    "verification_rationale": null
  },
  "relations": {
    "related_distinct": [],
    "conflicts_with": []
  }
}
```

### Ledger rules

- `anchor_hash` is a SHA-256 of the anchor content (file path + line range or
  hunk text). Two issues with the same `anchor_hash` are strong evidence that
  the issues refer to the same location, but they still need matching concern
  signatures before they qualify as `EQUIVALENT`.
- `support_count = len(proposed_by) + len(endorsed_by) + len(refined_by)`
- `dispute_count = len(disputed_by)`
- `claim` holds the canonical summary/category/impact.
- `verification.status` is `pending`, `verified`, or `invalidated`.
- `relations.related_distinct` and `relations.conflicts_with` are relation-only
  links; they do not absorb support counts.

Legacy top-level aliases are still migrated in memory so old ledgers remain
usable.

## Merge pipeline

Merges are conservative and auditable.

### Candidate generation

Only compare issues that share:

- the same severity
- the same `artifact_path` when an artifact path exists
- overlapping or nearby line ranges / the same diff hunk in code mode
- optional lexical similarity on normalized summaries
- optional category

### Classification

Each candidate pair is classified as one of:

- `EQUIVALENT` — issues describe the same concern with the same or overlapping
  anchors. Determined by: identical normalized summaries with related anchors,
  or matching concern signatures on the same anchor (or, when neither issue has
  a location anchor, matching concern signatures without anchors). `anchor_hash`
  alone is not enough, and raw lexical similarity alone is not enough. Conflict
  signals block `EQUIVALENT` classification. These are the only pairs that
  merge.
- `RELATED_DISTINCT` — issues touch the same code area or topic but raise
  meaningfully different concerns (e.g., "add auth check" and "add audit
  logging" on the same endpoint). Created when anchors overlap but summaries
  diverge, or when summaries are lexically similar but anchors differ.
- `CONFLICT` — issues propose opposing actions on the same anchor (e.g., "add
  caching" vs "remove caching"). Detected by shared anchor plus opposing
  verb signals in the summaries.
- `UNCERTAIN` — issues share an anchor area but lack sufficient lexical or
  semantic evidence to classify. Logged and left completely untouched — no
  merge, no relation link.

`SUBSUMES` is intentionally not part of v3.

### Application

- Only `EQUIVALENT` pairs are merged.
- `RELATED_DISTINCT` and `CONFLICT` add relation links only.
- `UNCERTAIN` is logged and left alone.
- Never merge across severity.
- Section-scan fallback only registers issues from explicit `### Blocking
  Issues` / `### Non-Blocking Issues` sections; inline `[B2]` references in
  cross-critique prose must not create new ledger items.
- Every decision is appended to `merge-log.jsonl`.

Round 1 keeps the raw independent ledger for verdict purposes; merge results are
persisted for later rounds. From round 2 onward, the merged ledger feeds the
next round and the final verdict.

## Verification

Verification is independent from the panel.

- `--verifier provider:model` is required for explicit verifier selection.
- If omitted, the orchestrator auto-selects a verifier outside the active panel.
- The verifier never sees support counts, reviewer identities, or prior debate.
- The verifier sees only the current artifact, the blocker ID, anchor data, the
  blocker summary, and the verification contract.
- Output must be exactly `VERIFIED <BLOCKER_ID>` or
  `INVALIDATED <BLOCKER_ID>` on the first non-empty line, followed by one concise
  rationale.
- Invalidated blockers are excluded from the derived verdict and early-exit
  checks.

## Round flow

1. **Round 1** — independent parallel review.
2. **Ledger build** — assign canonical IDs and capture anchors.
3. **Merge** — write conservative merge decisions and keep relation-only cases
   separate.
4. **Rounds 2+** — anonymous cross-critique with compressed later rounds and
   blind mode.
5. **Verification** — validate surviving blockers with an external verifier.
6. **Verdict** — derive APPROVED/REVISE from surviving blocking issues only.

The artifact verdict is ledger-derived and authoritative; individual reviewer
verdicts are advisory.

## Role packs

Role labels are hidden from peers but used to sharpen each reviewer's prompt.

- `plan` / `spec`: Skeptic, Constraint Guardian, User Advocate,
  Integrator-minded reviewer
- `code`: Correctness reviewer, Security reviewer, Maintainability reviewer,
  Performance/operability reviewer

## Compatibility notes

- `REVIEW.md` rubric text is still appended to the first-round prompt.
- Plan/spec review remains backward-compatible with the v2 tribunal path.
- Code review adds anchors but keeps the same structured output and ledger math.
- The system stays file-based and stateless; no external DB or heavy infra is
  required.
