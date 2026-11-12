# code-review-opencode — Reconstructing Claude Code's Native Code-Review System for OpenCode

> **Naming:** this project is `code-review-opencode`; its command is
> `/code-review-opencode`. Mentions of `/code-review` in this document name
> Claude Code's original command.

**Research date:** 2026-11-10
**Reference implementation:** Claude Code **v2.1.318** (locally installed native binary)
**Latest published snapshot checked:** Claude Code **v2.1.322** (Piebald-AI, 2026-11-09/10)
**Reconstruction target:** OpenCode **v2.2.5**

This report records what was actually recovered, how it was recovered, which
claims are verified, and where the reconstruction necessarily differs. It is
deliberately not a summary of READMEs: every load-bearing claim is tied to a
binary offset, a file blob SHA, or a reproducible command.

---

## 0. Executive summary

1. **The current `/code-review` is not the hidden multi-agent workflow.** The
   workflow existed in v2.1.162 and v2.1.221, and `/code-review` routed to it
   for a short window. The routing prompt was removed in **v2.1.232**, and the
   workflow script is **absent from the v2.1.318 binary**. The current system is
   a bundled skill whose prompt is assembled at runtime from a model-family ×
   effort dispatch table.

2. **The dispatch table is model-specific, and this is the single most
   important finding.** At v2.1.318 the same typed level runs a different
   recipe depending on the model family:

   | Family | medium | high | xhigh | max |
   |---|---|---|---|---|
   | default | inline 8-angle | inline 8-angle | inline 10-angle + sweep | multi-agent 10 + verify + sweep |
   | claude-sonnet-5 | multi-agent 8 + verify | multi-agent 8 + recall verify | multi-agent 10 + verify + sweep | same as xhigh |
   | claude-opus-4-8 | inline 8-angle | inline 8-angle | inline 10-angle + sweep | multi-agent 10 |
   | claude-opus-5 | **minimal** | **minimal** | inline 10-angle + sweep | multi-agent 10 |

   The Clawdipedia v2.1.311 capture (`high effort → 8 inline angles → dedup
   (no verify)`) is exactly the `o48-high-v1` cell used by the **default** and
   **opus-4-8** families at `high`. It is not a fallback and not a newer
   architecture; it is one cell of the table.

3. **The multi-agent path still exists** for `claude-sonnet-5` at
   medium/high/xhigh and for every family at `max`. Its prompt is prose that
   tells the main model to fan out through the `Agent` tool; there is no
   deterministic workflow engine in the current binary.

4. **The extracted workflow sources are real but historical.** v2.1.162 used a
   streaming pipeline with a 25-verifier budget and a 5-line dedup bucket.
   v2.1.221 replaced it with a barrier, location-grouped verification, one
   merged cleanup finder, and index-based synthesis. Both are preserved here as
   named compatibility modes; neither is the current default.

5. **The official Anthropic plugin is a different product.** It is PR-only,
   uses four fixed agents plus per-issue confidence scorers, filters below 80,
   and posts GitHub comments. It overlaps in spirit but not in contract.

6. **OpenCode cannot reproduce the reference exactly** because it has no
   schema-constrained subagent output, no `ReportFindings` host tool, no
   `Agent` tool with the same semantics, and no bundled workflow runtime. The
   reconstruction supplies a deterministic orchestrator, a schema-compatible
   `ReportFindings` adapter, and tolerant structured-output parsing. The
   remaining differences are enumerated in
   `CODE_REVIEW_EQUIVALENCE_REPORT.md`.

---

## 1. Sources and evidence labels

Evidence labels used throughout:

- **VERIFIED** — direct source text, a reproducible extraction, or a runtime
  observation.
- **STRONGLY SUPPORTED** — independent sources agree, but the exact runtime
  behavior was not reproduced.
- **INFERRED** — a plausible reading of incomplete evidence.
- **UNKNOWN** — insufficient evidence.

| # | Source | Revision | Date / version | Type | What it proves |
|---|---|---|---|---|---|
| S1 | Local Claude Code binary `~/.local/share/claude/versions/2.1.318` | SHA-256 `677a2ea7bf576cedd20e191d973914ed8a41796f53a63b1923381ddc4d5b5e7d` | 2026-11-03 build; v2.1.318 | Shipped artifact | The complete current dispatch table, all prompt builders, the argument parser, the `ReportFindings` schema, and the absence of the workflow script. **VERIFIED** |
| S2 | [Piebald-AI/claude-code-system-prompts](https://github.com/Piebald-AI/claude-code-system-prompts) | `main` @ `05e3f645073f4a31c27627a0437e82f298b69b41` | 2026-11-10; v2.1.322 | Extracted prompts (MIT) | Per-fragment files with `ccVersion` headers, independent corroboration of the binary text, and the version history in `CHANGELOG.md`. **VERIFIED** for text; **STRONGLY SUPPORTED** for v2.1.322 parity |
| S3 | [six-ddc gist: Claude Code bundled workflows](https://gist.github.com/six-ddc/e64a4531de33d63c7e13debcfe8bc2fb) | revision `fac413c84c2a12ca056ad4b5f858aad69a47f1f3` | v2.1.162 | Reverse-engineered source | The full v2.1.162 workflow JS, including `LEVEL_PARAMS`, `MAX_VERIFY = 25`, the dedup key, streaming `pipeline`, and the synthesis fallback. **VERIFIED** as an extraction; provenance is the author's stated byte offsets |
| S4 | [six-ddc/skills `workflows/code-review-extracted.js`](https://github.com/six-ddc/skills/blob/main/workflows/code-review-extracted.js) | blob `b22e695358` | v2.1.221 | Reverse-engineered source with constants resolved | The v2.1.221 workflow: barrier, one merged cleanup finder, location grouping, index synthesis, backfill. **VERIFIED** as an extraction |
| S5 | [Clawdipedia: Skill, /code-review](https://clawdipedia.cc/prompts/skills/skill-code-review) | page capture | Claude Code v2.1.311 | Captured runtime prompt | The assembled high-effort inline prompt, including the Reuse/Simplification/Altitude texts that Piebald does not publish separately. **VERIFIED** as a capture; matches the `co()` builder in S1 |
| S6 | [Anthropic official code-review plugin](https://github.com/anthropics/claude-plugins-official/blob/main/plugins/code-review/commands/code-review.md) | blob `8d1533fa42` | current `main` | Official source | The PR-only 4-agent + confidence-scoring workflow, threshold 80, CLAUDE.md compliance agents, permalink rules. **VERIFIED** |
| S7 | [Anthropic plugin README](https://github.com/anthropics/claude-plugins-official/blob/main/plugins/code-review/README.md) | blob `42cc8095cd` | current `main` | Official docs | Agent roles, false-positive list, confidence scale, comment format. **VERIFIED** |
| S8 | [six-ddc/codex-dynamic-workflows](https://github.com/six-ddc/codex-dynamic-workflows) | `main`; MIT | current | Portable runtime | Implements `agent()`/`parallel()`/`pipeline()`/`workflow()`/`phase()`. Supports Codex, Gemini, pi — **not OpenCode**. **VERIFIED** (README + provider registry) |
| S9 | OpenCode v2.2.5 docs and local API contract | `https://opencode.ai/docs/*`; `/openapi.json` from the running service | 2026-11-10 | Official docs + runtime schema | Agents, commands, plugins, child sessions, permissions, model refs. **VERIFIED** |

### 1.1 How S1 was read

The native binary is a Bun single-file executable. Its JavaScript bundle is
stored as **plain UTF-8**, not bytecode, so no decompiler is required. The
review module was located by searching for the literal
`Run **8 independent finder angles**` and carving a 150 KB window around it:

```bash
grep -a -o -b "Run \*\*8 independent finder angles\*\*" ~/.local/share/claude/versions/2.1.318
# 277943261, 277944540 (multi-agent medium/high), 277950031 (inline)
```

The window `277,870,000–278,020,000` was decoded (`\uXXXX`, `\\n`, `` \\` ``)
into `sources/cc-2.1.318-review-full.txt`. Every prompt fragment in the
reconstruction was then checked by normalized-substring search against that
decoded text; 15 of 18 matched literally and the remaining 3 matched after
restoring their `${...}` interpolation markers (they are templates, not
literals). See `test/prompts.test.ts`.

REA (`reverse-engineer-anything`) was available, but a disassembler adds
nothing when the target strings are plaintext. Direct byte-range extraction is
the stronger evidence here: it preserves exact bytes and is reproducible with
`grep`/`dd`/SHA-256. No native code path was needed for any claim in this
report.

### 1.2 Version history (code-review only)

| Version | Change | Evidence |
|---|---|---|
| 2.1.147 | GitHub `--comment` posting fragment | S2 `ccVersion` |
| 2.1.154 | `/simplify` 4-cleanup-agent workflow | S2 |
| 2.1.160 | Base finder angles A/B/C; recall-biased verification | S2 |
| **2.1.162** | Hidden `code-review` workflow: streaming find→verify, 25-verifier budget, 7/9 finders | S3 |
| 2.1.173 | Three-state verification; Angles B–E; Phase 0/2/3; efficiency and altitude dimensions | S2 |
| 2.1.178 | Conventions (CLAUDE.md) dimension | S2 |
| 2.1.196 | `ReportFindings` tool description | S2 |
| 2.1.206 | Consolidated correctness-finder block | S2 |
| 2.1.213 | Inline gap sweep; agent-unavailable inline mode | S2 |
| **2.1.221** | Workflow rewritten: barrier, merged cleanup finder, location grouping, index synthesis | S4 |
| 2.1.223 | `/review` slash command removed | S2 CHANGELOG |
| 2.1.224 | `/code-review` workflow routing added (ultra alias) | S2 CHANGELOG |
| 2.1.227 | Code-review command tool description removed; ultrareview comment poster | S2 CHANGELOG |
| **2.1.232** | **Workflow routing removed**; artifact publishing removed | S2 CHANGELOG |
| 2.1.235 | `--fix` fragment; low-effort minimum-findings mode | S2 |
| 2.1.248 | Workflow tool description (canonical pipeline example) | S2 |
| 2.1.257 | GitLab `--comment` posting | S2 |
| 2.1.260 | Standalone altitude dimension removed (folded into cleanup text) | S2 CHANGELOG |
| 2.1.288 | Configurable `--max-findings`; all review prompts updated; minimal mode | S2 |
| 2.1.290 | Levels become `low|medium|high|xhigh|max` | S2 CHANGELOG |
| 2.1.309 | Self-hosted runner token-fd error | S2 |
| **2.1.311** | Effort must precede target; Clawdipedia capture | S2, S5 |
| **2.1.318** | Local reference binary | S1 |
| 2.1.322 | Latest Piebald snapshot; no code-review changes in 2.1.319–2.1.322 | S2 |

The 2.1.319–2.1.322 changelog entries mention artifact intake, unsaved tool
output, and REPL descriptions; none mention `/code-review`. The reconstruction
therefore treats **v2.1.318 as the reference** and records v2.1.322 parity as
**STRONGLY SUPPORTED**, not verified.

---

## 2. The current architecture (v2.1.318)

### 2.1 Entry point

`/code-review` is a bundled, user-invocable skill with alias `review`
(S1, `wo()` registration). Its argument hint is:

```
[low|medium|high|xhigh|max] [--fix] [--comment] [<pr#>|<branch>|<path>] [--max-findings <n>|all]
```

`ultra` is accepted as a fallback marker: it maps to a billed cloud review and,
when unavailable, falls back to a local `max` review with an explicit notice.

### 2.2 Argument grammar (`xe`)

- `--max-findings` is extracted first by
  `/(^|\s)--max-findings(?:(?:\s*=\s*|\s+)(?!--)(\S+)|\s*=\S*)?(?=\s|$)/g`.
  The **last** occurrence wins.
- `--comment`, `--fix`, `--post`, `--no-post` are boolean flags.
- The first token is matched against the level set after lowercasing and
  applying the only alias, `med → medium`.
- A token that starts like a level but is not one (`highh`, `medum`) is
  reported as `unrecognizedLevel` and **stays in the target string**.
- `ultra` as the first token sets `ultraFallback`.
- A leading backtick and a leading `#` are stripped from the target's first
  token.

### 2.3 Effort resolution (`yo`)

```
explicit ?? lastUsed ?? sessionEffort ?? "medium"
```

Then `oL`: an invalid string collapses to `high`; `undefined` collapses to
`medium`. `max` is user-triggered only; the command description tells the model
not to choose it on its own judgment.

### 2.4 Model-family dispatch (`Ie`, `he`, `$s`)

The family is derived from the model id. The dispatch table is reproduced
verbatim in `cells.ts`. Two details matter:

- `modelEffort` is `"typed"` for almost every cell, meaning the API reasoning
  effort equals the typed level. `claude-sonnet-5` at `low` is the exception:
  it maps to `"medium"`.
- `finderBudgetHint` is true only for `claude-sonnet-5` high/xhigh/max. Those
  cells inject a diff-size hint before the prompt:

  ```
  This diff is about N lines. Spawn about Y finder subagents (min 2, max 8) —
  scale your investigation depth to the diff size rather than using a fixed
  large fleet.
  ```

  with `Y = max(2, min(8, ceil(N / 150)))`.

### 2.5 Output selection

The output contract is chosen by whether the `ReportFindings` tool is
available:

- available → `Vt(max)`: one `ReportFindings` call with `{level, findings}`;
  entries carry `file`, `line`, `summary`, `short_summary` (≤60), `failure_scenario`,
  `category`, and `verdict` when a verify pass ran.
- unavailable → `Yt(max)`: a bare JSON array of
  `{file, line, summary, failure_scenario}`, or `[]`.

The tool schema is reproduced in `reportfindings.ts`; `findings` is capped at
**32** by the tool. The `--max-findings` cap of 32 is applied **only when
`ReportFindings` is available**; the JSON contract can carry any count.

### 2.6 Execution paths

```
parse args
  → effort
  → family → cell
  → max-findings
  → cell.engine:
      inline  → one recovered prompt in the current context
      minimal → one recovered prompt, ReportFindings only
      multi   → multi-agent prompt (model-driven) or engine (deterministic)
```

The multi-agent prompt's phases:

1. **Phase 0** — gather the diff (`@{upstream}...HEAD`, `main...HEAD`,
   `HEAD~1`, plus `git diff HEAD`).
2. **Phase 1** — N independent finder angles via the `Agent` tool, each with a
   candidate cap.
3. **Phase 2** — dedup; one verifier per candidate; 3-state or recall-biased.
4. **Phase 3** — one gap sweep (xhigh/max only).
5. **Output** — rank, cap, emit.

### 2.7 The hidden workflow is gone

`grep -a "Workflow-backed code review"` and
`grep -a "one finder per correctness angle"` return **no hits** in v2.1.318.
`initBundledWorkflows` still exists, but the `code-review` workflow is not
registered. Telemetry in `Js()` hard-codes `routed_to_workflow:!1`.

This is the decisive contradiction with any source that presents the workflow
as the current default. The workflow is a **historical compatibility mode**.

---

## 3. The historical workflow implementations

### 3.1 v2.1.162 (S3)

```
Scope
  → pipeline(Find → dedup → Verify)   // no barrier
  → Sweep (xhigh/max)
  → Synthesize
```

- `LEVEL_PARAMS`: high = 3 correctness + 4 cleanup, ×6, ≤10; xhigh/max =
  5 + 4, ×8, ≤15; sweep only xhigh/max.
- `MAX_VERIFY = 25`; overflow is recorded in `budgetDropped`.
- Dedup key: `file + ":" + round(line/5)*5`, or
  `file + ":x:" + summary.toLowerCase().slice(0,40)` when no line.
- One verifier per candidate; `CONFIRMED`/`PLAUSIBLE` survive, `REFUTED` does
  not; a missing verdict drops the candidate.
- Synthesis agent returns `{summary, findings}`; failure salvages the ranked
  verified findings unmerged.

### 3.2 v2.1.221 (S4)

```
Scope
  → Find (barrier)
  → group by (file,line)
  → Verify (one agent per location, N verdicts)
  → Sweep (xhigh/max)
  → Synthesize (index decisions)
```

- high = 3 correctness + **1 merged cleanup** (5 lenses), ×6, ≤10;
  xhigh/max = 5 + 1, ×8, ≤15.
- No verifier budget.
- `canonFile` suffix-matches candidate paths against the scope's file list.
- A missing index in the group verdict drops that candidate.
- Synthesis returns `{summary, decisions:[{index, merge}]}`; the assembler
  merges by index, escalates the verdict to `CONFIRMED` if any merged member is
  `CONFIRMED`, backfills omitted verified findings, and appends a note to the
  summary.

The two versions are **not interchangeable**. The reconstruction keeps them as
separate named modes (`cc-workflow-2.1.162`, `cc-workflow-2.1.221`).

---

## 4. The official Anthropic plugin (S6, S7)

A different implementation with the same command name:

| Property | Official plugin |
|---|---|
| Entry | `/code-review [--comment]` on a GitHub PR |
| Preconditions | PR open, not draft, not trivial, not already reviewed |
| Context | haiku eligibility check; haiku CLAUDE.md discovery; sonnet summary |
| Reviewers | 4 parallel: 2× CLAUDE.md compliance (sonnet), 2× bug (opus) |
| Verification | one validator per issue; opus for bugs, sonnet for CLAUDE.md |
| Filter | confidence < 80 dropped |
| Output | terminal, or inline GitHub comments with full-SHA permalinks |
| False positives | pre-existing, correct-looking, nitpicks, linter-catchable, general quality, ignored rules |

It is **not** the bundled skill. It requires GitHub, uses a fixed 4-agent
shape, and has no effort levels, no `--fix`, no `--max-findings`, and no
workflow modes. The reconstruction does not implement it; it is documented as a
distinct reference.

---

## 5. Prompt inventory

All fragments live in `.opencode/plugins/code-review-opencode/prompts/` with a SHA-256
manifest. The complete table is in `CODE_REVIEW_SOURCE_MANIFEST.md`. Summary:

| Phase | Fragments | Source |
|---|---|---|
| Phase 0 | `phase-0` | S1 `K`; S2 blob `2fa6dc10` |
| Find | `angle-a`…`angle-e` | S1; S2 blobs `d6430d58`, `55c4d40c`, `aead7fe9`, `8e8a601d`, `d088b0ff` |
| Cleanup | `reuse`, `simplification`, `efficiency`, `altitude`, `conventions` | S1; S5 for reuse/simplification/altitude; S2 for efficiency/conventions |
| Precedence | `candidate-precedence` | S1; S4 `CLEANUP_PRECEDENCE` |
| Verify | `verdict-ladder`, `verdict-ladder-recall`, `verify-3state`, `verify-recall` | S1; S2 blobs `851f9b27`, `d91d782f`, `080e4205`, `cd03d76f` |
| Sweep | `sweep`, `sweep-focus` | S1; S2 blob `fe3d8976`; S4 `SWEEP_GAP_FOCUS` |
| Output | built in `prompts.ts` (`outputJson`, `outputReportFindings`) | S1 `Yt`, `Vt` |
| Low/minimal | built in `prompts.ts` | S1 `Kt`, `Xt`, `no`, `Ze` |
| Inline | built in `prompts.ts` (`inlineMedium/High/Xhigh`, `inlineFallback`) | S1 `ao`, `ro`, `co`, `Ps`, `Qe` |
| Multi | built in `prompts.ts` (`multiMedium/High/Xhigh`) | S1 `Jt`, `Qt`, `Zt` |
| Actions | `GITHUB_COMMENT`, `gitlabComment`, `fixBlock`, `FIX_LATER` | S1 `Us`, `js`, `Hs`, `Fs` |

The interpolation graph is in `CODE_REVIEW_SOURCE_MANIFEST.md` §3.

---

## 6. Contradictions and how they were resolved

| Claim | Contradicting evidence | Resolution |
|---|---|---|
| "The hidden workflow is the `/code-review` engine." (S3, S4 READMEs) | v2.1.232 changelog removes routing; v2.1.318 binary has no workflow script; telemetry says `routed_to_workflow:!1` | True for v2.1.162–~v2.1.231; false for the current release. Kept as a compatibility mode. |
| "Clawdipedia's 8-inline-angle high prompt is the new architecture." | It is exactly the `o48-high-v1` cell in the v2.1.318 dispatch table, used by the default and opus-4-8 families. | Not a new architecture; a model-specific recipe. The multi-agent path remains for sonnet-5 and for `max`. |
| "The official plugin is the bundled skill." | Different entry, 4 fixed agents, confidence 80, PR-only, no effort levels. | Two distinct implementations that share a command name. |
| "v2.1.221 workflow is the same as v2.1.162." | Different finder counts, barrier vs pipeline, grouped vs per-candidate verify, index vs text synthesis. | Separate modes; no hybrid by default. |
| "ReportFindings caps at 32, so `--max-findings all` is capped at 32." | The cap is applied only when the tool is available; the JSON contract passes `all` through. | Reproduced exactly: `resolveMaxFindings` applies 32 only for ReportFindings/minimal cells. |
| "`extra-high` is a valid level." | The parser's only alias is `med`. `extra-high` is an unrecognized token. | Reproduced: valid levels are `low|medium|high|xhigh|max`, plus `med`. |

---

## 7. OpenCode integration findings

- **V2 plugin API** (`@opencode/plugin`, `Plugin.define`) provides
  `ctx.session.create({parentID, agent, model})`, `session.prompt`,
  `session.wait`, `session.context`, `session.interrupt`, `tool.transform`, and
  `command.transform`. This is sufficient for a real deterministic
  orchestrator with independent child sessions.
- **Subagents are real child sessions with fresh context.** The plugin creates
  one per finder/verifier/sweep/synthesis call. Parallelism is real
  (`Promise.all` + a concurrency gate).
- **No schema-constrained output.** `session.prompt` has no `format`/schema
  field. The reconstruction extracts the first balanced JSON value and
  validates it against the recovered schema; malformed output follows the
  reference's drop policy.
- **No `ReportFindings` tool.** The plugin registers a schema-compatible
  adapter with the same name and fields.
- **No `Agent` tool named `Agent`.** The reference interpolates `${ut}`; in
  OpenCode it resolves to `subagent`. The engine does not rely on the model
  spawning agents; it creates the child sessions itself.
- **Child sessions do not inherit the parent model by default** in the API
  path used here. The runner passes the parent's `Model.Ref` explicitly.
- **Command handlers are durable user prompts.** A plugin command that returns
  without calling `session.prompt` still leaves a turn for the main agent. The
  command therefore submits the engine report with an explicit "do not re-run"
  instruction.
- **`codex-dynamic-workflows` is MIT but does not support OpenCode.** It is a
  reference for the `agent()/parallel()/pipeline()` shape, not a dependency.

---

## 8. What the reconstruction does not claim

- It does not claim byte-identical model behavior. Models differ; only prompt
  text, orchestration, budgets, and schemas can be exact.
- It does not claim v2.1.322 runtime parity. The binary inspected is v2.1.318;
  v2.1.322 parity is inferred from the unchanged Piebald fragments and the
  absence of code-review changelog entries.
- It does not claim the official plugin is reproduced. It is documented as a
  separate implementation.
- It does not claim the workflow modes are current. They are labeled
  compatibility modes with their source versions.

---

## 9. Reproducing the research

```bash
# binary identity
shasum -a 256 ~/.local/share/claude/versions/2.1.318

# locate the review module
grep -a -o -b "Run \*\*8 independent finder angles\*\*" ~/.local/share/claude/versions/2.1.318

# the decoded window used for every prompt check
python3 - <<'PY'
import re
p = __import__('os').path.expanduser('~/.local/share/claude/versions/2.1.318')
data = open(p, 'rb').read()[277_870_000:278_020_000].decode('utf-8', 'replace')
data = re.sub(r'\\u([0-9a-fA-F]{4})', lambda m: chr(int(m.group(1), 16)), data)
open('cc-2.1.318-review-full.txt', 'w').write(data.replace('\\\\n', '\n').replace('\\n', '\n'))
PY
```

The decoded window and the source manifest are checked into `sources/` for
audit; they are research inputs, not runtime dependencies.

---

## 10. Second-pass update (2026-11-11)

The second pass added a full mechanism-by-mechanism map:
[`CODE_REVIEW_ORCHESTRATION_MAP.md`](CODE_REVIEW_ORCHESTRATION_MAP.md).

Key additions:

1. **The prompt corpus is verified byte-for-byte.** The online captures at
   `asgeirtj/system_prompts_leaks` (`Anthropic/claude-code/skills/code-review/`)
   and `xsyetopz/claude-code-docs` were compared with the binary-extracted
   constants. `low`, `high`, `xhigh`, `medium` (minimal), and `max` match
   exactly, modulo `Agent` → `subagent`. The captures are saved under
   `sources/skill-code-review/`.

2. **There is no runtime reference-file mechanism.** The binary contains no
   `low.md`/`high.md`/`xhigh.md`/`max.md`/`report-findings-tool.md` strings,
   and the only `code-review` registration (`wo()`) has no `files:` property.
   The online per-effort files are captures/decompositions of the command's
   prompt variants, not files the skill loader reads. The official Anthropic
   plugin is a different, older 4-agent/confidence-scored design.

3. **Two prompt bugs were found and fixed.** The `max` prompt was missing
   “Keep candidates where the vote is CONFIRMED or PLAUSIBLE.”; the minimal
   prompt said `≤15 findings` instead of `at most 15 findings`.

4. **Schema-constrained child output is wired.** The plugin now registers
   `code_review_candidates`, `code_review_verdict`, `code_review_group_verdicts`,
   `code_review_report`, and `code_review_decisions`, with text-JSON fallback.
   The read-only child agents allow only the tool each role needs.

5. **Notices and schema constraints match the reference.** `ei`/`go` use the
   recovered wording; `ReportFindings` closes both objects and carries the
   JS safe-integer `line` bounds from the published schema.

6. **Tests: 71 passing at the second pass** (92 after the third-pass
   additions), including a test that compares the assembled prompts against the
   captured skill files.

---

## 11. Third-pass research: dedup/rank and public ports (2026-11-11)

The question was whether the dedup and surrounding orchestration can be
recovered exactly, or must be approximated.

### 11.1 No dedup/rank code exists

A byte search of the v2.1.318 binary found **no** `dedup`, `merge`, `rank`,
`same root cause`, `dedupCandidates`, `mergeFindings`, or `rankFindings`
helper. The only dedup/rank instructions are model-facing:

- `Wt` Phase 2: “Dedup candidates that point at the same line/mechanism,
  keeping the one with the most concrete failure scenario.”
- `Yt`/`Vt` output: “Ranked most-severe first. If more than N survive, keep
  the N most severe.”

The reference model performs the merge/rank in-context. There is no hidden
deterministic algorithm to extract.

### 11.2 The replica now uses the actual method

`review-synth` receives the verified findings and returns merge/rank decisions
by index using those exact criteria. It runs by default for `max` and
multi-agent `xhigh`; `--no-semantic-merge` disables it. The deterministic
token merge remains the pre-verify approximation and the fallback if the
synthesizer fails. This is a model-driven replication of the reference method,
not a third-party dedup heuristic.

### 11.3 Public ports: what was adopted and rejected

The full catalog, including ultra-style and adjacent ports, is in
[`CODE_REVIEW_PORTS.md`](CODE_REVIEW_PORTS.md).

Adopted because it maps to a real gap:

- **Structured-output contract** (`StructuredOutput` tool, validator error,
  retry limit) — platform equivalent of Claude Code’s Agent output schema.
- **Per-role turn caps** (`steps` finder/sweep 20, verifier/synth 15) — equivalent of the Agent tool’s
  `maxTurns`.
- **Semantic synthesis** — the model-driven dedup/rank above.
- **`/verify` follow-up** — the reference’s `Gs`/`Ws` block, gated on a
  locally installed `verify` skill.

Rejected because it would diverge from local `/code-review`:

- **`REVIEW.md` injection.** Official docs: local `/code-review` follows
  `CLAUDE.md` and **does not read `REVIEW.md`**; that file configures the
  managed cloud Code Review service.
- **Codex-port PR filters** (linter/pre-existing/nitpick/unchanged-line
  filters). Not in the v2.1.318 command prompt; they belong to the older
  official plugin.
- **`/simplify` chaining.** The reference’s after-review block is `/verify`,
  not `/simplify`.
- **Embeddings, neutral rankers, model pools, `confirmed_by`.** Not in the
  reference; the synthesizer already covers the semantic judgment.

### 11.4 Official behavior confirmed

- Local `/code-review` runs as a background subagent in a terminal session and
  in the foreground under `-p`/SDK; host apps that request a findings list use
  `ReportFindings`.
- A `--max-findings` value or effort level typed in a non-interactive `-p` run
  is **not** remembered. The replica now stores choices only for an interactive
  command without `--json`.
- The Agent tool defaults to 20 concurrent subagents; the replica keeps a
  lower default for provider rate limits and exposes `--concurrency`.
- `maxTurns` partial output is marked by Claude Code; the replica’s per-role
  `steps` cap is the equivalent.

### 11.5 Links

- Codex port: https://github.com/ttxs69/code-review-codex
- Pi port: https://github.com/fyeeme/pi-packages/tree/main/pi-review
- Pi package notes: https://pi.dev/packages/@fyeeme/pi-review
- Structured outputs:
  https://code.claude.com/docs/en/agent-sdk/structured-outputs
- Subagents: https://code.claude.com/docs/en/agent-sdk/subagents
- Local review: https://code.claude.com/docs/en/code-review-local
- Dedup issue: https://github.com/tag1consulting/ai-pr-review/issues/15
- Hybrid dedup: https://hackenproof.com/blog/build-a-multi-agent-ai-code-review-pipeline
- Empirical max run:
  http://quickchat.ai/post/claude-code-multi-agent-code-review
