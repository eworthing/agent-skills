---
name: quorum-review
description: >
  Multi-provider consensus review system. Assembles a panel of 3+ AI reviewers
  (Codex, Gemini CLI, Claude Code, Copilot CLI — or the same provider with
  different models) that deliberate on a plan or response. Each reviewer sees
  all prior feedback from every other reviewer, enabling a back-and-forth
  discussion that refines toward consensus. Use this skill when the user wants
  a quorum review, multi-model consensus, panel review, asks for multiple
  agents to review a plan, says 'get a quorum', 'multi-provider review',
  'panel discussion', or wants diverse AI perspectives to converge.
---

# Quorum Review — Multi-Provider Consensus

## Why this exists

Different models have different blind spots, reasoning styles, and domain
strengths. A single reviewer catches issues a single perspective misses, but a
**panel** of reviewers that can see and respond to each other's feedback
produces a deliberated consensus — not just parallel opinions.

This skill extends the `peer-plan-review` pattern from 1 reviewer to N,
adding a deliberation protocol where reviewers read and react to each other's
feedback across rounds.

## How it works

- **HOST agent**: the one reading this skill — orchestrates rounds, revises
  the plan, synthesizes feedback
- **PANEL**: 3+ reviewer CLIs (same or different providers/models) that
  produce reviews in deliberation mode — each sees all prior reviews
- **DELIBERATION**: each reviewer receives the plan + ALL prior reviews from
  ALL panel members, not just their own history — they can agree, disagree,
  or refine each other's points
- **CONSENSUS**: configurable quorum threshold — unanimous, supermajority,
  or simple majority — with a max round limit

## Invocation

Users invoke as:
```
/quorum-review <reviewer1> [reviewer2] [reviewer3] [...] [--threshold <mode>] [--effort <level>]
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
| Unanimous        | `--threshold unanimous`  | All reviewers must approve (default)       |
| Supermajority    | `--threshold super`      | All-but-one must approve (N-1 of N)        |
| Majority         | `--threshold majority`   | More than half must approve (⌊N/2⌋+1)     |

### Examples

```
/quorum-review claude:sonnet gemini:pro codex
/quorum-review claude:sonnet claude:opus claude:haiku --threshold super
/quorum-review gemini:flash codex copilot:gpt-5.4 --threshold majority --effort high
/quorum-review claude:opus gemini:pro copilot codex --threshold unanimous
```

## Available models

Same as `peer-plan-review` — see the provider reference files.

| Provider | Aliases                      | Raw ID examples          | Default    |
|----------|------------------------------|--------------------------|------------|
| claude   | sonnet, opus, haiku          | claude-opus-4-6          | (provider) |
| gemini   | auto, pro, flash, flash-lite | gemini-3-pro-preview     | auto       |
| codex    | (none — use raw IDs)         | o3, o4-mini              | (provider) |
| copilot  | (none — use raw IDs)         | gpt-5.4                  | (provider) |

## The review contract

Same verdict protocol as `peer-plan-review`, applied to each reviewer independently:

- The VERDICT must be the **LAST non-empty line** of each review output
- Must be exactly: `VERDICT: APPROVED` or `VERDICT: REVISE`
- Parse verdict from the bottom of the output file upward
- Reviewers operate in read-only / review-only mode
- Web search and URL fetching are always available

## The deliberation prompt structure

### Round 1 (initial review)

Each reviewer receives:
1. The review contract (verdict rules)
2. Panel context: "You are reviewer N of M in a quorum panel. Other reviewers
   are also evaluating this plan. In subsequent rounds you will see their
   feedback. Provide your independent assessment now."
3. The full plan text

### Rounds 2+ (deliberation)

Each reviewer receives:
1. The review contract (verdict rules)
2. Panel context: "You are reviewer N of M. Below are ALL reviews from the
   previous round, including your own. Consider the other reviewers' points.
   You may agree, disagree, or refine their feedback. The host has revised
   the plan based on the combined feedback."
3. **All reviews from the previous round** — labeled by reviewer identity
   (e.g., "Reviewer 1 (claude:sonnet)", "Reviewer 2 (gemini:pro)"), each
   separated by a horizontal rule
4. A bullet list: "Changes since last round" (from the host)
5. The updated plan (full text)

This deliberation structure means reviewers can:
- Reference and build on each other's feedback
- Explicitly agree or disagree with specific points
- Converge toward shared conclusions
- Raise new concerns sparked by another reviewer's observation

## Agent Instructions

### Step 0: Parse arguments & validate panel

Parse `$ARGUMENTS` to extract the reviewer list and options.

**Argument parsing rules:**
- Tokens matching `provider` or `provider:model` are reviewers
- `--threshold` followed by `unanimous|super|majority` sets the threshold
  (default: `unanimous`)
- `--effort` followed by `low|medium|high|xhigh` sets effort for ALL
  reviewers (individual effort overrides not supported in v1)
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
- Threshold: unanimous (3/3 must approve)
- Max rounds: 5
```

Read `references/<provider>.md` for each unique provider in the panel
(resolve relative to peer-plan-review's directory, since we share references).

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

### Step 2: Capture the plan

Write the current plan to `<TMPDIR>/qr-${QUORUM_ID}-plan.md`.
This is the immutable input for round 1.

### Step 3: Submit to panel (Round 1)

For **each reviewer** in the panel:

1. Write the round-1 prompt to their prompt file (review contract + panel
   context + full plan)
2. Call `run_review.py` from the `peer-plan-review` skill:

```bash
python3 <peer-plan-review-dir>/scripts/run_review.py \
  --reviewer <provider> \
  --plan-file <TMPDIR>/qr-${QUORUM_ID}-plan.md \
  --prompt-file <TMPDIR>/qr-${QUORUM_ID}-r${R}-prompt.md \
  --output-file <TMPDIR>/qr-${QUORUM_ID}-r${R}-review.md \
  --session-file <TMPDIR>/qr-${QUORUM_ID}-r${R}-session.json \
  --events-file <TMPDIR>/qr-${QUORUM_ID}-r${R}-events.jsonl \
  [--model MODEL] [--effort LEVEL] [--timeout SECONDS]
```

**Execution strategy:** Use `run_quorum.py` to launch all reviewers
concurrently (default) or sequentially (`--sequential`). If a reviewer
fails, report the error and continue with remaining panel members —
the quorum can proceed with N-1 if threshold allows.

```bash
python3 <skill-dir>/scripts/run_quorum.py \
  --plan-file <TMPDIR>/qr-${QUORUM_ID}-plan.md \
  --reviewers "claude:sonnet,gemini:pro,codex" \
  --quorum-id ${QUORUM_ID} \
  --round 1 \
  --threshold unanimous \
  --tmpdir <TMPDIR> \
  [--effort LEVEL] [--timeout SECONDS] [--sequential]
```

### Step 4: Read reviews & tally verdicts

For each reviewer, read:
1. Session file → extract actual model and effort used
2. Output file → extract review text and verdict

Present ALL reviews with labeled headers:

```
## Quorum Review — Round N

### Reviewer 1: claude:sonnet (model: claude-sonnet-4-20250514, effort: high)
[review text]
VERDICT: REVISE

---

### Reviewer 2: gemini:pro (model: gemini-3-pro-preview, effort: medium)
[review text]
VERDICT: APPROVED

---

### Reviewer 3: codex (model: o3, effort: medium)
[review text]
VERDICT: REVISE
```

**Tally results:**

```
### Round N Tally
- APPROVED: 1/3 (gemini:pro)
- REVISE: 2/3 (claude:sonnet, codex)
- Threshold: unanimous (3/3 required)
- Status: NOT MET — proceeding to revision
```

**Consensus check:** Compare approvals against threshold:
- `unanimous`: approvals == N
- `super`: approvals >= N-1
- `majority`: approvals > N/2

If consensus met → Step 7.
If not met and round < 5 → Step 5.
If round == 5 → Step 7 (with incomplete consensus noted).

**Compile deliberation log:** After each round, append all reviews to the
deliberation file for the next round's prompts.

### Step 5: Revise the plan

As HOST, synthesize feedback from ALL reviewers:

1. Identify **consensus points** — issues raised by multiple reviewers
2. Identify **unique points** — issues raised by only one reviewer
3. Identify **disagreements** — where reviewers contradict each other
4. Prioritize: consensus points first, then unique valid points, then
   resolve disagreements using your own judgment

Rewrite the plan. Summarize changes as a bullet list, noting which
reviewer(s) prompted each change.

### Step 6: Re-submit with deliberation context (Rounds 2-5)

For each reviewer, write the deliberation prompt:

1. Review contract
2. Panel context (round N, you are reviewer R of M)
3. **ALL reviews from the previous round** — each labeled with reviewer
   identity and verdict:
   ```
   --- Reviewer 1 (claude:sonnet) — VERDICT: REVISE ---
   [their full review text]

   --- Reviewer 2 (gemini:pro) — VERDICT: APPROVED ---
   [their full review text]

   --- Reviewer 3 (codex) — VERDICT: REVISE ---
   [their full review text]
   ```
4. Bullet list: "Changes since last round (by HOST)"
5. Updated plan (full text)

Call `run_review.py` with `--resume` for each reviewer, then repeat Step 4.

### Step 7: Present final result

**If consensus reached:**
```
## Quorum Review — CONSENSUS REACHED (Round N)
- Panel: claude:sonnet, gemini:pro, codex
- Threshold: unanimous (3/3)
- Approved: 3/3
- Total rounds: N

[Final plan text]
```

**If max rounds without consensus:**
```
## Quorum Review — MAX ROUNDS REACHED (Round 5)
- Panel: claude:sonnet, gemini:pro, codex
- Threshold: unanimous (3/3)
- Final tally: 2/3 approved (codex still revising)
- Outstanding concerns:
  [summary of unresolved feedback from dissenting reviewers]

[Latest plan text with remaining concerns noted]
```

### Step 8: Cleanup

Remove all temp files (explicit list, no glob):
- `<TMPDIR>/qr-${QUORUM_ID}-plan.md`
- `<TMPDIR>/qr-${QUORUM_ID}-deliberation.md`
- `<TMPDIR>/qr-${QUORUM_ID}-tally.json`
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
- Each reviewer's prompt includes ALL other reviewers' feedback (deliberation
  mode), not just their own history
- Bundled scripts resolve relative to `peer-plan-review/scripts/` (shared
  infrastructure)
- The orchestrator script `run_quorum.py` lives in this skill's `scripts/`
  directory
- Maximum 5 rounds — this is a hard limit to prevent infinite loops
- If a reviewer crashes mid-panel, continue with remaining reviewers; adjust
  quorum denominator only if the user confirms (default: keep original N)
- When a reviewer flips from REVISE to APPROVED (or vice versa), highlight
  the change in the round tally
