# Quorum Review — Protocol Reference (v3.1)

This file is the authoritative machine contract for `run_quorum.py`,
`run_review.py`, the reviewer prompts they generate, and the on-disk
artifacts they produce. For the user-facing skill description, invocation
flags, mode table, and examples, see [SKILL.md](../SKILL.md). For the
reviewer output template (round 1 + round 2+ cross-critique syntax), see
[output-format.md](output-format.md).

## Modes

- `plan` and `spec` share the same tribunal path.
- `code` reviews a code diff/change and requires anchors.
- `--mode` defaults to `plan`.
- `--verifier provider:model` selects the independent verifier; if omitted, the orchestrator auto-selects a verifier outside the active panel.

## Issue ledger

The ledger is canonical, immutable-by-ID, and stored at `<TMPDIR>/qr-${QUORUM_ID}-ledger.json`.

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

- `anchor_hash` is a SHA-256 of the anchor content (file path + line range or hunk text). Two issues with the same `anchor_hash` are strong evidence that the issues refer to the same location, but they still need matching concern signatures before they qualify as `EQUIVALENT`.
- `support_count = len(proposed_by) + len(endorsed_by) + len(refined_by)`
- `dispute_count = len(disputed_by)`
- `claim` holds the canonical summary/category/impact.
- `verification.status` is `pending`, `verified`, or `invalidated`.
- `relations.related_distinct` and `relations.conflicts_with` are relation-only links; they do not absorb support counts.

Legacy top-level aliases (v2 ledgers) are migrated in memory so old ledgers remain usable.

## Anchor keys

Accepted anchor keys, recognized by the parser:

- `Anchor:` — generic
- `Section:` — plan/spec sections (with optional `(lines N-M)` suffix)
- `File:` and `Path:` — code paths
- `Hunk:` — diff hunk markers (`@@ -A,B +C,D @@`)

For code reviews, every blocking/non-blocking issue MUST include one of these keys. The parser preserves line ranges and diff-hunk markers when present.

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

- **`EQUIVALENT`** — issues describe the same concern with the same or overlapping anchors. Determined by: identical normalized summaries with related anchors, or matching concern signatures on the same anchor (or, when neither issue has a location anchor, matching concern signatures without anchors). `anchor_hash` alone is not enough, and raw lexical similarity alone is not enough. Conflict signals block `EQUIVALENT` classification. **These are the only pairs that merge.**
- **`RELATED_DISTINCT`** — issues touch the same code area or topic but raise meaningfully different concerns (e.g., "add auth check" and "add audit logging" on the same endpoint). Created when anchors overlap but summaries diverge, or when summaries are lexically similar but anchors differ.
- **`CONFLICT`** — issues propose opposing actions on the same anchor (e.g., "add caching" vs "remove caching"). Detected by shared anchor plus opposing verb signals in the summaries.
- **`UNCERTAIN`** — issues share an anchor area but lack sufficient lexical or semantic evidence to classify. Logged and left completely untouched — no merge, no relation link.

`SUBSUMES` is intentionally not part of v3.

### Application

- Only `EQUIVALENT` pairs are merged.
- `RELATED_DISTINCT` and `CONFLICT` add relation links only.
- `UNCERTAIN` is logged and left alone.
- Never merge across severity.
- Section-scan fallback only registers issues from explicit `### Blocking Issues` / `### Non-Blocking Issues` sections; inline `[B2]` references in cross-critique prose must not create new ledger items.
- Every decision is appended to `merge-log.jsonl`.

Round 1 keeps the raw independent ledger for verdict purposes; merge results are persisted for later rounds. From round 2 onward, the merged ledger feeds the next round and the final verdict.

## Verification I/O contract

Verification is independent from the panel.

- The verifier sees only: the current artifact, the blocker ID, anchor data, the blocker summary, and the verification contract.
- The verifier never sees: support counts, reviewer identities, or prior debate.
- Verifier output MUST be exactly `VERIFIED <BLOCKER_ID>` or `INVALIDATED <BLOCKER_ID>` on the first non-empty line, followed by one concise rationale.
- Invalidated blockers are excluded from the derived verdict and early-exit checks.

## Parser hardening (v3.1)

Reviewer output is parsed in two tiers:

- **Tier 1 (strict contract):** exact match on the documented format (e.g., `VERDICT: APPROVED` as the last non-empty line).
- **Tier 2 (explicit syntactic variants):** case-insensitive, whitespace-tolerant, trailing punctuation OK. Conservative — does not accept ambiguous phrasing.

There is no Tier 3 heuristic. A total parse failure returns `None` (the caller treats `None` as REVISE per the v2.1 contract) AND emits a row to `parse-failures.jsonl` for operator audit. The failure log path is overridable via `QUORUM_PARSE_FAILURES_LOG` env var (tests redirect to per-test tmp paths to keep multiset assertions isolated).

## Round flow

1. **Round 1** — independent parallel review.
2. **Ledger build** — assign canonical IDs and capture anchors.
3. **Merge** — write conservative merge decisions and keep relation-only cases separate.
4. **Rounds 2+** — anonymous cross-critique with compressed later rounds and blind mode.
5. **Verification** — validate surviving blockers with an external verifier.
6. **Verdict** — derive APPROVED/REVISE from surviving blocking issues only.

The artifact verdict is ledger-derived and authoritative; individual reviewer verdicts are advisory.

## Compatibility notes

- `REVIEW.md` rubric text (if present in the project root) is appended to the first-round prompt.
- Plan/spec review remains backward-compatible with the v2 tribunal path.
- Code review adds anchors but keeps the same structured output and ledger math.
- The system stays file-based and stateless; no external DB or heavy infra is required.
- v2 ledgers (top-level aliases for `severity`, `support_count`, etc.) are migrated to v3 nested shape on first load. On-disk v2 files are not rewritten unless the orchestrator persists a new ledger snapshot.
