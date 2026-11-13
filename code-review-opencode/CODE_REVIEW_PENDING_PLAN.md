# code-review-opencode — Code-Review Pending Gaps — Research and Implementation Plan

> **Naming:** this project is `code-review-opencode`; its command is
> `/code-review-opencode`. Mentions of `/code-review` in this document name
> Claude Code's original command.

Status: **PARTIALLY IMPLEMENTED** — C3 (per-role model/effort) and C7
(`--fix` outcome summary) are implemented and tested. C1, C4, C10, and the two
benchmarks remain.
Date: 2026-11-11.
Scope: the remaining port-derived gaps from
[`CODE_REVIEW_IMPROVEMENT_BACKLOG.md`](CODE_REVIEW_IMPROVEMENT_BACKLOG.md)
(C1, C3, C4), the `--fix` outcome gap, effort precedence, concurrency,
`ReportFindings` output rendering, and the two validation benchmarks.

The P0/P1 port gaps themselves are closed; see
[`CODE_REVIEW_HARDENING_PLAN.md`](CODE_REVIEW_HARDENING_PLAN.md). This plan is
about fidelity and validation, not the hardening workstreams.

## 1. Evidence base

| Topic | Source | What it establishes |
|---|---|---|
| Terminal vs `-p` review | [Claude Code — Review locally with `/code-review`](https://code.claude.com/docs/en/code-review-local) | A terminal review runs as a **background subagent** with its own context; findings arrive in the conversation when it completes. `-p`/Agent SDK runs **foreground**. `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS=1` forces foreground; running `/code-review` again while one is in progress also runs foreground. A background `--fix` edits outside session checkpoints. |
| Subagent effort/model | [Claude Code — Create custom subagents](https://code.claude.com/docs/en/sub-agents) | Subagents support `model`, `effort` (`low`–`max`), `maxTurns`, and `background: true`. Background subagents get a reduced built-in tool set. |
| Findings re-report | Same `/code-review` page | Host apps receive `ReportFindings`; when Claude fixes findings later it re-reports them, and each entry is marked `fixed`, `skipped`, or `no change needed`. |
| OpenCode command shape | [OpenCode — Plugins: Server](https://opencode.ai/docs/build/plugins/server) and [Effect](https://opencode.ai/docs/build/plugins/effect) | A plugin command receives only `{ sessionID, prompt, delivery }`. There is **no interactive-vs-API flag**. Markdown/JSON commands support `subagent: true`, but plugin-registered commands do not expose that field. |
| OpenCode background primitives | Same plugin docs; [HTTP API](https://opencode.ai/docs/api) | `session.synthetic({ resume: false })` admits a display message without scheduling a model turn. `session.prompt({ delivery: "queue" })` queues a turn. `session.create` accepts a `model: { providerID, id, variant }` ref. `session.command` runs a command callback in a target session. |
| OpenCode models | [OpenCode — Models](https://opencode.ai/docs/models) | Variants are `provider/model#variant`. Agents, commands, sessions, and child sessions can select a variant. A subagent inherits the parent model when it has no configured model. |
| OpenCode agents | [OpenCode — Agents](https://opencode.ai/docs/agents) | Agent frontmatter supports `model`, `steps`, `mode`, and permissions. A subagent uses its configured model or inherits the parent's. |
| OpenCode permissions | [OpenCode — Permissions](https://opencode.ai/docs/permissions) | `*` matches any characters including `/`; a shell pattern ending in ` *` also matches the command without arguments. `git -C *` is the correct rule for `git -C <path> ...`. |
| GitHub suggestions | [REST pull request review comments](https://docs.github.com/rest/pulls/comments) and [Commenting on a pull request](https://docs.github.com/en/pull-requests/how-tos/review-pull-requests/commenting-on-a-pull-request) | A suggestion is a Markdown `suggestion` code fence in the comment body. Multi-line comments use `start_line`, `start_side`, `line`, and `side`. |
| Known-defect benchmark | [Martian Code Review Bench](https://github.com/withmartian/code-review-benchmark) | 50 PRs, 173 human-verified golden comments across 5 repos, 3 judge models, MIT-licensed pipeline and datasets. |
| Broader benchmark | [GitHub ReviewBench](https://github.blog/ai-and-ml/github-copilot/reviewbench-an-open-benchmark-for-ai-code-review/) | 219 PRs, 19 languages, 6 metrics (grounded/augmented precision/recall/F1), public dataset and self-serve runner. |

## 2. Gap matrix

| Gap | Reference behavior | OpenCode capability | Design confidence | Status |
|---|---|---|---|---|
| C1 background review | Terminal review is a background subagent; `-p` foreground | Command callback can return early; synthetic/prompt completion; no source flag | High (90%) | READY |
| C3 per-role effort | Subagent `effort`/`model` | Agent `model#variant`; child session model ref | High (95%) | DONE |
| `--fix` outcomes | Re-report with `fixed`/`skipped`/`no_change_needed` | Tool metadata + synthetic summary | High (90%) | DONE |
| C4 suggestions | Suggestion block only when it fully fixes the issue | Markdown fence + `start_line` API | High single-line (85%); medium multi-line (65%) | READY |
| Effort precedence | Explicit > last used > session effort > medium; `-p` not remembered | Already implemented; docs incomplete | High (95%) | READY (docs) |
| Host concurrency | Agent tool concurrency 20 | Provider-limited; default 8 | High (95%) | READY (docs) |
| `ReportFindings` output schema | Host renders typed findings + outcomes | Promise tool API has no output schema; metadata is the equivalent | Low (40%) | DESIGN / deferred |
| Role-prompt benchmark | Child prompts derived from parent instructions | Harness can run both prompts on the same diff | High (85%) | READY |
| Known-defect benchmark | — | Martian 50-PR and ReviewBench 219-PR datasets | High (90%) | READY |

## 3. Designs

### 3.1 C1 — background review

**Behavior to match.** In a terminal, `/code-review` runs in the background;
the parent stays usable and the findings arrive when the review completes. A
`-p`/SDK run waits. A second review while one is running waits (foreground).
`--fix` edits in the background review are outside the session checkpoints.

**OpenCode mapping.** The plugin command callback can start the review and
return before it finishes. The HTTP command endpoint returns 204 once the
callback resolves, so the parent session is free while the detached promise
continues in the server process.

**Design.**

- Add `--foreground` (extension) and `--cancel` (extension) flags.
- Keep the `code_review` tool path foreground; it is the API/structured-output
  equivalent of `-p`.
- Keep `--json` foreground: the command path displays it through
  `session.synthetic`, and a caller that needs the bare array should use the
  tool.
- For a command invocation with no `--foreground` and no `--json`, run the
  review in a detached promise:
  - Create an `AbortController` per session and store it in a
    `Map<sessionID, { controller, startedAt }>`.
  - Pass the controller's signal to `resolveAndRun` instead of the command
    request signal (which does not exist on the command path).
  - On completion:
    - `outcome.bare` → `session.synthetic({ sessionID, text, resume: false })`.
    - `outcome.needsModel` (fix or `/verify`) → `session.prompt({ sessionID,
      text, delivery: "queue" })`.
    - Otherwise → `session.synthetic({ sessionID, text, resume: false })`.
  - On error → synthetic error text with `resume: false`; log the stack.
  - In `finally`, delete the map entry.
- `--cancel` aborts the controller for the session, posts a short synthetic
  “review cancelled” message, and clears the map. The engine already checks the
  signal in scope discovery, the runner, and `mapLimit` callers.
- If a review is already running for the session, the new invocation runs
  foreground (matching the reference's “second review runs foreground”) and
  logs a notice. `--foreground` always awaits.
- `--fix` stays in the parent session when the queued prompt runs, so
  `/rewind` still restores its edits. This is a deliberate, documented
  difference from the reference's background-subagent checkpoint behavior.
- The command handler must not append the “review complete” acknowledgement;
  it returns immediately after starting the detached review.

**Files.** `parse.ts` (flags), `index.ts` (command handler + map),
`test/parse.test.ts`, `test/engine.test.ts` or a new
`test/background.test.ts`.

**Tests.** Deferred fake runner: the command returns before the runner settles;
the report is posted with `synthetic`; a fix result is posted with `prompt` and
`delivery: "queue"`; `--foreground` awaits; `--cancel` aborts; a second
invocation runs foreground; an error posts a synthetic error; `--json` stays
foreground.

**Risks.** A server restart loses the detached promise; the reference's
background review also dies if the process exits. There is no cross-process
resume.

### 3.2 C3 — per-role model and effort

**Behavior to match.** Claude Code subagents have their own `model` and
`effort`; the parent's level does not apply to a subagent on another model.
The Codex port maps correctness to medium and cleanup to low.

**OpenCode mapping.** Agent frontmatter supports
`model: provider/model#variant`. A subagent inherits the parent model when it
has no configured model. The runner currently forces `parent?.model` onto every
child, which defeats per-agent configuration.

**Design.** *(Implemented.)* The runner resolves the model per child: the
agent’s own `model` wins; otherwise `CODE_REVIEW_ROLE_VARIANTS` (role or finder
label → variant) applies a variant to the parent model; otherwise the parent
model is used. The parent model is passed explicitly because a child created
without a model produced an empty response in OpenCode. `--model` remains the
global override.

**Files.** `index.ts`, `runner.ts` (already accepts `model`), the four agent
files (comment), `README.md`, tests.

**Tests.** Child `create` input includes the role variant when configured; it
omits `model` by default; `--model` wins over the map; an unknown variant logs
and inherits.

**Acceptance.** Setting `model: ...#max` on `review-finder.md` changes only
finder sessions; verifier and sweep inherit; no provider-specific model is
shipped in the agent files.

### 3.3 `--fix` outcome surfacing

**Behavior to match.** After fixes, the reference re-reports findings through
`ReportFindings` and marks each entry `fixed`, `skipped`, or
`no change needed`. The host renders the updated list.

**OpenCode mapping.** The tool already accepts `outcome` and returns the
findings in `metadata`. The command path does not surface the re-report.

**Design.** *(Implemented.)* `ReportFindings.execute` detects
`findings.some((f) => f.outcome !== undefined)` and posts a synthetic summary
with `resume: false`; a per-session hash prevents duplicate posts. The tool
content and metadata are unchanged.

**Files.** `index.ts` (ReportFindings execute), `format.ts` (summary helper),
`test/reportfindings.test.ts`.

**Tests.** Outcomes post once; no outcomes means no post; a duplicate call does
not post twice.

**Acceptance.** After `--fix`, the transcript shows the per-finding outcomes.

### 3.4 C4 — `--comment` suggestion blocks

**Behavior to match.** The recovered `--comment` block says to include a
suggestion block only when it fully fixes the issue. The reference model posts
it through the host's inline-comment tool.

**OpenCode mapping.** A GitHub suggestion is a Markdown fence; the REST API
supports `start_line`/`line` for a multi-line replacement.

**Design v1 (single-line, engine path).**

- Add optional `suggestion?: string` and `start_line?: number` to the internal
  `RawFinding`/`Finding` type. These are **extensions**, not fields in the
  `ReportFindings` schema.
- Ask the finder for `suggestion` only when the replacement is complete and
  localized, and for `start_line` when the replacement spans multiple lines.
- `commentBody` appends:

  ````text
  ```suggestion
  <replacement>
  ```
  ````

- `buildGitHubCommentArgs` adds `start_line` and `start_side: "RIGHT"` when
  `start_line` is present; `line`/`side: "RIGHT"` are already set.
- Never synthesize a suggestion in the engine; only post one the finder
  supplied.
- Normalize `suggestion` and `start_line` in `json.ts`; cap the suggestion
  length (for example 4,000 characters) to keep comments bounded.

**Design v2 (model path, deferred).** Add a `code_review_comment` tool and
route `--comment` through the model when suggestions are wanted. This is more
faithful to the reference's model-composed comments but adds a model turn and
a new tool. Defer until the benchmark shows suggestions matter.

**Files.** `json.ts`, `finding.ts` or `engine.ts`, `comment.ts`,
`prompts.ts` (finder prompt), tests.

**Tests.** `commentBody` renders the fence; args include `start_line`; a
finding without a suggestion is unchanged; normalization accepts and caps the
field.

**Acceptance.** A finding with a suggestion posts a GitHub suggestion block;
findings without one are unchanged; the `ReportFindings` schema is untouched.

### 3.5 Effort precedence documentation

Document the exact chain in `README.md` and the backlog:

1. Explicit level in the command text.
2. Last-used level (interactive only; not remembered for a non-interactive
   run).
3. `prompt.effort` / the session model variant.
4. `medium`.

`--model provider/model#variant` selects the model for the review; it is not
the review level. `ultra` neither uses nor updates the remembered level. Add a
test per step (the existing `resolveEffort` tests already cover the chain;
extend them for the documented wording).

### 3.6 Host concurrency documentation

Keep the default at 8 for provider limits. Document that the reference Agent
tool allows 20 and that `--concurrency 20` is the reference-equivalent opt-in.
No code change.

### 3.7 `ReportFindings` output schema

The Promise tool API exposes an input schema and metadata but no declared
output schema. The Effect API supports `output`. Declaring the typed output
would let a host render the findings list and outcomes directly.

**Decision.** Defer. The current metadata contract is the equivalent, and an
Effect migration is disproportionate for this gap. Revisit if the plugin moves
to the Effect API.

### 3.8 Role-prompt benchmark

**Purpose.** The child finder/verifier/sweep prompts are the largest remaining
fidelity uncertainty (72–79% confidence). Measure them instead of guessing.

**Harness.** `bench/role-prompt.ts`:

1. Input: a diff, a role, a model, and a run count.
2. Run the role prompt (finder/verifier/sweep) and, for the finder, the
   reference parent prompt on the same diff.
3. Judge the candidate sets with the same model (or a stronger judge) using a
   semantic-match prompt: “do these describe the same underlying issue?”
4. Report recall, precision, and agreement per role and prompt variant.

**Ground truth.** The e2e fixture's seeded defects for a smoke test; Martian's
50 PRs / 173 golden comments for the real run.

**Acceptance.** Finder recall is within 5 points of the parent prompt;
verifier agreement is ≥ 90% on confirmed/refuted; the sweep adds at least one
real gap with < 10% false positives.

### 3.9 Known-defect benchmark

**Purpose.** Measure quality (precision/recall), not just prompt fidelity.

**Martian offline (first).** 50 PRs, 173 golden comments, 5 repos, 3 judge
models, MIT. Adapter:

1. For each PR, get the diff (`gh pr diff <url>`).
2. Run the engine at `max` (or the `code_review` tool) and collect findings.
3. Map `summary + failure_scenario` to benchmark candidates.
4. Run `step3_judge_comments` with the dedup groups and the chosen judge.
5. Report Strict/Core/All precision, recall, and F1/F2.

Start with a 10-PR stratified subset (2 per repo) to bound cost; expand to 50
if the signal is useful. Each max review is roughly an hour, so the subset is
about 10 hours.

**ReviewBench (later).** 219 PRs, 19 languages, 6 metrics, 25-PR test set,
public judge and runner. Use it for a broader run after the Martian subset.

**Acceptance.** Publish the baseline numbers and use them to tune the role
prompts. There is no pass/fail target initially; the benchmark is a quality
signal, not a fidelity gate.

### 3.10 C11 — full-set fix mode (`--fix-all`)

**Problem.** The two contracts disagree on purpose:

- `--json` now keeps the reference's 32-finding ceiling (the engine/fork path
  is capped), but it deliberately ignores `--fix`.
- Default report mode can apply fixes, and `ReportFindings` also caps the list
  at 32, so a 48-finding review needs a capture-then-fix loop.

**Proposed extension.** Add an explicit `--fix-all` flag rather than changing
`--json --fix` semantics.

1. **Capture without the host cap.** Run the engine with the full survivor set
   (the same path `--json` uses), then render the complete list once. With
   `--json`, the first and only machine-readable output remains the bare array;
   without it, use the human renderer.
2. **Apply in bounded batches.** Split the captured findings into batches sized
   for the model's step/context budget (start at 12–16). Each batch gets only
   its own findings plus the apply contract, and runs sequentially so a later
   batch sees earlier edits. Do not ask one turn to apply 48 findings.
3. **Report outcomes without the 32 cap.** A batch result is a synthetic
   per-batch summary (`fixed`/`skipped`/`no_change_needed` counts and any
   failures), not a 48-entry `ReportFindings` call. If a batch contains 32 or
   fewer findings, it may reuse `ReportFindings` for host rendering.
4. **Failure behavior.** A failed or cancelled batch marks only that batch
   unresolved and continues; the final line names the unapplied findings and
   sets the partial warning. A failed capture applies nothing.
5. **Options interaction.** `--fix-all` implies no 32-cap. An explicit
   `--max-findings n` limits the captured/fixed set; `--dry-run` captures only;
   `--comment` remains independent; `--json --fix-all` still prints the full
   array before the fix batches run.

**Acceptance.** A fixture with more than 32 verified findings produces the full
array (or human list), applies every batch, preserves finding order, emits no
duplicate fixes, and leaves the default `--json` and `ReportFindings` contracts
unchanged.

## 4. Sequencing

1. **C3** — DONE (runner wiring, agent comments, tests).
2. **`--fix` outcomes** — DONE (tool execute + synthetic summary + tests).
3. **Effort/concurrency docs** — DONE.
4. **C1 background** — next; flags, map, detached promise, tests. Do this
   after the next clean run and a green suite.
5. **C4 suggestions** — internal fields, comment body, args, tests.
6. **C11 full-set fix** — capture path, batch loop, partial-failure tests; keep
   the default `--json` and `ReportFindings` contracts unchanged.
7. **Role-prompt benchmark** — harness + e2e smoke test.
8. **Known-defect benchmark** — 10-PR Martian subset; expand if useful.
9. **`ReportFindings` output schema** — defer until an Effect migration.

## 5. Resolved open questions

- **Interactive-vs-API signal.** OpenCode does not expose one on the plugin
  command. Resolve it by mapping the command path to terminal/background and
  the `code_review` tool path to API/foreground; add `--foreground` for scripts
  that use the command path.
- **`ctx.skill.list()` envelope.** Resolved by B6; both the bare array and the
  `{data}` envelope are accepted.
- **Semantic synthesizer default.** Keep it on for `max` and multi-`xhigh`;
  document `--no-semantic-merge` and measure the extra call in the benchmark.
- **GitLab.** Out of scope.
- **`git -C` allowlist.** Added to the finder, sweep, and verifier in the main
  tree; sync it to the review copy after the current run.

## 6. Sources

- <https://code.claude.com/docs/en/code-review-local>
- <https://code.claude.com/docs/en/sub-agents>
- <https://code.claude.com/docs/en/commands>
- <https://opencode.ai/docs/build/plugins/server>
- <https://opencode.ai/docs/build/plugins/effect>
- <https://opencode.ai/docs/api>
- <https://opencode.ai/docs/models>
- <https://opencode.ai/docs/agents>
- <https://opencode.ai/docs/commands>
- <https://opencode.ai/docs/permissions>
- <https://docs.github.com/rest/pulls/comments>
- <https://docs.github.com/en/pull-requests/how-tos/review-pull-requests/commenting-on-a-pull-request>
- <https://github.com/withmartian/code-review-benchmark>
- <https://github.blog/ai-and-ml/github-copilot/reviewbench-an-open-benchmark-for-ai-code-review/>
