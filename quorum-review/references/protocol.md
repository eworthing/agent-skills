# Quorum Review — Protocol Reference

Read this file when you need detailed understanding of the review format,
cross-critique protocol, or issue ledger schema beyond what's in SKILL.md.

## Review contract (v2.2)

Each reviewer is prompted to produce a structured review with these sections:

```
### Reasoning
Write your complete analysis of the plan here. Consider architecture,
security, testing, performance, and any other relevant areas. This
section MUST come before your issue lists.

### Blocking Issues
- [B1] (HIGH) Description of blocking issue...
- [B2] (MEDIUM) Description of blocking issue...
(Write "None" if no blocking issues.)

### Non-Blocking Issues
- [N1] Description...
(Write "None" if no non-blocking issues.)

### Confidence
HIGH, MEDIUM, or LOW

### Scope
architecture, security, testing, API design, performance

VERDICT: APPROVED or VERDICT: REVISE
```

Per-issue confidence (`HIGH`, `MEDIUM`, `LOW`) is optional. If omitted, the
review-level confidence is used as the default for each issue.

**Verdict protocol:**
- The VERDICT must be the **LAST non-empty line** of each review output
- Must be exactly: `VERDICT: APPROVED` or `VERDICT: REVISE`
- Parse verdict from the bottom of the output file upward

**Fallback**: If a reviewer produces unstructured text, the orchestrator
extracts only the verdict (v1 behavior). All other fields default to empty.

## Cross-critique protocol (rounds 2+)

In rounds 2+, reviewers respond to each open issue before providing their
updated review. The response tags are:

- `[AGREE BLK-001]` — confirms the issue is valid
- `[DISAGREE BLK-001] reason` — disputes with explanation
- `[REFINE BLK-001] revised text` — agrees but refines scope (counts as support)
- `[B-NEW] description` — new blocking issue
- `[N-NEW] description` — new non-blocking issue

Cross-critique responses are placed BEFORE the standard review sections.
Every open issue should receive a response — silence means no data.

## Issue ledger schema

Issues get **canonical, immutable IDs** assigned by the orchestrator:
- Blocking: `BLK-001`, `BLK-002`, etc.
- Non-blocking: `NB-001`, `NB-002`, etc.

IDs are monotonically increasing and never reused. Each issue tracks:

| Field | Description |
|-------|-------------|
| `id` | Canonical ID (BLK-001, NB-001, etc.) |
| `severity` | `blocking` or `non_blocking` |
| `status` | `open`, `resolved`, `merged`, `invalidated_by_verifier` |
| `proposed_by` | Reviewer index who first raised it (always counts as 1 support) |
| `endorsed_by` | Reviewer indices who used [AGREE] |
| `refined_by` | Reviewer indices who used [REFINE] |
| `disputed_by` | Reviewer indices who used [DISAGREE] |
| `support_count` | 1 (proposer) + len(endorsed_by) + len(refined_by) |
| `dispute_count` | len(disputed_by) |
| `merged_from` | IDs of issues absorbed by host-agent merge |
| `owner_summary` | Current description text |
| `confidence` | Issue-level confidence (HIGH/MEDIUM/LOW or null) |

The ledger is stored at `<TMPDIR>/qr-${QUORUM_ID}-ledger.json`.

### Merge protocol

When the host agent identifies semantically equivalent issues in Step 5:

1. Pick the survivor (clearest description)
2. Add absorbed issue IDs to survivor's `merged_from` list
3. Set absorbed issues' status to `"merged"`
4. Add a merge record to the `merges` array: `{"survivor": "BLK-001", "absorbed": "BLK-003", "reason": "..."}`
5. Combine `endorsed_by`, `refined_by`, `disputed_by` lists (deduplicate reviewer indices)
6. Recalculate: `support_count` = 1 + len(endorsed_by) + len(refined_by),
   `dispute_count` = len(disputed_by)

## Round details

### Round 1 — Independent parallel review

Each reviewer receives the review contract, panel context ("You are reviewer N
of M"), and the full plan text. No prior reviews visible, no identities,
parallel execution by default.

### Round 2 — Anonymous cross-critique

Each reviewer receives the review contract, cross-critique instructions, all
round 1 reviews (labeled Reviewer A/B/C — no provider/model info), the current
issue ledger summary, host changes summary, and the updated plan.

### Rounds 3+ — Compressed context

Same cross-critique format, but with compressed context instead of full prose:
issue ledger table + condensed per-reviewer issue lists. Blind mode strips
support/dispute counts to prevent conformity anchoring.

### Verification stage

After cross-critique with surviving blockers, the first active panel reviewer
verifies each surviving blocker (`VERIFIED` or `INVALIDATED`). Blockers with
unanimous support skip verification (high-probability true positives).
Use `--skip-verification` to bypass.

### Early exit signals

The orchestrator checks after each round whether further rounds are futile:
- No open blockers → APPROVED
- No blockers meet threshold → APPROVED
- All surviving at max support → can't change, stop

The `early_exit` and `early_exit_reason` fields in the tally JSON signal this.

### Derived verdict rule

```
APPROVED = no blocking issue has support_count >= threshold
REVISE   = one or more blocking issues have support_count >= threshold
```

Individual reviewer verdicts are **advisory**; the ledger-derived verdict is
authoritative.
