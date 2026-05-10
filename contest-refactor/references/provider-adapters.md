# Provider Adapters

Per-provider spawn syntax, tool permissions, and model defaults for the loop subagent and the implementation reviewer subagent.

The skill protocol is provider-agnostic. The only provider-specific surface is **how a subagent is spawned** and **how read-only constraints are enforced**. This file is the single source of truth for both.

Each section is dated `verified <YYYY-MM-DD>` so staleness is visible. When a provider's CLI flags drift, update this file only — the skill body references this file by section.

## Detection (read by SKILL.md Step -1 step 0.5)

The main agent detects the active provider from environment variables. Binary presence on PATH is **not** consulted (multiple binaries can be installed; only one runtime is active).

| signal | provider |
|---|---|
| `CLAUDECODE=1` | `claude_code` |
| `CODEX_HOME` non-empty AND `CLAUDECODE` unset | `codex` |
| `OPENCODE_SESSION` non-empty AND `CLAUDECODE` unset AND `CODEX_HOME` unset | `opencode` |
| 2+ provider env vars set simultaneously | error — require explicit `--provider <name>` flag from user |
| none of the above | `unknown` (fall back to inline mode; no Loop Isolation) |

User flag `--provider <name>` overrides detection unconditionally.

## Reviewer read-only shell allow-list (uniform across providers)

The implementation reviewer (per `references/implementation-reviewer.md`) is strictly read-only. Where a provider's spawn flags can enforce no-write, they do; where the reviewer needs shell access for `git diff` and `cat`, the reviewer's prompt restricts shell to this allow-list:

```
cat, grep, rg, find, git diff, git show, git blame, git log, ls, head, tail, wc
```

Any shell command outside this list → reviewer returns `verdict: rejected` with `reason: 'tool out of scope: <command>'`. The reviewer does not attempt the command.

## Loop-spawn profile (Step 0 onward)

The loop subagent runs the Critic / Architect / Execution loop. It must edit code (Step 3 step 1), run tests (Step 3 step 3), and commit (Step 3 step 9). No read-only restriction applies.

### claude_code (verified 2026-05-09)

Spawn via the `Agent` tool from the main agent:

```
Agent({
  description: "Loop N execution",
  subagent_type: "general-purpose",
  model: "claude-sonnet-4-6",
  prompt: "<verbatim prompt template from references/trust-model.md § Loop Isolation>"
})
```

- **Default model**: `claude-sonnet-4-6` (full canonical ID)
- **Permissions**: subagent inherits parent permissions (write + shell + test execution all allowed)
- **Resume**: not supported by Agent tool; each loop is a fresh subagent invocation. State flows via files (`CURRENT_REVIEW.md`, `findings_registry.json`, etc.)

### codex (verified 2026-05-09)

Spawn via subprocess:

```
codex exec --model gpt-5.4-mini --no-ask-user --output-format json '<prompt>'
# resume: codex exec --continue --model gpt-5.4-mini --no-ask-user --output-format json '<prompt>'
```

- **Default model**: `gpt-5.4-mini`
- **Permissions**: no `--deny-tool` for the loop — write, shell, and test execution all allowed
- **Resume**: `--continue` flag picks up the most recent session
- **Nested-spawn caveat**: a running codex session may not be able to spawn a child `codex exec` subprocess (host process model varies; sandboxes commonly block recursive CLI invocation). If the spawn returns nonzero, the binary is not on PATH for the subprocess, or the session has no shell tool available, **fall back to inline mode**: set `spawn_isolation: "inline"`, document at top of `CURRENT_REVIEW.md` "codex subprocess spawn unavailable; running inline", and rely on Continuation Discipline + G20 (per [SKILL.md § Continuation Discipline](../SKILL.md#continuation-discipline) and [validation.md § G20](validation.md)) to keep the run autonomous across loops. Do **not** silently emit a user-facing close-out after loop 1 — that's the failure mode G20 catches.

### opencode (verified 2026-05-09)

Spawn via subprocess:

```
opencode run --model deepseek-v4-flash '<prompt>'
# resume: opencode run --session <id> --model deepseek-v4-flash '<prompt>'
```

- **Default model**: `deepseek-v4-flash`
- **Permissions**: default mode (write allowed)
- **Resume**: `--session <id>` flag

### unknown

No subagent spawn available. Fall back to inline mode: the loop runs in the main agent's context. Loop Isolation is skipped; main agent absorbs the per-loop token cost. Document at top of `CURRENT_REVIEW.md`: "provider: unknown; running inline; Loop Isolation unavailable".

- **loop_model / reviewer_model recording**: when `provider == "unknown"`, record `loop_model: null` and `reviewer_model: null` in `CURRENT_REVIEW.json` (with `*_source: "default"`). Do not invent placeholder strings like `"inline-current-model"` or `"session-default"` — the model identity is genuinely unknown and the schema treats null as the canonical "no provider-introspectable model" value. G19 admits null only when `provider == "unknown"`; for known providers, null is a violation.

## Reviewer-spawn profile (Step 3 step 6)

The implementation reviewer must be read-only. Different providers achieve this differently. The contract is uniform: shell write/exec denied; shell read-only commands restricted to the allow-list above.

### claude_code (verified 2026-05-09)

Spawn via the `Agent` tool:

```
Agent({
  description: "Implementation review for loop N",
  subagent_type: "general-purpose",
  model: "claude-sonnet-4-6",
  prompt: "<verbatim prompt template from references/implementation-reviewer.md>"
})
```

- **Default model**: `claude-sonnet-4-6`
- **Enforcement**: no enforcement gate available; the reviewer's prompt is the only read-only contract. The reviewer is instructed to use `Grep`, `Glob`, `Read` tools (not bash `cat`) for file reads, and to restrict `Bash` to the read-only shell allow-list.
- **Reviewer-permitted tools**: `Grep`, `Glob`, `Read`, `Bash` (restricted by prompt to the allow-list)

### codex (verified 2026-05-09)

```
codex exec --model gpt-5.4-mini --deny-tool=write,memory --no-ask-user --output-format json '<prompt>'
```

- **Default model**: `gpt-5.4-mini`
- **Enforcement**: `--deny-tool=write,memory` blocks file writes and persistent memory. **Shell is allowed** (denying shell would block `git diff` and the inspection commands the reviewer needs); the reviewer's prompt restricts shell to the read-only allow-list.
- **Reviewer-permitted tools**: shell commands from the read-only allow-list above (other shell commands → reviewer rejects)

### opencode (verified 2026-05-09)

```
opencode run --model deepseek-v4-flash --read-only '<prompt>'
```

- **Default model**: `deepseek-v4-flash`
- **Enforcement**: `--read-only` mode flag enforces no writes globally. Shell still permitted; reviewer's prompt restricts to the read-only allow-list for cleanliness.
- **Reviewer-permitted tools**: OpenCode native `read`, `grep`, `glob`; shell restricted to the read-only allow-list

### unknown

No subagent. Reviewer logic runs inline in the main agent context with whatever tools the host provides. Main agent must vet the reviewer's verdict before accepting (the prompt-only contract is weaker without isolation). Document at top of `CURRENT_REVIEW.md` Implementation Review section: "reviewer ran inline; verdict requires manual confirmation".

## Model overrides

Two override paths, applied in this precedence (higher wins):

1. **User flag** on `/contest-refactor` invocation:
   - `--loop-model <id>` overrides loop-spawn default
   - `--reviewer-model <id>` overrides reviewer-spawn default
2. **Environment variable**:
   - `CONTEST_REFACTOR_LOOP_MODEL=<id>` overrides loop-spawn default
   - `CONTEST_REFACTOR_REVIEWER_MODEL=<id>` overrides reviewer-spawn default

Recorded in `CURRENT_REVIEW.json` as `loop_model_source` and `reviewer_model_source` ∈ {`default`, `env_override`, `user_flag`}.

## When to upgrade the model

The default per-provider models (Sonnet on Claude Code, gpt-5.4-mini on Codex, deepseek-v4-flash on OpenCode) are tuned for typical loop work on small-to-medium codebases. On codebases >100K LOC or with deep architectural complexity (heavy concurrency, large state machines, cross-module ownership puzzles), Step 1 critic may need a stronger model. Upgrade via:

- Claude Code: `--loop-model claude-opus-4-7`
- Codex: `--loop-model gpt-5.4` (full, not mini)
- OpenCode: `--loop-model deepseek-v4`

The reviewer subagent rarely needs upgrading — verifying a small diff against three checks is well within the small-tier models.

## Token cost

This file (~150 lines, ~5K tokens) is loaded **once per main-agent invocation** (Pre-Step-0 in the Reference Load Matrix), not per loop. Per-loop overhead is negligible.
