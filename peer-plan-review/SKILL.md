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

Pressure-test a plan before execution. The host agent owns the plan and revises
it between rounds. The reviewer critiques only; it never edits files or runs
the host workflow.

## Bundled resources

- `scripts/run_review.py` — provider-specific CLI invocation, resume, output
  capture, model normalization, metadata extraction. Do not reimplement it.
- Provider references — read exactly one after the reviewer is chosen:
  [`references/codex.md`](references/codex.md),
  [`references/gemini.md`](references/gemini.md),
  [`references/claude.md`](references/claude.md),
  [`references/copilot.md`](references/copilot.md).
- [`references/output-format.md`](references/output-format.md) — structured
  output template to include in every prompt.
- [`references/adapter-cli.md`](references/adapter-cli.md) — adapter CLI
  flags, session-file contract.
- [`references/adversarial.md`](references/adversarial.md) — prompt
  additions for the adversarial stance.
- [`references/env.md`](references/env.md) — env vars the runner reads
  (`GEMINI_CONFIG_DIR`, `CODEX_HOME`,
  `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC`).

For available models prefer:
`python3 <skill-dir>/scripts/run_review.py --list-models --reviewer <provider>`.

## Require a plan source

Before starting, confirm one of: a plan already in the session, a plan pasted
by the user, or a file path. If none, ask.

## Parse reviewer arguments

Normalize to:

- `reviewer` — `codex`, `gemini`, `claude`, `copilot` (required; ask if omitted)
- `model` — optional; pass-through if not a known alias
- `effort` — optional `low | medium | high | xhigh`

Parsing rule: the first token after the reviewer is `effort` iff it is one of
those four literals; otherwise treat it as `model` and read the next token as
optional `effort`. If `model` is omitted, tell the user once that the provider
default will be used.

## Review stance

- **Standard** (default): cooperative, iterative loop (up to 5 rounds).
- **Adversarial**: deliberately skeptical single-round review — see
  `references/adversarial.md`. Trigger on *pressure-test*, *break the plan*,
  *adversarial review*, *find holes in*.

## Preflight

1. Resolve `<skill-dir>` relative to this `SKILL.md`.
2. Read `references/<provider>.md`.
3. Verify the CLI:
   `python3 <skill-dir>/scripts/run_review.py --self-check --reviewer <provider>`.
4. If the user supplied an unfamiliar shorthand model, warn once and continue —
   the runner passes unknown values through as raw IDs.

## Create a review session

```bash
REVIEW_ID=$(python3 -c "import uuid; print(uuid.uuid4().hex[:12])")
TMPDIR=$(python3 -c "import tempfile; print(tempfile.gettempdir())")
```

Paths:

- `${TMPDIR}/ppr-${REVIEW_ID}-plan.md`
- `${TMPDIR}/ppr-${REVIEW_ID}-prompt.md`
- `${TMPDIR}/ppr-${REVIEW_ID}-review.md`
- `${TMPDIR}/ppr-${REVIEW_ID}-session.json`
- `${TMPDIR}/ppr-${REVIEW_ID}-events.jsonl`
- `${TMPDIR}/ppr-${REVIEW_ID}-errors.jsonl` *(retained after cleanup)*

Snapshot the plan into `plan.md` before each round and treat the snapshot as
immutable for the round. Number every line (`cat -n` style) so the reviewer can
cite specific lines — include the **numbered** plan in the prompt.

## Round 1

Build a prompt with:

1. Verdict contract: final non-empty line must be `VERDICT: APPROVED` or
   `VERDICT: REVISE`.
2. The line-numbered plan.
3. The structured output template from `references/output-format.md`.

Run the adapter (see `references/adapter-cli.md` for the full flag list). Omit
`--resume` on round 1. Default timeout 600 s — raise for large plans.

## Read the result

1. Read the session file; extract actual `model`, `effort`, `effort_source`
   (and Gemini `thinking_tokens`).
2. Read the review output file.
3. Parse the verdict from the last non-empty line, searching upward.
4. Call `parse_structured_review()` from `ppr_io.py`. Scopes to `### Blocking
   Issues` / `### Non-Blocking Issues` only; extracts `[B<n>]`/`[N<n>]` tags
   with confidence, section/line refs, and recommendations. On success, present
   findings in a severity-ordered summary table before the full review text.
   On empty result, present the raw review — graceful degradation.
5. Header:
   `## Peer Review - Round N (reviewer: <provider>, model: <actual>, effort: <actual>)`

If no valid verdict: treat as `REVISE` and say the verdict parse failed.
If `model` or `effort` is missing: fall back to requested → provider default →
`"default"`.

## Revise and re-review

Standard stance only. Adversarial skips directly to Finalize after round 1.

On `REVISE`:

1. Address each finding.
2. Rewrite the plan snapshot with the updated full plan.
3. Write a short `Changes since last round` bullet list.
4. Rebuild the prompt in this order: verdict contract → previous reviewer
   feedback (with finding IDs) → `Changes since last round` → updated numbered
   plan. Each round uses fresh per-round IDs.
5. Re-run the adapter with `--resume` added.

Stop after approval or five rounds, whichever comes first.

## Handle failures

- `--resume` is a request, not a guarantee. The runner auto-falls-back to a
  fresh execution once if resume fails with no usable output.
  `resume_requested`, `resume_attempted`, `resume_fallback_used` record this.
  Do not submit a second manual retry on top of the automatic fallback.
- Runner non-zero + no output: report and ask the user to retry, switch
  reviewers, or stop.
- Runner non-zero + some output: try to extract the review anyway.
- Binary missing: fail fast and quote the install command from the provider
  reference.

## Finalize

- Approved → present the final revised plan; note reviewer approval.
- Round limit (standard) → present the latest plan + unresolved concerns.
- Adversarial round ended `REVISE` → present findings as-is.
- **In all cases, STOP.** Do not begin implementing changes, editing code, or
  modifying files. Ask the user which findings, if any, they want addressed.
- Remove the five session temp files (plan, prompt, review, session, events).
  Do not use globs. The error log is intentionally retained for post-mortem.

## Rules

- Keep the reviewer read-only. Never ask it to modify files or execute the host
  workflow.
- Capture full output each round. No tail-scraping.
- Never use transcript-sharing flags (`--share`, `--share-gist`).
- Treat prompt/review/session/events files as sensitive (they contain plan text).
- Show actual model/effort from the session file, not guessed values.
