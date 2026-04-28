---
name: peer-plan-review
description: >
  Send an implementation plan to another AI agent such as Codex, Gemini CLI,
  Claude Code, Copilot, or opencode for iterative review, then revise and
  re-submit until the reviewer approves or the round limit is reached. Use when
  the user wants a second opinion on a plan, asks for cross-agent review,
  mentions 'codex review', 'gemini review', 'claude review', 'copilot review',
  or 'opencode review', wants to validate a plan before executing it, or asks
  for peer review.
---

# Peer Plan Review

Pressure-test plan before execution. Host agent own plan, revise between rounds. Reviewer critique only; never edit files or run host workflow.

## Bundled resources

- `scripts/run_review.py` — provider-specific CLI invocation, resume, output capture, model normalization, metadata extraction. No reimplement.
- Provider references — read exactly one after reviewer chosen:
  [`references/codex.md`](references/codex.md),
  [`references/gemini.md`](references/gemini.md),
  [`references/claude.md`](references/claude.md),
  [`references/copilot.md`](references/copilot.md),
  [`references/opencode.md`](references/opencode.md).
- [`references/output-format.md`](references/output-format.md) — structured output template. Include in every prompt.
- [`references/adapter-cli.md`](references/adapter-cli.md) — adapter CLI flags, session-file contract.
- [`references/adversarial.md`](references/adversarial.md) — prompt additions for adversarial stance.
- [`references/env.md`](references/env.md) — env vars runner reads
  (`GEMINI_CONFIG_DIR`, `CODEX_HOME`,
  `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC`).

For available models prefer:
`python3 <skill-dir>/scripts/run_review.py --list-models --reviewer <provider>`.

## Require a plan source

Before start, confirm one of: plan already in session, plan pasted by user, or file path. If none, ask.

## Parse reviewer arguments

Normalize to:

- `reviewer` — `codex`, `gemini`, `claude`, `copilot`, `opencode` (required; ask if omitted)
- `model` — optional; pass-through if not known alias
- `effort` — optional `low | medium | high | xhigh`

Parsing rule: first token after reviewer is `effort` iff one of those four literals; otherwise treat as `model`, read next token as optional `effort`. If `model` omitted, tell user once provider default used.

## Review stance

- **Standard** (default): cooperative, iterative loop (up to 5 rounds).
- **Adversarial**: deliberately skeptical single-round review — see
  `references/adversarial.md`. Trigger on *pressure-test*, *break the plan*,
  *adversarial review*, *find holes in*.

## Preflight

1. Resolve `<skill-dir>` relative to this `SKILL.md`.
2. Read `references/<provider>.md`.
3. Verify CLI:
   `python3 <skill-dir>/scripts/run_review.py --self-check --reviewer <provider>`.
4. If user supplied unfamiliar shorthand model, warn once and continue — runner pass unknown values through as raw IDs.

## Create a review session

```bash
REVIEW_ID=$(python3 -c "import uuid; print(uuid.uuid4().hex[:12])")
eval "$(
  python3 <skill-dir>/scripts/ppr_paths.py \
    --review-id "$REVIEW_ID" \
    --format shell
)"
```

Canonical temp files:

- `${TMPDIR}/ppr-${REVIEW_ID}-plan.md`
- `${TMPDIR}/ppr-${REVIEW_ID}-prompt.md`
- `${TMPDIR}/ppr-${REVIEW_ID}-review.md`
- `${TMPDIR}/ppr-${REVIEW_ID}-session.json`
- `${TMPDIR}/ppr-${REVIEW_ID}-events.jsonl`
- `${TMPDIR}/ppr-${REVIEW_ID}-errors.jsonl` *(retained after cleanup)*

If you persist the current review for later rounds, persist the `REVIEW_ID`
only, then reconstruct all file paths with `ppr_paths.py`. Do not use ad hoc
inline Python that reads `PROMPT_FILE` or related path vars from the
environment before they have been exported.

Example for a persisted id file:
`python3 <skill-dir>/scripts/ppr_paths.py --review-id-file /tmp/ppr-current-id.txt --format shell`

Snapshot plan into `plan.md` before each round. Treat snapshot immutable for round. Number every line (`cat -n` style) so reviewer cite specific lines — include **numbered** plan in prompt.

## Round 1

Build prompt with:

1. Verdict contract: final non-empty line must be `VERDICT: APPROVED` or
   `VERDICT: REVISE`.
2. Line-numbered plan.
3. Structured output template from `references/output-format.md`.

Run adapter (see `references/adapter-cli.md` for full flag list). Omit `--resume` on round 1. Default timeout 600 s — raise for large plans.

## Read the result

1. Read session file; extract actual `model`, `effort`, `effort_source`
   (and Gemini `thinking_tokens`).
2. Read review output file.
3. Parse verdict from last non-empty line, search upward.
4. Call `parse_structured_review()` from `ppr_io.py`. Scopes to `### Blocking Issues` / `### Non-Blocking Issues` only; extracts `[B<n>]`/`[N<n>]` tags with confidence, section/line refs, recommendations. On success, present findings in severity-ordered summary table before full review text. On empty result, present raw review — graceful degradation.
5. Header:
   `## Peer Review - Round N (reviewer: <provider>, model: <actual>, effort: <actual>)`

If no valid verdict: treat as `REVISE`, say verdict parse failed.
If `model` or `effort` missing: fall back to requested → provider default →
`"default"`.

## Revise and re-review

Standard stance only. Adversarial skip direct to Finalize after round 1.

On `REVISE`:

1. Address each finding.
2. Rewrite plan snapshot with updated full plan.
3. Write short `Changes since last round` bullet list.
4. Rebuild prompt in this order: verdict contract → previous reviewer feedback (with finding IDs) → `Changes since last round` → updated numbered plan. Each round use fresh per-round IDs.
5. Re-run adapter with `--resume` added.

Stop after approval or five rounds, whichever first.

## Handle failures

- `--resume` is request, not guarantee. Runner auto-fall-back to fresh execution once if resume fails with no usable output.
  `resume_requested`, `resume_attempted`, `resume_fallback_used` record this.
  No submit second manual retry on top of automatic fallback.
- Runner non-zero + no output: report, ask user to retry, switch reviewers, or stop.
- Runner non-zero + some output: try extract review anyway.
- Binary missing: fail fast, quote install command from provider reference.

## Finalize

- Approved → present final revised plan; note reviewer approval.
- Round limit (standard) → present latest plan + unresolved concerns.
- Adversarial round ended `REVISE` → present findings as-is.
- **In all cases, STOP.** No begin implementing changes, editing code, or modifying files. Ask user which findings, if any, they want addressed.
- Remove five session temp files (plan, prompt, review, session, events).
  No globs. Error log intentionally retained for post-mortem.

## Rules

- Keep reviewer read-only. Never ask it to modify files or execute host workflow.
- Capture full output each round. No tail-scraping.
- Never use transcript-sharing flags (`--share`, `--share-gist`).
- Treat prompt/review/session/events files as sensitive (contain plan text).
- Show actual model/effort from session file, not guessed values.
