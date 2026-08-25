# Provider Adapters

Per-provider spawn syntax, tool permissions, and model defaults for the loop subagent and the implementation reviewer subagent.

The skill protocol is provider-agnostic. The only provider-specific surface is **how a subagent is spawned** and **how read-only constraints are enforced**. This file is the single source of truth for both.

Each section is dated `verified <YYYY-MM-DD>` so staleness is visible. When a provider's CLI flags drift, update this file only — the skill body references this file by section.

## Contents

- [Detection (read by SKILL.md Step -1 step 0.5)](#detection-read-by-skillmd-step--1-step-05)
- [Reviewer read-only shell allow-list (uniform across providers)](#reviewer-read-only-shell-allow-list-uniform-across-providers)
- [Loop-spawn profile (Step 0 onward)](#loop-spawn-profile-step-0-onward)
- [Reviewer-spawn profile (Step 3 step 6)](#reviewer-spawn-profile-step-3-step-6)
- [panel_certification capability manifest (v5 panel authorization)](#panel_certification-capability-manifest-v5-panel-authorization)
- [Model overrides](#model-overrides)
- [When to upgrade the model](#when-to-upgrade-the-model)
- [Token cost](#token-cost)

## Detection (read by SKILL.md Step -1 step 0.5)

The main agent detects the active provider from environment variables. **This table is the single source of truth for the predicates** — no other file restates them. Detection reads **session-scoped** variables, the ones a live run sets per session. A config or path override (`CODEX_HOME`) never detects: it is unset on a default install and stays set when the tool is merely installed. Binary presence on PATH is **not** consulted (multiple binaries can be installed; only one runtime is active).

| signal | provider |
|---|---|
| `CLAUDECODE=1` | `claude_code` |
| `CODEX_SESSION_ID` or `CODEX_THREAD_ID` non-empty AND `CLAUDECODE` unset | `codex` |
| any `OPENCODE_*` var non-empty (e.g. `OPENCODE_PID`) AND `CLAUDECODE` unset AND both codex session vars unset | `opencode` |
| 2+ of the trigger variables above set simultaneously | error — require explicit `--provider <name>` flag from user |
| none of the above | `unknown` (fall back to inline mode; no Loop Isolation) |

`CLAUDECODE` matches **exactly `1`**, never a `CLAUDE_CODE_*` prefix. A live codex session was observed carrying `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` and `GEMINI_CLI_IDE_*` (2026-08-23): provider variables leak across sessions, so a prefix match on this family misdetects. Only the trigger variables named above count toward the 2+ error row.

User flag `--provider <name>` overrides detection unconditionally.

## Reviewer read-only shell allow-list (uniform across providers)

Moved — canonical in [`provider-adapters-reviewer.md`](provider-adapters-reviewer.md#reviewer-read-only-shell-allow-list-uniform-across-providers). Step 3 loads that file; this one is main-agent scoped.

## Loop-spawn profile (Step 0 onward)

The loop subagent runs the Critic / Architect / Execution loop. It must edit code (Step 3 step 1), run tests (Step 3 step 3), and commit (Step 3 step 11). No read-only restriction applies.

### claude_code (verified 2026-05-09)

Spawn via the `Agent` tool from the main agent:

```
Agent({
  description: "Loop N execution",
  subagent_type: "general-purpose",
  model: "claude-sonnet-5",
  prompt: "<verbatim prompt template from references/trust-model.md § Loop Isolation>"
})
```

- **Default model**: `claude-sonnet-5` (full canonical ID; the host `sonnet` tier — was `claude-sonnet-4-6` until 2026-07-13)
- **Permissions**: subagent inherits parent permissions (write + shell + test execution all allowed)
- **Resume**: not supported by Agent tool; each loop is a fresh subagent invocation. State flows via files (`CURRENT_REVIEW.md`, `findings_registry.json`, etc.)

### codex (verified 2026-08-19)

Spawn via subprocess:

```
codex exec --model gpt-5.6-luna -c model_reasoning_effort=high --sandbox workspace-write --json '<prompt>'
# resume: codex exec --continue --model gpt-5.6-luna -c model_reasoning_effort=high --sandbox workspace-write --json '<prompt>'
```

- **Default model**: `gpt-5.6-luna`
- **Reasoning effort**: `high`, pinned on the command line — see [Reasoning effort](#reasoning-effort)
- **Permissions**: `--sandbox workspace-write` — write, shell, and test execution all allowed
- **Resume**: `--continue` flag picks up the most recent session
- **Nested-spawn caveat**: a running codex session may not be able to spawn a child `codex exec` subprocess (host process model varies; sandboxes commonly block recursive CLI invocation). If the spawn returns nonzero, the binary is not on PATH for the subprocess, or the session has no shell tool available, **fall back to inline mode**: set `spawn_isolation: "inline"`, document at top of `CURRENT_REVIEW.md` "codex subprocess spawn unavailable; running inline", and rely on Continuation Discipline + G20 (per [SKILL.md § Continuation Discipline](../SKILL.md#continuation-discipline) and [validation.md § G20](validation.md)) to keep the run autonomous across loops. Do **not** silently emit a user-facing close-out after loop 1 — that's the failure mode G20 catches.

### opencode (verified 2026-08-24)

Three-tier spawn preference, tried in order. **The tier actually used determines the recorded `{model, model_source, isolation}` triple for that role** — the artifact records what the spawn did, never what the agent infers afterwards. Loop, reviewer, and challenger roles each record their own attribution independently; a challenger spawned via one tier does not inherit another role's recorded values.

**Tier 1 — native host task**, preferred when the session exposes a task/subagent tool. The task type is exactly `general`. The hyphenated claude_code task-type name from [claude_code § Loop-spawn profile](#claude_code-verified-2026-05-09) above **does not exist on opencode** — a run that tries that name gets an invalid-type error and must fall back to the correct bare `general` type, not retry the invalid one. Native tasks are created with `model=undefined` and inherit the parent session's model — there is no way to pin a different model for the child task at this tier. Record `spawn_isolation: "subagent"`, `loop_model` = the parent session's model identity (not the provider-adapters default), and `loop_model_source: "inherited"`.

**Tier 2 — subprocess**, when no native task tool is available:

```
opencode run --model opencode-go/deepseek-v4-flash '<prompt>'
# resume: opencode run --session <id> --model opencode-go/deepseek-v4-flash '<prompt>'
```

- **Default model**: `opencode-go/deepseek-v4-flash` — `--model` takes `provider/model`; a bare id is invalid
- **Permissions**: default mode (write allowed)
- **Resume**: `--session <id>` flag
- Record `spawn_isolation: "subagent"`, `loop_model` = the `--model` value passed, and `loop_model_source` per [Model overrides](#model-overrides) (`user_flag` / `env_override` / `default`).

**Tier 3 — inline fallback**, when neither tier works. MUST record `spawn_isolation: "inline"` and document at top of `CURRENT_REVIEW.md`, mirroring the codex nested-spawn caveat above. An inline claim that the subprocess was tested and found unavailable is only legitimate if `opencode run` was actually invoked and failed — asserting "subprocess unavailable" without attempting it is a fabricated cause, not an honest fallback. `loop_model` = whatever model the primary session is actually running under, if introspectable, else `null`; `loop_model_source: "inherited"`.

### unknown

No subagent spawn available. Fall back to inline mode: the loop runs in the main agent's context. Loop Isolation is skipped; main agent absorbs the per-loop token cost. Document at top of `CURRENT_REVIEW.md`: "provider: unknown; running inline; Loop Isolation unavailable".

Copilot CLI and Gemini Antigravity CLI (AGY) currently use this profile because neither has a dedicated contest-refactor adapter or provider enum.

- **loop_model / reviewer_model recording**: when `provider == "unknown"`, record `loop_model: null` and `reviewer_model: null` in `CURRENT_REVIEW.json` (with `*_source: "default"`). Do not invent placeholder strings like `"inline-current-model"` or `"session-default"` — the model identity is genuinely unknown and the schema treats null as the canonical "no provider-introspectable model" value. G19 admits null only when `provider == "unknown"`; for known providers, null is a violation.

## Reviewer-spawn profile (Step 3 step 6)

Moved — canonical in [`provider-adapters-reviewer.md`](provider-adapters-reviewer.md#reviewer-spawn-profile-step-3-step-6).

## Challenger-spawn profile (Step-1 HALT_SUCCESS challenge)

The HALT_SUCCESS challenger ([references/halt-verifier.md](halt-verifier.md)) is **read-only with identical enforcement to the Reviewer-spawn profile above** — only the prompt differs (`halt-verifier.md`, not `implementation-reviewer.md`). Reuse each provider's reviewer-spawn flags, read-only allow-list, and the same model tier as the loop subagent (fresh eyes need equal capability). The one structural difference: the challenger is spawned by the **main orchestrator**, not the loop subagent, so the verdict is independent of the Critic that produced the scorecard. On `unknown` provider the challenger runs inline and main must vet it ("challenger ran inline; verdict requires manual confirmation") — but a terminal `HALT_SUCCESS` still requires the recorded held challenge (G32); an inline-unavailable challenger fails closed to `verification_blocked`.

**Why same-tier (not a bigger same-family model) — measured 2026-06-27.** Independence here comes from *who spawns it* (main, not the Critic) and *fresh context*, not from a different Claude. A disagreement probe found Opus and Sonnet agree **9/10** on the hardest cross-module defects (same training family → correlated blind spots), and on the one differing case Opus was *more lenient* — so upgrading the challenger to a bigger same-family model buys little independence and isn't the right lever. Genuine challenger diversity would need a **different family** (a Codex/Gemini challenger breaking a Claude Critic's claim) — untested, structural, recorded as a future direction in [evals/reviewer-model-experiment.md](../evals/reviewer-model-experiment.md). Until then, same-tier-different-spawner is the deliberate, evidence-checked default.

### panel_certification capability manifest (v5 panel authorization)

Default-deny. SSOT is `canon/panel-certification.toml`, keyed by **provider + exact
model + `protocol_digest`** — a profile is authorized only when all three match a
recorded pass. Checked via
`python3 "$SKILL_DIR/scripts/_panel_capability.py" check --provider <p> --model <m>`
→ `{"emit": "v5"|"v4", "reason", "protocol_digest"}`; missing, stale-digest, or
never-recorded profiles emit `v4`.

`protocol_digest` is `sha256` over 10 length-prefixed inputs, one canonical
algorithm — `compute_protocol_digest` in
[`scripts/_panel_gate_adapter.py`](../scripts/_panel_gate_adapter.py) — shared by
both gate evidence and runtime lookup so the two cannot drift independently:
(1) `halt-verifier.md` full file bytes, (2) the panel routing-precedence table +
staged-launch rules, (3) the break-normalization transaction steps, (4) the v5
`halt_success_challenge` schema block, (5) the gate thresholds (panel count,
per-panel break requirement, restraint all-hold requirement), (6) `C_max` for the
profile, (7) the challenger spawn profile + tool allow-list for that provider,
(8) the budget-enforcement configuration + the adapter implementing it, (9) the
gate scenario + assertion definitions, (10) the grading adapter's own bytes. Any
behavior-affecting change invalidates every recorded pass.

Hard protocol disablement is recorded **separately**, as an explicit
`unsupported_digests` list, independent of the creation-capability entries — a
digest on that list routes to the fresh v4 Critic path even if it would otherwise
still be executable (rollback-resume; see
[resume-detection.md § Resume Precedence Matrix row 6b](resume-detection.md#resume-precedence-matrix)).

Recording an entry requires a gate **PASS** at the exact digest, evidenced in
[`evals/panel_gate_results.json`](../evals/panel_gate_results.json) (see
[`plans/rec1-panel-certification.md` § Pre-enforcement gate](../plans/rec1-panel-certification.md#pre-enforcement-gate)).

**Zero entries are recorded today.** The only measured profile — `claude_code`
in-session `Agent` tool — cannot stop a member before it crosses `C_max` (budget
enforcement is post-hoc discard, not preemptive) and does not natively report
token usage, so no capability entry may be recorded for it; every profile
therefore emits v4, and the machinery is live while the capability is not.

## Helper-spawn profile (read-only analysis sidecars)

The loop subagent MAY spawn ≤2–3 read-only helper sub-agents for bounded analysis (interpret an `audit_*` output, grep public surface, summarize churn). Unlike the reviewer and challenger, a helper emits **no verdict** — it returns candidate evidence the loop subagent re-derives and synthesizes, and the Critic/reviewer do the real judgment — so nothing the loop commits is gated on a helper. That makes the helper the one role where the **cheapest** model is the right default.

- **Default model (helper tier):** claude_code `claude-haiku-4-5`; codex `gpt-5.6-luna` at `-c model_reasoning_effort=medium`; opencode `opencode-go/deepseek-v4-flash` (codex/opencode are already at their cheapest tier). Read-only enforcement is the same as the reviewer-spawn profile.
- **Evidence (2026-06-27):** on bounded read-only analysis, `claude-haiku-4-5` matched `claude-sonnet-4-6` exactly — same real concerns surfaced, same look-alikes dismissed, zero misleading output (3/3 tasks). See [evals/reviewer-model-experiment.md § Helpers](../evals/reviewer-model-experiment.md). This is the inverse of the reviewer result: haiku's weakness is open-ended *judgment* (where it over-rejects), and a helper makes no judgment call.
- **Not recorded** in `CURRENT_REVIEW.json` — helpers are ephemeral and off the audit/gate path, so there is no `helper_model` field or gate (deliberate low scope; nothing consumes it).

## Reasoning effort

Pinned per role on the spawn command line, never inherited. An unpinned spawn silently adopts the
operator's interactive `model_reasoning_effort` from `~/.codex/config.toml`, which is set for
chat sessions rather than autonomous loops — so the same artifact could be produced by a `low`
Critic on one machine and an `xhigh` Critic on another, with nothing in `CURRENT_REVIEW.json`
recording the difference. Pinning makes the run reproducible across machines.

| role | effort | why |
|---|---|---|
| loop subagent (Actor + Critic) | `high` | writes the scorecard and judges Meta-Rule-4 risk boundaries — the judgment every commit is gated on |
| implementation reviewer | `xhigh` | verdict-emitting; its rejection is the only thing standing between a bad loop and a commit |
| HALT_SUCCESS challenger | `xhigh` | verdict-emitting, and the last control before terminal success |
| helper sidecars | `medium` | emits no verdict; returns candidate evidence the Critic re-derives |

Codex syntax is `-c model_reasoning_effort=<level>`, levels `none|minimal|low|medium|high|xhigh`.
Owner-set 2026-08-23; the loop tier is a deliberate compromise between cost and the Critic's
judgment load, not a measured optimum — no effort-tier experiment has been run.

## Model overrides

Two override paths, applied in this precedence (higher wins):

1. **User flag** on `/contest-refactor` invocation:
   - `--premium-dry-run-model <id>` overrides loop-spawn default and forces invocation-scoped dry-run. It is mutually exclusive with `--loop-model`.
   - `--loop-model <id>` overrides loop-spawn default
   - `--reviewer-model <id>` overrides reviewer-spawn default
2. **Environment variable**:
   - `CONTEST_REFACTOR_PREMIUM_DRY_RUN_MODEL=<id>` overrides loop-spawn default and forces invocation-scoped dry-run.
   - `CONTEST_REFACTOR_LOOP_MODEL=<id>` overrides loop-spawn default
   - `CONTEST_REFACTOR_REVIEWER_MODEL=<id>` overrides reviewer-spawn default

Recorded in `CURRENT_REVIEW.json` as `loop_model_source` and `reviewer_model_source`, one of four values:

| value | meaning | set by |
|---|---|---|
| `user_flag` | a `--loop-model` / `--reviewer-model` / `--premium-dry-run-model` flag on the invocation chose the model | the operator, per-invocation |
| `env_override` | a `CONTEST_REFACTOR_*` environment variable chose the model | the operator's environment |
| `default` | no flag or env var was set; the adapter's documented per-provider default (this file's per-provider tables) was used | provider-adapters.md |
| `inherited` | the spawn mechanism adopted the parent/session model without an explicit choice — e.g., an opencode native host task, or an inline fallback with no model argument | the spawn mechanism itself |

Precedence when resolving a model **before** spawn: `user_flag` > `env_override` > `default`. `inherited` is not a rung on that ladder — it is not chosen among competing sources, it records that the spawn mechanism made no explicit choice at all (native opencode tasks always inherit; there is nothing to override to a different value at that tier). See [opencode § Loop-spawn profile](#opencode-verified-2026-08-24) for the concrete case.

### Premium model budget policy

Premium loop models are listed in `canon/premium-models.toml` (currently `claude-fable-5`). They are guarded because a full autonomous loop can spend the user's limited premium quota before the agent has proven the run is worth it.

The intended workflow is:

1. Run a bounded premium plan: `/contest-refactor --premium-dry-run-model claude-fable-5 --cap 1`.
2. Review the emitted `HALT_DRY_RUN` plan.
3. Re-invoke with the default model for execution, or explicitly authorize one premium loop with `/contest-refactor --loop-model claude-fable-5 --allow-premium-loop --cap 1`.

If a resolved `loop_model` is premium and the invocation is not dry-run, the main agent must stop before dispatch unless `--allow-premium-loop` is present. `--allow-premium-loop` is never a project config default; it is an invocation-only acknowledgement.

## When to upgrade the model

The default per-provider models (Sonnet on Claude Code, gpt-5.6-luna on Codex, opencode-go/deepseek-v4-flash on OpenCode) are tuned for typical loop work on small-to-medium codebases.

**Prefer the default; upgrading is a precaution, not a measured win (evidence, 2026-06-27).** The default-tier (Sonnet) Critic caught **5/5** cross-module / forces-dependent defects in the `principal_baseline` benchmark, and a focused re-check found Sonnet catches the **3 hardest** principal flags (consistency-boundary, abstraction-seam, process-owner) decisively. So upgrading the Critic to Opus shows **no measured recall benefit** on the tested corpus — there is nothing in it Sonnet misses for Opus to catch. Treat the upgrade as an *unmeasured precaution* for codebases beyond what that corpus exercises (very large >100K LOC, dense concurrency, large state machines), or when a run visibly stalls — not as a default reflex on "this feels complex." Reflexively upgrading to Opus burns tokens for a benefit that is, so far, unmeasured. (Full method + result: [evals/reviewer-model-experiment.md § Critic tier](../evals/reviewer-model-experiment.md).) If you do upgrade:

- Claude Code: `--loop-model claude-opus-4-8`
- Codex: `--loop-model gpt-5.6-sol` (full flagship, not the luna tier)
- OpenCode: `--loop-model deepseek-v4`

For the hardest critic runs on Claude Code — very large or architecturally dense codebases where even Opus leaves residual uncertainty — there is one tier above Opus: **Claude Fable 5** (`claude-fable-5`). It is the most capable option and the most expensive; reserve it for runs where an Opus critic has visibly struggled, not as a default. First use it through `--premium-dry-run-model claude-fable-5`; a full premium loop requires `--loop-model claude-fable-5 --allow-premium-loop --cap 1`. (No Fable-equivalent top tier is wired for Codex/OpenCode; their flagship upgrade targets above are the ceiling.)

The reviewer subagent **does not** go cheaper than its default and rarely needs upgrading: a 2026-06-27 measurement found dropping the Claude Code reviewer to `claude-haiku-4-5` regresses (haiku over-rejects legitimate single-adapter-seam / risk-evidence refactors — see [reviewer-model-experiment.md](../evals/reviewer-model-experiment.md)), while Opus is unnecessary for the bounded three-check verification. Sonnet is the measured floor. Model IDs are mutable; `scripts/_model_catalog_selftest.py` guards this list against drift (verified 2026-06-24).

## Skill-directory resolution

Helper scripts under `scripts/` (`dry-run.sh`, `purge.sh`, `audit-*.sh`) are invoked from the target repo's CWD via `bash "$SKILL_DIR/scripts/<name>.sh"`. The agent must resolve `$SKILL_DIR` once on first action of every invocation. Per-host mechanics:

| Provider | Resolution path | Notes |
|---|---|---|
| `claude_code` | The agent's skill-loader exports the absolute path of the loaded skill as session-scoped state. Read it directly. Falls back to `$HOME/.claude/skills/contest-refactor`. | Default install per agent-skills/CLAUDE.md is a symlink at `~/.claude/skills/contest-refactor` → repo. |
| `codex` | Skills under `$CODEX_HOME/skills/`. Compute `$SKILL_DIR="$CODEX_HOME/skills/contest-refactor"` if `$CODEX_HOME` set; else fall back to `$HOME/.codex/skills/contest-refactor`. | |
| `opencode` | Skills under `$HOME/.config/opencode/skills/`. Compute `$SKILL_DIR="$HOME/.config/opencode/skills/contest-refactor"`. no `OPENCODE_*` var encodes the install path; rely on the standard installation directory. | |
| `gemini` / `gemini-antigravity` | Skills under `$HOME/.agents/skills/` (shared community location) or `$HOME/.gemini/antigravity-cli/skills/` (Antigravity CLI). `$GEMINI_CONFIG_DIR` does not encode the install path; rely on standard directories. | |
| `copilot` | Skills under `$HOME/.agents/skills/` (shared community location) — same as Gemini CLI. | |
| `unknown` | Last-resort fallback chain in [resume-detection.md § Skill-script path resolution](resume-detection.md#skill-script-path-resolution). | |

The 5-path fallback chain (in order: `~/.claude` → `~/.codex` → `~/.config/opencode` → `~/.agents` → `~/.gemini/antigravity-cli`) is the universal escape hatch when provider-specific resolution fails. First existing path wins.

Per `agent-skills/CLAUDE.md` Installation section, every install path is a symlink back to the same repo (`/Users/Shared/git/agent-skills/contest-refactor/`), so whichever path resolves first points to the same `scripts/`.

If all 5 fallback paths fail, also try `./contest-refactor/scripts/<name>.sh` relative to CWD (covers repo-local checkouts). If that also fails, emit Purge Precondition-Error handoff per [halt-handoff.md § Purge Precondition-Error handoff](halt-handoff.md#purge-precondition-error-handoff) (the handoff covers any `scripts/*` invocation failure, not just purge).

## Token cost

This file (~1.8k words, ~2.4k heuristic tokens) is loaded in main-agent Step -1 for provider/model detection, then again during normal Step 3 loops for reviewer-spawn rules. Reviewer and challenger sidecars also read the relevant provider allow-list/profile. The cost is modest compared with `method.md`, `architecture-rubric.md`, and the selected lens, but it is not zero per loop.
