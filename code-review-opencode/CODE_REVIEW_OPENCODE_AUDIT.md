# code-review-opencode — OpenCode V2 Plugin Audit

> **Naming:** this project is `code-review-opencode`; its command is
> `/code-review-opencode`. Mentions of `/code-review` in this document name
> Claude Code's original command.

Audit date: **2026-11-12**. Target: the production plugin under
`.opencode/plugins/code-review-opencode/`. Reference behavior: Claude Code
**v2.1.318**, plus the current Claude Code local-review documentation.

## Method

This audit used the `deep-research` methodology: broad exploration of the
OpenCode V2 plugin surface, a deep dive into the official docs and OpenAPI
schema, validation against community guidance and the live runtime, then a
source audit of this plugin. Every reported defect was checked against the
current code and, where host behavior mattered, against a live OpenCode V2
server before it was changed.

### Sources

| Source | What it established |
|---|---|
| [OpenCode plugins](https://opencode.ai/docs/plugins/) | Discovery, configuration, local directory rules, reload behavior |
| [Plugin overview](https://opencode.ai/docs/build/plugins/) | `Plugin.define`, stable `id`, parts, server/TUI/GUI split |
| [Plugin server API](https://opencode.ai/docs/build/plugins/server/) | Transforms, tools, commands, sessions, storage, events, hooks |
| [Migrate plugins from V1](https://opencode.ai/docs/build/plugins/migrate-v1/) | V1 plugins do not run in V2; transforms are synchronous and replayable |
| [Commands](https://opencode.ai/docs/commands/) | Markdown/JSON command fields and execution rules |
| [Agents](https://opencode.ai/docs/agents/) | `mode`, `steps`, `permissions`, global vs project discovery |
| [Custom tools](https://opencode.ai/docs/custom-tools/) | Tool definitions and the V1/V2 distinction |
| [Permissions](https://opencode.ai/docs/permissions/) | Rule order, `allow`/`ask`/`deny`, agent rules |
| [Tools](https://opencode.ai/docs/tools/) | `context.signal`, plugin tool permission expectations |
| [JavaScript client](https://opencode.ai/docs/build/client/) | Session/event method shapes |
| [OpenAPI document](https://opencode.ai/docs/openapi.json) | `Command.Info`, `PromptInput`, `Session.CreateInput`, synthetic payloads |
| [Claude Code local review](https://code.claude.com/docs/en/code-review-local) | Reference flags, effort reuse, attachments, output contracts |
| [Claude Code review service](https://code.claude.com/docs/en/code-review) | Reference find/verify/rank/post model |
| [Flavio Copes — V2 plugin tutorial](https://flaviocopes.com/opencode-plugin/) | Synchronous transforms, JSON Schema inputs, V2 result shape |
| [OpenCode plugin guide (community)](https://gist.github.com/rstacruz/946d02757525c9a0f49b25e316fbe715) | V1 API caveats and migration pitfalls |
| [Hooks guide (community)](https://dev.to/einarcesar/does-opencode-support-hooks-a-complete-guide-to-extensibility-k3p) | V1 hook names and why they do not carry into V2 |

### Live probes

The audit used throwaway servers outside the repository:

1. A probe command logged the actual `CommandInvocation` prompt keys:
   `text`, `files`, `agents`, `skills` — no `model`, no `effort`.
2. `GET /api/command` returned only `name` and `description` for each command;
   the unsupported `argumentHint` field never appeared.
3. A real `/code-review-opencode low` invocation with a file attachment
   produced a user message containing the review prompt **and** the attached
   file, confirming the attachment fix.
4. The plugin loaded cleanly and the command returned HTTP 204.

## Best-practice checklist

| Area | Practice | Status |
|---|---|---|
| Entrypoint | V2 `Plugin.define({ id, setup })`, stable id, local `index.ts` | Pass |
| Transforms | Synchronous, cheap, replayable; no I/O in the callback | Pass |
| Tools | JSON Schema inputs, `{ content }` results, metadata, `context.signal` | Pass |
| Commands | Only documented fields; preserve `prompt` attachments; pass `delivery` | Fixed |
| Model/effort source | Read the session, not the command prompt | Fixed |
| Cancellation | Propagate `context.signal`; interrupt child sessions | Pass (tool path) |
| Storage | `ctx.storage`, plugin-scoped keys | Pass |
| State bounds | Cap per-session maps and outcome caches | Pass |
| Recursion guard | Block review children and their descendants | Pass |
| Cleanup | Return a cleanup function for timers/sessions | Residual |
| Permissions | Assert plugin-tool actions | Accepted risk |
| Output parity | Reference prompts, dispatch, schema, caps, ranking | Pass |
| Docs | Version requirement and current test behavior | Fixed |

## Findings

### F1 — Command path lost the session model and effort (fixed)

**Severity:** high for Claude-family parity, medium for non-Claude sessions.

OpenCode V2's `CommandInvocation` is:

```ts
{ sessionID, prompt: PromptInput, delivery: "steer" | "queue" }
```

`PromptInput` carries `text`, `files`, `agents`, and `skills`; it does **not**
carry the selected model or effort variant. The plugin command handler was
reading `prompt.model` and `prompt.effort`, which are always `undefined`. As a
result:

- `detectFamily(undefined)` always selected the `default` family. A Claude
  Sonnet 5 session therefore received the Opus-4.8/default high recipe instead
  of the Sonnet multi-agent recipe.
- `resolveEffort(..., undefined)` ignored the session's model variant. A
  session configured as `#max` ran with the remembered or medium default when
  the user typed no level.

**Fix:** `resolveAndRun` now resolves the parent session once (the caller may
pass `inv.session`; otherwise it calls `ctx.session.get`), derives
`sessionModel` and `sessionEffort`, and uses them for family dispatch, effort
fallback, and the child-session model. The command handler reads and passes the
session; the tool handler already had it and now passes it through, removing a
duplicate lookup.

**Parity:** this restores Claude Code's documented rule that a review with no
typed level uses the session's current effort, and restores the recovered
Claude family dispatch table. Non-Claude models still map to `default`.

### F2 — Command attachments were dropped (fixed)

**Severity:** medium (scope fidelity).

The command handler built every follow-up prompt with only `sessionID`, `text`,
and `delivery`. Files, agent mentions, and skill mentions supplied with the
command were discarded, so an attached file never reached an inline or
`--fix` review.

**Fix:** the handler now carries `prompt.files`, `prompt.agents`, and
`prompt.skills` onto the model-driven final turn. The original `mention`
offsets are removed because the command text is replaced by the recovered
review prompt; keeping the attachments without stale offsets is the
documented-safe behavior. The bare `--json` echo and the no-op completion
acknowledgement deliberately do not receive attachments.

**Verification:** a live `/code-review-opencode low` run with `note.txt`
attached produced a user message containing the review prompt and the file.

### F3 — `argumentHint` was not a V2 command field (fixed)

**Severity:** low.

The V2 `CommandDefinition` and `Command.Info` schemas expose `name`,
`description`, and `execute`; `Command.Info` has
`additionalProperties: false`. The live command list never returned
`argumentHint`. The field was dead data and a future strict host could reject
the registration.

**Fix:** removed it. The syntax remains in the command description, which is
the field OpenCode displays.

### F4 — A synthetic failure could drop a completed engine report (fixed)

**Severity:** low.

The `--json` fallback caught a failed `ctx.session.synthetic` call and fell
through to a constrained model turn. The normal engine-report path did not: a
transient synthetic failure would reject the command and lose a review that had
already completed.

**Fix:** the normal path now catches the synthetic failure and falls through to
the same constrained completion turn. Successful runs are unchanged.

### F5 — No plugin cleanup for in-flight reviews (residual)

**Severity:** low, lifecycle.

`setup` returns no cleanup function. A review can poll for a long time, wait
on child sessions, and create dozens of children. If the plugin is reloaded or
unloaded mid-review, those children and waits are not cancelled by the plugin
lifecycle. The runner does remove children on every normal exit path, and the
stall watchdog bounds genuinely stuck children, so this is a reload-time leak
rather than a steady-state one.

**Recommendation:** track active review `AbortController`s and return a cleanup
that aborts them, or at minimum interrupt and remove every id in
`reviewChildSessions` on unload. Not applied in this pass because it changes
reload semantics and needs a live reload test; it does not affect normal review
output.

### F6 — Internal git/gh actions do not assert OpenCode permissions (accepted)

**Severity:** low, security posture.

The `code_review` tool runs `git` and `gh` through `execFile` (argument arrays,
no shell) rather than through OpenCode's shell tool, so those commands are not
individually checked by OpenCode's shell permission rules. The docs say plugin
tools enforce the permissions they assert. The review is read-only by default,
and `--comment` is an explicit user request; adding per-command assertions
would introduce prompts (and could hang batch runs) and would diverge from
Claude Code's local review.

**Decision:** accepted and documented. If OpenCode adds a non-interactive
policy API for plugin tools, gate `--comment` and the `git`/`gh` subprocesses
behind it.

### F7 — Command runs in the foreground; no `/review` alias (accepted)

**Severity:** low, host behavior.

Claude Code's terminal `/code-review` runs as a background subagent. The V2
command transform blocks the command turn. Adding a background child would
change result delivery and is already tracked as C1 in
`CODE_REVIEW_PENDING_PLAN.md`. A `/review` alias was not added because
OpenCode ships a built-in `/review`; registering the same name would replace
unrelated behavior.

### F8 — Output-route differences are intentional (accepted)

- GitLab `--comment` is out of scope; the prompt and the host path both say so.
- `ultra` falls back to a local max-effort review, matching the reference's
  non-cloud fallback.
- A completed engine report is displayed through `ctx.session.synthetic` (or a
  constrained acknowledgement on hosts without synthetic) instead of being
  printed as assistant prose.
- `ReportFindings` is registered globally for protocol compatibility, with a
  recursion guard around `code_review`; the schema tools are prefixed
  `code_review_*`.

## Parity assessment

- **Prompts:** the assembled reference prompts are checked against committed
  SHA-256/length digests; no third-party prompt text is stored in this
  repository.
- **Dispatch:** the family × effort table, caps, phases, synthesis, and
  verifier behavior are unchanged; the command path now selects the correct
  row from the session model instead of always selecting `default`.
- **Output:** the human renderer, bare JSON array, `ReportFindings` schema and
  result text, partial-run warning, and artifact shape are unchanged.
- **Model/effort:** now follows the session on the command path as well as the
  tool path.
- **Attachments:** now preserved on model-driven command turns.
- **Known divergences:** GitLab comments, ultra cloud review, background
  execution, and the absence of a `/review` alias.

## Verification

| Check | Result |
|---|---|
| `node --test test/*.test.ts` | 338 passed, 0 failed |
| Live command registration | `code-review-opencode` present |
| Live invocation | HTTP 204 |
| Live attachment | `note.txt` present in the user review message |
| Command schema | `argumentHint` absent, as V2 expects |
| Global symlinks | `scripts/install-global.sh --check` passes all five links |
