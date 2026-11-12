# code-review-opencode — Code-Review Confidence Map

> **Naming:** this project is `code-review-opencode`; its command is
> `/code-review-opencode`. Mentions of `/code-review` in this document name
> Claude Code's original command.

An estimate of how closely each logical part of this OpenCode reconstruction
matches Claude Code v2.1.318, and where the remaining gaps are.

**Confidence is an analyst estimate of behavioral equivalence, not a statistical
measurement.** It is grounded in the binary extraction, the captured prompt
variants, the 89-test suite, and the DeepSeek `max` runs. A section can be
“high confidence” and still have a small host-specific gap; the gap column calls
that out.

Scale:

| Confidence | Meaning |
|---|---|
| 95–100% | Recovered byte-for-byte or table-for-table and verified. |
| 85–94% | Recovered text/behavior with a minor host substitution. |
| 70–84% | Model-driven behavior reconstructed with exact constraints; wording or context differs. |
| 55–69% | Significant platform adaptation or partial host integration. |
| <55% | Not implemented, or only a fallback exists. |
| N/A | Reference-only host feature with no OpenCode surface. |

---

## 1. Summary

| # | Logical group | Confidence | What is exact / adapted | Main gap |
|---|---|---|---|---|
| 1 | Command registration & metadata | **90%** | Name, description, argument hint, effort plumbing. | `/review` alias and `whenToUse` are host-only; ultra subcommand N/A. |
| 2 | Argument parsing & flags | **98%** | `xe` grammar, `--comment/--fix/--post/--no-post`, `--max-findings`, `med` alias, target cleanup, `ultra`. | None material. |
| 3 | Effort resolution & storage | **88%** | Typed > last used > session > medium; non-interactive memory rule; ultra fallback. | `Dg`/`Ry`/`ig` model/session override chain approximated. |
| 4 | Family detection & dispatch | **95%** | `he` table, default/sonnet-5/opus-4.8/opus-5 cells, sonnet-5 finder hint. | Claude model-ID normalization approximated; default family exact. |
| 5 | Cell definitions & prompt selection | **93%** | All cells, caps, floors, sweep flags, `$s` switch. | Child prompt bodies reconstructed. |
| 6 | Parent prompt assembly | **91%** | `Js` order, notices, target, finder hint, comment/fix/fix-later, `/verify`, output contracts. | `Bs`, `yn`, ultra cloud N/A. |
| 7 | Diff discovery & scope | **87%** | Upstream/main/HEAD~1, working tree, PR/branch/path/range, CLAUDE.md discovery, diffLines, captured unified diff. | Free-form target is path-hint based; GitLab dropped; AGENTS.md is an OpenCode extension. |
| 8 | Finder orchestration | **79%** | 8/10 angles, 6/8 caps, per-role agents, category, short_summary, conventions scoping, captured diff in every prompt. | Child prompt wording; no per-role reasoning effort; deterministic scheduling. |
| 9 | Candidate dedup | **85%** | Model dedup before verification with the exact Phase 2 criterion; the synth now sees the captured diff; deterministic fallback. Run 7 reduced verifiers 10 → 6. | Wording and synth judgment remain model-driven. |
| 10 | Verification | **88%** | One verifier per candidate, 3-state/recall ladders, evidence, read-only, schema retry, captured diff, recall single-vote sentence, grouped wf221. | Verifier prompt wording reconstructed; no per-role effort. |
| 11 | Sweep | **87%** | One fresh finder, gaps only, up to 8, exact sweep focus, captured diff. | Sweep prompt wording reconstructed. |
| 12 | Semantic merge & ranking | **86%** | Exact “same line/mechanism / most concrete scenario” and “most-severe first” criteria via `review-synth`; the synth now sees the captured diff; validated in Runs 6–7. | Deterministic fallback ranking is heuristic. |
| 13 | Output contracts | **96%** | JSON array, ReportFindings payload, `jt` human renderer, control chars, category, short_summary. | ReportFindings output schema not declared (host API limit). |
| 14 | ReportFindings tool | **91%** | Schema, description, result text, 32 cap, outcome field. | Outcome re-report is not surfaced by the command path. |
| 15 | Actions (`--fix`, `--comment`) | **80%** | Fix block, GitHub inline comments, GitLab note (dropped), comment ignore notice. | No suggestion blocks; fix outcome/checkpoint behavior differs. |
| 16 | Notices | **95%** | Effort reuse/typo, max-findings cap/reuse, ultra fallback, `--post`. | Cloud-capable ultra branches N/A. |
| 17 | Failure behavior | **76%** | Malformed finder/verifier/sweep, cancellation, agent-unavailable fallback, schema retry limit. | `partial` is an extension; reference has no equivalent marker. |
| 18 | Host integration | **72%** | Command + tool + ReportFindings + schema tools + child sessions + permissions + metadata; no default child wall-clock cap (`steps` is the bound). | Interactive background review not implemented; concurrency 4 vs 20; API timeout. |
| 19 | Tests & provenance | **96%** | 253 tests, byte-exact skill captures, binary search, e2e runs. | Quality benchmark against a known-defect corpus not yet run. |

**Overall weighted confidence: ~88%.**
**Critical-path contract (parser, dispatch, cells, assembly, verification,
outputs, ReportFindings): ~93%.**
**Model-driven orchestration (finders, dedup, sweep, merge/rank): ~84%.**
**Host integration: ~70%.**

The pattern is deliberate: the deterministic contract is near-exact; the
model-driven orchestration is reconstructed; the host integration is where
OpenCode differs most.

---

## 2. Detailed groups

### 1. Command registration and metadata — 90%

Exact: `wo()`’s name (`code-review`), description (`Vs`), argument hint (`Xs`),
user-invocable flag, effort plumbing, and the `ultra` fallback marker.

Adapted: the `/review` alias is intentionally not registered because OpenCode
already owns `/review`; `whenToUse` has no OpenCode command field; the `ultra`
subcommand and `--post` cloud behavior have no host surface.

Gap: low. The command is discoverable and its description/argument hint match
the reference apart from the ultra clauses.

### 2. Argument parsing and flags — 98%

Exact: level-first grammar, target cleanup (`ot`), `med` → `medium` alias (the
binary’s alias map is exactly `{med:"medium"}`), `--max-findings` last-wins
regex, bare/invalid values, `ultra` fallback, and the four boolean flags.
Extensions are stripped before the reference parser runs.

Gap: none material.

### 3. Effort resolution and storage — 88%

Exact: typed > last-used > session > medium; invalid stored effort collapses to
high; ultra resolves to max and does not update the remembered level; a typed
level or `--max-findings` in a non-interactive run is not remembered.

Adapted: Claude Code’s `Dg`/`Ry`/`ig` chain can override the typed effort from
model/session/permission-layer settings. OpenCode exposes the session effort via
the prompt/model variant; the replica uses that as the session fallback. The
precedence is documented end-to-end (explicit > last used > session effort >
medium), and per-role model variants are a planned, low-risk change.

Gap: low. The remaining uncertainty is model-specific override behavior.

### 4. Family detection and dispatch — 95%

Exact: the `he` table, the four families, the cell IDs, `modelEffort`, and the
sonnet-5-only `finderBudgetHint`.

Adapted: Claude model-ID normalization (`et`/`zt`) is approximated by substring
matching for sonnet-5/opus-5/opus-4.8; every unknown or non-Claude model maps to
`default`, which is the reference’s fallback.

Gap: low. A future Claude model ID could map to `default` until the family
matcher is updated.

### 5. Cell definitions and prompt selection — 93%

Exact: all cell shapes, finder counts, per-angle caps, default limits, inline
floors, sweep flags, verify modes, and the `$s` switch. The five captured prompt
variants (`low`, `high`, `xhigh`, `medium`=minimal, `max`) match byte-for-byte,
modulo `Agent` → `subagent`.

Adapted: the finder/verifier/sweep child prompt bodies are reconstructions; the
reference model writes them at runtime.

Gap: medium. Parent prompt behavior is near-exact; child wording is the main
uncertainty.

### 6. Parent prompt assembly — 91%

Exact: the `Js` order — notices, target, finder-budget hint, recipe, comment,
fix, fix-later, `/verify`, output contract. The effort/max-findings notices and
the GitHub/GitLab blocks match the reachable branches.

Adapted/N/A: `Bs` (host message mode), `yn` (end marker), and the ultra cloud
branches have no OpenCode equivalent. The `/verify` block is gated on a locally
installed `verify` skill.

Gap: low. The missing blocks are host-only.

### 7. Diff discovery and scope — 87%

Exact/equivalent: upstream/main/HEAD~1 probing, working-tree inclusion, PR
numbers via `gh`, branch and range targets, path restriction, deleted/renamed
files, `diffLines`, and ancestor-scoped `CLAUDE.md`/`CLAUDE.local.md` discovery.
The unified diff is captured once and passed to every child and the synthesizer.

Adapted: a free-form target becomes a path hint rather than model-interpreted
scope; `AGENTS.md` is included as an OpenCode convention source; GitLab targets
are out of scope per the user.

Gap: medium-low. Free-form instructions are narrower than the reference model’s
interpretation.

### 8. Finder orchestration — 79%

Exact: angle counts (A–C at 3, A–E at 5), cleanup lenses, caps (6/8), the
barrier for v2.1.318, streaming for 2.1.162, grouped for 2.1.221, per-finder
categories, `short_summary`, conventions-text scoping, and the captured diff in
every finder prompt.

Adapted: the child finder prompts are reconstructions; the engine schedules
deterministically instead of the model choosing Agent calls. Per-role
model/effort is implemented: the runner no longer forces the parent model, and
each agent can set `model: provider/model#variant`.

Gap: medium-high. Wording and per-role effort are the largest behavioral
uncertainties.

### 9. Candidate dedup — 85%

Exact criteria: a `review-synth` child now dedups **before verification** with
the reference’s sentence, “Dedup candidates that point at the same
line/mechanism, keeping the one with the most concrete failure scenario.”
Unclaimed candidates are backfilled so nothing is silently dropped.

Validated: Runs 7 and 8 reduced the verifier children from 10 to 6 and still
reported zero duplicate pairs with no partial warning.

Adapted: the synthesizer now receives the captured diff in its prompt, matching
the reference model’s context; the deterministic token merge is the fallback.

Gap: medium-low. C6 is resolved; the remaining uncertainty is model judgment.

### 10. Verification — 88%

Exact: one verifier per remaining candidate, 3-state and recall-biased ladders,
CONFIRMED/PLAUSIBLE kept, REFUTED dropped, evidence quoting, read-only tools,
schema-constrained verdicts, grouped verification for 2.1.221, the captured
diff in the verifier prompt, and the “single non-REFUTED vote” sentence in
both the recall ladder and the max 3-state ladder.

Adapted: the verifier prompt is reconstructed; no per-role effort; the reference
model may choose a different verifier prompt.

Gap: medium-low. The ladder and keep/drop rules are exact.

### 11. Sweep — 87%

Exact: one fresh finder after verification, gaps only, up to 8 candidates, the
exact sweep-focus text (moved code, second-tier footguns, test asymmetry,
config defaults), and the captured diff in the sweep prompt. Its additional
candidates go straight to ranking without a second verification pass, matching
Phase 3.

Adapted: the child sweep prompt is reconstructed; the sweep gets the verified
list and paths-only conventions. The sweep’s `steps` budget is 60 (the finder
budget) because a 15-step cap exhausted it on a 6,102-line diff.

Gap: low-medium.

### 12. Semantic merge and ranking — 86%

Exact criteria: the post-verify `review-synth` applies “Dedup findings that
point at the same line/mechanism, keeping the one with the most concrete failure
scenario” and “Rank most-severe first.” Decisions are index-based, backfilled,
and the representative’s own location is not repeated in the “also at” marker.
The synthesizer receives the captured diff, matching the reference model’s
context.

Validated: Runs 6–8 all produced zero duplicate pairs and no partial warning;
Runs 7 and 8 both reported 5 distinct findings.

Adapted: the synth lacks the diff; the deterministic fallback ranks correctness
before cleanup and CONFIRMED before PLAUSIBLE.

Gap: medium-low. Ranking is model judgment in the reference; the fallback is a
heuristic.

### 13. Output contracts — 96%

Exact: the JSON array with exactly `file/line/summary/failure_scenario`; the
ReportFindings payload with `level/findings` and the extended fields; the `jt`
human renderer with control-character sanitization; the 32-entry cap; category
and short_summary.

Adapted: the `code_review` tool returns `formatReportFindings(engine)` as
metadata, the OpenCode equivalent of a host findings list.

Gap: low. The ReportFindings output schema is not declared (host API limit).

### 14. ReportFindings tool — 91%

Exact: name, description, input schema, closed objects, JS safe-integer line
bounds, result text, 32 cap, and the `outcome` enum.

Adapted: the command path renders text; a host that renders the typed list uses
the tool metadata. A `ReportFindings` call with outcomes posts a deduped
synthetic summary, so the command path shows the per-finding result.

Gap: medium-low. Outcome host integration is partial.

### 15. Actions — 80%

Exact: the `--fix` block and the `--comment` blocks; GitHub inline comments via
`gh api`; GitLab note via `glab` (out of scope per user); the ignore notice when
the target is not a PR.

Adapted: the engine posts comments directly instead of the model using an MCP
inline-comment tool. Suggestion blocks are planned as optional internal fields
(`suggestion`/`start_line`) rendered as a GitHub suggestion fence; the
`ReportFindings` schema stays unchanged. `--fix` edits stay in the parent
session so `/rewind` still restores them.

Gap: medium. Suggestion blocks and checkpoint behavior are platform-limited.

### 16. Notices — 95%

Exact: effort typo/reuse, max-findings ignored/reused/cap, ultra fallback,
`--post` ignored, and the “level typed last time” wording.

N/A: cloud-capable ultra branches.

Gap: low.

### 17. Failure behavior — 76%

Exact/equivalent: malformed finder → zero candidates; malformed verifier →
candidate dropped; malformed sweep → no gaps; agent-unavailable fallback prompt;
cancellation interrupts child sessions; schema validation retries up to three
times; step-capped children.

Adapted: `partial` and warnings are an extension; the reference prompt has no
equivalent marker. The reference model may retry a malformed child instead of
dropping it.

Gap: medium-low.

### 18. Host integration — 78%

Exact/equivalent: command and tool registration, ReportFindings, five schema
tools, child sessions, read-only permissions, skill-list envelope handling, and
typed metadata.

Adapted: the command currently blocks the turn; the reference terminal review
runs as a background subagent (`-p`/SDK is foreground, which our `code_review`
tool path matches). The background design is READY: the command callback can
return early, the report posts with `session.synthetic({ resume: false })`, and
a fix/`/verify` result posts with `session.prompt({ delivery: "queue" })`.
`--foreground` and `--cancel` are planned extensions. The default child
concurrency is 4 vs the Agent tool’s 20, a provider-rate-limit adaptation. The
`opencode api` client caps requests at ~6 minutes; long runs need
`curl`/another client.

The fixed 300s child timeout was removed after the self-review lost three
finders on a 6,102-line diff. There is no wall-clock cap; the agent’s `steps`
field is the real bound, matching Claude’s `maxTurns`, and cancellation
interrupts the children. A port-derived **stall watchdog** now covers the
remaining hang: if a child’s `time.updated` does not change for
`CODE_REVIEW_STALL_MS` (default 600s), the runner interrupts it; a healthy
long-running child keeps re-arming the watchdog. `time.updated` is turn-level,
so 180s interrupted healthy max-effort finders; the higher default and a
no-retry-after-stall rule fixed the retry cascade in self-review 6.

Gap: medium-low. Background mode remains the main missing host behavior;
per-role effort and `--fix` outcomes are implemented.

### 19. Tests and provenance — 96%

Exact: 253 tests; byte-exact comparisons against the captured `low`/`high`/
`xhigh`/`medium`/`max` variants; the no-dedup/rank-code search; five clean e2e
runs with documented results, plus a self-review of the implementation.

Gap: low-medium. Role-prompt and known-defect benchmark harnesses are designed
but not run.

---

## 3. Gap ranking

| Rank | Gap | Confidence in that area | Severity | Next action |
|---|---|---|---|---|
| 1 | Child finder/verifier/sweep prompt wording | 72–79% | High | V1 harness READY: run the role prompt and the reference parent prompt on the same diff with a judge. |
| 2 | Interactive background review | 78% | Medium | C1 READY: command path background, tool path foreground, `--foreground`/`--cancel`. |
| 3 | `--comment` suggestion blocks | 80% | Low-medium | C4 READY: optional `suggestion`/`start_line` internal fields + fence. |
| 4 | Failure/partial semantics | 80% | Low | Keep the extension; document that the reference has no partial marker. |
| 5 | ReportFindings output schema / outcome rendering | 40% | Low | C10 deferred; OpenCode’s Promise tool API has no output schema, metadata is the equivalent. |

Resolved in the third run: all 32 self-review findings were fixed, including
the per-role model wiring (C3), `--fix` outcome surfacing (C7), the opt-in
artifact, the `CODE_REVIEW_PARTIAL` stderr record, and the exact-only
pre-verify dedup. Effort precedence and concurrency are documented.

### Research evidence (2026-11-11)

The pending plan re-checked every remaining gap against the primary docs:

- Claude Code’s `/code-review` page confirms the terminal review is a background
  subagent, `-p`/SDK is foreground, a second review runs foreground, and a
  background `--fix` is outside session checkpoints.
- Claude Code subagents support `model`, `effort`, and `maxTurns`; OpenCode
  agents support `model: provider/model#variant` and `steps`.
- OpenCode plugin commands expose only `sessionID`, `prompt`, and `delivery`;
  there is no interactive-vs-API flag. The command/tool split is the mapping.
- OpenCode `session.synthetic({ resume: false })` and
  `session.prompt({ delivery: "queue" })` provide the background completion
  path; `session.create` accepts a model ref with a variant.
- GitHub suggestion blocks are Markdown fences; the REST API supports
  `start_line`/`line`.
- Martian’s 50-PR/173-comment benchmark and ReviewBench’s 219-PR benchmark are
  the validation corpora.

Full designs and acceptance criteria: [`CODE_REVIEW_PENDING_PLAN.md`](CODE_REVIEW_PENDING_PLAN.md).

Resolved: C6 (the synthesizer now receives the captured diff) is closed in this
pass. The dedup and merge groups rose accordingly. The P1 self-review timeout
(three finders cut off at 300s on a 6,102-line diff) is also fixed: there is no
default wall-clock cap, and the agent `steps` field is the bound.

## 4. N/A, not gaps

These are reference-only host features with no OpenCode surface, so they are not
counted against fidelity:

- Ultra cloud review and its `--post` behavior.
- The `/verify` follow-up when no `verify` skill is installed.
- `Bs` message-mode outcome text.
- `yn` end-of-response marker.
- Skill-preload family override.
- `whenToUse` command metadata.
- The `/review` alias (OpenCode already owns `/review`).
- GitLab targets (explicitly dropped by the user).

## 5. Deliberate extensions (not reference behavior)

`code_review` tool, `--json`, `--mode`, `--family`, `--model`, `--driver`,
`--concurrency`, `--keep-sessions`, `--full-fleet`,
`--semantic-merge`/`--no-semantic-merge`, `--verbose`, `--dry-run`, and
`AGENTS.md` convention discovery.

One prompt adaptation is tracked separately: `GITHUB_COMMENT` adds a
GitHub-Enterprise `--hostname` sentence that the captured block does not have.
It affects comment posting only; the review prompt and findings are unchanged.

These are labeled as extensions; they do not count toward the fidelity
percentages.

## 6. How to raise the overall confidence

1. **Role-prompt benchmark**: run a golden diff through the reference and the
   replica, compare child outputs and final findings. This is the only way to
   raise the finder/verifier/sweep confidence above ~80%.
2. **Background mode**: implement the terminal background behavior while
   keeping `-p`/API foreground.
3. **Outcome extraction**: read the model’s re-report after `--fix` and surface
   the per-finding outcome.
4. **Per-role effort**: add the configurable variant map once a provider is
   known to support variants.
5. **Known-defect benchmark**: measure recall/precision on a corpus with
   ground-truth bugs; this measures quality, not fidelity, but it tells you
   whether the reconstruction is useful.
