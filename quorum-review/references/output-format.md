# Reviewer Output Format

All reviewer prompts request the same structured output so the parser
(`quorum.parsing.parse_structured_review` /
`quorum.parsing.parse_cross_critique`) extracts findings uniformly.
Include the matching template verbatim in every reviewer prompt.

## Round 1 template

```
### Reasoning
Full analysis of the artifact covering sequencing, hidden assumptions,
missing validation, rollback, and dependency gaps.

### Blocking Issues
- [B1] (HIGH|MEDIUM|LOW) Short description of blocking issue
  Anchor: <one of Section: / File: / Path: / Hunk: — see below>
  Recommendation: Concrete fix or mitigation

(Write "None" if no blocking issues.)

### Non-Blocking Issues
- [N1] Short description of non-blocking issue
  Anchor: <as above>
  Recommendation: Suggested improvement

(Write "None" if no non-blocking issues.)

### Confidence
HIGH | MEDIUM | LOW

### Scope
<one-line statement of what the reviewer considered in scope>

VERDICT: APPROVED or VERDICT: REVISE
```

## Rules

- Per-issue confidence (`HIGH`, `MEDIUM`, `LOW`) is **required** on blocking issues, optional on non-blocking.
- The final non-empty line of the response must be exactly `VERDICT: APPROVED` or `VERDICT: REVISE` (Tier 2 accepts case / whitespace / trailing punctuation variants — see [protocol.md](protocol.md) "Parser hardening").
- Each round uses fresh per-round IDs (`B1`, `B2`, `N1`, ...). Do not ask the reviewer to continue numbering from a previous round; the host maps cross-round findings by anchor + summary similarity.

## Anchors

Accepted keys (see [protocol.md](protocol.md) "Anchor keys"): `Anchor:`, `Section:`, `File:`, `Path:`, `Hunk:`.

Plan / spec review:

```
- [B1] (HIGH) Sequencing bug — Step 3 starts the migration before Step 2 finishes the read replica.
  Section: Phase 3 — Dual-write migration (lines 88-102)
  Recommendation: Hold Step 3 behind the readiness gate defined in Step 2.
```

Code review (anchor is **required**, point at a file path and either a line range or diff hunk):

```
- [B1] (HIGH) Missing JWT validation on admin route — request bypasses auth.
  File: src/middleware/auth.ts
  Hunk: @@ -45,8 +45,8 @@
  Recommendation: Reinstate verifyToken() before the route handler runs.
```

## Round 2+ cross-critique

In rounds 2+ reviewers respond to each open issue from the shared ledger before writing their updated review. The orchestrator de-duplicates these responses by canonical issue ID.

```
[AGREE BLK-001]
[DISAGREE BLK-002] The line range cited covers a generated file — fix is not actionable.
[REFINE BLK-003] Scope to the admin-only path; the user route already validates.
[B-NEW] (HIGH) Audit log misses correlation id on error paths.
[N-NEW] Style nit — inconsistent quote style in new code.
```

Rules:

1. Every open issue must receive exactly one response (AGREE, DISAGREE, or REFINE).
2. `[B-NEW]` / `[N-NEW]` introduce new issues for rounds 2+.
3. Reviewer identities stay anonymous in the shared deliberation context (`Reviewer A/B/C`). The reviewer's own role label (Skeptic, Security reviewer, etc.) is private to its own prompt and never leaks to peers.

## Blind mode (rounds 3+)

From round 3 onward, the orchestrator may strip support/dispute counts from the issue ledger shown to reviewers, to prevent conformity anchoring. Issues are still presented by canonical ID so cross-critique can address them, but the social signal ("3 of 4 reviewers agreed") is hidden. This behavior is automatic — reviewers do not need to handle it specially.
