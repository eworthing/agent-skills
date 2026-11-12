# code-review-opencode — Code-Review Orchestration Map

> **Naming:** this project is `code-review-opencode`; its command is
> `/code-review-opencode`. Mentions of `/code-review` in this document name
> Claude Code's original command.

Reference: Claude Code **v2.1.318**, Mach-O arm64, SHA-256
`677a2ea7bf576cedd20e191d973914ed8a41796f53a63b1923381ddc4d5b5e7d`.

This document maps every orchestration mechanism in Claude Code's code-review
surface to its equivalent in the OpenCode reconstruction. It separates three
things that are easy to conflate:

1. **What the reference actually ships** (observed in the binary or a verified
   capture).
2. **What is reconstructed** (the reference behavior is model-driven, so the
   replica has to choose a deterministic execution).
3. **What is an OpenCode-only extension** (no reference equivalent).

Status legend:

| Status | Meaning |
|---|---|
| **EXACT** | Text, table, or rule recovered and reproduced byte-for-byte, modulo documented tool-name substitution. |
| **EQUIVALENT** | Same observable behavior through a different host mechanism. |
| **ADAPTED** | Reference behavior depends on the model or host; the replica implements a deterministic approximation. |
| **EXTENSION** | No reference equivalent; added for OpenCode ergonomics. |
| **N/A** | Reference-only host feature with no OpenCode surface. |

---

## 0. The two code-review surfaces

Claude Code v2.1.318 exposes **two distinct review surfaces**, plus one cloud
surface and one older plugin:

| Surface | Registration | Prompt source | Effort model |
|---|---|---|---|
| **`/code-review` command** | `wo()` → `bl({name:hY, aliases:["review"], ...})` | Assembled in code by `Js()` from `$s()` and the `he` cell table | Family × effort → cell |
| **`code-review` bundled skill** | Same `wo()` registration, also listed in `wTr`; loaded by the Skill tool with `skill: "code-review"` | `SKILL.md` capture = the default high prompt; the binary assembles the other efforts in `Js()` | Effort → cell prompt |
| **`/code-review ultra`** | `subcommands:{ultra:"ultrareview"}`; cloud orchestrator `K6r`/`z6r` | Cloud session | Cloud fleet |
| **Official `code-review` plugin** | `anthropics/claude-code` marketplace plugin | `plugins/code-review/commands/code-review.md` | 4 agents + 0–100 confidence score, threshold 80 |

The reconstruction targets the **command** and mirrors the **captured prompt
variants**. The official plugin is a different, older design and is **not** the
same algorithm.

### 0.1 Reference files: what actually exists

This directly answers "are there reference-type files used in different cases?"

**In the binary: no runtime reference files.** The only code-review
registration is `wo()`, and it has no `files:` property:

```js
function wo(){bl({name:hY, aliases:["review"], ..., getPromptForCommand:Js})}
```

A byte search of the v2.1.318 binary finds **zero** occurrences of
`low.md`, `high.md`, `xhigh.md`, `max.md`, or
`report-findings-tool.md`. The command assembles every effort variant in code
through `$s()` and the `he` cell table. The `code-review` entry in the bundled
skill list `wTr` is the same registration, not a separate file-backed skill.

**Online captures present the variants as files.** The leak repo
`asgeirtj/system_prompts_leaks` stores the corpus as:

```
Anthropic/claude-code/skills/code-review/
  SKILL.md                    # default: high inline, JSON output
  low.md                      # low inline, JSON, ≤4
  medium.md                   # minimal single pass, ReportFindings, ≤15
  high.md                     # high inline, JSON, ≤10, floor 5
  xhigh.md                    # xhigh inline, JSON, ≤15, floor 7, sweep
  max.md                      # max multi-agent, JSON, ≤15, verify + sweep
  report-findings-tool.md     # ReportFindings description + JSON schema
```

These are **captures/decompositions of the command's prompt variants**, not
evidence of a runtime file-loading mechanism. They are still valuable: they
independently verify the text we recovered from the binary. They are saved
verbatim under `sources/skill-code-review/`, alongside the
`xsyetopz/claude-code-docs` 2.1.311 capture
(`docs/prompts/skills/skill-code-review.md`).

Our assembled prompts match the captured variants exactly:

| Captured file | Our function | Result |
|---|---|---|
| `low.md` | `lowPrompt("json", 4)` | **EXACT** |
| `high.md` / `SKILL.md` body | `inlineHigh("json", 10)` | **EXACT** |
| `xhigh.md` | `inlineXhigh("json", 15)` | **EXACT** |
| `medium.md` | `minimalPrompt(15)` | **EXACT** |
| `max.md` | `multiMax("json", 15)` | **EXACT** after `Agent` → `subagent` |
| `report-findings-tool.md` | `REPORT_FINDINGS_SCHEMA` + description | **EXACT** |

`prompts.test.ts` asserts these comparisons against
`sources/skill-code-review/`.

**The official plugin is different.** `anthropics/claude-code`'s
`plugins/code-review/commands/code-review.md` is a single command file with no
reference files. It runs 4 agents (2 CLAUDE.md compliance, 2 bug) plus
confidence scoring and an 80-point threshold. It is not the v2.1.318
command/skill algorithm.

---

## 1. Reference control flow (command, v2.1.318)

```
/code-review <args>
  │
  ├─ xe(args)                       argument grammar
  │    ├─ --comment --fix --post --no-post
  │    ├─ --max-findings <n>|all|default   (last occurrence wins)
  │    ├─ ultra → ultraFallback
  │    └─ level token → explicit | unrecognizedLevel | target
  │
  ├─ rt(parsed)                     last-used effort (storageV5)
  ├─ yo(parsed)                     effort resolution
  ├─ pc(context) → Ie(model)        model family
  ├─ he[family][effort] → cell      dispatch
  ├─ it(context) → j                ReportFindings availability
  ├─ fo(parsed, cell, U)            max-findings resolution
  ├─ Qs(model, effort, target)      diff-size finder hint
  ├─ ei(...) + go(...)              notices
  ├─ $s(cell, output, agent, U, limit)
  │    └─ one of Kt/Xt/Jt/Qt/Zt/no/ro/co/Ps/Ze/Qe
  ├─ decorate: target + comment + fix + fix-later + message + verify
  ├─ getContext → "fork" | "inline"
  └─ getPromptForCommand → Js(...)
       └─ forked context runs the prompt; model spawns Agent subagents
            find → dedup → verify → sweep → rank/cap
```

### 1.1 Where the orchestration actually runs

In v2.1.318 there is **no JavaScript workflow engine** for the command. The
prompt tells the main model to:

- run N independent finder angles via the `Agent` tool;
- dedup candidates;
- run one verifier per candidate via the `Agent` tool;
- run one more finder as a gap sweep;
- rank, cap, and report.

The model chooses the child prompts. `subagent_type` defaults to
`"general-purpose"` unless a more specific type fits. There is no bundled
finder/verifier agent definition for code review.

This is why the exact child prompts cannot be recovered from the binary: they
are generated by the model at runtime. The replica's child prompts are
reconstructions; the parent prompts and all orchestration rules are exact.

The older hidden workflows (`v2.1.162`, `v2.1.221`) were separate workflow
scripts. They were removed from the command path at v2.1.232. The reconstruction
keeps them as `cc-workflow-2.1.162` and `cc-workflow-2.1.221` for comparison,
not as v2.1.318 behavior.

---

## 2. Argument parsing (`xe`)

Recovered exactly:

| Rule | Reference | Replica |
|---|---|---|
| Level first | First whitespace token | `parseArgs` |
| Aliases | `oN` + `le` alias map (`med` → `medium`) | `normalizeLevel` |
| Level-looking typo | `qs = ^(low|med|hig|xhi|max)[a-z]*$` case-insensitive | same |
| Target | `ot(tokens)`: strip backticks from first token, strip leading `#`, rejoin | `cleanTarget` |
| `--max-findings` | `uo` regex; last match wins; bare or `=n` | `MAX_FINDINGS_RE` |
| Invalid max | `maxFindingsIgnored = true` | same |
| `ultra` | `ultraFallback = true`, target after it | same |
| Flags | `--comment`, `--fix`, `--post`, `--no-post` stripped by `Xe` | `stripFlags` |
| `--post` | Only meaningful for ultra; notice otherwise | notice |

Extensions stripped before the reference parser: `--json`, `--mode`,
`--driver`, `--family`, `--model`, `--concurrency`,
`--keep-sessions`, `--full-fleet`, `--quiet`, `--verbose`, `--dry-run`.

---

## 3. Effort resolution (`yo`)

Reference order:

```
ultraFallback ? "max"
  : explicit ?? lastUsed
  : model-specific turn effort (Dg)
  : session effort (Ry)
  : "medium"
```

`oL` normalizes invalid values to `high`. `st(family, level)` maps a cell's
`modelEffort`:

- `"typed"` → pass the typed level through;
- `"medium"` → sonnet-5 `low` runs at medium API effort.

Replica:

```
resolveEffort(parsed, lastUsed, sessionEffort):
  ultraFallback ? "max"
  : explicit ?? lastUsed ?? sessionEffort ?? "medium"
  → coerceLevel
```

`sessionEffort` comes from the OpenCode session's model variant / prompt effort.
The reference's `Dg`/`Ry`/`ig` chain is host-specific; the replica's simpler
precedence is documented as **ADAPTED**.

Storage:

- `codeReviewLastEffort` — written when an explicit level is typed.
- `codeReviewLastMaxFindings` — written when `--max-findings` is typed;
  `default` clears it.

Both use the OpenCode plugin storage (`ctx.storage`).

---

## 4. Family dispatch and the cell matrix (`he`)

Family detection (`Ie`): normalize the model ID; if it names a known family,
use it; otherwise `"default"`. The reference's `Os` set forces `"default"` for
opus-4-8/opus-5 during skill preload.

| Family | low | medium | high | xhigh | max |
|---|---|---|---|---|---|
| `default` (DeepSeek, unknown, GPT, etc.) | `low` | `o48-high-v1` | `o48-high-v1` | `o48-xhigh-v1` | `max` |
| `claude-sonnet-5` | `low-sonnet5` | `medium` | `high` | `xhigh` | `max` |
| `claude-opus-4-8` | `o48-low-v1` | `o48-med-v1` | `o48-high-v1` | `o48-xhigh-v1` | `max` |
| `claude-opus-5` | `low` | `o5-bmin` | `o5-bmin` | `o48-xhigh-v1` | `max` |

`finderBudgetHint` is attached to the **family entry**, not the shared cell:
only sonnet-5 `high`/`xhigh`/`max` get the diff-size hint. Default-family max
intentionally keeps the full 10-finder fleet.

### 4.1 Cell behavior

| Cell | Engine | Finders | Per-finder cap | Verify | Sweep | Default limit |
|---|---|---|---|---|---|---|
| `low` | inline | 0 | — | none | no | 4 |
| `low-sonnet5` | inline | 0 | — | none | no | none (min files,4 target) |
| `medium` | multi | 8 (3 correctness + 5 cleanup) | 6 | 3-state | no | 8 |
| `high` | multi | 8 (3 + 5) | 6 | recall-biased | no | 10 |
| `xhigh` | multi | 10 (5 + 5) | 8 | 3-state | yes | 15 |
| `max` | multi | 10 (5 + 5) | 8 | 3-state | yes | 15 |
| `o48-low-v1` | inline | 0 | — | none | no | 8 |
| `o48-med-v1` | inline | 8 angles | 6 | none | no | 8 (floor 4) |
| `o48-high-v1` | inline | 8 angles | 6 | none | no | 10 (floor 5) |
| `o48-xhigh-v1` | inline | 10 angles | 8 | none | yes | 15 (floor 7) |
| `o5-bmin` | minimal | 0 | — | none | no | 15 |

Cleanup angles are Reuse, Simplification, Efficiency, Altitude, Conventions.
Correctness angles are A (line scan), B (removed behavior), C (cross-file),
D (language pitfalls), E (wrapper/proxy). A–C run at every multi level; D–E
only at xhigh/max.

Inline floor injection (`so`): `max(1, floor(min(limit, defaultMax) / 2))`.
This applies to `o48-med-v1`, `o48-high-v1`, `o48-xhigh-v1`; it does not apply
to the multi cells.

### 4.2 Prompt switch (`$s`)

| Cell | Builder | Output |
|---|---|---|
| `low` | `Kt(hasReportFindings, limit)` | ReportFindings or JSON |
| `low-sonnet5` | `Xt(hasReportFindings)` | ReportFindings or JSON |
| `medium` | `Jt(hasReportFindings, agentAvailable, limit)` | ReportFindings or JSON |
| `high` | `Qt(...)` | ReportFindings or JSON |
| `xhigh` | `eo = Zt("xhigh")` | ReportFindings or JSON |
| `max` | `to = Zt("max")` | ReportFindings or JSON |
| `o48-low-v1` | `no(hasReportFindings, limit)` | ReportFindings or JSON |
| `o48-med-v1` | `ro(hasReportFindings, limit)` | ReportFindings or JSON |
| `o48-high-v1` | `co(hasReportFindings, limit)` | ReportFindings or JSON |
| `o48-xhigh-v1` | `ho = Ps` | ReportFindings or JSON |
| `o5-bmin` | `Ze(limit)` | always ReportFindings |

When the `Agent` tool is unavailable, `Jt`/`Qt`/`Zt` fall back to `Qe`, the
generic single-pass inline prompt. `Qe` includes the angle list, a dedup/self-check
phase, an optional same-context sweep, the output contract, and the
"single-pass review" disclosure. The `o48-*` cells are always inline.

---

## 5. Prompt assembly (`Js`)

Exact order:

```
ei(notices)                         effort/ultra/post notices
go(maxFindings)                     limit notices
target line                         Review target: `...`
Qs(finderBudget)                    only when finderBudgetHint
$s(cell, output, agent, U, limit)   the recipe
Us / js                             --comment block
Hs(U)                               --fix block
Fs                                  fix-later block (U && cell !== o5-bmin)
Bs                                  message-outcome note (j === "message")
Ws                                  /verify suggestion (host-gated)
yn                                  end-of-response marker
```

`Fs` is appended whenever ReportFindings is in use and the cell is not
`o5-bmin`, even without `--fix`: if findings are fixed later in the session,
the model must re-report them with `outcome`.

`Bs` only applies when ReportFindings is declared by the host's message mode
(`it(context) === "message"`). OpenCode has no equivalent; the replica's
ReportFindings tool result is the report.

`Ws`/`Gs` recommend running `/verify` after the review when the diff has a
runtime surface. OpenCode has no bundled `/verify`; the replica omits this
block (N/A) rather than inventing one.

`yn` is a host marker for parsing the end of a non-fork response. OpenCode
returns tool results directly; N/A.

---

## 6. Prompt corpus and exactness

Every fragment below is stored in
`.opencode/plugins/code-review-opencode/prompts/` and hashed in `manifest.json`.
The reference constants were extracted from the binary region
`~277.93–277.98 MB`; the skill files were captured online and cross-checked.

| Reference constant | Purpose | Replica | Status |
|---|---|---|---|
| `K` | Phase 0 diff gathering | `phase-0.md` / `PHASE_0` | EXACT |
| `ys` | Angle A | `angle-a.md` | EXACT |
| `ws` | Angle B | `angle-b.md` | EXACT |
| `vs` | Angle C | `angle-c.md` | EXACT |
| `ks` | Angle D | `angle-d.md` | EXACT |
| `Cs` | Angle E | `angle-e.md` | EXACT |
| `we` + `Gt` | short Reuse for multi | `reuse.md` | EXACT (`Gt` + `we` equals long `oo`) |
| `oo` | long Reuse for inline | `reuse.md` | EXACT |
| `Z` | Simplification | `simplification.md` | EXACT |
| `oe` | Efficiency | `efficiency.md` | EXACT |
| `ne` | Altitude | `altitude.md` | EXACT |
| `ue` | Conventions | `conventions.md` | EXACT |
| `de` | cleanup candidate note | `candidate-precedence.md` | EXACT |
| `Es` | 3-state verdict ladder | `verdict-ladder.md` | EXACT |
| `Ss` | recall-biased ladder | `verdict-ladder-recall.md` | EXACT |
| `qt` | sweep focus | `sweep-focus.md` | EXACT |
| `As` | Phase 3 sweep block | `sweep.md` | EXACT (placeholder substitution) |
| `Wt` | Phase 2 3-state verify | `verify-3state.md` | EXACT (placeholder substitution) |
| `Ts` | Phase 2 recall verify | `verify-recall.md` | EXACT (placeholder substitution) |
| `Yt` | JSON output contract | `outputJson` | EXACT |
| `Vt` | ReportFindings contract | `outputReportFindings` | EXACT |
| `Kt` | low | `lowPrompt` | EXACT |
| `Xt` | low-sonnet5 | `lowMinimumPrompt` | EXACT |
| `no` | o48-low | `lowExpandedPrompt` | EXACT |
| `ro` | o48-medium | `inlineMedium` | EXACT |
| `co` | o48-high | `inlineHigh` | EXACT |
| `Ps` | o48-xhigh | `inlineXhigh` | EXACT |
| `Jt` | medium multi | `multiMedium` | EXACT |
| `Qt` | high multi | `multiHigh` | EXACT |
| `Zt` | xhigh/max multi | `multiXhigh` / `multiMax` | EXACT |
| `Ze` | minimal | `minimalPrompt` | EXACT |
| `Qe` | agent-unavailable fallback | `inlineFallback` | EXACT |
| `xs` | "Agent tool isn't available" | `inlineFallback` | EXACT |
| `Is` | single-pass disclosure | `inlineFallback` | EXACT |
| `Je` | "perform each angle yourself" | `AGENT_UNAVAILABLE` | EXACT |
| `Us` | GitHub comment block | `GITHUB_COMMENT` | ADAPTED (port-only GHE `--hostname` sentence) |
| `js` | GitLab comment block | `gitlabComment` | EXACT |
| `Hs` | `--fix` block | `fixBlock` | EXACT |
| `mo` | re-report with outcome | `fixBlock`/`FIX_LATER` | EXACT |
| `Fs` | fix-later block | `FIX_LATER` | EXACT |
| `Bs` | message-outcome note | — | N/A |
| `Gs`/`Ws` | after-review `/verify` | — | N/A |
| `ei` | effort/ultra/post notices | `effortNotice`/`ultraNotice`/`postNotice` | EXACT (local/fallback branches) |
| `go` | max-findings notices | `maxFindingsNotice` | EXACT |
| `Vs` | command description | command description | EXACT (ultra clause omitted) |
| `Ks` | when-to-use | — | N/A (OpenCode has no field) |
| `Xs` | argument hint | `argumentHint` | EXACT (no `ultra`) |
| `nls` | ReportFindings description | tool description | EXACT |
| `ar` | ReportFindings schema | `REPORT_FINDINGS_SCHEMA` | EXACT |
| `lr` | ReportFindings tool behavior | tool execute | EXACT |
| `jt` | terminal renderer | `formatHuman` | EXACT |
| `Ft` | fork result formatter | — | ADAPTED (engine formats directly) |
| `Qs` | diff-size finder hint | `plannedFinderCount` | EXACT formula |
| `Zs` | diff line counter | `scope.diffLines` | EQUIVALENT |
| `fo` | max-findings resolution | `resolveMaxFindings` | EXACT |
| `rt`/`Ys`/`zs` | last effort storage | `ctx.storage` | EQUIVALENT |
| `st` | model effort mapping | `modelEffort` field | EXACT table, host-limited |
| `he` | dispatch table | `V318_FAMILIES`/`V318_CELLS` | EXACT |

### 6.1 Known text differences

Only two classes remain:

1. **Tool name**: the reference says `Agent`; OpenCode's tool is `subagent`.
   The substitution is applied in every prompt and asserted by the skill-file
   test for `max.md`.
2. **Host-only blocks**: `Bs`, `Gs`, `Ws`, `yn`, and the ultra clauses have no
   OpenCode equivalent and are omitted rather than fabricated.

Line wrapping is otherwise byte-exact; the earlier apparent mismatches were
artifacts of the extraction script (escaped backticks and `\u2014`).

---

## 7. Child-agent orchestration: reference vs replica

### 7.1 Reference

- The main model receives the recipe prompt in a forked context.
- It spawns `Agent` children with `subagent_type: "general-purpose"` unless a
  more specific type fits.
- Finder children get one angle, the diff scope, and a candidate cap; they
  return `file`, `line`, `summary`, `failure_scenario`.
- The model dedups semantically (same line/mechanism, keep the most concrete
  scenario).
- One verifier per remaining candidate returns CONFIRMED / PLAUSIBLE / REFUTED
  with a quoted line.
- A fresh finder sweeps for gaps not on the verified list.
- The model ranks most-severe first, caps at the stated limit, and calls
  ReportFindings or prints JSON.

### 7.2 Replica

- `runReview` builds finders from the cell.
- Each finder is a child session (`review-finder`) with a deterministic prompt.
- Barrier (`cc-2.1.318`), streaming (`2.1.162`), or grouped (`2.1.221`)
  scheduling is selected by the cell.
- **Pre-verify dedup is the actual method.** A synthesizer child applies the
  reference’s Phase 2 sentence — “Dedup candidates that point at the same
  line/mechanism, keeping the one with the most concrete failure scenario” —
  before verification. `applyCandidateDedup` keeps the most concrete scenario
  and backfills unclaimed candidates so the synthesizer cannot silently drop a
  non-duplicate. If the synthesizer fails, the deterministic token merge is
  the fallback:
  - exact claims merge;
  - same file + compatible line + paraphrase-level token overlap merge
    (calibrated at Jaccard ≥ 0.17 or containment ≥ 0.30, from observed finder
    paraphrases at 0.17–0.43 Jaccard);
  - the merge is transitive across a cluster;
  - a cleanup helper declared at line N and paraphrased at line N+1 merges
    when the two summaries share two non-generic content tokens; correctness
    and convention claims on adjacent lines do not;
  - distinct claims at the same line with almost no shared vocabulary stay
    separate.
- **Post-verify semantic merge is the actual method.** A synthesizer child
  (`review-synth`) receives the verified list and returns merge/rank decisions
  by index using the reference’s exact criteria — “Dedup findings that point
  at the same line/mechanism, keeping the one with the most concrete failure
  scenario” and “Rank most-severe first.” This runs by default for `max` and
  for multi-agent `xhigh`; `--no-semantic-merge` disables it. If the
  synthesizer fails, the deterministic merge/rank is the fallback.
- The captured unified diff is included in every finder, verifier, sweep,
  dedup, and merge prompt (120k-character budget), matching the reference
  model’s shared diff context. Because the diff is already in the prompt,
  child prompts tell the agent to use it directly and run the diff command
  only when the included copy is truncated. The reference model makes that
  choice itself; the explicit instruction is a child-prompt adaptation.
- One verifier child (`review-verifier`) per candidate (or per location for
  grouped mode) returns a typed verdict. At `max`, the verifier uses the
  3-state ladder plus the reference’s recall sentence.
- One sweep child (`review-sweep`) gets the verified list. Its “additional
  candidates” go straight to ranking, exactly as in the reference’s Phase 3;
  they are not re-verified.
- Findings are ranked correctness-first, CONFIRMED before PLAUSIBLE, then by
  location; the cap is applied last.
- The result is formatted by `formatHuman` / `formatJson` / `formatToolResult`.

### 7.3 What is exact vs adapted

| Mechanism | Status |
|---|---|
| Roles (finder/verifier/sweep), counts, caps, phases | EXACT |
| Verify ladders and keep/drop rules | EXACT |
| Sweep focus text | EXACT |
| Output contracts | EXACT |
| Parent prompt assembly | EXACT |
| Child prompt wording | ADAPTED (model-generated in reference; included-diff instruction) |
| Semantic dedup | EXACT criteria, model-driven via `review-synth`; deterministic pre-verify fallback |
| Ranking | ADAPTED (deterministic sort) |
| Scheduling/barriers | ADAPTED (host sessions) |
| Failure reporting | EXTENSION (`partial` + warnings) |

The reference's Phase 2 dedup is performed by the main model; there is no
specified deterministic key. The replica's token-overlap merge is a
reconstruction, not a recovered algorithm.

---

## 8. ReportFindings

Recovered exactly from the binary and the published schema:

- Tool name: `ReportFindings`.
- `searchHint`: "report code-review findings as a structured list".
- `backgrounding: "never"`, `maxResultSizeChars: 256`, `strict: true`.
- Read-only, concurrency-safe.
- Input: `{ level?, findings: Array(max 32) }`.
- Finding: `{ file, line?, summary, short_summary?≤60, failure_scenario,
  category?≤40, verdict?: CONFIRMED|PLAUSIBLE, outcome?: fixed|skipped|no_change_needed }`.
- Required: `file`, `summary`, `failure_scenario`.
- Both objects are closed (`additionalProperties: false`).
- `line` is an integer with JS safe-integer bounds; no minimum of 0.
- Result text: `"No findings reported."` or `"N finding(s) reported."`.
- Result data: `{ count, level, findings }`.

The 32-entry cap applies only when the ReportFindings contract is active, or
for `o5-bmin`. `--json` bypasses it. `fo` maps `all` or any value above 32 to
32 for those paths.

Replica:

- `ReportFindings` is registered as an OpenCode tool with the same schema,
  description, and result text.
- `normalizeReportFindings` validates strictly: an invalid verdict, missing
  required field, unknown property, overlong `short_summary`/`category`, or
  >32 entries rejects the call so the model re-emits the complete list; valid
  findings survive. An invalid optional `level` is ignored.
- `formatToolResult` emits the exact reference text.
- The 32 cap is enforced by `resolveMaxFindings` and the schema's `maxItems`.
- A completed engine run can write a private report artifact when
  `CODE_REVIEW_REPORT_DIR` is set; the JSON file is written directly in that
  directory. A normal review writes nothing into the checkout. The `--json`
  stdout contract remains a bare array.

---

## 9. Actions

### 9.1 `--fix`

Reference: `Hs(U)` appends the fix block to the prompt. The model applies the
findings to the working tree, skips behavior-changing/out-of-scope/false-positive
fixes, and re-reports with `outcome` when ReportFindings is active.

Replica: the command appends `fixBlock(kind)` to the prompt and sets the
explicit `needsModel` flag when `--fix` applies or a `/verify` follow-up is
present. The engine itself remains read-only. Child agents are read-only; the
main session performs fixes. **EQUIVALENT** (the reference also applies fixes
in the review context, not in the finder children).

### 9.2 `--comment`

Reference:
- GitHub PR: inline comment per finding via
  `mcp__github_inline_comment__create_inline_comment`, fallback `gh api`.
- GitLab MR: one general note via `glab mr note`.
- Otherwise: print and note that `--comment` was ignored.

Replica: `postComments` uses `gh api` per finding with `commit_id`, `path`,
`line`, `side=RIGHT`, bounded concurrency, and a checked-out branch-PR
lookup. GitHub and GitLab are detected from the origin remote; GitLab MR
posting is a notice (documented non-goal). **EQUIVALENT for GitHub**, with a
documented GitLab divergence.

### 9.3 `--post`

Reference: only for `/code-review ultra` on a GitHub.com PR; posts the finished
review as a single comment. Otherwise a notice.

Replica: always a notice; no cloud path. **N/A**.

### 9.4 `--max-findings`

Reference: `fo` + `go`, stored in `codeReviewLastMaxFindings`; `default` clears
it. Replica: `parseArgs` preserves `"default"`, `resolveMaxFindings` clears it,
and the command stores `null`. **EXACT**.

### 9.5 `--json`

Reference: `i9()` output format `json` disables ReportFindings and uses the
JSON-array contract. Replica: `--json` selects `OutputKind = "json"`, bypasses
ReportFindings, and prints a bare array. **EQUIVALENT** (OpenCode flag name is
an extension; the contract is exact).

---

## 10. Notices, storage, and limits

### 10.1 Effort notice (`ei`)

Reference variants:

- unrecognized level:
  `Ignoring unrecognized effort "X"; valid: low, medium, high, xhigh, max. Using <level>[, the level the user typed last time].`
- no level + last used:
  `No effort level given — reusing <last>, the level the user typed last time[; running at <level> here].`
- ultra fallback: one of the cloud-unavailable variants.
- `--post`: the typed flag applies only to ultra and was ignored.

Replica: `effortNotice` covers the first two; `ultraNotice` emits the
reference's "isn't available in this environment" branch (or the `--fix`
variant), and `postNotice` emits the exact `--post` wording with the
GitHub/GitLab and comment/no-comment variants. The cloud-capable ultra branches
are N/A. **EXACT** for the reachable branches.

### 10.2 Max-findings notice (`go`)

Reference:

- ignored flag: `` `--max-findings` was ignored: type a whole number above zero, `all`, or `default` after it.``
  plus ` Using the usual limit.` when not reused.
- asked but no stated limit:
  `` `--max-findings` does not change this review: low effort here has no maximum.``
- stated !== asked:
  `<The user|You> set `--max-findings <asked>` last time. This review reports at most 32 findings, so the limit is 32 here.`
  or the cap note alone.
- reused with a valid limit:
  `Reporting every finding, as <the user|you> chose last time with `--max-findings all`.`
  or `Reporting up to N finding(s), the limit <the user|you> set last time with `--max-findings`.`

Replica: `maxFindingsNotice` implements the same branches and uses "the user"
for the command path. **EXACT**.

### 10.3 Finder budget (`Qs`)

Only for `finderBudgetHint` cells. `Zs` counts `git diff --numstat` for a
simple range (≤256 chars, ref-like) with hooks/fsmonitor/askPass disabled and a
5 s timeout. `y = max(2, min(8, ceil(lines/150)))`.

The hint text has two variants:

- committed-only: "The committed diff (@{upstream}...HEAD) is about N lines.
  Uncommitted changes aren't counted here, so treat this as a floor — start
  with about Y finder subagents (min 2, max 8) and scale up if Phase 0 finds
  additional working-tree scope."
- with working-tree scope: "This diff is about N lines. Spawn about Y finder
  subagents (min 2, max 8) — scale your investigation depth to the diff size
  rather than using a fixed large fleet."

Replica: `scope.diffLines` + `plannedFinderCount`; the deterministic engine
groups lenses round-robin when the budget is below the full fleet. The
reference leaves grouping to the model. **ADAPTED**.

### 10.4 Storage

Reference keys: `codeReviewLastEffort`, `codeReviewLastMaxFindings`.
Replica uses the same key names in `ctx.storage`. **EQUIVALENT**.

---

## 11. Failure behavior

| Condition | Reference | Replica |
|---|---|---|
| Agent tool unavailable | Prompt tells the model to run every angle and verification itself, single-pass; no verify. | `driver=prompt` emits `Qe` fallback; `driver=engine` still spawns child sessions (the host has `subagent`). |
| Finder returns malformed output | The model may drop it or retry; no typed error. | Treated as zero candidates; warning; `partial=true`. |
| Verifier returns malformed output | The model may drop the candidate or retry. | Candidate dropped; warning; `partial=true`. |
| Sweep fails | The model may continue without it. | No gap candidates; warning; `partial=true`. |
| Cancellation | The host cancels the turn. | Abort signal interrupts child sessions; returns a partial result with a warning. |
| No findings | `[]` / "No findings." / empty ReportFindings. | Same. |
| Invalid JSON escapes (`\``) | The model's structured output avoids this. | `json.ts` repairs invalid escapes before scanning. |
| Host client timeout | The Claude Code client keeps the turn open. | The `opencode api` CLI caps a request at ~6 minutes. A max run can exceed it; the server keeps running. Use `curl` with basic auth (`service.json` password) or a client with no cap, then read the session context. |
| Child wall-clock cap | None; the Agent tool is bounded by `maxTurns`. | None. The agent’s `steps` (finder/sweep 60, verifier/synth 20) is the real bound; cancellation interrupts the child sessions. |
| Plugin hot-reload during a run | N/A (the binary is not edited mid-turn). | The server hot-reloads plugins on save. A running engine holds the old `schemaResults` map while child tools write to the new one, so schema capture is lost and the run looks partial. Do not edit `.opencode` while a review is running. |

`partial` is an **EXTENSION**: the reference prompt has no explicit partial
marker. It is used to avoid presenting an incomplete run as complete.

---

## 12. OpenCode mapping

| Reference mechanism | OpenCode implementation | Status |
|---|---|---|
| `bl({name:hY,...})` command | `ctx.command.transform` → `code-review` | EQUIVALENT |
| `ReportFindings` tool | `ctx.tool.transform` → `ReportFindings` | EXACT |
| `Agent` tool fan-out | `ctx.session.create` + `prompt` + `wait` + `context` | EQUIVALENT |
| Fork context | Child sessions, one per role | EQUIVALENT |
| `subagent_type: general-purpose` | `agent: review-finder` / `review-verifier` / `review-sweep` / `review-synth` | ADAPTED |
| Output schema on Agent calls | Role-specific tools (`code_review_candidates`, etc.) + text-JSON fallback | EQUIVALENT |
| `getContext` inline vs fork | `driver=engine` vs `driver=prompt` | EXTENSION |
| `i9()` output format | `--json` | EQUIVALENT |
| `pc()` model | `--model` / parent session model | EQUIVALENT |
| `Ie()` family | `detectFamily` + `--family` | EQUIVALENT |
| `he` dispatch | `V318_FAMILIES` / `V318_CELLS` | EXACT |
| `$s` prompt switch | `resolveInline` / `resolveMulti` / `resolveAngles` | EXACT |
| `Qs` finder hint | `scope.diffLines` + `plannedFinderCount` | EQUIVALENT |
| `Zs` diff count | `git diff --numstat` in `scope.ts` | EQUIVALENT |
| `fo`/`go` limits | `resolveMaxFindings` + `maxFindingsNotice` | EXACT |
| `ei` notices | `effortNotice`/`ultraNotice`/`postNotice` | EXACT (local/fallback branches) |
| Non-interactive memory | `remember = interactive && !json` | EXACT |
| `Us`/`js` comments | `comment.ts` (`gh api`, `glab mr note`) | EQUIVALENT |
| `Hs` fixes | `fixBlock` + main-session model | EQUIVALENT |
| `Fs` fix-later | `FIX_LATER` | EXACT |
| `jt` renderer | `formatHuman` + `sanitizeControl` | EXACT |
| `Ft` fork formatter | Engine formats directly | ADAPTED |
| `Ws`/`Gs` `/verify` | `verifyFollowUp` gated on `hasSkill(..., "verify")` | EQUIVALENT |
| Pre-verify dedup | `candidateDedupPrompt` + `applyCandidateDedup` | EXACT criteria, model-driven; deterministic fallback |
| ReportFindings `category` | `categoryFor` carries the angle slug | EXACT |
| Finder context independence | `renderScope(..., { includeConventions })` | EXACT |
| Schema validation/retry | detailed validators + 3 attempts | EQUIVALENT |
| Per-role turn caps | agent `steps` finder/sweep 60, verifier/synth 20 | ADAPTED |
| Child wall-clock cap | none | EQUIVALENT |
| `yn` end marker | — | N/A |
| Ultra cloud | Fallback notice only | N/A |
| Official plugin 4-agent/confidence | — | N/A (different design) |

---

## 13. Divergences and deliberate omissions

1. **No ultra cloud path.** OpenCode has no equivalent of the Claude cloud
   reviewer. `ultra` is accepted, produces a notice, and runs a local
   max-effort review. This matches the reference's local fallback branch, not
   its cloud branch.
2. **No `/verify` follow-up.** The reference may append a `/verify` suggestion
   when the diff has a runtime surface. OpenCode has no bundled `/verify`; the
   replica omits the block.
3. **No host message mode.** `Bs` only applies when the host renders
   ReportFindings as a message card. OpenCode's tool result is the report.
4. **No end-of-response marker.** `yn` is a Claude Code host parsing aid.
5. **No skill-preload override.** `Os` forces the default family during skill
   preload; OpenCode has no equivalent context.
6. **Deterministic child prompts.** The reference model writes the child
   prompts. The replica's finder/verifier/sweep prompts are reconstructed from
   the parent instructions and the role contracts.
7. **Deterministic dedup/rank.** The reference model dedups and ranks
   semantically. The replica uses exact + token-overlap merging and a stable
   severity/location sort.
8. **`code_review` tool.** An extension so agents can invoke the command
   programmatically. The reference exposes only the command/skill and
   ReportFindings.
9. **`--full-fleet`, `--verbose`, `--driver`, `--mode`, `--family`,
   `--model`, `--concurrency`, `--keep-sessions`, `--dry-run`.**
   Reconstruction controls; none are reference flags.
10. **`--json`.** The reference's output-format switch is a print-mode setting;
    the replica exposes it as a command flag.

---

## 14. Test coverage

`node --test test/*.test.ts` → **253 passing**.

Coverage relevant to this map:

- `parse.test.ts` — argument grammar, aliases, flags, effort precedence,
  max-findings resolution, `default` reset, 32 cap, finder budget, structured
  tool input, declarative cell modes.
- `prompts.test.ts` — fragment hashes, angle ordering, no unresolved markers,
  low/medium/high/xhigh/max shapes, floor injection, agent-unavailable
  disclosure, output contracts, Phase 0 fallbacks, the wf221 grouped-verifier
  recall ladder, the context package, **byte-exact comparison with the bundled
  skill files**.
- `engine.test.ts` — find/verify/sweep barriers, streaming, grouped
  verification, dedup, ranking, caps, malformed outputs, cancellation, the
  shared concurrency gate, refuted-sweep suppression, wf162 no-line synthesis,
  and the combined wf162 e2e.
- `reportfindings.test.ts` — schema, strict finding validation, 32-entry
  rejection, outcome normalization, line-0 handling, human renderer, JSON
  contract, tool result text.
- `scope.test.ts` — repository detection, upstream/main/HEAD~1, working tree,
  ranges, branches, paths, deletions, renames, fresh repos, submodule/nearest
  roots, `@`-prefixed paths, quoted paths, timeouts/abort, the context
  package, conventions ordering/budget, and one-patch/one-metadata PR
  resolution.
- `comment.test.ts` — GitHub/GitLab/other host detection, checked-out branch
  PR resolution, explicit no-PR notice, bounded posting, deterministic failure
  order, line-0 skipping.
- `runner.test.ts` — schema capture, text salvage, one retry, retry limit,
  session removal, keep-sessions, create failure, pre-aborted requests.
- `host.test.ts` — skill envelope handling, runtime-surface exemptions,
  child-session capability probe, recursion guard.
- `artifact.test.ts` — artifact fields, atomic private write, write-failure
  fallback.

---

## 15. Evidence index

| Evidence | Location |
|---|---|
| Command executor `Js` | binary ~277,965,390 |
| Prompt switch `$s` | binary ~277,945,000 |
| Dispatch table `he` | binary ~277,946,000 |
| ReportFindings tool `lr` | binary ~276,603,000 |
| ReportFindings schema `ar` | binary ~276,603,074 |
| ReportFindings description `nls` | binary ~129,052,060 |
| Command registration `wo` | binary ~277,971,738 |
| Human renderer `jt` | binary ~277,959,000 |
| Fork formatter `Ft` | binary ~277,959,000 |
| Finder budget `Qs`/`Zs` | binary ~277,957,000 |
| Notices `ei`/`go` | binary ~277,967,000 |
| Decoded module text | `sources/cc-2.1.318-review-full.txt` |
| Bundled skill files | `sources/skill-code-review/` |
| Skill capture (2.1.311) | `sources/skill-code-review/xsyetopz-capture.md` |
| Official plugin | `sources/anthropic-plugin/` |
| OpenCode built-in `/review` prompt | `sources/opencode-review-prompt.txt` |
| Prompt hashes | `.opencode/plugins/code-review-opencode/prompts/manifest.json` |

### 15.1 External captures consulted

- `asgeirtj/system_prompts_leaks` —
  `Anthropic/claude-code/skills/code-review/{SKILL,low,medium,high,xhigh,max,report-findings-tool}.md`.
- `xsyetopz/claude-code-docs` —
  `docs/prompts/skills/skill-code-review.md` (2.1.311 full text).
- `Piebald-AI/claude-code-system-prompts` — parts 1–10 (angles, low, medium,
  high, xhigh/max, 3-state verify, recall verify, sweep, output,
  ReportFindings).
- `arthrod/claude-code-system-probmpts`, `KrismithReddy12/claude-code-system-prompts`,
  `skogai/claude-system-prompts`, `fivetaku/claude-code-system-prompts` —
  corroborating copies of the same prompt fragments.
- `melian-agent/melian` — independent analysis of the angle/effort matrix.
- `ttxs69/code-review-codex` — independent Codex port of the max pipeline.
- `anthropics/claude-code` plugin `code-review` — older 4-agent,
  confidence-scored design (not the v2.1.318 command).

### 15.2 The dedup/rank search

A byte search of the v2.1.318 binary found **no** `dedup`, `merge`, `rank`,
`same root cause`, `dedupCandidates`, `mergeFindings`, or `rankFindings`
helper. The only dedup/rank instructions are model-facing:

- `Wt` Phase 2: “Dedup candidates that point at the same line/mechanism,
  keeping the one with the most concrete failure scenario.”
- `Yt`/`Vt` output: “Ranked most-severe first. If more than N survive, keep
  the N most severe.”

The reference model performs the merge/rank in-context. The synthesizer
replicates that judgment with the same criteria; it is not a recovered
deterministic algorithm.

### 15.3 Public ports and official behavior references

The full catalog, including ultra-style and adjacent ports, is in
[`CODE_REVIEW_PORTS.md`](CODE_REVIEW_PORTS.md).

Adopted only where they map to a real gap:

- **Codex port** — https://github.com/ttxs69/code-review-codex — full max
  prompt, per-role reasoning effort, PR-comment composer.
- **Pi port** — https://github.com/fyeeme/pi-packages/tree/main/pi-review —
  12 role agents, `maxTurns` finder/sweep 20, verifier/synth 15, finder budget, grouped verification.
- **Structured outputs** —
  https://code.claude.com/docs/en/agent-sdk/structured-outputs — the
  `StructuredOutput` tool, validator re-prompt, retry limit.
- **Subagents** — https://code.claude.com/docs/en/agent-sdk/subagents —
  fresh context, `maxTurns`, partial marking, concurrency default.
- **Local review** — https://code.claude.com/docs/en/code-review-local —
  background subagent, `ReportFindings` host mode, non-interactive memory rule,
  and the fact that local review does **not** read `REVIEW.md`.

Rejected because they diverge from local `/code-review`:

- `REVIEW.md` injection (cloud service only).
- Codex-port PR filters (linter/pre-existing/nitpick/unchanged-line).
- `/simplify` chaining (the reference’s follow-up is `/verify`).
- Embeddings, neutral rankers, model pools, `confirmed_by` (not in the
  reference; the synthesizer covers the semantic judgment).

### 15.4 What remains unknown

- The exact **child-agent prompts** the model writes at runtime. They are not
  shipped. Our role prompts are reconstructions.
- The exact **semantic dedup** and **ranking** the model performs. Our
  deterministic equivalents are documented approximations.
- The **ultra** cloud orchestrator's internal fleet, model routing, and
  aggregation. Out of scope for the local reconstruction.
- The exact **`Dg`/`Ry`/`ig`** effort-override chain, which depends on Claude
  Code's session/permission-layer state. Our precedence is an approximation.

---

## 16. Bottom line

- The **parent prompt corpus is exact** for every cell, both output contracts,
  all action blocks, and all three verify/sweep variants.
- The **dispatch table, parser, limits, storage keys, and ReportFindings
  contract are exact**.
- The **five captured prompt variants match byte-for-byte**, modulo the
  `Agent` → `subagent` tool name. They are captures of the command's prompt
  corpus; the binary has no runtime file-loading mechanism for them.
- The **child-agent execution is a deterministic reconstruction** of a
  model-driven orchestration; its roles, counts, caps, phases, and rules are
  exact. The child prompt wording is reconstructed. Semantic dedup/rank uses
  the reference’s exact criteria through a synthesizer child, with a
  deterministic pre-verify/fallback path.
- The **only reference mechanisms intentionally omitted** are host-only:
  ultra cloud, `/verify` follow-up, message-mode outcome text, end marker, and
  skill-preload family override.
