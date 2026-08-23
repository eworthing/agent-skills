# Provider Adapters — Reviewer Spawn (Step 3)

<!-- CANONICAL: the reviewer read-only allow-list and the reviewer-spawn profile live here.
     Other files MUST reference, not restate. -->

The two sections Step 3 needs from the provider adapters, split out of
[`provider-adapters.md`](provider-adapters.md) so the loop subagent does not reload the eight
sections belonging to Step -1, Step 0, the HALT_SUCCESS challenge, and main-agent setup. Everything
else — detection, loop-spawn and challenger-spawn profiles, the `panel_certification` manifest,
model overrides, skill-directory resolution — stays in the parent and is main-agent scoped.

## Reviewer read-only shell allow-list (uniform across providers)

The implementation reviewer (per `references/implementation-reviewer.md`) is strictly read-only. Where a provider's spawn flags can enforce no-write, they do; where the reviewer needs shell access for `git diff` and `cat`, the reviewer's prompt restricts shell to this allow-list:

```
cat, grep, rg, find, git diff, git show, git blame, git log, ls, head, tail, wc
```

Any shell command outside this list → reviewer returns `verdict: rejected` with `reason: 'tool out of scope: <command>'`. The reviewer does not attempt the command.

## Reviewer-spawn profile (Step 3 step 6)

The implementation reviewer must be read-only. Different providers achieve this differently. The contract is uniform: shell write/exec denied; shell read-only commands restricted to the allow-list above.

**Verdict is the final message — join before routing.** Because the reviewer is read-only it cannot persist its verdict to a file; the verdict travels only as the subagent's final message. Spawn it as a **synchronous join**: await completion and read the final-message JSON as the result. On harnesses where a completed subagent's final message is not surfaced as a tool result (async / background spawn), read it from the runtime's run record / transcript before routing — a missing tool-result from a reviewer that completed is not a transient failure. Same rule applies to the challenger ([Challenger-spawn profile](#challenger-spawn-profile-step-1-halt_success-challenge)). See [implementation-reviewer.md § Verdict delivery](implementation-reviewer.md) and [halt-verifier.md § Verdict delivery](halt-verifier.md).

### claude_code (verified 2026-05-09)

Spawn via the `Agent` tool:

```
Agent({
  description: "Implementation review for loop N",
  subagent_type: "general-purpose",
  model: "claude-sonnet-5",
  prompt: "<verbatim prompt template from references/implementation-reviewer.md>"
})
```

- **Default model**: `claude-sonnet-5`
- **Enforcement**: no enforcement gate available; the reviewer's prompt is the only read-only contract. The reviewer is instructed to use `Grep`, `Glob`, `Read` tools (not bash `cat`) for file reads, and to restrict `Bash` to the read-only shell allow-list.
- **Reviewer-permitted tools**: `Grep`, `Glob`, `Read`, `Bash` (restricted by prompt to the allow-list)

### codex (verified 2026-08-19)

```
codex exec --model gpt-5.6-luna -c model_reasoning_effort=xhigh --sandbox read-only --json '<prompt>'
```

- **Default model**: `gpt-5.6-luna` at `-c model_reasoning_effort=xhigh` (verdict-emitting role; the HALT_SUCCESS challenger reuses this profile and therefore this effort)
- **Enforcement**: `--sandbox read-only` (values `read-only|workspace-write|danger-full-access`) is a real gate — stronger than the prompt-only contract other providers fall back to.
- **Reviewer-permitted tools**: shell commands from the read-only allow-list above (other shell commands → reviewer rejects)

### opencode (verified 2026-08-19)

```
opencode run --model opencode-go/deepseek-v4-flash '<prompt>'
```

- **Default model**: `opencode-go/deepseek-v4-flash`
- **Enforcement**: there is **no `--read-only` flag**, and unknown flags are silently ignored — relying on one runs with write allowed. Set `permission` in `opencode.json`: `{"edit": "deny"}` (values `ask|allow|deny`). `OPENCODE_PERMISSION` carries the same shape, unverified.
- **Reviewer-permitted tools**: native `read`, `grep`, `glob`; shell restricted to the read-only allow-list

### unknown

No subagent. Reviewer logic runs inline in the main agent context with whatever tools the host provides. Main agent must vet the reviewer's verdict before accepting (the prompt-only contract is weaker without isolation). Document at top of `CURRENT_REVIEW.md` Implementation Review section: "reviewer ran inline; verdict requires manual confirmation".
