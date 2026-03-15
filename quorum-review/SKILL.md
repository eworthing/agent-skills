---
name: quorum-review
description: >
  Multi-provider consensus review system (v2). Assembles a panel of 3+ AI
  reviewers (Codex, Gemini CLI, Claude Code, Copilot CLI — or the same
  provider with different models) that deliberate on a plan through structured,
  anonymous cross-critique. Reviewers identify blocking and non-blocking issues
  with canonical IDs, then explicitly agree, disagree, or refine each other's
  findings across rounds. The artifact verdict is DERIVED from surviving
  blocking issues, not raw approval counts. Use this skill when the user wants
  a quorum review, multi-model consensus, panel review, asks for multiple
  agents to review a plan, says 'get a quorum', 'multi-provider review',
  'panel discussion', or wants diverse AI perspectives to converge.
---

# Quorum Review — Multi-Provider Consensus (v2)

## Why this exists

Different models have different blind spots, reasoning styles, and domain
strengths. A single reviewer catches issues a single perspective misses, but a
**panel** of reviewers that can see and respond to each other's feedback
produces a deliberated consensus — not just parallel opinions.

This skill extends the `peer-plan-review` pattern from 1 reviewer to N,
adding a deliberation protocol where reviewers read and react to each other's
feedback across rounds — anonymously, to prevent prestige bias.

## How it works

- **HOST agent**: the one reading this skill — orchestrates rounds, revises
  the plan, merges duplicate issues, synthesizes feedback
- **PANEL**: 3+ reviewer CLIs (same or different providers/models) that
  produce structured reviews with issue IDs, confidence, and scope
- **ANONYMITY**: all deliberation uses anonymous labels (Reviewer A/B/C) —
  true identities appear only in the final report
- **ISSUE LEDGER**: canonical issue IDs (BLK-001, NB-001) tracked across
  rounds with explicit agreement/disagreement counts
- **DERIVED VERDICT**: the artifact is APPROVED when no blocking issue
  survives the configured threshold; REVISE when any blocker survives
- **CROSS-CRITIQUE**: in rounds 2+, reviewers explicitly respond to each
  prior issue with AGREE/DISAGREE/REFINE

## Invocation

Users invoke as:
```
/quorum-review <reviewer1> [reviewer2] [reviewer3] [...] [--threshold <mode>] [--effort <level>] [--on-failure <policy>] [--max-rounds <N>]
```

Each reviewer is specified as `provider[:model]`, e.g.:
- `claude:sonnet` — Claude Code with Sonnet model
- `gemini:pro` — Gemini CLI with Pro model
- `codex` — Codex with default model
- `copilot:gpt-5.4` — Copilot with GPT-5.4

**Minimum 3 reviewers** required for a meaningful quorum.

### Threshold modes

| Mode             | Flag                    | Rule                                      |
|------------------|-------------------------|-------------------------------------------|
| Supermajority    | `--threshold super`      | A blocker survives if endorsed by N-1 of N active reviewers (default) |
| Unanimous        | `--threshold unanimous`  | A blocker survives only if endorsed by all active reviewers |
| Majority         | `--threshold majority`   | A blocker survives if endorsed by more than half of active reviewers |

### Failure policy

| Mode             | Flag                         | Behavior                                        |
|------------------|------------------------------|-------------------------------------------------|
| Shrink-quorum    | `--on-failure shrink-quorum`  | Continue with remaining; threshold uses surviving N (minimum 3) (default) |
| Fail-open        | `--on-failure fail-open`      | Continue with remaining; threshold uses original N |
| Fail-closed      | `--on-failure fail-closed`    | Abort if any reviewer fails                      |

### Examples

```
/quorum-review claude:sonnet gemini:pro codex
/quorum-review claude:sonnet claude:opus claude:haiku --threshold unanimous
/quorum-review gemini:flash codex copilot:gpt-5.4 --threshold majority --effort high
/quorum-review claude:opus gemini:pro copilot codex --on-failure shrink-quorum
```

## Available models

Same as `peer-plan-review` — see the provider reference files.

| Provider | Aliases                      | Raw ID examples          | Default    |
|----------|------------------------------|--------------------------|------------|
| claude   | sonnet, opus, haiku          | claude-opus-4-6          | (provider) |
| gemini   | auto, pro, flash, flash-lite | gemini-3-pro-preview     | auto       |
| codex    | (none — use raw IDs)         | o3, o4-mini              | (provider) |
| copilot  | (none — use raw IDs)         | gpt-5.4                  | (provider) |

## The review contract (v2)

Each reviewer is prompted to produce a structured review:

```
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

**Verdict protocol** (unchanged from v1):
- The VERDICT must be the **LAST non-empty line** of each review output
- Must be exactly: `VERDICT: APPROVED` or `VERDICT: REVISE`
- Parse verdict from the bottom of the output file upward
- Reviewers operate in read-only / review-only mode

**Fallback**: If a reviewer produces unstructured text, the orchestrator
extracts only the verdict (v1 behavior). All other fields default to empty.

## The issue ledger

Issues get **canonical, immutable IDs** assigned by the orchestrator:
- Blocking: `BLK-001`, `BLK-002`, etc.
- Non-blocking: `NB-001`, `NB-002`, etc.

IDs are monotonically increasing and never reused. The ledger tracks:
- `status`: open, resolved, merged
- `proposed_by`: reviewer who first raised the issue (always counts as support)
- `endorsed_by`: reviewers who used [AGREE] (adds to support_count)
- `refined_by`: reviewers who used [REFINE] (adds to support_count)
- `disputed_by`: reviewers who used [DISAGREE] (adds to dispute_count)
- `support_count`: 1 (proposer) + len(endorsed_by) + len(refined_by)
- `dispute_count`: len(disputed_by)
- `merged_from`: for host-agent merge operations

The ledger is stored at `<TMPDIR>/qr-${QUORUM_ID}-ledger.json`.

## Derived verdict

The artifact verdict is a **consequence** of issue-level consensus:

```
APPROVED = no blocking issue has support_count >= threshold
REVISE   = one or more blocking issues have support_count >= threshold
```

Individual reviewers' `VERDICT: APPROVED/REVISE` lines are collected as
**advisory signals** for auditability, but they do NOT determine the outcome.

## Round protocol

### Round 1 — Independent Parallel Review

Each reviewer receives:
1. The structured review contract (blocking/non-blocking/confidence/scope)
2. Panel context: "You are reviewer N of M. Provide your independent assessment."
3. The full plan text

No prior reviews visible. No identities. Execution: parallel by default.

### Round 2 — Anonymous Cross-Critique

Each reviewer receives:
1. The structured review contract
2. Cross-critique instructions (AGREE/DISAGREE/REFINE per canonical issue ID)
3. Panel context (round N, anonymous)
4. **All reviews from round 1** — labeled Reviewer A/B/C (NO provider/model info)
5. The current issue ledger summary
6. Changes since last round (by host)
7. The updated plan (full text)

Reviewers must respond to each open issue:
- `[AGREE BLK-001]` — confirms the issue is valid
- `[DISAGREE BLK-001] reason` — disputes with explanation
- `[REFINE BLK-001] revised text` — agrees but refines scope (counts as support)

Reviewers may raise new issues:
- `[B-NEW] description` — new blocking issue
- `[N-NEW] description` — new non-blocking issue

### Rounds 3+ — Anonymous Convergence (compressed context)

Same cross-critique format, but with **compressed context** instead of full prose:
1. Issue ledger table (open issues with support/dispute counts)
2. Condensed per-reviewer issue lists (not full review text)
3. Changes since last round
4. Updated plan

Identities remain anonymous. Focus narrows to surviving blocking issues.

Default maximum is **3 rounds** (configurable up to 5 with `--max-rounds 5`).

### Verification stage

After cross-critique rounds complete with surviving blockers, the orchestrator
generates targeted verification prompts for each surviving blocker. A single
reviewer (or the host agent) responds `VERIFIED` or `INVALIDATED` with rationale.
Only VERIFIED blockers survive to the derived verdict.

Use `--skip-verification` to bypass for speed.

### Consensus gate

After each round: if derived verdict is APPROVED (no blockers survive threshold), stop.
If round == max_rounds, stop with incomplete consensus noted.

## Agent Instructions

### Step 0: Parse arguments & validate panel

Parse `$ARGUMENTS` to extract the reviewer list and options.

**Argument parsing rules:**
- Tokens matching `provider` or `provider:model` are reviewers
- `--threshold` followed by `unanimous|super|majority` sets the threshold
  (default: `super`)
- `--effort` followed by `low|medium|high|xhigh` sets effort for ALL
  reviewers (individual effort overrides not supported in v1)
- `--on-failure` followed by `fail-closed|fail-open|shrink-quorum` sets
  the failure policy (default: `fail-open`)
- Valid providers: `claude`, `gemini`, `codex`, `copilot`

**Validation:**
- Minimum 3 reviewers required. If fewer, ask: "Quorum review requires at
  least 3 reviewers. Add more reviewers or use /peer-plan-review for a
  single reviewer."
- Check each reviewer binary: `command -v <binary>`
- Validate model aliases against the Available Models table (same rules as
  peer-plan-review)

**Plan detection** — same as peer-plan-review:
- Active plan file in current session
- Plan pasted/dictated in conversation
- File path referenced by user
- If none found, ask the user

Display panel summary:
```
## Quorum Review Panel
- Reviewer 1: claude:sonnet
- Reviewer 2: gemini:pro
- Reviewer 3: codex (default model)
- Threshold: supermajority (blocker survives with 2/3 endorsements)
- Failure policy: shrink-quorum
- Max rounds: 3 (configurable up to 5)
```

Read `references/<provider>.md` for each unique provider in the panel
(resolve relative to peer-plan-review's directory, since we share references).

If a `REVIEW.md` file exists in the current working directory, its contents
are included in the review contract prompt as project-specific review guidelines.

### Step 1: Generate session ID & temp paths

```bash
QUORUM_ID=$(uuidgen | tr '[:upper:]' '[:lower:]' | head -c 8)
```

Temp files per reviewer (where `R` is the 1-indexed reviewer number):

- `<TMPDIR>/qr-${QUORUM_ID}-plan.md` — shared plan snapshot
- `<TMPDIR>/qr-${QUORUM_ID}-r${R}-prompt.md` — reviewer-specific prompt
- `<TMPDIR>/qr-${QUORUM_ID}-r${R}-review.md` — reviewer output
- `<TMPDIR>/qr-${QUORUM_ID}-r${R}-session.json` — reviewer session metadata
- `<TMPDIR>/qr-${QUORUM_ID}-r${R}-events.jsonl` — reviewer event stream
- `<TMPDIR>/qr-${QUORUM_ID}-deliberation.md` — compiled deliberation log
- `<TMPDIR>/qr-${QUORUM_ID}-ledger.json` — issue ledger

### Step 2: Capture the plan

Write the current plan to `<TMPDIR>/qr-${QUORUM_ID}-plan.md`.
This is the immutable input for round 1.

### Step 3: Submit to panel (Round 1)

Call `run_quorum.py` to launch all reviewers concurrently (default) or
sequentially (`--sequential`):

```bash
python3 <skill-dir>/scripts/run_quorum.py \
  --plan-file <TMPDIR>/qr-${QUORUM_ID}-plan.md \
  --reviewers "claude:sonnet,gemini:pro,codex" \
  --quorum-id ${QUORUM_ID} \
  --round 1 \
  --threshold super \
  --on-failure fail-open \
  --tmpdir <TMPDIR> \
  --ledger-file <TMPDIR>/qr-${QUORUM_ID}-ledger.json \
  [--effort LEVEL] [--timeout SECONDS] [--sequential]
```

### Step 4: Read reviews, tally, & check derived verdict

For each reviewer, read:
1. Session file → extract actual model and effort used
2. Output file → extract review text, structured issues, and verdict

Present ALL reviews with **anonymous** headers:

```
## Quorum Review — Round N

### Reviewer A — VERDICT: REVISE
[review text]

---

### Reviewer B — VERDICT: APPROVED
[review text]

---

### Reviewer C — VERDICT: REVISE
[review text]
```

**Issue consensus (derived from ledger):**

```
### Issue Consensus
- BLK-001 "No auth on admin": support 2/3 — SURVIVES
- BLK-002 "Minor naming issue": support 1/3 — DROPPED
- NB-001 "Add pagination": support 1/3 — NON-BLOCKING

### Derived Verdict: REVISE (1 blocking issue survives supermajority threshold)
```

**Advisory tally** (for reference, not authoritative):

```
### Round N Advisory Tally
- APPROVED: 1/3 (Reviewer B)
- REVISE: 2/3 (Reviewer A, Reviewer C)
- Threshold: supermajority (2/3)
- Advisory status: NOT MET (advisory — derived verdict is authoritative)
```

**Consensus check:** Derived verdict from `run_quorum.py` exit code:
- Exit 0: APPROVED (no blockers survive)
- Exit 2: REVISE (blockers survive)
- Exit 3: INDETERMINATE (all reviews unstructured / parse failures)

If APPROVED → Step 7.
If REVISE and round < 5 → Step 5.
If round == 5 → Step 7 (with incomplete consensus noted).

### Step 5: Revise the plan & manage issue ledger

As HOST, synthesize feedback from ALL reviewers:

1. **Review the issue ledger.** If multiple reviewers raised semantically
   equivalent issues (e.g., BLK-001 "no auth on admin" and BLK-003 "admin
   routes lack authentication"), merge them:
   - Pick the survivor (clearest description)
   - Add absorbed issue IDs to survivor's `merged_from` list
   - Set absorbed issues' status to `"merged"`
   - Add a merge record to the `merges` array with reason
   - Combine `agreed_by`/`disagreed_by` lists
   - Update `support_count` and `dispute_count`

2. **Prioritize**: Surviving blocking issues (multi-reviewer support) first,
   then single-reviewer blockers, then non-blocking suggestions.

3. **Address issues**: For each blocking issue, either fix it in the plan
   (mark resolved in ledger) or explain why it's not applicable.

4. **Summarize changes** as a bullet list, referencing issue IDs:
   ```
   - Fixed BLK-001: Added authentication middleware to /admin routes
   - Resolved BLK-002: Added input validation (was SQL injection risk)
   - Noted NB-001: Pagination deferred to phase 2 (out of scope)
   ```

5. **Update the ledger JSON** with resolved/merged status before next round.

### Step 6: Re-submit with cross-critique context (Rounds 2-5)

Call `run_quorum.py` with the next round number and updated files:

```bash
python3 <skill-dir>/scripts/run_quorum.py \
  --plan-file <TMPDIR>/qr-${QUORUM_ID}-plan.md \
  --reviewers "claude:sonnet,gemini:pro,codex" \
  --quorum-id ${QUORUM_ID} \
  --round N \
  --threshold super \
  --on-failure fail-open \
  --tmpdir <TMPDIR> \
  --ledger-file <TMPDIR>/qr-${QUORUM_ID}-ledger.json \
  --deliberation-file <TMPDIR>/qr-${QUORUM_ID}-deliberation.md \
  --changes-summary <TMPDIR>/qr-${QUORUM_ID}-changes.md \
  [--effort LEVEL] [--timeout SECONDS]
```

Then repeat Step 4.

### Step 7: Present final result

**If derived verdict is APPROVED:**
```
## Quorum Review — CONSENSUS REACHED (Round N)
- Panel: claude:sonnet (Reviewer A), gemini:pro (Reviewer B), codex (Reviewer C)
- Threshold: supermajority (2/3)
- Derived verdict: APPROVED (0 blocking issues survive)
- Total rounds: N

### Issue Summary
- BLK-001 "No auth on admin": resolved in round 2
- BLK-002 "SQL injection": resolved in round 2
- NB-001 "Add pagination": informational (deferred)

[Final plan text]
```

**If max rounds without consensus:**
```
## Quorum Review — MAX ROUNDS REACHED (Round 5)
- Panel: claude:sonnet (Reviewer A), gemini:pro (Reviewer B), codex (Reviewer C)
- Threshold: supermajority (2/3)
- Derived verdict: REVISE (1 blocking issue survives)
- Surviving blockers:
  - BLK-003 "Missing error recovery" (support: 2/3)

[Latest plan text with remaining concerns noted]
```

### Step 8: Cleanup

Remove all temp files (explicit list, no glob):
- `<TMPDIR>/qr-${QUORUM_ID}-plan.md`
- `<TMPDIR>/qr-${QUORUM_ID}-deliberation.md`
- `<TMPDIR>/qr-${QUORUM_ID}-tally.json`
- `<TMPDIR>/qr-${QUORUM_ID}-ledger.json`
- `<TMPDIR>/qr-${QUORUM_ID}-changes.md` (if written for `--changes-summary`)
- For each reviewer R: `-r${R}-prompt.md`, `-r${R}-review.md`,
  `-r${R}-session.json`, `-r${R}-events.jsonl`

## Rules

- Display actual model and effort from session files — never hardcode
- Never use transcript-sharing flags in automated runs
- Treat all review artifacts as sensitive (they contain plan text)
- If a reviewer CLI is not installed, remove it from the panel and warn;
  proceed if 3+ reviewers remain
- The host agent must NOT delegate file modifications to reviewers
- Minimum 3 reviewers enforced — no exceptions
- All deliberation context is ANONYMOUS (Reviewer A/B/C) — reveal true
  identities only in the final Step 7 report
- Bundled scripts resolve relative to `peer-plan-review/scripts/` (shared
  infrastructure)
- The orchestrator script `run_quorum.py` lives in this skill's `scripts/`
  directory
- Default 3 rounds, maximum 5 — hard limit to prevent infinite loops
- When a reviewer flips from REVISE to APPROVED (or vice versa), highlight
  the change in the round tally
- The host agent is responsible for merging duplicate issues in Step 5 — the
  orchestrator does NOT auto-deduplicate
- The derived verdict (from surviving blockers) is authoritative; individual
  reviewer verdicts are advisory
- Non-blocking issues inform improvement but NEVER gate approval
- `shrink-quorum` never reduces below 3 active reviewers
- The final report must state original panel size, active panel size, and
  applied threshold
