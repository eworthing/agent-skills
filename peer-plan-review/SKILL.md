---
name: peer-plan-review
description: >
  Send an implementation plan to another AI agent such as Codex, Claude Code,
  Copilot, opencode, Antigravity (agy), or Gemini CLI for iterative review, then
  revise and re-submit until the reviewer approves or the round limit is reached.
  Use when the user wants a second opinion on a plan, asks for cross-agent
  review, mentions 'codex review', 'agy review', 'antigravity review', 'claude
  review', 'copilot review', 'opencode review', or 'gemini review', wants to
  validate a plan before executing it, or asks for peer review.
allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Bash
---

# Peer Plan Review

Pressure-test a plan before execution. The host agent owns the plan and revises it between rounds. The reviewer critiques only; it never edits files or runs the host workflow.

## Contents

- [Bundled resources](#bundled-resources)
- [Require a plan source](#require-a-plan-source)
- [Parse reviewer arguments](#parse-reviewer-arguments)
- [Review stance](#review-stance)
- [Preflight](#preflight)
- [Create a review session](#create-a-review-session)
- [Domain context](#domain-context-optional)
- [Round 1](#round-1)
- [Read the result](#read-the-result)
- [Revise and re-review](#revise-and-re-review)
- [Handle failures](#handle-failures)
- [Finalize](#finalize)
- [Rules](#rules)

## Bundled resources

- `scripts/run_review.py` — provider-specific CLI invocation, resume, output capture, model normalization, metadata extraction. Do not reimplement it.
- Provider references — read exactly one after reviewer chosen:
  [`references/codex.md`](references/codex.md),
  [`references/claude.md`](references/claude.md),
  [`references/copilot.md`](references/copilot.md),
  [`references/opencode.md`](references/opencode.md),
  [`references/antigravity.md`](references/antigravity.md) (`agy` — experimental, not read-only),
  [`references/gemini.md`](references/gemini.md) (EOL 2026-06-18; enterprise-only successor is `agy`).
- [`references/output-format.md`](references/output-format.md) — structured output template. Include in every prompt.
- [`references/adapter-cli.md`](references/adapter-cli.md) — adapter CLI flags, session-file contract.
- [`references/adversarial.md`](references/adversarial.md) — prompt additions for adversarial stance.
- [`references/env.md`](references/env.md) — env vars runner reads
  (`GEMINI_CONFIG_DIR`, `CODEX_HOME`,
  `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC`).

For available models prefer:
`python3 <skill-dir>/scripts/run_review.py --list-models --reviewer <provider>`.

## Require a plan source

Before starting, confirm one of: a plan already in the session, a plan pasted by the user, or a file path. If none, ask.

## Parse reviewer arguments

Normalize to:

- `reviewer` — required; the **provider** acting as reviewer for this run. One of: `codex`, `gemini`, `claude`, `copilot`, `opencode`, `agy` (Antigravity — `antigravity` is accepted and normalized to `agy`). (The `--reviewer <provider>` CLI flag uses the same values; "reviewer" names the role, "provider" names the CLI tool fulfilling it.) **`agy` is experimental and NOT guaranteed read-only** — see [`references/antigravity.md`](references/antigravity.md); run it only on trusted plans with a clean/committed tree.
- `model` — optional; pass-through if not known alias
- `effort` — optional `low | medium | high | xhigh`

Parsing rule: accepted forms are `reviewer`, `reviewer <effort>`, `reviewer <model>`, or `reviewer <model> <effort>`. The first token after `reviewer` is `effort` iff it is one of those four literals (then `model` uses the provider default); otherwise it is `model`, and the next token, if present, is `effort`. If `model` omitted, tell user once provider default used. If `effort` omitted, no effort flag is injected — each provider uses its own persisted config or built-in default.

## Review stance

- **Standard** (default): cooperative, iterative loop (up to 5 rounds) — refine a plan toward approval.
- **Adversarial**: deliberately skeptical single-round review — surface major flaws fast, no revise loop. See
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
- `${TMPDIR}/ppr-${REVIEW_ID}-codex-homes.list` *(Codex isolation manifest; reclaimed at Finalize)*

Keep the `REVIEW_ID` in your own working context across rounds and reconstruct
every path with `ppr_paths.py` (the `eval` above also exports
`$CODEX_HOME_MANIFEST`). Do not use ad hoc inline Python that reads `PROMPT_FILE`
or related path vars from the environment before they have been exported.

**Concurrency:** several peer reviews can run side by side against one codebase.
Each generates its own random `REVIEW_ID`, so their temp files never collide, and
the Codex adapter now isolates each run's session storage (a per-run `CODEX_HOME`
tracked in the manifest) so concurrent Codex reviews can't capture each other's
session. Never share one id-file path between concurrent reviews — a shared
pointer is the one thing that *would* make them step on each other.

Snapshot the plan into `plan.md` before each round. Treat the snapshot as immutable for that round. Number every line (`cat -n` style) so the reviewer can cite specific lines — include the **numbered** plan in the prompt.

## Domain context (optional)

Give the reviewer the host's domain conventions **only** when the plan depends on
**project-specific rules a strong general model would not already apply** — a bespoke
architecture contract, a custom design-token system, a private framework's invariants.
Skip it for **well-known** platform idioms (idiomatic SwiftUI, REST, common security
practice): a capable reviewer already enforces those, so a block is prompt weight for no
gain. Baseline testing confirmed the asymmetry — a strong reviewer flagged idiomatic
SwiftUI violations unaided but missed bespoke project rules (e.g. "writes must go through
the audit store", "every model must be registered or it loses data on migration")
entirely. Default **off**; add a block only when the convention is genuinely non-obvious.
The user may opt out per run (e.g. a maximally independent adversarial pass).

There is no API to enumerate the host's loaded skills — only you know which are active, so
you author this block yourself as prose in the prompt; it is never runner logic.

**Author it as criteria, not prescriptions** — state the standard the plan must meet,
never restate the solution the plan already chose. Hard rule while writing it:

> Do not reference the specific files, classes, or architectural choices made in the plan.
> Output only the abstract rules the plan must satisfy — 3–6 bullets, one checkable rule each.

Place the block between the numbered plan and the output template, in this shape:

```
## Domain context (review criteria — challenge these if any are wrong)
- <checkable rule 1>
- <checkable rule 2>
```

When a block is present, the reviewer uses the two-pass output variant in
`references/output-format.md`: an independent Pass A that must not assume the criteria are
right, then a Pass B that checks the plan against the criteria **and challenges the
criteria themselves**. That preserves the independent second opinion — the reviewer can
reject a biased or incomplete block instead of rubber-stamping the host's framing.

## Round 1

Build prompt with:

1. Verdict contract: final non-empty line must be `VERDICT: APPROVED` or
   `VERDICT: REVISE`.
2. Line-numbered plan.
3. *(optional)* Domain context block — see [Domain context](#domain-context-optional).
   Placed between the plan and the output template.
4. Structured output template from `references/output-format.md`. If a Domain context
   block is included, use its two-pass variant.

Run the runner (see `references/adapter-cli.md` for full flag list). Omit `--resume` on round 1. Default timeout 600 s — raise for large plans.

## Read the result

Dump both files with `cat` — never with `read`, and never with inline Python
that prints a dict. `read VAR` treats a leaked quote/space as a variable name
and fails with `read: '': not a valid identifier`; printing parsed JSON as a
Python dict corrupts it into single-quoted non-JSON. `SESSION_FILE` is already
JSON; emit it verbatim.

```bash
# paths must already be exported via ppr_paths.py --format shell
echo "=== SESSION ==="; cat "$SESSION_FILE"
echo "=== REVIEW ==="; cat "$OUTPUT_FILE"
```

1. Read session file; extract actual `model`, `effort`, `effort_source`
   (and Gemini `thinking_tokens`).
2. Read review output file.
3. Parse verdict from last non-empty line, search upward.
4. Call `parse_structured_review()` from the vendored `_common.session` module
   (`from _common.session import parse_structured_review`, with `scripts/` on
   `sys.path`). Scopes to `### Blocking Issues` / `### Non-Blocking Issues` only; extracts `[B<n>]`/`[N<n>]` tags with confidence, section/line refs, recommendations. On success, present findings in severity-ordered summary table before full review text. On empty result, present raw review — graceful degradation.
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
5. Re-run the runner with `--resume` added.

Stop after approval or five rounds, whichever first.

## Handle failures

- `--resume` is a request, not a guarantee. The runner auto-falls back to a fresh execution once if resume fails with no usable output.
  `resume_requested`, `resume_attempted`, `resume_fallback_used` record this.
  Do not submit a second manual retry on top of the automatic fallback.
- Runner non-zero + no output: report, ask user to retry, switch reviewers, or stop.
- Runner non-zero + some output: try extract review anyway.
- Binary missing: fail fast, quote install command from provider reference.

## Finalize

- Approved → present final revised plan; note reviewer approval.
- Round limit (standard) → present latest plan + unresolved concerns.
- Adversarial round ended `REVISE` → present findings as-is.
- **In all cases, STOP.** Do not begin implementing changes, editing code, or modifying files. Ask the user which findings, if any, they want addressed.
- Reclaim any per-run Codex homes (no-op for other reviewers):
  `python3 <skill-dir>/scripts/ppr_paths.py --cleanup --review-id "$REVIEW_ID"`.
  It validates each recorded home before removing it and is safe to re-run.
- Remove five session temp files (plan, prompt, review, session, events).
  No globs. Error log intentionally retained for post-mortem.

## Rules

- Keep the reviewer read-only. Never ask it to modify files or execute the host workflow. (Exception: `agy`/Antigravity has no read-only mode and auto-approves tools — the runner sandboxes it and prepends a read-only directive, but it can still write. Treat it as experimental; run only on trusted plans with a clean/committed tree.)
- Capture the full output each round; no tail-scraping.
- Never use transcript-sharing flags (`--share`, `--share-gist`).
- Treat the prompt/review/session/events files as sensitive (they contain plan text).
- Show the actual model/effort from the session file, not guessed values.
