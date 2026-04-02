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

## Review stance

Two stances are available:

- **Standard** (default): Cooperative review seeking to improve the plan.
  Uses the iterative loop (up to 5 rounds) to converge on approval.
- **Adversarial**: Deliberately skeptical single-round review. The reviewer
  tries to find reasons the plan should NOT proceed. Runs one round only —
  present findings and let the user triage. Does not enter the revision loop.

Use adversarial when the user asks to "pressure-test", "break the plan",
"adversarial review", or "find holes in" a plan.

### Adversarial prompt template

When writing the adversarial prompt, include these instructions for the
reviewer:

- Default to skepticism — assume the plan can fail in subtle, high-cost,
  or user-visible ways until evidence says otherwise
- Do not give credit for good intent, partial fixes, or likely follow-up work
- Focus on expensive, dangerous, or hard-to-detect failures:
  - Auth, permissions, trust boundaries
  - Data loss, corruption, irreversible state changes
  - Rollback safety, idempotency gaps
  - Race conditions, ordering assumptions, stale state
  - Missing error handling for degraded dependencies
  - Schema/version compatibility risks
  - Observability gaps that would hide failure
- Prefer one strong, well-evidenced finding over multiple weak ones
- Use the same structured output format (### Blocking Issues with [B1] tags,
  ### Non-Blocking Issues with [N1] tags, Section/Lines references)
- End with `VERDICT: APPROVED` or `VERDICT: REVISE`

After the single adversarial round, present findings and wait for user
direction. Do not enter the revision loop. Go directly to Finalize.

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
REVIEW_ID=$(python3 -c "import uuid; print(uuid.uuid4().hex[:12])")
TMPDIR=$(python3 -c "import tempfile; print(tempfile.gettempdir())")
```

Use these explicit paths:

- `${TMPDIR}/ppr-${REVIEW_ID}-plan.md`
- `${TMPDIR}/ppr-${REVIEW_ID}-prompt.md`
- `${TMPDIR}/ppr-${REVIEW_ID}-review.md`
- `${TMPDIR}/ppr-${REVIEW_ID}-session.json`
- `${TMPDIR}/ppr-${REVIEW_ID}-events.jsonl`
- `${TMPDIR}/ppr-${REVIEW_ID}-errors.jsonl` (error log, retained after cleanup)

Snapshot the current plan into the `plan.md` file before each round. Treat that
snapshot as immutable for the duration of the round.

Number every line of the plan snapshot so the reviewer can cite specific lines.
Use a simple prefix format (e.g., `cat -n` style). Include the numbered plan
in the prompt, not the raw plan. This grounds any line references the reviewer
produces.

## Round 1

Write a prompt that includes:

1. The verdict contract: the final non-empty line must be exactly
   `VERDICT: APPROVED` or `VERDICT: REVISE`
2. The line-numbered implementation plan
3. Instructions requesting this output structure:

```
### Reasoning
Full analysis of the plan covering sequencing, hidden assumptions,
missing validation, rollback, and dependency gaps.

### Blocking Issues
- [B1] (HIGH|MEDIUM|LOW) Short description of blocking issue
  Section: <plan section name> (lines <N-M>)
  Recommendation: Concrete fix or mitigation

(Write "None" if no blocking issues.)

### Non-Blocking Issues
- [N1] Short description of non-blocking issue
  Section: <plan section name> (lines <N-M>)
  Recommendation: Suggested improvement

(Write "None" if no non-blocking issues.)

VERDICT: APPROVED or VERDICT: REVISE
```

Per-issue confidence (HIGH, MEDIUM, LOW) is required on blocking issues,
optional on non-blocking. Section and line references refer to the
numbered plan provided in the prompt.

Run the adapter:

```bash
python3 <skill-dir>/scripts/run_review.py \
  --reviewer <provider> \
  --plan-file <plan.md> \
  --prompt-file <prompt.md> \
  --output-file <review.md> \
  --session-file <session.json> \
  --events-file <events.jsonl> \
  --error-log <errors.jsonl> \
  --review-id <REVIEW_ID> \
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
4. Attempt to extract structured findings from the review using
   `parse_structured_review()` from `ppr_io.py`:
   - Scopes parsing to `### Blocking Issues` and `### Non-Blocking Issues`
     sections only (ignores `### Reasoning` to prevent false positives)
   - Extracts `[B<n>]`/`[N<n>]` tagged findings with confidence, section
     references, and recommendations
   If structured parsing succeeds, present findings in a summary table
   ordered by severity before showing the full review text.
   If structured parsing fails (returns empty list), present the raw
   review text as today — graceful degradation.
5. Present the review with a header that uses the actual metadata from the
   session file:

```text
## Peer Review - Round N (reviewer: <provider>, model: <actual-model>, effort: <actual-effort>)
```

If no valid verdict is present, treat the round as `REVISE` and say that the
verdict parse failed.

If `model` or `effort` is missing, fall back to the user-requested value and
then to the provider default or `"default"` as appropriate.

## Revise and re-review

This section applies to standard reviews only. For adversarial stance,
skip directly to Finalize after Round 1.

When the verdict is `REVISE`:

1. Address the review point by point.
2. Rewrite the plan snapshot with the updated full plan.
3. Write a short `Changes since last round` bullet list.
4. Rebuild the prompt in this order:
   - verdict contract
   - previous reviewer feedback (include finding IDs so the reviewer can
     see what was already raised)
   - `Changes since last round`
   - updated line-numbered full plan
   Each round uses fresh per-round IDs (B1, B2, N1, etc.). Do not ask the
   reviewer to continue numbering from a previous round. If the host needs
   cross-round continuity, it maps findings after parsing based on content
   similarity.
5. Re-run the adapter with `--resume`.

```bash
python3 <skill-dir>/scripts/run_review.py \
  --reviewer <provider> \
  --plan-file <plan.md> \
  --prompt-file <prompt.md> \
  --output-file <review.md> \
  --session-file <session.json> \
  --events-file <events.jsonl> \
  --error-log <errors.jsonl> \
  --review-id <REVIEW_ID> \
  --resume \
  [--model MODEL] \
  [--effort LEVEL] \
  [--timeout SECONDS]
```

Stop after approval or five total rounds, whichever comes first.

## Handle failures

- `--resume` is a request, not a guarantee. If resume fails and no usable
  output was produced, the runner automatically falls back to a fresh execution.
  This fallback happens at most once per invocation. Session metadata records
  whether resume was attempted and whether fallback occurred
  (`resume_requested`, `resume_attempted`, `resume_fallback_used`). Do not
  submit a second manual retry on top of the automatic fallback.
- If the runner exits non-zero and there is no usable output, report the error
  and let the user choose whether to retry, switch reviewers, or stop.
- If the runner exits non-zero but wrote output, try to extract the review and
  verdict anyway before deciding it failed.
- If the reviewer binary is missing, fail fast and quote the installation path
  or command from the selected provider reference.

## Finalize

- If approved, present the final revised plan and note that the reviewer
  approved it.
- If the round limit is reached (standard stance), present the latest plan
  plus the unresolved reviewer concerns.
- If adversarial stance completed its single round with REVISE, present the
  findings as-is — there is no revision loop to exhaust.
- In all three cases, after presenting the outcome, STOP. Do not begin
  implementing changes, editing code, or modifying files based on the review
  findings. Explicitly ask the user which findings, if any, they want
  addressed before taking any action.
- Remove the five explicit temp files created for the session (plan, prompt,
  review, session, events). Do not use globs. The error log
  (`ppr-${REVIEW_ID}-errors.jsonl`) is intentionally retained for post-mortem
  analysis and must not be deleted during cleanup.

## Rules

- Keep the reviewer read-only. Do not ask it to modify files, execute the host
  workflow, or manage artifacts.
- Use full-output capture for every round. Do not rely on tail-scraping.
- Never use transcript-sharing flags such as `--share` or `--share-gist`.
- Treat the prompt, review, session, and events files as sensitive because they
  contain the plan text.
- Show actual model and effort values from the session file, not guessed values.
- After the review loop completes, do not auto-apply fixes or begin
  implementation. Present findings and wait for user direction.
