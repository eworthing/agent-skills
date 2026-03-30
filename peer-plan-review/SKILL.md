---
name: peer-plan-review
description: >
  Send an implementation plan to another AI agent such as Codex, Gemini CLI,
  Claude Code, or Copilot for iterative review, then revise and re-submit until
  the reviewer approves or the round limit is reached. Use when the user wants
  a second opinion on a plan, asks for cross-agent review, mentions 'codex
  review', 'gemini review', 'claude review', or 'copilot review', wants to
  validate a plan before executing it, or asks for peer review.
---

# Peer Plan Review

Use this skill to pressure-test a plan before execution. The host agent owns the
plan and revises it between rounds. The reviewer critiques only; it never edits
files or runs the host workflow.

## Use the bundled resources

- Use `scripts/run_review.py` for all provider-specific CLI invocation, resume
  handling, output capture, model normalization, and metadata extraction. Do not
  reimplement those flags manually.
- Read exactly one provider reference after selecting the reviewer:
  `references/codex.md`, `references/gemini.md`, `references/claude.md`, or
  `references/copilot.md`.
- When the user asks which models are available, prefer:
  `python3 <skill-dir>/scripts/run_review.py --list-models --reviewer <provider>`
  instead of relying on a static table in memory.

## Require a plan source

Before starting, confirm that one of these exists:

- The current session already has a plan to review
- The user pasted the plan in the conversation
- The user pointed to a plan file

If no plan is available, ask the user what to review.

## Parse reviewer arguments

Accept explicit command-style or natural-language inputs. Normalize to:

- `reviewer`: `codex`, `gemini`, `claude`, or `copilot`
- `model`: optional
- `effort`: optional `low`, `medium`, `high`, or `xhigh`

Parsing rule:

- If the token after the reviewer is exactly one of `low`, `medium`, `high`,
  or `xhigh`, treat it as `effort` and leave `model` unset.
- Otherwise treat that token as the `model`, and read the next token as
  optional `effort`.

If the reviewer is omitted, ask which reviewer to use.

If the model is omitted, tell the user once that the provider default model
will be used and that they can pass a model override explicitly.

## Preflight

1. Resolve `<skill-dir>` relative to this `SKILL.md`.
2. Read `references/<provider>.md` for install, auth, and CLI-specific notes.
3. Verify the reviewer CLI is available:
   `python3 <skill-dir>/scripts/run_review.py --self-check --reviewer <provider>`
4. If the user supplied an unfamiliar shorthand model, warn once and continue.
   The runner already normalizes known aliases and passes unknown values through
   as raw model IDs.

## Create a review session

Generate a short review ID and keep all artifacts in the platform temp
directory.

```bash
REVIEW_ID=$(uuidgen | tr '[:upper:]' '[:lower:]' | head -c 8)
TMPDIR=$(python3 -c "import tempfile; print(tempfile.gettempdir())")
```

Use these explicit paths:

- `${TMPDIR}/ppr-${REVIEW_ID}-plan.md`
- `${TMPDIR}/ppr-${REVIEW_ID}-prompt.md`
- `${TMPDIR}/ppr-${REVIEW_ID}-review.md`
- `${TMPDIR}/ppr-${REVIEW_ID}-session.json`
- `${TMPDIR}/ppr-${REVIEW_ID}-events.jsonl`

Snapshot the current plan into the `plan.md` file before each round. Treat that
snapshot as immutable for the duration of the round.

## Round 1

Write a prompt that:

- uses this simple order:
  - verdict contract
  - full implementation plan
- asks for a review of the full implementation plan
- focuses on sequencing, hidden assumptions, missing validation, rollback, and
  dependency gaps
- requires the final non-empty line to be exactly one of:
  `VERDICT: APPROVED` or `VERDICT: REVISE`

Run the adapter:

```bash
python3 <skill-dir>/scripts/run_review.py \
  --reviewer <provider> \
  --plan-file <plan.md> \
  --prompt-file <prompt.md> \
  --output-file <review.md> \
  --session-file <session.json> \
  --events-file <events.jsonl> \
  [--model MODEL] \
  [--effort LEVEL] \
  [--timeout SECONDS]
```

Do not pass `--resume` on round 1.
Pass only the portable `--effort` value to `run_review.py`; the adapter maps it
to each provider's native flags or settings internally.

Default timeout is 600 seconds. Increase it for large plans or slower reviewers.

## Read the result

1. Read the session file first and extract the actual model and effort used.
   Key fields: `model`, `model_requested`, `effort`, `effort_source`,
   `effort_requested`, and for Gemini `thinking_tokens`.
2. Read the review output file.
3. Parse the verdict from the last non-empty line, searching upward from the
   bottom of the file.
4. Present the review with a header that uses the actual metadata from the
   session file:

```text
## Peer Review - Round N (reviewer: <provider>, model: <actual-model>, effort: <actual-effort>)
```

If no valid verdict is present, treat the round as `REVISE` and say that the
verdict parse failed.

If `model` or `effort` is missing, fall back to the user-requested value and
then to the provider default or `"default"` as appropriate.

## Revise and re-review

When the verdict is `REVISE`:

1. Address the review point by point.
2. Rewrite the plan snapshot with the updated full plan.
3. Write a short `Changes since last round` bullet list.
4. Rebuild the prompt in this order:
   - verdict contract
   - previous reviewer feedback
   - `Changes since last round`
   - updated full plan
5. Re-run the adapter with `--resume`.

```bash
python3 <skill-dir>/scripts/run_review.py \
  --reviewer <provider> \
  --plan-file <plan.md> \
  --prompt-file <prompt.md> \
  --output-file <review.md> \
  --session-file <session.json> \
  --events-file <events.jsonl> \
  --resume \
  [--model MODEL] \
  [--effort LEVEL] \
  [--timeout SECONDS]
```

Stop after approval or five total rounds, whichever comes first.

## Handle failures

- If `--resume` fails and no output file was produced, the runner already falls
  back to a fresh execution automatically. Do not submit a second manual retry
  on top of that behavior.
- If the runner exits non-zero and there is no usable output, report the error
  and let the user choose whether to retry, switch reviewers, or stop.
- If the runner exits non-zero but wrote output, try to extract the review and
  verdict anyway before deciding it failed.
- If the reviewer binary is missing, fail fast and quote the installation path
  or command from the selected provider reference.

## Finalize

- If approved, present the final revised plan and note that the reviewer
  approved it.
- If the round limit is reached, present the latest plan plus the unresolved
  reviewer concerns.
- Remove the five explicit temp files created for the session. Do not use globs.

## Rules

- Keep the reviewer read-only. Do not ask it to modify files, execute the host
  workflow, or manage artifacts.
- Use full-output capture for every round. Do not rely on tail-scraping.
- Never use transcript-sharing flags such as `--share` or `--share-gist`.
- Treat the prompt, review, session, and events files as sensitive because they
  contain the plan text.
- Show actual model and effort values from the session file, not guessed values.
