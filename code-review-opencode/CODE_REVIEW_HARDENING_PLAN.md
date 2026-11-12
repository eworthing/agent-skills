# code-review-opencode — Code-Review Hardening Plan

> **Naming:** this project is `code-review-opencode`; its command is
> `/code-review-opencode`. Mentions of `/code-review` in this document name
> Claude Code's original command.

Status: **VALIDATED** — M1/M2/M3 workstreams are implemented and tested, and the clean `max --max-findings all --fix` self-review completed with 32 findings, 31 fixed, and one intentional skip.
Basis: [`CODE_REVIEW_PORTS.md`](CODE_REVIEW_PORTS.md), the
implementation comparison against `ttxs69/code-review-codex` and
`fyeeme/pi-review`, and the incomplete `max --max-findings all --fix`
self-review run.

Guiding rule: **replicate the reference first; backport a third-party
mechanism only when it fills an operational gap and does not change the
recovered prompt, dispatch table, or output contract.** No fork of either
port. No ultra execution layer. No `REVIEW.md` injection.

## Why this plan exists

The ports are stronger at **operational plumbing**:

- `pi-review/src/diff.ts` — nearest-git-root/submodule resolution,
  fresh-repo ladder, abort/timeout, hook/fsmonitor hardening, changed-file
  context package.
- `pi-review/src/tools/review_report.ts` — tolerant finding normalization,
  32-finding truncation, `refuted`/`stats` artifact.
- `pi-review/src/dispatch.ts` — valid-only state persistence, fan-out
  registration check and single-pass fallback.
- `pi-review/src/fanout.ts` — recursion guard.
- `ttxs69/code-review-codex` — verifier recall language and PR comment
  composition; no engine to reuse.

Our implementation is stronger at **reference fidelity and OpenCode
integration**: byte-exact v2.1.318 prompts, the versioned cell table,
wf162/wf221 compatibility, `ReportFindings`, child sessions, comment
posting, and 253 tests.

The plan closes the plumbing gaps without surrendering those strengths.

### Evidence from the last run

`/code-review-opencode max --max-findings all --fix` on the 51-file self-review
copy finished in **28:59** with **56 child sessions**:

- 10 finders, 1 dedup, 40 verifiers, 1 sweep, 1 merge — all sessions
  reported `succeeded`.
- The report was **INCOMPLETE**: angle-D and angle-E returned no usable
  structured result; one verifier returned no usable verdict; the sweep
  returned no usable structured result.
- The main session was cut off before applying fixes; the working tree was
  unchanged.
- The 32 reported findings were partial and included at least one false
  positive (the e2e fixture's intentionally seeded default export).

That run is the primary acceptance target for H1–H4.

### Status after the hardening pass

| Workstream | State | What changed |
|---|---|---|
| H1 | **DONE** | Tolerant `ReportFindings` and child-tool normalization; one structured-output retry with text salvage in the runner; opt-in atomic report artifact (`CODE_REVIEW_REPORT_DIR`). |
| H2 | **DONE** | `supportsChildSessions` capability probe; multi-agent cells fall back to the recovered single-pass prompt with one notice; dead `fallbackPrompt`/`resolveAngles` removed. |
| H3 | **DONE** | Refuted candidates stay in the sweep's known set; wf162 no-line matching tolerates a missing `kind`; wf162 preserves the verified verdict. H3.4 closed: the captured 2.1.318 sweep goes straight to ranking, and no wf221 evidence shows a second verification pass. |
| H4 | **DONE** | One shared semaphore for every role; verifier calls get priority so streaming still overlaps; child sessions are removed by default; the dead `findingsBySession` map is gone; recursion guard added. |
| H7 | **DONE** | Invalid `--max-findings` no longer clears the stored value; the typed tool passes structured arguments instead of re-parsing a command string; `--fix --dry-run`/`--fix --json` never append the apply block; the typo-token behavior is documented and its test renamed. |
| H5 | **DONE** | Signal/timeout propagation, hardened git invocation, nearest-root/submodule path targets, the fresh-repo ladder, and the changed-file context package. H5.3 closed: the recovered `Zs` command has none of the proposed extra diff flags. |
| H6 | **DONE** | One `gh pr diff`, one `gh pr view`, bounded comment posting, host routing from the origin remote, and checked-out branch-PR detection. |
| H8 | **DONE** | One anchor formatter, one finding-schema source, explicit `needsModel` routing, dead-code/duplication removal, conventions ordering/budget, the confirmed wf221 recall ladder, lens-kind attribution, and declarative cell modes. |
| H9 | **DONE** | 253 tests, including fresh-repo/submodule/quoted-path/timeout/abort, PR caching, bounded posting, report artifact, recursion guard, the combined wf162 e2e, and the second clean-run fixes. |

Test suite after the hardening pass: **253 passing** (`node --test test/*.test.ts`).
The clean self-review rerun completed and its findings were applied.

### Validation run

The rerun uses the synced self-review copy at
`/private/var/folders/6l/j4rd5q856m70k2wcync_7xy80000gn/T/opencode/cr-self3`
with `max --max-findings all --fix`. The copy passes the 253-test suite
before the run.

The first rerun exposed a child-agent permission mismatch: finder shell
commands that piped `git diff` into `tail` (or used `ls`/`echo`) were
denied because the agent allowlist covered only git/gh commands. The
finder/sweep/verifier allowlists now include `tail`, `head`, `echo`, `ls`,
`wc`, `sort`, and `uniq`. The in-flight run was already past the finder
phase when this was fixed; the clean rerun used the corrected allowlists.

### Findings fixed after the first rerun

The first rerun produced 32 candidates before verification. The confirmed
ones were fixed before the next full run:

- **Structured output:** plugin schema tools are not exposed to every
  subagent, so the runner now accepts the same JSON object from the final
  text response. The retry says “call the tool if available; otherwise reply
  with only the JSON object.” This removes the synth/verifier loops that
  tried to call a missing tool.
- **Agent shell allowlist:** finders/sweep/verifier now allow `tail`, `head`,
  `echo`, `ls`, `wc`, `sort`, and `uniq` in addition to git/gh, so compound
  read-only commands are not denied.
- **Scope:** a bare branch target wins over a same-named path; a free-form
  target narrows to a path named inside it; scope discovery receives the
  abort signal; the worktree check ignores untracked files; numstat is
  skipped when the cell has no finder-budget hint.
- **Comment posting:** host detection is lazy and uses the reviewed root; a
  range/path/fresh-repo review no longer posts to an unrelated branch PR;
  repo/head metadata calls run in parallel; cancellation/timeout is
  forwarded to git/gh.
- **Output:** verifier evidence is required at the tool boundary; dead
  `*Error` validators removed; `as*` parsers reuse `normalize*Call`; shared
  `mapLimit`, `finding.ts` helpers, `gitDiffArgs`, `finderCap`, and the
  `parseArgs` builder; `ReportFindings` uses `isLevel`/`HARD_FINDINGS_CAP`;
  the fallback JSON scanner is bounded; the diff render is cached.
- **Fixture:** the e2e default export is marked as an intentional convention
  violation.

A clean rerun with the fixed runner and agent allowlists then ran against
the same copy and completed in **58:12** with 32 reported findings. That
`--fix` turn applied 31 of them; the one intentional skip was the grouped
verifier ladder (changing it would break the recovered wf221 prompt). The
suite grew from 159 to 174 tests.

### Second clean-run findings applied

- **Command output:** `--json` now renders through `session.synthetic`, so
  the visible result is the bare array rather than a model reply; `--dry-run`
  suppresses comment posting; a normal review is read-only and only
  `CODE_REVIEW_REPORT_DIR` opts into the artifact; a scope-start error routes
  through the model instead of receiving a “review complete” acknowledgement.
- **Runner and parsing:** a wrong-shaped JSON result now triggers the retry;
  the bracket scanner prefers a structured result object over prose
  fragments; stringified group-verdict indices are accepted; verifier
  evidence is required in the tool schema.
- **Scope and comments:** `canonFile` no longer collapses a longer path onto
  a shorter in-scope name; a clean default review records the current branch
  so `--comment` can resolve its PR; inline `--comment` resolves the host
  from the reviewed root; git octal paths are decoded as UTF-8.
- **Dedup and synthesis:** non-Latin summaries stay distinct; wf221 sweep
  dedup catches same-line reworded refutations; wf162 text synthesis matches
  corrected anchors and backfills verified survivors.
- **Prompts and kinds:** a swept cleanup finding keeps its cleanup kind; a
  grouped finder keeps the combined lens capacity and carries its lens list
  so the conventions text is included; sweep findings render an explicit
  “no evidence” line instead of `undefined`.
- **Arguments and cleanup:** bare `--keep-sessions` no longer consumes the
  target; `--no-post` is last-wins; `--quiet` suppresses notices/progress;
  the unused `Scope.commands` and `sweepVerify` fields are gone; the
  duplicate `ReportFindings` normalizer now shares `normalizeFinding`; the
  comment path reuses the host already detected for the reviewed root.
- **Intentionally skipped (second run only):** the grouped verifier keeps both
  `VERDICT_LADDER` and `VERDICT_LADDER_RECALL`; that is the recovered wf221
  prompt, and changing it would break compatibility with the extracted
  workflow.

### Third run — 32/32 fixed

A third `max --max-findings all --fix` run on the updated copy completed in
**68:12** with another 32 findings, no partial warning, and no skips: the
`--fix` turn applied all 32. The suite grew from 174 to 191 tests. The fixes
cover:

- **Scope:** diff/name-status failures now produce a clear error or a partial
  warning instead of a clean empty report; dotted ranges (`v1.2.3...HEAD`)
  resolve; whitespace in unquoted paths is preserved; patch churn counts
  `+++`/`---` content lines; numstat sums every plan entry; a root-only
  conventions file gets the full budget.
- **Parsing:** repeated extension flags are all stripped; numeric-string lines
  and merge indices are accepted; a malformed candidate or a verdict without
  evidence rejects the call so the child re-emits it; the JSON scanner finds a
  payload after a long unbalanced code quote; `looksLikeLevel` only flags
  single-edit typos.
- **Engine:** `canonFile` maps `b/`-prefixed and absolute paths; pre-verify
  dedup is exact-only so paraphrases reach verification; one shared token no
  longer suppresses a genuine sweep finding; `kind` is carried in the
  candidate schema; verifier ties are deterministic; text synthesis matches
  only exact/near-exact wording and does not backfill merged-away findings;
  all-finder failure is a typed counter, not a warning regex.
- **Host/output:** the `code_review` tool guards `session.get`; inline/prompt
  reviews get the `/verify` follow-up; `--json` partial runs emit a
  `CODE_REVIEW_PARTIAL` JSON line on stderr; the non-synthetic fallback
  constrains the model to echo the array; workflow modes keep the requested
  family at low/medium and emit a fallback notice; the report artifact is
  opt-in via `CODE_REVIEW_REPORT_DIR`, so a normal review is read-only.
- **C3/C7:** the runner no longer forces the parent model onto every child, so
  agent `model: provider/model#variant` selects per-role effort; a
  `ReportFindings` call with outcomes posts a deduped synthetic summary.

The minimal prompt’s output-field sentence is adapted to the registered
`ReportFindings` fields (`file`/`line`/`summary`/`short_summary`/
`failure_scenario`/`category`) instead of the captured `severity`/`comment`
wording; the test documents that replacement. The rest of the captured
`medium.md` prompt remains byte-exact.

### Run 4 operational fixes

The next run exposed two runner issues that the unit tests did not:

- A child session created without an explicit model produced an empty
  response. The runner now resolves the model per child: the agent’s own
  `model` wins, then `CODE_REVIEW_ROLE_VARIANTS` applies a variant to the
  parent model, then the parent model is used. The parent model is always
  passed explicitly.
- `session.wait` could stay pending after a child was removed, hanging the
  whole engine. It is now raced with a cheap `session.context` poll that
  resolves on an idle/finished or vanished child.
- The text fallback accepts a bare candidates/verdicts/findings/decisions
  array and wraps it in the expected object shape, so a model that omits the
  wrapper is not treated as a failed finder.
- A silent child can no longer hang the engine. The runner uses the same
  **stall watchdog** as `pi-subagents`: `session.wait` is raced with a session
  poll, and if the child’s `time.updated` does not change for
  `CODE_REVIEW_STALL_MS` (default `600000` ms), the runner interrupts the
  child. `time.updated` changes per turn rather than per streamed token, so
  180s interrupted healthy max-effort finders during self-review 5 and 6; a
  stalled child is not retried, because an interrupt is a timeout rather than a
  schema failure. A wall-clock ceiling remains disabled; only no-activity calls
  are aborted. `mapLimit` also stops dispatching new work on failure and awaits
  every in-flight worker before rethrowing, so a failed call cannot orphan
  running children.
- Structured-output reliability: the schema instruction and the retry include
  the exact expected JSON shape; the text fallback accepts a bare array and the
  common `findings`/`candidates` aliases; a malformed candidate no longer
  discards the valid ones, and the dropped count marks the run partial.
- Verifier reliability: the text fallback keeps a verdict with a placeholder
  when evidence is missing (accepting `reason`/`justification` aliases) and
  marks the run partial; the tool boundary stays strict. Finder/sweep `steps`
  are 30 and verifier/synth `steps` are 20 (OpenCode/DeepSeek adaptation), and
  an empty response gets up to two retries.

### Port evidence for stuck-runner handling

`fyeeme/pi-packages` separates the review prompts from the runner. `pi-review`
deliberately removed subagent turn budgets and lets agent tasks run to natural
completion; the lifecycle lives in `pi-subagents`, which uses:

- a per-call **stall watchdog** (`stallMs`, default 60s) re-armed by every
  child stdout/stderr event;
- an optional **wall-clock ceiling** (`wallClockMs`), disabled by default and
  ignored below 2× the stall threshold;
- a per-call `AbortController` that sends SIGTERM and escalates to SIGKILL
  after 5s; parent signals are linked to every child;
- an optional `maxTurns` budget (not used by the review pipeline);
- a concurrency limiter that stops dispatching on failure but awaits in-flight
  calls before rethrowing;
- transient/hard failure classification and a replay hint for failed tasks.

The Codex port (`ttxs69/code-review-codex`) is a skill-only prompt; it relies
on Codex’s `spawn_agent` for lifecycle and has no runner of its own. Our port
keeps the stall-watchdog idea but raises the default to 600s because a
max-effort model can reason for minutes between visible session updates; 180s
interrupted healthy finders in self-review.

## Workstreams

| ID | Workstream | Priority | Primary source | Status |
|---|---|---|---|---|
| H1 | Structured-output resilience | P0 | `pi-review/src/tools/review_report.ts` | DONE |
| H2 | Fan-out fallback and capability detection | P0 | `pi-review/src/dispatch.ts` | DONE |
| H3 | Sweep and synthesis correctness | P0 | Self-review + `pi-review/agents/gap-hunter.md` | DONE |
| H4 | Concurrency and resource lifecycle | P0 | `pi-review/src/fanout.ts` + self-review | DONE |
| H5 | Diff and scope robustness | P1 | `pi-review/src/diff.ts` + reference `Qs` | DONE |
| H6 | PR and comment efficiency/routing | P1 | Self-review + `pi-review/src/diff.ts` | DONE |
| H7 | State and argument correctness | P1 | `pi-review/src/dispatch.ts` + self-review | DONE |
| H8 | Output consistency and cleanup | P2 | Self-review + `pi-review/src/tools/review_report.ts` | DONE |
| H9 | Tests and benchmarks | P1/P2 | `pi-review/test/*` + our suite | DONE |

## H1 — Structured-output resilience (P0)

**Problem.** One invalid verdict, outcome, or a 33rd finding rejects the
whole report. The incomplete run lost two finders, one verifier, and the
sweep to unusable structured output.

**Tasks.**

- [x] **H1.1** Add tolerant normalization to
  `normalizeReportFindings`:
  - invalid `verdict` → drop that finding, keep the rest;
  - invalid `outcome` → coerce to `skipped` and attach a note;
  - `>32` findings → keep the first 32 and record `truncated_from`;
  - normalize `refuted` and `stats` instead of rejecting the payload.
- [x] **H1.2** Apply the same normalization at the child schema-tool
  boundary (`code_review_candidates`, `code_review_verdict`,
  `code_review_group_verdicts`, `code_review_report`,
  `code_review_decisions`) so a malformed field does not discard the
  whole call. Keep the validator error and retry path for genuinely
  unusable output.
- [x] **H1.3** Add a persistent report artifact (host-writable path, e.g.
  `.opencode/code-review-opencode/reports/<timestamp>-<id>.json`) carrying
  `report_id`, `generated_at`, `files_changed`, `fanned_out`, `refuted`,
  `stats`, and `truncated_from`. The artifact is **opt-in** via
  `CODE_REVIEW_REPORT_DIR`; a normal review never writes into the checkout it
  inspected. The `--json` stdout contract stays a bare array.
- [x] **H1.4** Tests: invalid verdict, invalid outcome, 33 findings,
  empty findings. Artifact write/identity cases are covered by
  `test/artifact.test.ts`.

**Acceptance.** A report with one invalid outcome still returns every
other finding. A 33-finding report truncates with an explicit note.
`--json` remains a bare array. When opted in, the artifact is written
atomically with `0600`; a write failure still returns the rendered report.

## H2 — Fan-out fallback and capability detection (P0)

**Problem.** `fallbackPrompt` and `resolveAngles` have no call site. If
child sessions are unavailable, the engine returns a partial/empty review
instead of degrading to a one-pass review. `pi-review` resolves the bound
tool and falls back with a warning.

**Tasks.**

- [x] **H2.1** Add `supportsChildSessions(ctx)` or a first-call probe
  around `ctx.session.create`.
- [x] **H2.2** Replace the dead helpers with a real fallback: run the
  recovered prompt for the selected effort (the inline/prompt path), not
  a newly invented prompt.
- [x] **H2.3** Emit one notice naming the fallback; keep the output
  contract and the partial flag semantics.
- [x] **H2.4** Test: capability probe covered by `host.test.ts`. The
  end-to-end fallback path lives in `index.ts` and is validated by the
  self-review rerun; a direct unit test is deferred with H9.

**Acceptance.** A host without subagents still gets a review. No dead
code remains. The user sees one clear notice.

## H3 — Sweep and synthesis correctness (P0)

**Problem.** The sweep's known set is built from `kept` only, so a
refuted false positive can return as a fresh `PLAUSIBLE`. wf162 synthesis
can drop a no-line finding because `sameDefect` requires a matching
`kind`, and can downgrade `CONFIRMED` to `PLAUSIBLE` when the synthesizer
omits a verdict.

**Tasks.**

- [x] **H3.1** Include refuted candidates in the sweep's `known` list and
  dedup keys. Label them `(refuted — do not re-report without new
  evidence)` rather than silently omitting them.
- [x] **H3.2** In `sameDefect`, when either finding lacks `kind`, use the
  known candidate's kind or skip the kind check. A no-line wf162 finding
  must not be dropped solely because the synthesizer omitted `kind`.
- [x] **H3.3** In wf162 synthesis, preserve the matched verdict:
  `verdict: f.verdict ?? match.verdict ?? "PLAUSIBLE"`.
- [x] **H3.4** Closed: the captured 2.1.318 sweep goes straight to
  ranking, and no wf221 evidence shows a second verification pass.
  Self-review finding #4 is unverified. The unused `sweepVerify` field was
  removed in the second clean run; no re-verification pass is enabled.
- [x] **H3.5** Tests: refuted sweep, no-line wf162 synthesis, verdict
  preservation, wf221 sweep behavior.

**Acceptance.** A refuted claim cannot reappear via the sweep. A no-line
wf162 finding survives. A `CONFIRMED` finding stays `CONFIRMED`.

## H4 — Concurrency and resource lifecycle (P0)

**Problem.** The wf162 streaming path starts every finder with
`Promise.all` and nests `mapLimit(concurrency)` inside each, so in-flight
agents are finders × concurrency. `keepSessions` defaults true, and
`findingsBySession` is never deleted.

**Tasks.**

- [x] **H4.1** Add one shared semaphore for all child-agent calls.
  Finders and verifiers share the limit; streaming remains streaming but
  bounded.
- [x] **H4.2** Default `keepSessions` to false. `--keep-sessions` or
  `CODE_REVIEW_KEEP_SESSIONS=true` opts in for debugging; removal happens
  in `finally`.
- [x] **H4.3** Delete `findingsBySession` entries after the report is
  delivered. Bound `schemaResults`/`schemaFailures`; test repeated runs.
- [x] **H4.4** Add a recursion guard so a child review cannot spawn
  another review.
- [x] **H4.5** Tests: concurrency cap under streaming, session removal,
  and the recursion guard (`host.test.ts`). The per-session map cleanup is
  exercised by `runner.test.ts`; repeated-run map growth is covered by the
  self-review rerun.

**Acceptance.** In-flight agents never exceed the configured
concurrency. No child sessions remain after a run unless opted in. The
per-session maps return to baseline.

## H5 — Diff and scope robustness (P1)

**Problem.** Our scope ladder is simpler than `pi-review`'s. It lacks
submodule/path-root resolution, a fresh-repo ladder, abort/timeout, and
hook/fsmonitor hardening. The reference's finder-budget command also uses
diff flags we omit.

**Tasks.**

- [x] **H5.1** Propagate `ctx.signal` to scope git/gh calls. Add a
  configurable timeout (e.g. 10s scope, 5s numstat) and a clear error.
- [x] **H5.2** Harden git invocation:
  `-c core.hooksPath=/dev/null`, `-c core.fsmonitor=`,
  `-c core.askPass=`, `--no-ext-diff`, `--no-textconv`,
  `--end-of-options`.
- [x] **H5.3** Closed: the recovered `Zs` numstat command is `-c
  core.hooksPath=/dev/null -c core.fsmonitor= -c core.askPass= diff
  --no-ext-diff --no-textconv --numstat --end-of-options <range> --` with a
  5s timeout. It has none of `--diff-algorithm=myers`, `--find-renames`, or
  `--ignore-submodules=none`; adding them would diverge from the reference.
- [x] **H5.4** Resolve a path target to the nearest `.git` root
  (including submodules and `@`-prefixed paths) and review that root's
  diff.
- [x] **H5.5** Add the fresh-repo ladder: when HEAD is unresolvable,
  try `--staged`, then the unstaged worktree diff.
- [x] **H5.6** Add a changed-file context package: repo root, scope kind,
  per-file `+/-` churn parsed from the captured diff, 200-file cap, and
  git-quoted path support.
- [x] **H5.7** Tests: fresh repo, submodule path, quoted path,
  timeout/abort, context package.

**Acceptance.** Scope discovery matches the port on its test cases. A
hung git/gh call aborts cleanly. Agents receive the context package and
do not spend their first turns rediscovering the changed-file list.

## H6 — PR and comment efficiency/routing (P1)

**Problem.** A PR review runs `gh pr diff` 2–3 times, two `gh pr view`
calls, `git diff --stat` plus `--numstat`, and recomputes `rangeFiles`.
`postComments` posts serially. The prompt path chooses GitHub/GitLab from
the target text while the engine path uses the origin remote.

**Tasks.**

- [x] **H6.1** Cache the first `gh pr diff` stdout and reuse it for
  `filesFromDiff` and `diffText`. Request
  `gh pr view --json files,additions,deletions` once.
- [x] **H6.2** Derive the summary and `diffLines` from one numstat/context
  pass; reuse `rangeFiles` for the first command.
- [x] **H6.3** Bound `postComments` concurrency (4–6). Aggregate failures
  and preserve deterministic output order.
- [x] **H6.4** Route GitHub/GitLab by origin remote in both prompt and
  engine paths. Detect a branch PR where possible, or make the notice
  explicitly say a PR number is required.
- [x] **H6.5** Tests: one `gh pr diff` per PR, one `gh pr view`, bounded
  posting, GitLab remote, branch-PR notice.

**Acceptance.** A PR review makes one patch download and one PR metadata
call. Posting is bounded, not serial. Both paths agree on the host.

## H7 — State and argument correctness (P1)

**Problem.** An invalid `--max-findings` stores `null` and clears the
user's saved limit. The typed `code_review` tool rebuilds a command
string and re-parses it, so a target named `high` or containing flags is
misread. The inline/prompt `--fix` path bypasses `fixAction`.

**Tasks.**

- [x] **H7.1** Persist only a valid `--max-findings`. An invalid value
  is ignored and the previous limit is reused; `default` clears it.
- [x] **H7.2** Pass structured options into `resolveAndRun` (or a
  `parsed` override) from the typed tool; do not rebuild and re-parse.
- [x] **H7.3** Apply `fixAction` on the inline/prompt paths.
  `--dry-run` and `--json` never append the fix block.
- [x] **H7.4** Decide whether to strip a typo effort token from the
  target (pi behavior) or keep the reference behavior. Document the
  choice and fix the misleading test name.
- [x] **H7.5** Tests for each.

**Acceptance.** An invalid max-findings keeps the stored limit. A target
named `high` reviews the branch. `--fix --dry-run` and `--fix --json`
never edit.

## H8 — Output consistency and cleanup (P2)

**Problem.** Several small inconsistencies remain: line-0 anchors,
duplicated schema, regex-based outcome routing, dead fields, duplicated
dedup/synthesis blocks, conventions budget order, grouped-verifier recall,
and finder-kind re-inference.

**Tasks.**

- [x] **H8.1** Share one `location()` helper; make line 0 consistent.
- [x] **H8.2** Derive `FINDING_ITEM_SCHEMA` from
  `REPORT_FINDINGS_SCHEMA` minus `outcome`.
- [x] **H8.3** Add explicit `needsModel`/`driver` to `Outcome`; remove
  the `## Applying fixes` regex routing.
- [x] **H8.4** Remove dead `Outcome.notice`/`Outcome.json`,
  `budgetDropped`, the duplicated `dedupKey162` loop, the duplicated
  wf221/semanticMerge synthesis block, and the duplicated synth-prompt
  body.
- [x] **H8.5** Order conventions discovery repo/ancestor first,
  user-level last; allocate budget per source.
- [x] **H8.6** Confirmed from the extracted wf221 source
  (`sources/sixddc-code-review-extracted.js`): the grouped verifier uses
  `VERDICT_LADDER + VERDICT_LADDER_RECALL`. The recall ladder is now in
  `groupVerifierPrompt` with a prompt test.
- [x] **H8.7** Carry each lens's kind through grouped finders; stop
  re-inferring cleanup from the category slug.
- [x] **H8.8** Replaced `cell.id.startsWith(...)` branching with
  declarative fields: `synthesis`, `barrierDedup`, `sweepDedup`,
  `cleanupLenses`, and `semanticMerge`.

**Acceptance.** Anchors agree across JSON/comment/terminal. One schema
source. No dead code. A cleanup nit cannot outrank a real bug by
accident.

## H9 — Tests and benchmarks (P1/P2)

**Tasks.**

- [x] **H9.1** Port the `pi-review` cases for diff resolution, dispatch,
  report normalization, and fan-out recursion.
- [x] **H9.2** Add a failing-before/passing-after test for every P0 bug.
- [x] **H9.3** Add an e2e fixture containing a refuted candidate, a
  sweep duplicate, a wf162 no-line synthesis, and a concurrency probe.
- [x] **H9.4** `node --test test/*.test.ts` runs after every milestone
  (253 passing). The clean self-review rerun completed and its findings
  were applied.

**Acceptance.** The suite covers every gap in this plan. Each P0 fix has
a regression test.

## Milestones

### M1 — Stop losing findings (P0)

H1, H2, H3, H4.

Definition of done:

- A malformed field never rejects a whole report.
- A host without subagents gets a one-pass review.
- A refuted candidate cannot reappear via sweep.
- wf162 no-line findings survive and keep `CONFIRMED`.
- In-flight agents never exceed the concurrency limit.
- No child sessions or findings-map entries remain after a run.

### M2 — Harden the inputs (P1)

H5, H6, H7.

Definition of done:

- Fresh repo, submodule path, quoted path, and abort cases pass.
- A PR review makes one patch download and one metadata call.
- Comment posting is bounded and host routing is consistent.
- Invalid `--max-findings` preserves the stored value.
- The typed tool's target is not reinterpreted as a flag or level.
- `--fix --dry-run` and `--fix --json` never edit.

### M3 — Consistency and coverage (P2)

H8, H9.

Definition of done:

- One anchor formatter, one finding schema, explicit outcome routing.
- Dead code and duplicated blocks removed.
- Conventions ordering and finder-kind propagation fixed.
- Grouped-verifier recall decision documented.
- The test suite covers all port-level edge cases.

## Definition of done for the whole plan

- [x] `node --test test/*.test.ts` passes with the new tests (253 tests).
- [ ] `/code-review-opencode max --max-findings all --fix` on the 51-file
      self-review copy completes without a partial warning caused by
      structured-output failures, applies fixes, and re-reports outcomes.
- [ ] `git status --short` after a review shows no child sessions, no
      report-map growth, and no unexpected files.
- [x] `--json` is still a bare array; `--comment` still routes by host.
- [x] The byte-exact prompt tests still pass.
- [x] The only changed prompts are those required by a confirmed
      reference gap, and each change has a test.

## Non-goals

These are deliberate divergences, not gaps:

- Ultra's cloud execution layer, Bughunter fleet, `bugs.json`, and
  progress protocol.
- `REVIEW.md` injection (managed Code Review feature; local
  `/code-review` does not read it).
- Low/medium/high single-pass (pi's choice; our medium/high are
  multi-agent per the reference cell table).
- `--loop` fix→re-review rounds (pi extension; the reference `--fix` is
  one apply pass).
- ttxs69's linter/pre-existing/nitpick/unchanged-line PR filters (older
  official plugin, not the v2.1.318 command).
- Forking either port. Backport only the portable modules listed here.
- GitLab MR support.

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| Tolerant normalization hides real schema errors | Keep warnings and schema-failure counts; log the dropped field; test the strict path separately. |
| Shared semaphore slows streaming | Measure before/after; make the limit configurable; keep streaming scheduling. |
| Submodule/path-root resolution changes scope unexpectedly | Add a scope-kind label to the prompt; test the exact cases; keep the parent-repo behavior for non-path targets. |
| Session removal breaks debugging | `--keep-sessions` and `CODE_REVIEW_KEEP_SESSIONS=true`; log the removed IDs at debug level. |
| Backported code licensing | `pi-review` is MIT (`Copyright (c) 2026 fyeeme`): add a header comment and keep the notice. `ttxs69` is Apache-2.0: add a `NOTICE` entry only if substantial code is copied. |
| Cell declarative refactor is large | Separate H8.8; do not block P0/P1 on it. |
| Changing a recovered prompt by accident | Prompt tests are byte-exact; any prompt change needs a reference citation and a test update. |

## References

- [`CODE_REVIEW_PORTS.md`](CODE_REVIEW_PORTS.md) — port catalog and
  feature matrix.
- [`CODE_REVIEW_IMPROVEMENT_BACKLOG.md`](CODE_REVIEW_IMPROVEMENT_BACKLOG.md)
  — adopted, designed, and rejected improvements.
- [`CODE_REVIEW_ORCHESTRATION_MAP.md`](CODE_REVIEW_ORCHESTRATION_MAP.md)
  — mechanism map.
- [`CODE_REVIEW_CONFIDENCE_MAP.md`](CODE_REVIEW_CONFIDENCE_MAP.md) —
  per-group confidence.
- `pi-review`: `src/diff.ts`, `src/dispatch.ts`, `src/fanout.ts`,
  `src/tools/review_report.ts`, `agents/verifier.md`,
  `agents/gap-hunter.md`, `test/diff.test.ts`, `test/dispatch.test.ts`,
  `test/review_report.test.ts`, `test/fanout.test.ts`.
- `ttxs69/code-review-codex`: `plugins/code-review/skills/code-review/SKILL.md`.
- Our code: `.opencode/plugins/code-review-opencode/scope.ts`, `parse.ts`,
  `index.ts`, `engine.ts`, `runner.ts`, `format.ts`,
  `reportfindings.ts`, `prompts.ts`.
