# code-review-opencode — Public `/code-review` ports — reference catalog

> **Naming:** this project is `code-review-opencode`; its command is
> `/code-review-opencode`. Mentions of `/code-review` in this document name
> Claude Code's original command.

Surveyed **2026-11-11** against Claude Code **v2.1.318** and this
reconstruction's `max` path.

This is a reference catalog, not a recommendation. It records the public
ports and adjacent multi-agent reviewers that were consulted while
reconstructing `/code-review`, what each one actually implements, and what
this project adopted or rejected. Features are as claimed by each project's
README, `SKILL.md`, or config; this is a documentation survey, not a code
audit or an execution test.

## How to read this

- **Max port** — a port of Claude Code's local `max` prompt/pipeline.
- **Ultra-style** — a project that explicitly targets `/code-review ultra`
  or copies its surface (fleet, verification, worktree, severity).
- **Adjacent** — a multi-agent reviewer with a different architecture that
  informed the design but is not a port of the reference command.
- **Ultra feature** here means the substantive parts of ultra, not just
  "runs several agents": execution-backed verification, an isolated
  full-repo workspace, `pre_existing` classification, the `bugs.json`
  contract, the `finding → verifying → synthesizing` progress protocol, and
  the async cloud lifecycle.

## Quick map

| Project | Kind | Effort coverage | Verification | Sweep | Report cap | Execution | Ultra features |
|---|---|---|---|---|---|---|---|
| [`ttxs69/code-review-codex`](https://github.com/ttxs69/code-review-codex) | Codex max port | `max` only | 1 verifier, 3-state | Yes | 15 | No | None |
| [`fyeeme/pi-packages/pi-review`](https://github.com/fyeeme/pi-packages/tree/main/pi-review) | Pi max port | `low`–`max` | 1 verifier; grouped at `xhigh`/`max` | Yes at `xhigh`/`max` | 15 default; 32 with `all` | No | None |
| [`cogine-ai/local-ultra-review`](https://github.com/cogine-ai/local-ultra-review) | Ultra-style Claude skill | `light` / `deep` / `max` | Verifier with `pre_existing` | No explicit sweep | 20 findings / 5 nits | Optional (`run_tests: auto`) | Partial: worktree, `pre_existing`, proof, GitHub posting |
| [`grandamenium/local-ultrareview`](https://github.com/grandamenium/local-ultrareview) | Ultra surface copy | None | Synthesis only | No | None | No | None |
| [`adamjgmiller/adamsreview`](https://github.com/adamjgmiller/adamsreview) | Multi-stage Claude Code + Codex peer | Codex effort levels | Validation gates | No | Not documented | No | None |
| [`ctxr-dev/skill-code-review`](https://github.com/ctxr-dev/skill-code-review) | Backend-agnostic FSM | Risk-tiered | Neutral ranker | No | None | No | None |
| [`vikingmute/review-forge`](https://github.com/vikingmute/review-forge) | Cross-client workflow | None | Independent verify | No | None | Tests after fixes | None |
| [`shinpr/pr-review-skill`](https://github.com/shinpr/pr-review-skill) | Claude/Codex PR plugin | None | Reviewer agents + quality profile | No | Severity filter | No | None |
| [`openai/codex` built-in](https://github.com/openai/codex/blob/main/.codex/skills/code-review/SKILL.md) | Codex-native orchestrator | `xhigh` reasoning | One subagent per skill | No | Unlimited | No | None |
| [`anthropics/claude-code` plugin](https://github.com/anthropics/claude-code/tree/main/plugins/code-review) | Historical 4-agent plugin | None | Confidence score ≥ 80 | No | None | No | None |

## Max ports

### `ttxs69/code-review-codex`

**What it is.** A Codex port of `pi-code-review-max`, which itself adapts
`code-review-max`. The README says the pipeline is unchanged; only the
packaging, agent-dispatch idiom (`spawn_agent` vs the Agent tool), the
instruction filename (`AGENTS.md` vs `CLAUDE.md`), and the comment footer
differ.

**What it implements.**

- 10 finder angles: 5 correctness (A–E), 3 cleanup (reuse, simplification,
  efficiency), 1 altitude, 1 conventions.
- Each finder surfaces up to 8 candidates.
- One verifier per deduped candidate, returning `CONFIRMED` / `PLAUSIBLE` /
  `REFUTED`; recall mode keeps anything non-`REFUTED`.
- One gap-sweep subagent, up to 8 additional findings.
- 15-finding cap, ranked most-severe first.
- PR targets post via `gh pr comment`; non-PR targets return a JSON array.

**What it does differently.**

- Before posting a PR comment it filters linter/typechecker issues,
  pre-existing issues, pedantic nits, and issues on unchanged lines. Those
  filters are from the older official `anthropics/claude-code` plugin, not
  the v2.1.318 command prompt; the JSON output still contains them.

**Ultra features adopted.** None. No execution, no worktree, no
`pre_existing` severity, no `bugs.json`, no progress protocol, no async
lifecycle.

**Relevance.** Confirms the max pipeline is portable across agent hosts.
Its PR-comment filters were explicitly rejected by this reconstruction
because they are not in the reference command.

### `fyeeme/pi-packages/pi-review`

**What it is.** A close port of Claude Code's local `/code-review` for the
`pi` agent, packaged as skills + prompts + 12 role agents (finder A–E,
cleaner reuse/simplification/efficiency, altitude, conventions, verifier,
gap-hunter).

**What it implements.**

- Effort split: `low` / `medium` / `high` run one pass in the main session;
  `xhigh` / `max` fan out through a provider-bound `subagent` tool.
- `xhigh` / `max` keep the quad tuple
  `{correctnessAngles, perAngle, maxFindings, sweep}`, grouped-by-location
  independent verification, and the gap-hunt.
- Finder budget at `xhigh` / `max`: `ceil(changed_lines / 150)` clamped to
  2–8 finder agents.
- `review_report` structured findings sink: Markdown back to the
  conversation plus JSON under `<cwd>/.pi/review/` for CI, `--fix`, and
  `--comment`.
- `--max-findings all` lifts the numeric cap, but a single report is
  hard-capped at 32; `review_report` truncates and stamps the report past
  that.
- `REVIEW.md` injection from the **base** version (`@{upstream}`, then
  `main`, then the worktree) as "Repository review instructions." The
  README explicitly calls this a port of the CC cloud Code Review feature.
- `--loop` on single-pass levels drives fix → re-review rounds (default 3).
- `/code-simplify` chaining after a review, gated on runtime-surface diffs
  and no further user instruction.

**Ultra features adopted.** None of ultra's execution, worktree,
`pre_existing`, `bugs.json`, or progress protocol. It does adopt the
managed Code Review `REVIEW.md` feature, which is a different product
surface.

**Relevance.** The closest public port of the local `max` / `xhigh`
behavior. Its `REVIEW.md` injection and 32-cap match the managed service /
`ReportFindings` path, not the local reference command; this reconstruction
rejected the `REVIEW.md` injection and kept the 32 cap only for the typed
tool.

## Ultra-style local ports

### `cogine-ai/local-ultra-review`

**What it is.** A Claude skill that explicitly runs an "Ultra Review style"
local review. It is read-only: no edits, commits, pushes, or fixes.

**What it implements.**

- Modes: `light` (3 lenses), `deep` (default, 5 lenses), `max` (broader).
- Isolated detached worktree under
  `.local-ultra-review/worktrees/<session-id>/`; applies staged and
  unstaged tracked changes; does not copy secrets; network disabled by
  default.
- Phase 4 impact map (no findings), then five reviewer lenses:
  correctness/regression, security/privacy, integration/API contract,
  state/concurrency/migration/rollback, tests/verification.
- Verifier classifies each candidate as `confirmed`, `false_positive`,
  `pre_existing`, or `needs_manual_review`. A confirmed finding must have a
  real file/line, code support, a concrete failure scenario, evidence, a
  targeted test/command/typecheck/static check/static reasoning path, a
  base check, and provenance/best-fix/refactor/proof/risk.
- Outputs `report.md`, `findings.json`, `candidates.jsonl`,
  `verification.jsonl`, `review-bundle.json`, and logs. GitHub summary or
  review posting is opt-in.

**Config defaults.**

```yaml
mode: deep
default_base: origin/main
include_uncommitted: true
include_untracked: false
max_reviewers: 5
max_findings: 20
max_nits: 5
run_tests: auto
network: disabled
copy_secrets: false
cleanup_worktree: true
output_dir: .local-ultra-review
worktree_dir: .local-ultra-review/worktrees
large_file_limit_bytes: 200000
max_patch_chars_per_file: 60000
destructive_actions: false
```

**Ultra features adopted.** The closest match in public: isolated worktree,
5-lens fleet, `pre_existing` classification, proof requirements, optional
test execution, and GitHub posting. It does **not** have the Bughunter
fleet/budgets, the exact `bugs.json` array, the
`finding → verifying → synthesizing` progress protocol, or the async cloud
lifecycle.

**Relevance.** The strongest evidence that ultra's *contract* can be
localized. It is a Claude skill, not a Codex port, and it is read-only, so
it does not replace the cloud sandbox's execution-backed verification.

### `grandamenium/local-ultrareview`

**What it is.** A self-described "local replication of /ultrareview" with
three Opus agents (correctness, security/performance, architecture),
synthesis, and an implementation-plan agent. Adds live per-agent logs and
asks whether to apply the plan.

**What it implements.** Parallel review → synthesis → implementation plan →
optional apply. No worktree, no execution, no `pre_existing`, no
`bugs.json`, no progress protocol.

**Ultra features adopted.** Only the surface: multiple agents and a
synthesis step. This is the clearest example of copying ultra's shape
without its verification substance.

**Relevance.** Not adopted. It confirms that "3 agents + synthesis" is not
what makes ultra different.

## Adjacent multi-agent reviewers

### `adamjgmiller/adamsreview`

**What it is.** A Claude Code plugin with a Codex CLI peer command. Six
commands: `review`, `codex-review`, `add`, `walkthrough`, `fix`, `promote`.

**What it implements.**

- Up to seven parallel lenses, a dedup pass, a cheap-then-deep validation
  gate, and an optional holistic Opus cross-cutting pass.
- Persistent JSON artifact, PR comment publish, and pre-computed auto-fix
  proposals.
- `:fix` dispatches per-group subagents, re-reviews the work with Opus,
  reverts regressions, and commits the survivors.
- `:add` injects externally sourced findings (including a cloud
  `/ultrareview` paste) into the existing artifact, deduped and validated.
- `--ensemble` adds a Codex CLI pass and a PR bot-comment scrape.

**Ultra features adopted.** None of ultra's execution, worktree,
`pre_existing`, or `bugs.json`. It adopts the *verification + fix-loop*
ideas, and its fix loop is stronger than ultra's one-pass `--fix` because
it re-reviews and reverts regressions.

**Relevance.** Useful reference for a post-review fix loop. Not adopted
here because the reference `--fix` is a single apply pass.

### `ctxr-dev/skill-code-review`

**What it is.** A backend-agnostic 19-state FSM reviewer that runs on
Claude, Codex, Cursor, or raw Anthropic/OpenAI APIs.

**What it implements.**

- 479 leaf reviewers in a 26-category taxonomy; a diff activates only the
  relevant leaves.
- 100% changed-file coverage through a parallel specialist fan-out.
- Deterministic dedup (location + embedding) and a neutral ranker that
  scores defect confidence and marks a `primary` set.
- Eight release gates and a `GO` / `CONDITIONAL` / `NO-GO` verdict.
- Benchmarked on `withmartian/code-review-benchmark` (5-PR pilot: recall
  0.73, precision 0.53, F1 ~0.62).

**Ultra features adopted.** None. It is a different architecture, not a
port of the Claude Code prompt. No execution-backed verification.

**Relevance.** A useful benchmark-driven alternative. Its embeddings and
neutral ranker were rejected here because they are not in the reference;
the semantic synthesizer already covers the judgment.

### `vikingmute/review-forge`

**What it is.** A cross-client Agent Skill for structured, auditable review
workflows: `review`, `synthesize`, `fix`, `verify`.

**What it implements.**

- One model-specific review file per perspective; synthesis into a fix
  checklist; checkboxes as the human approval boundary.
- Fixes only approved items; requires tests after fixes unless blocked and
  documented; independent verification when possible.
- Artifacts under `code_review/<feature>/` (`codex.md`, `opencode.md`,
  `cursor.md`, `summary.md`, `fix-plan.md`, `verify.md`, `status.md`).

**Ultra features adopted.** None of ultra's execution/workspace/severity
contract. It does require tests after fixes and an independent verify pass,
which is adjacent to ultra's verification goal.

**Relevance.** Process workflow, not a max port. Not adopted.

### `shinpr/pr-review-skill`

**What it is.** A Claude Code and Codex plugin for reviewing GitHub pull
requests with reviewer agents over a repeatable PR snapshot.

**What it implements.**

- Context collector → reviewer agent(s) → structured findings → comment
  publisher.
- Severity `must` / `should` / `nit`; posting filter; quality profiles
  derived from repository sources.
- Claude and Codex reviewer engines; combined JSON validated against a
  review schema; read-only reviewer.

**Ultra features adopted.** None of ultra's execution, worktree,
`pre_existing`, or `bugs.json`. It has a severity vocabulary and PR
posting, but not ultra's verification.

**Relevance.** PR-integration reference, not a max port.

### `openai/codex` built-in `code-review`

**What it is.** Codex's own orchestrator skill: use subagents to review
code using all `code-review-*` skills other than the orchestrator; one
subagent per skill; pass the full skill path; use `xhigh` reasoning.

**What it implements.** Returns every issue from every subagent, with an
unlimited number of findings, as raw Markdown. Adds a `code-reviewed` label
when the PR owner runs it; no GitHub comments unless explicitly asked.

**Ultra features adopted.** None. No verification, sweep, severity schema,
execution, or progress protocol.

**Relevance.** Shows Codex's native approach is "one subagent per skill,
unlimited findings," which is not the same as Claude's max pipeline.

### `anthropics/claude-code` plugin `code-review` (historical)

**What it is.** The older official plugin, not the v2.1.318 command. Four
agents: two `CLAUDE.md` compliance agents, one bug detector, one
git-history analyzer. Each issue gets a 0–100 confidence score; issues
below 80 are filtered; findings post as PR comments.

**Ultra features adopted.** None.

**Relevance.** The Codex port's PR filters (linter, pre-existing, nitpick,
unchanged lines) come from this older design, not from the current
`/code-review` command. This reconstruction deliberately does not reproduce
it.

## Feature matrix

Values reflect the project's own documentation. `Optional` and `Not specified`
are used where the docs do not make a hard claim.

| Project | Effort levels | Finders | Verifier | Sweep | Cap | `--fix` | `--comment` | Guidance | Execution | `pre_existing` | `bugs.json` | Progress | Worktree | Async |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `ttxs69/code-review-codex` | `max` | 10 angles | 3-state, 1 vote | Yes | 15 | No | Yes (PR) | `AGENTS.md` | No | No | No | No | No | No |
| `fyeeme/pi-review` | `low`–`max` | 10 angles | 3-state; grouped at `xhigh`/`max` | Yes at `xhigh`/`max` | 15 / 32 | Yes | Yes | `REVIEW.md` (base) | No | No | No | No | No | No |
| `cogine/local-ultra-review` | `light`/`deep`/`max` | 3 / 5 / 5 (broader) | `confirmed`/`false_positive`/`pre_existing`/`manual` | No | 20 findings, 5 nits | No (read-only) | Yes (opt-in) | `REVIEW.md` (context) | Optional | Yes | No (`findings.json`) | Logs | Yes | No |
| `grandamenium/local-ultrareview` | None | 3 agents | Synthesis only | No | None | Via plan | No | No | No | No | No | Live logs | No | No |
| `adamsreview` | Codex `low`–`xhigh` | Up to 7 lenses | Validation gates | No | Not documented | Yes (loop) | Yes | `CLAUDE.md` | No | No | No (`artifact.json`) | Phase logs | No | No |
| `ctxr/skill-code-review` | Risk-tiered | 479 leaves | Neutral ranker | No | None | No | No | No | No | No | No (report JSON) | FSM states | No | No |
| `review-forge` | None | Per-perspective | Independent verify | No | None | Yes (approved) | No | Not documented | Tests after fixes | No | No (`status.md`) | No | No | No |
| `shinpr/pr-review-skill` | None | Reviewer agents | Quality profile | No | Severity filter | No | Yes (approved) | Quality profile | No | No | No (JSON findings) | No | No | No |
| `openai/codex` built-in | `xhigh` reasoning | One per skill | No | No | Unlimited | No | No | `AGENTS.md` | Not specified | No | No | No | No | No |
| `anthropics/claude-code` plugin | None | 4 agents | Confidence ≥ 80 | No | None | No | Yes | `CLAUDE.md` | No | No | No | No | No | No |

## What this project adopted

Cross-referenced with
[`CODE_REVIEW_RECONSTRUCTION_RESEARCH.md`](CODE_REVIEW_RECONSTRUCTION_RESEARCH.md)
§11.3 and
[`CODE_REVIEW_ORCHESTRATION_MAP.md`](CODE_REVIEW_ORCHESTRATION_MAP.md) §15.3.

- **Structured-output contract** (validator error, retry limit) from the
  Agent SDK / public ports. This is the platform equivalent of Claude
  Code's Agent output schema.
- **Per-role `steps` caps** (finder/sweep 20, verifier/synth 15) as the
  equivalent of the Agent tool's `maxTurns`.
- **Semantic synthesis** — the model-driven dedup/rank that matches the
  reference's Phase 2/4 judgment.
- **`/verify` follow-up** — the reference's after-review block, gated on a
  locally installed `verify` skill.
- **Grouped verification** for the `cc-workflow-2.1.221` compatibility
  mode, matching the pi port's grouped-by-location verifier.
- **Tolerant report normalization + artifact** from `pi-review`: invalid
  findings are dropped instead of rejecting the report, outcomes are
  coerced, the 32-entry cap records `truncated_from`, and a private
  `<CODE_REVIEW_REPORT_DIR>/<timestamp>-<uuid>.json` artifact records
  the run when the environment variable opts in. A normal review is read-only;
  `--json` stdout remains a bare array.
- **Diff/scope hardening** from `pi-review`: nearest-git-root and
  submodule path targets, the fresh-repo staged/unstaged ladder, git
  hook/fsmonitor/askpass suppression, `--end-of-options`, abort/timeout
  propagation, git-quoted path parsing, and the changed-file context
  package with per-file churn.
- **PR/comment efficiency**: one `gh pr diff` download and one
  `gh pr view --json files,additions,deletions` call per PR, bounded
  inline-comment posting, host routing from the origin remote, and
  checked-out branch-PR resolution.
- **Confirmed wf221 recall ladder**: the extracted wf221 source shows the
  grouped verifier using `VERDICT_LADDER + VERDICT_LADDER_RECALL`; the
  grouped verifier now matches it.

## What this project rejected

- **`REVIEW.md` injection.** The local `/code-review` follows `CLAUDE.md`
  and does not read `REVIEW.md`; that file configures the managed cloud
  Code Review service. The pi port's base-branch injection is a managed
  feature, not the local reference.
- **Codex-port PR filters** (linter, pre-existing, nitpick, unchanged
  lines). Not in the v2.1.318 command prompt; they belong to the older
  official plugin.
- **`/simplify` chaining.** The reference's after-review block is
  `/verify`, not `/simplify`.
- **Embeddings, neutral rankers, model pools, `confirmed_by`.** Not in the
  reference; the semantic synthesizer already covers the judgment.
- **Ultra surface copies.** Three agents plus a synthesis step is not
  ultra's differentiator. The substantive features are execution, a full
  workspace, `pre_existing`, and the `bugs.json` contract.

## What no public port has adopted

As of the survey date, no public port has adopted the substantive ultra
features as its default:

- **Execution-backed verification.** `cogine/local-ultra-review` has
  `run_tests: auto`, but its verifier still accepts static reasoning as
  proof and the skill is read-only. The cloud sandbox's required
  reproduction is not reproduced.
- **The Bughunter fleet and budgets.** Default 5 agents, 10-minute agent
  timeout, 22-minute total wall clock.
- **The exact `bugs.json` contract.** `file_path`, `start_line`,
  `end_line`, `severity` (`normal`/`nit`/`pre_existing`), `pr_comment`,
  `reasoning`; bare array; `<remote-review>` envelope.
- **The progress protocol.** `finding` / `verifying` / `synthesizing` with
  `bugs_found` / `bugs_verified` / `bugs_refuted`.
- **The async cloud lifecycle.** Background task, survives terminal close,
  stop/archive, no partial findings.

The ports are tracking the local `max` pipeline and the managed Code
Review features (`REVIEW.md`, severity, worktrees), not the ultra execution
layer.

The implementation plan for closing these gaps is
[`CODE_REVIEW_HARDENING_PLAN.md`](CODE_REVIEW_HARDENING_PLAN.md).

## Maintenance checklist

When re-surveying, check each project's README, `SKILL.md`, and config for:

1. Effort levels and whether `max` is a distinct path.
2. Finder count/angles and whether a finder budget is dynamic.
3. Verifier shape: 1-vote, 3-state, recall-biased, grouped, or adversarial
   quorum.
4. Sweep/gap-hunt presence.
5. Cap: 15, 32, unlimited, or a configured number.
6. `--fix` and `--comment` behavior, and whether fixes are re-verified.
7. `REVIEW.md` / `AGENTS.md` / `CLAUDE.md` injection and which revision it
   reads.
8. Execution: worktree, tests, repros, sandbox, network policy.
9. Finding schema: severity, `pre_existing`, `bugs.json`, `reasoning`.
10. Progress/async lifecycle.

Record the date and the commit or release examined. A README claim is not a
code audit; note when a feature is claimed but not verified in code.

## Sources

- [`ttxs69/code-review-codex`](https://github.com/ttxs69/code-review-codex)
- [`fyeeme/pi-packages/pi-review`](https://github.com/fyeeme/pi-packages/tree/main/pi-review)
  — package notes: <https://pi.dev/packages/@fyeeme/pi-review>
- [`cogine-ai/local-ultra-review`](https://github.com/cogine-ai/local-ultra-review)
- [`grandamenium/local-ultrareview`](https://github.com/grandamenium/local-ultrareview)
- [`adamjgmiller/adamsreview`](https://github.com/adamjgmiller/adamsreview)
- [`ctxr-dev/skill-code-review`](https://github.com/ctxr-dev/skill-code-review)
- [`vikingmute/review-forge`](https://github.com/vikingmute/review-forge)
- [`shinpr/pr-review-skill`](https://github.com/shinpr/pr-review-skill)
- [`openai/codex` built-in code-review skill](https://github.com/openai/codex/blob/main/.codex/skills/code-review/SKILL.md)
- [`anthropics/claude-code` plugin `code-review`](https://github.com/anthropics/claude-code/tree/main/plugins/code-review)
- Official local review docs: <https://code.claude.com/docs/en/code-review-local>
- Official ultrareview docs: <https://code.claude.com/docs/en/ultrareview>
