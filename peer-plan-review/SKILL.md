---
name: peer-plan-review
description: >
  Send the current implementation plan to another AI agent (Codex, Gemini CLI,
  Claude Code, or Copilot CLI) for iterative review. The host agent revises the
  plan based on reviewer feedback and re-submits until the reviewer approves.
  Use this skill whenever the user wants a second opinion on an implementation
  plan, asks for cross-agent review, mentions 'codex review', 'gemini review',
  'claude review', 'copilot review', wants to validate a plan before executing,
  or says things like 'have another model check this', 'get a review', or
  'peer review'.
---

# Peer Plan Review

## Why this exists

Different models catch different blind spots. An iterative review-revise
loop converges on better plans than a single-shot review because the
reviewer can verify that its feedback was actually addressed.

## How it works

Host agent (the one reading this skill) runs the review loop.
Reviewer CLI (Codex, Gemini, Claude Code, or Copilot) produces external reviews.
Host revises. Reviewer re-checks. Max 5 rounds.

Key roles:
- **HOST**: the agent reading this skill — revises the plan between rounds
- **REVIEWER**: the external CLI — produces feedback, never modifies files

## Invocation

Users invoke as: `/peer-plan-review <codex|gemini|claude|copilot> [model] [effort]`

If no argument, ask which reviewer to use.
Second argument optionally selects the model.
Third argument optionally sets reasoning effort: `low`, `medium`, `high`, `xhigh`.

Examples:
- `/peer-plan-review codex`
- `/peer-plan-review claude opus high`
- `/peer-plan-review gemini flash medium`
- `/peer-plan-review copilot gpt-5.4 xhigh`

## Available models

| Provider | Aliases (shorthand)          | Raw ID examples          | Default    |
|----------|------------------------------|--------------------------|------------|
| claude   | sonnet, opus, haiku          | claude-opus-4-6          | (provider) |
| gemini   | auto, pro, flash, flash-lite | gemini-3-pro-preview     | auto       |
| codex    | (none — use raw IDs)         | o3, o4-mini              | (provider) |
| copilot  | (none — use raw IDs)         | gpt-5.4                  | (provider) |

If the user provides a model not in this table, warn that it may be invalid
and ask for confirmation. Unknown names are still passed through — they may
be newly released models.

Canonical model list: see `MODEL_ALIASES` in `scripts/run_review.py`.

## The review contract

Provider-neutral rules all reviewers must follow:

- The VERDICT must be the **LAST non-empty line** of the review output
- Must be exactly: `VERDICT: APPROVED` or `VERDICT: REVISE`
- Parse verdict from the bottom of the output file upward (the plan text
  or prior feedback could contain "VERDICT" as a substring — do not match
  first occurrence)
- Both initial and re-review use full-output capture (never tail-scraping)
- Resume is optional; stateless rerun with prior context is the default
  fallback
- Reviewers operate in read-only / review-only mode — no write or shell
  capabilities; web search and URL fetching are always available
- Provider references: read `references/<provider>.md` for exact CLI syntax

## The re-review prompt structure

For rounds 2+, the prompt file MUST contain (in this order):

1. The review contract (verdict rules)
2. The previous reviewer feedback
3. A bullet list: "Changes since last round"
4. The updated plan (full text)

This makes stateless reruns viable when resume fails, because the
reviewer has full context even without session history.

## Agent Instructions

### Step 0: Pre-check & select reviewer

Parse `$ARGUMENTS`. If no reviewer specified, ask the user which to use.

Before proceeding, verify a plan exists to review. Accepted sources:
- An active plan file in the current session (plan mode)
- A plan the user pasted or dictated in the conversation
- A file path the user referenced

If none of these exist, ask the user: "What would you like reviewed?
Paste your plan, point me to a file, or enter plan mode first."

When the user omits the model argument, use the provider default.
Mention once: "Using <provider>'s default model. Run with a model
name to override (e.g., opus, flash). See Available Models above."

Check binary is installed: `command -v <binary>`

Parsing rule: if the second token matches low|medium|high|xhigh exactly,
treat it as effort (model is omitted). Otherwise treat it as model.
This resolves `/peer-plan-review claude high` → effort=high, model=default.

Validate the model argument against the Available Models table. If not
recognized and the provider has known aliases, warn: "Model '<name>' isn't
in the known list for <provider>. Known: <aliases>. Proceed anyway?"
Do not warn for providers with no aliases (codex, copilot) — they expect
raw model IDs.

Read `references/<provider>.md` for the selected backend (resolve relative
to the directory containing this SKILL.md).

Optionally run the self-check:
```bash
python3 <skill-dir>/scripts/run_review.py --self-check --reviewer <provider>
```

### Step 1: Generate session ID & temp paths

```bash
REVIEW_ID=$(uuidgen | tr '[:upper:]' '[:lower:]' | head -c 8)
```

Use the platform temp directory for all temp files. Resolve it via
`python3 -c "import tempfile; print(tempfile.gettempdir())"` or your
platform's equivalent (`$TMPDIR` on POSIX, `%TEMP%` on Windows).

Temp files (explicit list — `<TMPDIR>` is the resolved temp directory):
- `<TMPDIR>/ppr-${REVIEW_ID}-plan.md`
- `<TMPDIR>/ppr-${REVIEW_ID}-prompt.md`
- `<TMPDIR>/ppr-${REVIEW_ID}-review.md`
- `<TMPDIR>/ppr-${REVIEW_ID}-session.json`
- `<TMPDIR>/ppr-${REVIEW_ID}-events.jsonl`

### Step 2: Capture the plan

Write the current plan content to `<TMPDIR>/ppr-${REVIEW_ID}-plan.md`.
This snapshot is the immutable input for this round — do not modify mid-review.

### Step 3: Submit for review (Round 1)

Write the review prompt to `<TMPDIR>/ppr-${REVIEW_ID}-prompt.md`. Include:
- The review contract (from above)
- The full plan text

Call `run_review.py` (resolve relative to this SKILL.md's directory):
```bash
python3 <skill-dir>/scripts/run_review.py \
  --reviewer <codex|gemini|claude|copilot> \
  --plan-file <TMPDIR>/ppr-${REVIEW_ID}-plan.md \
  --prompt-file <TMPDIR>/ppr-${REVIEW_ID}-prompt.md \
  --output-file <TMPDIR>/ppr-${REVIEW_ID}-review.md \
  --session-file <TMPDIR>/ppr-${REVIEW_ID}-session.json \
  --events-file <TMPDIR>/ppr-${REVIEW_ID}-events.jsonl \
  [--model MODEL] \
  [--effort LEVEL] \
  [--timeout SECONDS]
```

Default timeout is 600s (10 min). For large plans or reviewers that use
tool calls extensively, increase with `--timeout 900` or higher.

### Step 4: Read review & check verdict

Read the session file to get the actual model and effort used. The adapter
extracts metadata from the reviewer's structured output:

- `model` — actual model used (e.g., `"gpt-5.4"`, `"gemini-3-pro-preview"`)
- `effort` — actual effort level, with fallback chain:
  detected (from reviewer output) > requested (`--effort` arg) > provider default
- `effort_source` — one of `"detected"`, `"requested"`, `"provider_default"`
- `effort_requested` — what the user passed via `--effort` (or `"default"`)
- `thinking_tokens` — (Gemini only) actual thinking token count

If model extraction fails, the field falls back to the user-specified
model or `"default"`.

Read the output file. Present the review with header:

```
## Peer Review — Round N (reviewer: ${BACKEND}, model: ${ACTUAL_MODEL}, effort: ${EFFORT})
```

Parse VERDICT from the **last non-empty line** of the output file.
Check for `VERDICT: APPROVED` or `VERDICT: REVISE`.

If `VERDICT: APPROVED` — proceed to Step 7.
If `VERDICT: REVISE` — proceed to Step 5.

If run_review.py exits non-zero:

1. **Resume failure** (already handled): fall back to fresh exec with
   full context in the prompt file. This is the existing behavior.

2. **Stateless failure** (timeout, binary crash, no output file):
   - Report the error and stderr to the user
   - Do NOT auto-retry — the provider may have consumed input or
     created partial state
   - Ask the user: "Review failed: <error>. Retry with fresh session,
     try a different provider, or skip?"

3. **Partial output** (non-zero exit but output file exists):
   - Attempt to extract text and verdict as normal
   - If extraction succeeds, proceed (some providers exit non-zero
     on warnings)
   - If extraction fails, show raw output and ask user how to proceed

If no valid verdict found — treat as REVISE and note the parse failure.

### Step 5: Revise the plan

Address reviewer feedback point by point. Rewrite the plan file (new
immutable snapshot). Summarize changes as a bullet list.

### Step 6: Re-submit (Rounds 2-5)

Write updated prompt using the re-review structure:
1. Review contract
2. Previous reviewer feedback
3. Bullet list of changes since last round
4. Updated plan (full text)

Call `run_review.py` with `--resume`:
```bash
python3 <skill-dir>/scripts/run_review.py \
  --reviewer <codex|gemini|claude|copilot> \
  --plan-file <TMPDIR>/ppr-${REVIEW_ID}-plan.md \
  --prompt-file <TMPDIR>/ppr-${REVIEW_ID}-prompt.md \
  --output-file <TMPDIR>/ppr-${REVIEW_ID}-review.md \
  --session-file <TMPDIR>/ppr-${REVIEW_ID}-session.json \
  --events-file <TMPDIR>/ppr-${REVIEW_ID}-events.jsonl \
  --resume \
  [--model MODEL] \
  [--effort LEVEL] \
  [--timeout SECONDS]
```

Repeat Steps 4-6 until APPROVED or max 5 rounds reached.

### Step 7: Present final result

If approved: display the final plan with a success header.
If max rounds reached without approval: display the latest plan and
remaining feedback, note that the reviewer did not approve within 5 rounds.

### Step 8: Cleanup

Remove these explicit temp files (no glob). Use `rm -f` on POSIX or
`Remove-Item -ErrorAction SilentlyContinue` on Windows — whichever
matches the host agent's shell:
- `<TMPDIR>/ppr-${REVIEW_ID}-plan.md`
- `<TMPDIR>/ppr-${REVIEW_ID}-prompt.md`
- `<TMPDIR>/ppr-${REVIEW_ID}-review.md`
- `<TMPDIR>/ppr-${REVIEW_ID}-session.json`
- `<TMPDIR>/ppr-${REVIEW_ID}-events.jsonl`

## Rules

- Display the actual model and effort from the session file in output
  headers — never hardcode model names or effort levels
- Never use transcript-sharing flags (`--share`, `--share-gist`) in
  automated runs
- Treat session/event logs as sensitive artifacts (they contain plan text)
- If the reviewer CLI is not installed, fail fast with a clear message
  and installation instructions from the provider reference
- If resume fails with no output (session-level failure), the adapter
  falls back to fresh exec automatically. If resume fails but output
  exists (partial output or provider warning), the adapter returns
  non-zero for the host to triage per Step 4's error categories
- The host agent must NOT delegate file modifications to the reviewer —
  the reviewer is read-only
- Bundled resource paths (scripts/, references/) resolve relative to
  the directory containing this SKILL.md
