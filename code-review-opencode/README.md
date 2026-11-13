# code-review-opencode

`code-review-opencode` is a reconstruction of Claude Code's bundled
`/code-review` command and skill for OpenCode V2. Reference: **Claude Code
v2.1.318**
(`677a2ea7bf576cedd20e191d973914ed8a41796f53a63b1923381ddc4d5b5e7d`).

The plugin id is `code-review-opencode`; the user-facing command is
`/code-review-opencode`. It targets the OpenCode V2 plugin API
(`@opencode/plugin`; tested on OpenCode 2.2.5). The reconstruction is
**read-only by default**. It does not edit, commit, push, or post comments
unless the invocation explicitly asks for `--fix` or `--comment`.

## What is here

```
.opencode/
  plugins/code-review-opencode/
    index.ts            command + tool registration, notices, output routing
    cells.ts            family × effort dispatch table
    parse.ts            argument grammar, effort/limit resolution
    prompts.ts          recovered prompt corpus and assemblers
    engine.ts           deterministic find/verify/sweep orchestration
    runner.ts           OpenCode child-session runner + schema tools
    scope.ts            diff discovery, submodules, context package, conventions
    reportfindings.ts   ReportFindings schema and validation
    format.ts           JSON / human / tool-result contracts
    json.ts             tolerant structured-output parsing
    comment.ts          GitHub/GitLab comment posting, bounded + host-routed
    host.ts             child-session and skill capability probes
    finding.ts          shared anchor, short-summary, and plural helpers
    concurrency.ts      shared bounded worker pool
    artifact.ts         atomic persistent report artifact
    prompts/            hashed prompt fragments + manifest.json
  agents/               read-only finder/verifier/sweep/synth agents
sources/                local-only third-party captures (gitignored)
test/                   338 tests (node --test)
scripts/install-global.sh          global symlink installer for this account
CODE_REVIEW_ORCHESTRATION_MAP.md   full mechanism map
CODE_REVIEW_RECONSTRUCTION_RESEARCH.md
CODE_REVIEW_PORTS.md               public port catalog + feature matrix
CODE_REVIEW_HARDENING_PLAN.md      prioritized gap-closing plan
CODE_REVIEW_PENDING_PLAN.md        remaining fidelity gaps: research + designs
```

## Global installation

The plugin is deployed for the current account, not one project, by symlinking
it and its four agents into the global OpenCode config directory:

```text
~/.config/opencode/plugins/code-review-opencode
  -> <checkout>/.opencode/plugins/code-review-opencode
~/.config/opencode/agents/review-finder.md
  -> <checkout>/.opencode/agents/review-finder.md
~/.config/opencode/agents/review-verifier.md
  -> <checkout>/.opencode/agents/review-verifier.md
~/.config/opencode/agents/review-sweep.md
  -> <checkout>/.opencode/agents/review-sweep.md
~/.config/opencode/agents/review-synth.md
  -> <checkout>/.opencode/agents/review-synth.md
```

Install or refresh the links from the checkout:

```bash
./scripts/install-global.sh
./scripts/install-global.sh --check
```

OpenCode discovers `~/.config/opencode/plugins/` automatically, so no
`opencode.json` edit is needed. Because both plugin and agents are symlinks,
edits to this checkout take effect in the next session (or after `/reload`).
The command is `/code-review-opencode`; the plugin id is
`code-review-opencode`.

## Use

```
/code-review-opencode [low|medium|high|xhigh|max] [--fix] [--comment] \
  [<pr#>|<branch>|<range>|<path>] [--max-findings <n>|all|default] [--json]
```

Examples:

```
/code-review-opencode max
/code-review-opencode high --max-findings 5
/code-review-opencode max --json 42
/code-review-opencode xhigh --comment
/code-review-opencode high --fix src/auth.ts
```

Extensions (not reference flags):

```
--mode cc-2.1.318 | cc-workflow-2.1.162 | cc-workflow-2.1.221
--family default | claude-sonnet-5 | claude-opus-4-8 | claude-opus-5
--model provider/model#variant
--driver engine | prompt
--concurrency <n>   --keep-sessions <bool>
--full-fleet        --semantic-merge      --no-semantic-merge
--verbose           --dry-run
```

There is no wall-clock timeout. A stall watchdog interrupts a child that
produces no session activity for `CODE_REVIEW_STALL_MS` (default `600000` ms;
`0` disables it); healthy long work keeps re-arming it. The session `updated`
timestamp changes per turn rather than per streamed token, so 180s interrupted
healthy max-effort finders during self-review; a stalled child is not retried,
because an interrupt is a timeout rather than a schema failure. The per-agent
bound is the agent’s `steps` field: finder/sweep 60, verifier/synth 20. The
reference `maxTurns` is 20, but DeepSeek exhausted a 30-step finder budget on a
6k-line diff and then received OpenCode’s “maximum steps” summary instruction;
the higher finder budget is a documented adaptation.
Cancellation interrupts the child sessions. A 300s cap lost three finders on a
6,102-line diff during self-review, so a fixed wall-clock cap was removed
rather than tuned.

## Model mapping

DeepSeek V4.1 Flash (and any model that is not a named Claude family) maps to
the reference's **`default`** family:

| Effort | Recipe |
|---|---|
| `low` | one diff pass, ≤4 findings, no verify |
| `medium` | inline 8 angles, dedup, ≤10 (floor 5) |
| `high` | inline 8 angles, dedup, ≤10 (floor 5) |
| `xhigh` | inline 10 angles, dedup, sweep, ≤15 (floor 7) |
| `max` | 10 finder subagents × 8, one verifier per candidate, sweep, ≤15 |

The sonnet-5-only diff-size finder hint does **not** apply to DeepSeek; default
max intentionally runs the full 10-finder fleet.

### Effort precedence

The review level is resolved in this order:

1. The level typed in the command text (`low`–`max`).
2. The last level typed in an interactive session.
3. The session effort (`prompt.effort` / the session model variant).
4. `medium`.

A level typed in a non-interactive run is not remembered. `ultra` neither uses
nor updates the remembered level. `--model provider/model#variant` selects the
model for the review; it is not the review level. The child concurrency default
is 4. OpenCode Go publishes **no concurrency cap**; its limits are dollar-based
per model. DeepSeek V4.1 Flash on Go has a $100 monthly allowance, so $20 per
5-hour window and $50 per week, priced at $0.15/M input, $0.003/M cached read,
and $0.60/M output off-peak (peak doubles). A full self-review costs roughly
$1, so the 5-hour allowance is not the constraint — provider queueing is. Eight
concurrent max-effort children saturated the provider, and a six-way run
(self-review 10) stalled one finder, while four completed cleanly. Four is the
default: the highest value with a complete run on this workload. Use
`--concurrency 6` for smaller diffs or off-peak, and `--concurrency 8` only when
the provider is healthy. `--concurrency 20` is the reference Agent-tool
equivalent. OpenCode does not expose per-model concurrency configuration
(issue #12019), so this gate is the only control.

Scope self-review passes to one surface: `.opencode` (plugin code and agent
configs) first, then `test`, then docs. The full-repo pass is the final gate,
not every iteration. See
[`CODE_REVIEW_SCOPE_ROTATION.md`](CODE_REVIEW_SCOPE_ROTATION.md).

## How it runs

- **Inline cells** return the recovered prompt to the current session; the model
  follows it directly.
- **Multi-agent cells** run a deterministic engine: finder children, dedup,
  one verifier per candidate, a sweep, then rank and cap. Child sessions are
  isolated and read-only.
- **Semantic dedup/rank** is the reference’s actual method: the binary contains
  no dedup/rank code, only the model-facing sentences “Dedup findings that
  point at the same line/mechanism, keeping the one with the most concrete
  failure scenario” and “Rank most-severe first.” At `max` and multi-agent
  `xhigh`, a `review-synth` child first dedups candidates **before
  verification**, then merges and ranks the verified list. The deterministic
  token merge is the fallback if either synthesizer pass fails.
  `--no-semantic-merge` disables both passes.
- **Schema-constrained output** uses role-specific tools
  (`code_review_candidates`, `code_review_verdict`,
  `code_review_group_verdicts`, `code_review_report`,
  `code_review_decisions`) with text-JSON fallback.
- **Per-role model/effort:** an agent’s own
  `model: provider/model#variant` wins. Otherwise
  `CODE_REVIEW_ROLE_VARIANTS` (for example
  `finder=max,verifier=high,reuse=low`) applies a variant to the parent model;
  otherwise the parent model is inherited. `--model` is the global override.
  The parent model is always passed explicitly because a child created without
  a model produced an empty response in OpenCode.
- **Fix outcomes:** after `--fix`, a `ReportFindings` re-report with
  `fixed`/`skipped`/`no_change_needed` posts a deduped synthetic summary, so
  the command path shows the per-finding result.
- **ReportFindings** is registered as a schema-compatible OpenCode tool; its
  description, schema, and result text match the reference.
- **Artifacts:** a normal review is read-only. Set
  `CODE_REVIEW_REPORT_DIR` to write the private atomic report artifact; the
  `--json` stdout contract stays a bare array, and a partial run emits a
  `CODE_REVIEW_PARTIAL` JSON line on stderr.
- **Low-effort `--json` exception:** the reference's low prompt emits
  one-line prose even when `--json` is set, and the port preserves that prompt
  verbatim. The bare-array contract applies to every other cell; for a
  machine-readable low-effort result, use the default ReportFindings path.

## Tests

```bash
node --test test/*.test.ts
```

The suite covers the argument grammar, dispatch table, prompt assembly
(including byte-for-byte checks against committed reference-prompt digests),
engine phases, dedup, ranking, caps, ReportFindings, failure behavior, and
diff discovery.

## Pending gaps

The remaining port-derived work is designed but not implemented. See
[`CODE_REVIEW_PENDING_PLAN.md`](CODE_REVIEW_PENDING_PLAN.md) for the evidence,
designs, and acceptance criteria:

- **C1** background review: command path background, tool path foreground,
  `--foreground`/`--cancel` extensions.
- **C4** `--comment` suggestion blocks: optional `suggestion`/`start_line`
  internal fields.
- **C10** `ReportFindings` output schema: deferred until an Effect migration.
- **V1/V2** role-prompt and known-defect benchmarks (Martian, ReviewBench).

## Documents

- [`CODE_REVIEW_ORCHESTRATION_MAP.md`](CODE_REVIEW_ORCHESTRATION_MAP.md) —
  every mechanism, its reference evidence, and its OpenCode equivalent.
- [`CODE_REVIEW_CONFIDENCE_MAP.md`](CODE_REVIEW_CONFIDENCE_MAP.md) —
  per-group confidence estimates and the ranked gap list.
- [`CODE_REVIEW_EQUIVALENCE_REPORT.md`](CODE_REVIEW_EQUIVALENCE_REPORT.md) —
  built-in `/review` vs this reconstruction, with the e2e run history.
- [`CODE_REVIEW_IMPROVEMENT_BACKLOG.md`](CODE_REVIEW_IMPROVEMENT_BACKLOG.md) —
  adopted, queued, designed, and rejected improvements.
- [`CODE_REVIEW_RECONSTRUCTION_RESEARCH.md`](CODE_REVIEW_RECONSTRUCTION_RESEARCH.md)
  — how the reference was recovered and what is verified.
- [`CODE_REVIEW_PORTS.md`](CODE_REVIEW_PORTS.md) — public max/ultra ports,
  their feature matrix, and what this project adopted or rejected.
- [`CODE_REVIEW_HARDENING_PLAN.md`](CODE_REVIEW_HARDENING_PLAN.md) —
  prioritized workstreams for closing the operational gaps, with
  acceptance criteria and tests.
- [`CODE_REVIEW_PENDING_PLAN.md`](CODE_REVIEW_PENDING_PLAN.md) — the remaining
  fidelity gaps: research evidence, designs, sequencing, and acceptance
  criteria.
- [`CODE_REVIEW_OPENCODE_AUDIT.md`](CODE_REVIEW_OPENCODE_AUDIT.md) — the
  OpenCode V2 plugin audit: API contracts, lifecycle, permissions, parity, and
  the fixes applied for command model/effort and attachments.
- `sources/` — local-only captures of the reference implementations. The
  directory is gitignored; populate it locally if you need to re-run the
  capture-vs-fixture checks.

## Deliberate omissions

Host-only Claude Code features with no OpenCode equivalent are omitted rather
than invented: ultra cloud review, the bundled `/verify` follow-up (the port
only suggests it when a `/verify` skill is installed), the message-mode outcome
note, the end-of-response marker, and the skill-preload family override.
`ultra` is accepted and falls back to a local max-effort review, matching the
reference's non-cloud fallback branch.
