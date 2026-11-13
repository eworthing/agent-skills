# code-review-opencode — Code-Review Improvement Backlog

> **Naming:** this project is `code-review-opencode`; its command is
> `/code-review-opencode`. Mentions of `/code-review` in this document name
> Claude Code's original command.

Guiding rule: **replicate the reference first; adapt only where the model or
platform makes the reference mechanism impossible.** A third-party idea is
adopted only when it fills a gap that maps directly to Claude Code behavior.

Status legend: **DONE**, **READY**, **DESIGN**, **REJECTED**.

## A. Recovered and implemented

| # | Improvement | Why it maps | Status |
|---|---|---|---|
| A1 | Exact `StructuredOutput` contract for child schema tools | Claude Code validates an Agent output schema and re-prompts with the validator error; our role tools are the platform equivalent. | DONE |
| A2 | Detailed schema validation errors + 3-attempt retry limit | Same `StructuredOutput` behavior: validator error, re-call, retry cap. | DONE |
| A3 | Semantic merge/rank synthesizer | The binary has no dedup/rank code; the actual method is the model applying “Dedup findings that point at the same line/mechanism, keeping the one with the most concrete failure scenario” and “Rank most-severe first.” `review-synth` now does exactly that at `max`/multi-`xhigh`. | DONE |
| A4 | Deterministic pre-verify/fallback merge | The reference model dedups before verification; our engine cannot share its context, so token merge is the pre-verify approximation and fallback. | DONE |
| A5 | Non-interactive `--max-findings`/effort not remembered | Official `/code-review` behavior: a value typed in a non-interactive `-p` run is not persisted. | DONE |
| A6 | `/verify` follow-up (`Gs`/`Ws`) | Reference appends the block when `/verify` exists and the diff has a runtime surface. Gated on a locally installed `verify` skill. | DONE |
| A7 | Per-role `steps` caps (finder/sweep 60, verifier/synth 20) | Equivalent of the Agent tool’s `maxTurns`; numbers are a port heuristic, documented as adaptation. OpenCode injects a “maximum steps, respond with text only” instruction on the final step; 30 exhausted the finder budget on a 6k-line diff before it could submit, so finder/sweep use 60. | DONE |
| A8 | Control-character sanitization in the terminal renderer | `jt` runs `nM` before printing. | DONE |
| A9 | Schema-result cleanup | Prevents per-session map growth after timeouts. | DONE |
| A10 | Remove the child timeout entirely; use `steps` as the bound | Claude’s Agent tool is bounded by `maxTurns`, not a wall-clock cap. The self-review lost 3 finders at 300.0s on a 6,102-line diff. | DONE — `withTimeout` and `--timeout` are gone; the agent `steps` field is the bound; cancellation interrupts children; 253 tests. |
| A11 | Stall watchdog for child runners | `pi-subagents` aborts a call after `stallMs` of no child activity; its wall-clock ceiling is disabled by default. A fixed wall-clock cap is wrong, but a silent child must not hang the engine forever. | DONE — `session.wait` is raced with a session poll; no `time.updated` change for `CODE_REVIEW_STALL_MS` (default 600s) interrupts the child; a stalled child is not retried; `mapLimit` awaits in-flight workers before rethrowing; 253 tests. |

## B. Directly mapped — implemented in this pass

| # | Improvement | Why it maps | Status |
|---|---|---|---|
| B1 | Category from the producing angle | The `ReportFindings` output contract names `category` as a kebab-case angle slug (`correctness`, `reuse`, `simplification`, `efficiency`, `altitude`, `conventions`), not the generic `cleanup`. | DONE — `categoryFor` carries the finder label into each candidate; engine test asserts `reuse`. |
| B2 | Ask finders for `short_summary` and `category` | The output contract requires `short_summary` (≤60 chars, claim alone) and `category`; the reference main model compresses them at report time. | DONE — `finderPrompt` requests both; prompt test asserts the fields. |
| B3 | Conventions context only for the conventions finder | The reference’s angles are independent; only the conventions angle is told to read `CLAUDE.md`. Passing the full text to every finder biases all angles toward conventions. | DONE — `renderScope(..., { includeConventions })`; only the conventions finder and merged cleanup finder get the full text; the sweep gets paths only. |
| B4 | ~~GitLab `!123` and MR URL targets~~ | Out of scope per user. | DROPPED. |
| B5 | `ReportFindings` category fallback | `formatReportFindings` fell back to `f.kind` (`cleanup`). With B1 it uses the angle slug. | DONE — fallback is `f.category ?? (cleanup ? "cleanup" : "correctness")`. |
| B6 | Handle the `ctx.skill.list()` envelope | Live `GET /api/skill` returns `{location, data: [...]}`; `verifyFollowUp` only accepted a bare array, so the `/verify` block never fired. | DONE — `host.ts` accepts both shapes; `hasSkill` test covers the envelope. |

## C. Design — platform-equivalent, higher risk

| # | Improvement | Why it maps | Design |
|---|---|---|---|
| C1 | Background interactive review | Official docs: a terminal `/code-review` runs as a background subagent; `-p`/SDK runs in the foreground. Our command handler blocks the turn. | READY — OpenCode has no interactive-vs-API flag on a plugin command, so map the command path to background and the `code_review` tool path to foreground. Add `--foreground` and `--cancel` extensions; post the report with `session.synthetic({ resume: false })` and a fix/`/verify` result with `session.prompt({ delivery: "queue" })`. Full design in [`CODE_REVIEW_PENDING_PLAN.md`](CODE_REVIEW_PENDING_PLAN.md) §3.1. |
| C2 | Pre-verify semantic dedup | The reference model dedups candidates before spawning verifiers. Our pre-verify merge was deterministic. | DONE — `candidateDedupPrompt` + `applyCandidateDedup` run a `review-synth` dedup pass before verification at `max`/multi-`xhigh`; unclaimed candidates are backfilled so nothing is silently dropped. Test asserts one verifier for two paraphrases. Deterministic token merge is the fallback. |
| C3 | Per-role reasoning effort | The Agent tool accepts an `effort` parameter and a subagent `model`; the Codex port maps correctness → medium, cleanup → low. OpenCode child sessions inherit the parent model/variant. | DONE — the runner resolves per child: agent `model` wins, then `CODE_REVIEW_ROLE_VARIANTS` applies a variant to the parent model, then the parent model is used. The parent model is always passed explicitly because a child without a model produced an empty response. `--model` remains the global override. |
| C4 | `--comment` suggestion blocks | The reference GitHub block says to include a suggestion block only when it fully fixes the issue. Our `gh api` poster has no code suggestion. | READY — add optional `suggestion`/`start_line` internal fields (not the `ReportFindings` schema) and render a `suggestion` code fence; the REST API supports `start_line`/`line`. §3.4. |
| C5 | `ReportFindings` host rendering | Claude Code host apps render the typed list and per-finding outcomes. OpenCode has no equivalent findings card. | DONE — the `code_review` tool now returns `formatReportFindings(engine)` as metadata (`{level, findings}`), so a host can render the typed list; the command path keeps the human renderer. |
| C6 | Give children and the synthesizer the captured diff | The reference model has the diff in context; our children re-ran the command and the synth saw only summaries. | DONE — `resolveScope` captures the unified diff; `renderScope` and the dedup/merge prompts include it, budgeted at 120k chars. Finder, verifier, sweep, dedup, and merge prompts now share the same diff. |
| C7 | Surface `--fix` outcomes | The reference re-reports findings after fixes with `fixed`/`skipped`/`no_change_needed`; a host renders the updated list. | DONE — a `ReportFindings` call with outcomes posts a deduped synthetic summary with `resume: false`; the helper is unit-tested. |
| C8 | Document the effort precedence | Explicit > last used > session effort > medium; a non-interactive run is not remembered; `--model` selects the model, not the review level. | READY — document the chain and add tests; no behavior change. §3.5. |
| C9 | Document host concurrency | The reference Agent tool allows 20; our default is 8 for provider limits. | READY — document `--concurrency 20` as the reference-equivalent opt-in. §3.6. |
| C10 | `ReportFindings` output schema | The host renders a typed findings list and outcomes. | DESIGN / deferred — the Promise tool API has no declared output schema; metadata is the equivalent. Revisit only if the plugin moves to the Effect API. §3.7. |
| C11 | Full-set fix mode (`--fix-all`) | Both `--json` and `ReportFindings` now keep the reference's 32-finding ceiling, and `--fix` is ignored with `--json`; a large review therefore needs a capture-then-fix loop. | DESIGN — explicit opt-in that captures every verified finding without the host cap, then applies them in bounded batches. Keep the default `--json` contract and the reference 32-entry `ReportFindings` contract unchanged. §3.10. |

## V. Validation — planned

| # | Item | Why it matters | Status |
|---|---|---|---|
| V1 | Role-prompt benchmark | The child finder/verifier/sweep prompts are the largest remaining fidelity uncertainty (72–79%). Compare each role prompt against the reference parent prompt on the same diff with an LLM judge. | READY — harness design in [`CODE_REVIEW_PENDING_PLAN.md`](CODE_REVIEW_PENDING_PLAN.md) §3.8. |
| V2 | Known-defect benchmark | Measures quality (precision/recall), not fidelity. Use Martian's 50 PRs / 173 golden comments first, then ReviewBench's 219 PRs / 25-PR test set. | READY — adapter design in §3.9. |

## D. Rejected — would diverge from local `/code-review`

| # | Idea | Source | Why rejected |
|---|---|---|---|
| D1 | `REVIEW.md` injection | Pi port | Official docs: local `/code-review` follows `CLAUDE.md` and does **not** read `REVIEW.md`; that file configures the managed cloud service. |
| D2 | Linter/pre-existing/nitpick/unchanged-line filters | Codex port | Not in the v2.1.318 command prompt; they belong to the older official plugin. |
| D3 | `/simplify` chaining after the report | Pi port | The reference’s after-review block is `/verify`, not `/simplify`. |
| D4 | Embeddings/neutral ranker/`confirmed_by`/model pools | Adjacent reviewers | Not in the reference; the synthesizer already performs the semantic judgment. |
| D5 | Separate `review` command alias | Various | OpenCode already has a built-in `/review`; our command stays `code-review` to avoid a collision. Documented divergence. |

## E. Hardening plan

The port-gap workstreams are tracked in
[`CODE_REVIEW_HARDENING_PLAN.md`](CODE_REVIEW_HARDENING_PLAN.md):
structured-output resilience, fan-out fallback, sweep/synthesis
correctness, concurrency/lifecycle, diff/scope robustness, PR/comment
efficiency, state/argument correctness, output consistency, and tests.
That plan is the execution order; this backlog remains the record of
adopted, designed, and rejected ideas.

Status: **validated** (253 tests). The clean
`/code-review-opencode max --max-findings all --fix` self-review completed with 32
findings; all 32 were applied in the third run, and the one intentional skip
from the second run (the recovered wf221 verifier ladder) remains. C3
(per-role model/effort) and C7 (`--fix` outcome summary) are implemented.

The remaining port-derived work is the design and validation plan in
[`CODE_REVIEW_PENDING_PLAN.md`](CODE_REVIEW_PENDING_PLAN.md): C1 background
review, C4 suggestion blocks, C10 output schema, and the two benchmarks.

## F. Open questions

- Resolved: OpenCode has no interactive-vs-API signal on a plugin command.
  Map the command path to terminal/background and the `code_review` tool path
  to API/foreground; add `--foreground` for scripts that use the command path.
- Resolved: B6 accepts both the bare array and the `{data}` envelope from
  `ctx.skill.list()`; the `/verify` block no longer fails closed on the
  envelope shape.
- GitLab target support is out of scope; GitHub PR targets remain the supported
  `--comment` path.
- Is the semantic synthesizer’s one extra call acceptable at `max` by default,
  or should it be opt-in for cost-sensitive users? Current default: on for
  `max` and multi-agent `xhigh`, with `--no-semantic-merge`. Measure the cost in
  the V2 benchmark.
