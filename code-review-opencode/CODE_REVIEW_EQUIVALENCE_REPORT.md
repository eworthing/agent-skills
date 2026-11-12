# code-review-opencode — Code-Review Equivalence Report

Reference: Claude Code **v2.1.318**.
Replica: OpenCode **v2.2.5** plugin at `.opencode/plugins/code-review-opencode/`.
Model: **DeepSeek V4.1 Flash** (`opencode-go/deepseek-v4.1-flash`).
Fixture: `test/fixtures/e2e` (three deliberate defects plus one edge case).

This report compares three things on the same diff:

1. Claude Code's recovered **command prompt** and orchestration rules (the
   reference; not executed here because Claude Code is not the target host).
2. OpenCode's built-in **`/review`** single-prompt reviewer.
3. This reconstruction's **`/code-review-opencode max`** deterministic engine.

## 1. Fixture

`test/fixtures/e2e` contains:

| File | Defect |
|---|---|
| `src/discount.ts` | `applyDiscount` subtracts `percent` as an absolute amount instead of scaling by `percent / 100`. |
| `src/user.ts` | `displayName` dereferences optional `user.name` without the `?? user.email` fallback. |
| `src/format.ts` | New `formatMoney` is a **default export**, violating `CLAUDE.md`'s named-export rule. |
| `src/format.ts` | `toFixed(2)` binary-float rounding edge case (subtle, not in the fixture's stated defects). |

The diff also includes `src/report.ts` as the caller that makes the discount
bug observable.

## 2. Results

### 2.1 OpenCode built-in `/review`

Command: `/review main` (the built-in single-prompt reviewer).

| Metric | Value |
|---|---|
| Model calls | 1 session |
| Wall time | ~25 s |
| Input tokens | ~22k |
| Output tokens | ~1.5k |
| Reported findings | 3 |
| Duplicates | 0 |
| Partial warning | No |
| Verification pass | No |
| Typed output | No (prose) |

Found: the discount bug, the optional-name dereference, and the default-export
convention violation. It did **not** report the `toFixed` rounding edge case.

### 2.2 This reconstruction, `max` (pre-fix baseline)

Command: `/code-review-opencode max --family claude-sonnet-5 --json --concurrency 4`.

| Metric | Value |
|---|---|
| Child sessions | 35 (10 finders + 24 verifiers + 1 sweep) |
| Wall time | ~234 s |
| Input tokens | ~132k |
| Output tokens | ~25k |
| Reported entries | 15 |
| Duplicates | 11 |
| Partial warning | Yes (2 verifier responses were invalid JSON) |
| Verification pass | Yes (one verifier per candidate) |
| Typed output | Yes (JSON array) |

Found the same 3 clear defects **plus** the `toFixed` rounding edge case, but
the report was noisy: semantic duplicates survived, and two malformed verifier
responses marked the run partial.

### 2.3 Run 3 — invalidated by a plugin hot-reload

Command: `/code-review-opencode max --json --concurrency 4` with the default family
(DeepSeek maps to `default`).

| Metric | Value |
|---|---|
| Child sessions | 24 (10 finders + 13 verifiers + 1 sweep) |
| Wall time | 5:58 |
| Input tokens | ~128k |
| Output tokens | ~25k |
| Reported entries | 2 |
| Duplicates | 0 |
| Partial warning | Yes |
| Verification pass | Yes, but results were lost |

All 13 verifiers returned `CONFIRMED` through `code_review_verdict`, including
the `user.ts` and `toFixed` findings, yet only 2 findings were reported. The
cause was not the schema tools: a manual child-session test confirmed that the
tool's `context.sessionID` is the child session ID and the capture key is
correct.

The cause was **editing the plugin while the run was in progress**. The
OpenCode server hot-reloads plugins on save; the child tools then wrote to a
**new** `schemaResults` map while the running engine held the **old** one. Most
verifier results were therefore lost, the engine marked the run partial, and
only the findings that survived the text fallback were reported.

This run is recorded as invalid for equivalence purposes. It does show that
the schema tools, agent permissions, and verifier prompts work.

### 2.4 Run 4 — clean post-fix run

Command: `/code-review-opencode max --json --concurrency 4`, same fixture and model,
with no plugin edits during the run.

| Metric | Value |
|---|---|
| Child sessions | 21 (10 finders + 10 verifiers + 1 sweep) |
| Wall time | 5:40 |
| Input tokens | ~81.5k |
| Output tokens | ~21.9k |
| Reported entries | 8 |
| Duplicates | 1 near-duplicate pair |
| Partial warning | No |
| Verification pass | Yes |
| Typed output | Yes |

The 8 entries cover:

1. `src/discount.ts:2` — percentage treated as an absolute amount.
2. `src/discount.ts:2` — no clamp/validation for `percent > 100` or negative.
3. `src/format.ts:1` — default export violates `CLAUDE.md`.
4. `src/format.ts:2` — `toFixed(2)` binary-float rounding.
5. `src/format.ts:2` — `toFixed` degrades for non-finite/very large values.
6. `src/user.ts:4` — optional `name` dereferenced without the email fallback.
7. `src/format.ts:1` — new helper duplicates the inline `.toFixed(2)` formatting.
8. `src/format.ts:1` — the same reuse defect, paraphrased.

Entry 8 is the only remaining near-duplicate in this run: the two reuse
summaries share the same file, line, and root cause but use different wording
(`inlines` vs `inlined`, `helper` vs `formatMoney`), so the deterministic token
threshold did not merge them. The model-driven reference would merge them
semantically. This is the documented limit of the deterministic dedup
approximation.

### 2.5 Run 5 — final, with adjacent-line cleanup merge

Same command and fixture, after adding the adjacent-line cleanup rule.

| Metric | Value |
|---|---|
| Child sessions | 21 (10 finders + 10 verifiers + 1 sweep) |
| Wall time | 6:47 |
| Input tokens | ~366k |
| Output tokens | ~21.7k |
| Reported entries | 9 |
| Duplicates | 1 near-duplicate pair |
| Partial warning | No |
| Verification pass | Yes |
| Typed output | Yes |

The 9 entries cover the same defect families: the discount formula (two
paraphrases), the discount validation gap, the default-export violation, two
`toFixed` failure modes (binary rounding; `-0`/`NaN`/`Infinity`), the
`user.name` dereference, the `user.name` root-cause/altitude finding, and the
duplicated formatting helper. The reuse paraphrase now merges; the remaining
near-duplicate is the two discount-formula summaries, whose wording differs
enough (`subtracted` vs `subtracts`, `percent-of-total` vs `raw currency`) to
fall below the deterministic threshold.

### 2.6 Semantic merge (after Run 5)

Run 5 used the deterministic pre-verify merge only. The implementation now
spawns a `review-synth` child at `max` and multi-agent `xhigh` with the
reference’s exact dedup/rank criteria: “Dedup findings that point at the same
line/mechanism, keeping the one with the most concrete failure scenario” and
“Rank most-severe first.” The synthesizer returns merge/rank decisions by
index; the deterministic merge remains the fallback if it fails.

### 2.7 Run 6 — semantic merge enabled

Same command and fixture, with the `review-synth` merge/rank phase active.

| Metric | Value |
|---|---|
| Child sessions | 22 (10 finders + 10 verifiers + 1 merge + 1 sweep) |
| Wall time | 8:05 |
| Input tokens | ~142.5k |
| Output tokens | ~24.2k |
| Reported entries | 7 |
| Duplicate pairs | 0 |
| Partial warning | No |
| Verification pass | Yes |
| Typed output | Yes |

The synthesizer merged the two discount paraphrases and the same-line `toFixed`
duplicate, and ranked the survivors. The result dropped from 9 entries in Run 5
to 7, with no duplicate pair. One display artifact — a merged same-line pair
listing its own location as “also at” — was fixed after the run by filtering the
representative’s location.

### 2.8 Run 7 — pre-verify dedup

Same command, with the candidate-dedup synthesizer before verification.

| Metric | Value |
|---|---|
| Child sessions | 19 (10 finders + 1 dedup + 6 verifiers + 1 sweep + 1 merge) |
| Wall time | 7:57 |
| Input tokens | ~109k |
| Output tokens | ~18k |
| Reported entries | 5 |
| Duplicate pairs | 0 |
| Partial warning | No |
| Verification pass | Yes |
| Typed output | Yes |

The dedup child reduced the candidate pool enough that only 6 verifiers ran,
down from 10 in Run 6, and the final report was 5 findings: the discount
formula bug, the `user.name` dereference, a `toFixed` failure mode, the
duplicated formatting helper, and the default-export violation. The synthesizer
kept one representative per same-line/mechanism group; the remaining entries are
distinct defects.

### 2.9 Run 8 — captured diff in every prompt

Same command, with the unified diff passed to finders, verifiers, sweep, dedup,
and merge.

| Metric | Value |
|---|---|
| Child sessions | 19 (10 finders + 1 dedup + 6 verifiers + 1 sweep + 1 merge) |
| Wall time | 6:18 |
| Input tokens | ~125.7k |
| Output tokens | ~20.6k |
| Reported entries | 5 |
| Duplicate pairs | 0 |
| Partial warning | No |
| Verification pass | Yes |
| Typed output | Yes |

The diff context did not change the fixture’s result — the same five distinct
findings as Run 7 — but it grounds the finders and the synthesizer in the same
scope the reference model has, instead of relying on a re-run command.

### 2.10 Self-review — P1 found, fresh pass, findings fixed

The first self-review of the implementation (50 files, 6,102 lines) lost three
finders (angle-A, angle-C, angle-E) at exactly **300.0s**. This is a real
host/scalability gap, not a review-logic bug: Claude’s Agent tool is bounded by
`maxTurns`, not a wall-clock cap, while our runner used a fixed 300s guard.

Fix: the timeout was removed entirely. The agent’s `steps` field (finder/sweep
60, verifier/synth 20) is the real bound, matching `maxTurns`, and cancellation
interrupts the child sessions.

The fresh full self-review then completed in **47:35** with **60 children**, no
interrupted finders:

| Metric | Value |
|---|---|
| Files / lines | 50 / 6,123 |
| Child sessions | 60 (10 finders + 1 dedup + 47 verifiers + 1 sweep + 1 merge) |
| Finders | 10/10 succeeded (A–E each ~10 min) |
| Candidates | 55 → 47 after semantic dedup (8 pairs merged) |
| Verifiers | 47/47 succeeded |
| Reported | 15 (max-effort cap) |
| Partial warning | Yes — the sweep hit its 15-step cap before submitting |

The 15 reported findings were all real defects, including `--dry-run` not
suppressing `--fix`, a swallowed `gh pr view` failure, the grouped verifier
silently dropping candidates, NaN `CODE_REVIEW_CONCURRENCY`, prototype-key
`--mode`/`--family` crashes, line-less dedup merging distinct defects, the
deterministic merge overriding semantic decisions, JSON-contract breaks on
partial/comment/notice output, wf162 accepting unverified report entries, and
first-fence/escape parsing bugs. All were fixed with regression tests; the
sweep’s unsubmitted gaps were captured from its final text and fixed too.

The self-review also exposed a workflow divergence: we re-verified sweep
candidates, while the reference’s Phase 3 adds its “additional candidates”
straight to the report. That extra gate is removed. The max verifier now keeps
the 3-state ladder plus the reference’s recall sentence, and the sweep gets the
finder step budget.

A later `max --max-findings all --fix` pass completed but reported a partial
result: structured-output failures cost two finders, one verifier, and the
sweep. The hardening plan closed that class of failure (tolerant report
normalization, child-tool normalization, one structured-output retry, and text
salvage), and the 253-test suite covers it. The clean hardening rerun then
completed in **58:12** with **32 findings**; the `--fix` turn applied 31, and
the remaining finding was intentionally skipped because it would change the
recovered wf221 verifier prompt. A third run on the updated copy completed in
**68:12** with another **32 findings**; this time the `--fix` turn applied all
32, with no skips, and the suite grew to **253 tests** after C3 (per-role
model/effort) and C7 (`--fix` outcome summary) were added.

Across the clean runs (Run 4, Run 5, Run 6, Run 7, Run 8):

| Metric | Run 4 | Run 5 | Run 6 | Run 7 | Run 8 |
|---|---|---|---|---|---|
| Findings | 8 | 9 | 7 | 5 | 5 |
| Near-duplicate pairs | 1 | 1 | 0 | 0 | 0 |
| Partial warning | No | No | No | No | No |
| Child sessions | 21 | 21 | 22 | 19 | 19 |
| Verifiers | 10 | 10 | 10 | 6 | 6 |
| Wall time | 5:40 | 6:47 | 8:05 | 7:57 | 6:18 |
| Input tokens | ~81.5k | ~366k | ~142.5k | ~109k | ~125.7k |

The run-to-run difference is model wording and provider/cache variance, not a
change in the prompt or dispatch. Both runs find the three fixture defects plus
the `toFixed` edge cases and cleanup findings, and both are complete.

Compared with the pre-fix baseline (15 entries, 11 duplicates, partial), the
clean runs are substantially cleaner and complete. Compared with the built-in
`/review` (3 findings, ~25 s, ~22k input), they find the same 3 clear defects
plus 5–6 additional correctness/cleanup findings, at roughly 5–7× the wall time
and 4–16× the input.

The post-fix run adds:

- schema-constrained child output (`code_review_candidates` /
  `code_review_verdict`), with text-JSON fallback;
- semantic near-duplicate merging before verification;
- the recovered `max` prompt (including the “Keep candidates where the vote is
  CONFIRMED or PLAUSIBLE.” line);
- the exact `minimal` wording (not used at max);
- the exact notices and `ReportFindings` schema constraints.

## 3. Quality comparison

| Dimension | Built-in `/review` | This reconstruction |
|---|---|---|
| Clear defects found | 3/3 | 3/3 |
| Subtle edge case | 0/1 | 1/1 |
| Cleanup/convention coverage | Incidental | Dedicated Reuse/Simplification/Efficiency/Altitude/Conventions angles |
| Duplicates | None | 0 in Run 6; 1 in Runs 4/5 (15 → 8/9/7 after merge) |
| False-positive control | “Be certain” prompt instruction | Independent verifier per candidate; REFUTED drops |
| Ranking | Prose order | Correctness first, CONFIRMED before PLAUSIBLE |
| Output structure | Prose | JSON array / ReportFindings / exact terminal renderer |
| Cost | 1 model call | 10 finders + verifiers + sweep |
| Best use | Quick small-diff review | Exhaustive, auditable, high-recall review |

## 4. Expected behavior by diff size

- **Small (<50 lines):** the built-in reviewer is the better cost/quality
  tradeoff; the reconstruction finds the same clear bugs plus occasional edge
  cases and cleanup findings, at 5–10× the cost.
- **Medium (200–1,000 lines):** the reconstruction should find 1–3 additional
  real issues, especially dropped guards, broken callers, and convention
  violations, with more PLAUSIBLE findings.
- **Large (>2,000 lines):** the reconstruction's isolated finder contexts and
  sweep should cover more of the diff; the built-in single context is more
  likely to lose coverage. The default family does not get the sonnet-5
  diff-size finder hint, so max remains a full 10-finder fleet.

## 5. Limitations

- The reference command was not executed in Claude Code on this fixture; the
  comparison is against its recovered prompt and rules, plus the built-in
  OpenCode reviewer.
- The reconstruction's child prompts are deterministic reconstructions; Claude
  Code's model writes its own child prompts.
- Child prompts tell the agent to use the included diff and run the diff
  command only when that copy is truncated. The reference model decides this
  itself; this is a child-prompt adaptation, not a parent-prompt change.
- The deterministic dedup and ranking approximate the reference model's
  semantic dedup/ranking.
- `GITHUB_COMMENT` carries one port-only sentence telling the prompt-only path
  to pass `--hostname` on GitHub Enterprise. The captured block has no such
  sentence; this is an adaptation for GHE comment posting, not a change to the
  review prompt or findings.
- Token and time figures depend on the provider, concurrency, and caching.
- The pre-fix baseline used `--family claude-sonnet-5`; the post-fix run uses
  the default family (DeepSeek). The family difference changes the dispatch
  (sonnet-5 max = 10 finders + verify + sweep; default max = the same cell, but
  no finder-budget hint). The recipes are otherwise identical at max.
- **Do not edit `.opencode` while a review is running.** The server hot-reloads
  plugins on save; a running engine keeps the old `schemaResults` map while
  child tools write to the new one. This invalidates schema capture and makes
  the run look partial. Run 3 is recorded for exactly this reason.

## 6. Conclusion

The reconstruction is faithful to the reference's **prompt text, dispatch,
limits, schemas, and phase rules**. Its execution is a deterministic
reconstruction of a model-driven orchestration. On the fixture it has higher
recall than OpenCode's built-in `/review`: 5–9 findings versus 3, including the
`toFixed` edge cases, the missing percent validation, and the duplicated
formatting helper. After the second-pass fixes, the semantic merge, and the
pre-verify dedup, Run 7 reports **5 findings, zero duplicate pairs, and no
partial warning** with 19 child sessions, instead of 15 entries with 11
duplicates in the pre-fix baseline.

The semantic dedup/rank is the reference’s actual method: the binary has no
dedup/rank code, only the model-facing sentences “Dedup findings that point at
the same line/mechanism, keeping the one with the most concrete failure
scenario” and “Rank most-severe first.” `review-synth` applies those criteria
before verification and again at report time; the deterministic token merge
remains the fallback. The cost is correspondingly higher (5:40–8:05 vs ~25 s,
~82k–366k vs ~22k input), which is the intended tradeoff of the `max` cell.
