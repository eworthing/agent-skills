# code-review-opencode — Self-review 12 — triage

Run: `max --max-findings all --fix` in `cr-self4`, 2026-11-12, concurrency 4.

Result: **18 findings**, `partial: true`. No finder failures, but **34 verifier
children returned no usable verdict** and both the sweep and the semantic merge
returned no usable structured result. The run fails the stopping rule on
completeness, count, and severity.

## Run stats

- finders: 10, candidates: 67, verifier agents: 57
- verified: 23, refuted: 5, dupes: 10, reported: 18
- finder failures: 0
- warnings: 36 (34 dropped verifier candidates, one sweep failure, one merge failure)

## Verifier-reliability note

The 34 empty verifier responses are not model failures. The run used the
`waitForChild` grace fallback added for hosts whose `session.wait` resolves
before the queued turn starts: after `session.wait` resolved, the runner waited
one second and then declared the child idle, before the verifier had answered.
A captured schema result was not consulted, so the candidate was dropped.

The fix (applied before this triage): settle only from a **new transcript
message**, a real **busy/idle edge**, or a **captured schema result**. A
rejected `session.wait` is no longer treated as a gone child, and a transient
`session.context` failure no longer ends the wait. The stall watchdog remains
the only timeout.

## Severity

- **High:** crash, data loss, security, corrupt output, or a broken core path.
- **Medium:** wrong behavior, silent loss, broken contract, partial review, unpostable comment, or a reliability failure.
- **Low:** duplication, dead code, naming, comments/docs, performance cleanup, or a purely cosmetic fix.

## Findings

| # | Location | Finding | Severity |
|---|---|---|---|
| 0 | `.opencode/plugins/code-review-opencode/engine.ts:379` | Same-line dedup requires the failure scenarios to share tokens, so paraphrases of one defect with different consequences are reported twice. | Medium |
| 1 | `.opencode/plugins/code-review-opencode/engine.ts:521` | A file-level finding that inherits a merged line anchor also reports that line as an additional location. | Medium |
| 2 | `.opencode/plugins/code-review-opencode/engine.ts:616` | An unattributed cleanup candidate from a mixed grouped finder falls back to the aggregate correctness kind and can outrank a real bug. | Medium |
| 3 | `.opencode/plugins/code-review-opencode/json.ts:194` | A paraphrased schema example after the real payload replaces the real payload. | Medium |
| 4 | `.opencode/plugins/code-review-opencode/json.ts:420` | `asGroupVerdicts` accepts an in-range 1-based verdict list and attributes every verdict to the wrong candidate. | Medium |
| 5 | `.opencode/plugins/code-review-opencode/parse.ts:157` | Reference boolean flags inside a free-form review target are stripped and applied as command options. | Medium |
| 6 | `.opencode/plugins/code-review-opencode/prompts.ts:629` | The truncated-diff notice tells the synthesizer to run a command its prompt omits and its agent forbids. | Medium |
| 7 | `.opencode/plugins/code-review-opencode/runner.ts:672` | The step-limited formatter child is told both not to explore and to do its work by reading files and running commands. | Medium |
| 8 | `.opencode/plugins/code-review-opencode/scope.ts:1070` | A timed-out or aborted `rev-parse HEAD` is treated as an unborn repository instead of a discovery failure. | Medium |
| 9 | `.opencode/plugins/code-review-opencode/scope.ts:418` | The rename-header split chooses the closest path lengths, which is wrong when the new name contains ` b/` and the lengths are asymmetric. | Medium |
| 10 | `.opencode/plugins/code-review-opencode/scope.ts:963` | A numeric PR target resolves as a filesystem path first, so a same-named nested repo redirects the `gh pr` calls. | Medium |
| 11 | `.opencode/agents/review-synth.md:26` | The synth agent says "Do not use tools" while the runner tells the same child to call the schema tool. | Medium |
| 12 | `.opencode/plugins/code-review-opencode/engine.ts:1033` | A line-level refuted claim suppresses a file-level sweep gap when the new candidate has no line. | Medium |
| 13 | `.opencode/plugins/code-review-opencode/index.ts:430` | A failed parent-session lookup drops the known session model, so children can be created model-less and return empty responses. | Medium |
| 14 | `.opencode/plugins/code-review-opencode/index.ts:454` | `includeDiffLines` skips the PR metadata call, so a PR with no parseable patch blocks reports "No changes found." | Medium |
| 15 | `.opencode/plugins/code-review-opencode/runner.ts:268` | `hitStepLimit` scans only the last six messages, so an older step-limit notice is missed and the poisoned session is retried. | Medium |
| 16 | `.opencode/plugins/code-review-opencode/runner.ts:454` | A rejected `session.wait` is treated as proof the child is gone. | Medium |
| 17 | `.opencode/plugins/code-review-opencode/json.ts` | `asReport`/`normalizeReportCall` cap reports at 64 entries and discard the truncation notes. | Low |

## Fix status

All 18 findings are fixed in the main tree:

- **0:** a strong same-line summary paraphrase (Jaccard ≥ 0.5) merges even when
  the two finders describe different consequences; weaker overlap still needs
  the failure mechanisms to agree.
- **1:** the inherited anchor is resolved before the "also at" list is computed.
- **2:** an unattributed candidate from a mixed grouped finder ranks as cleanup;
  a unanimous correctness group still ranks as correctness.
- **3:** a result object preceded by `Expected shape:` / `Example` is treated as
  a schema echo even when its values are paraphrased.
- **4:** a verdict list that omits index 0 is rejected as an offset submission.
- **5:** reference booleans follow the same target/trailing-option boundary as
  the extensions.
- **6:** `renderDiff` takes `canRunCommand: false` for the synthesizer and the
  dedup prompts.
- **7:** the formatter passes the synthetic `format` role, which suppresses the
  "do your work" line.
- **8:** a timed-out or aborted `rev-parse` throws a discovery error.
- **9:** `walkPatch` prefers the authoritative `rename from` / `rename to` pair
  over the ambiguous header split.
- **10:** a bare numeric target never resolves as a path.
- **11:** the synth agent now instructs one schema-tool call with a text
  fallback, matching the runner.
- **12:** a line-scoped refutation only covers its own line; a file-level sweep
  candidate survives.
- **13:** the caller's already-read model ref is threaded into `resolveAndRun`
  and used when the parent lookup fails.
- **14:** PR metadata is always fetched; if it fails and the patch has no file
  blocks, `gh pr diff --name-only` is the last resort.
- **15:** the step-limit scan covers the whole transcript with a `startsWith`
  guard against quoted diffs.
- **16:** a rejected wait keeps polling; only a transcript message, a busy/idle
  edge, a captured schema result, or the stall watchdog settles.
- **17:** the report normalizer carries a `truncated` flag and the engine marks
  the run partial with a warning.

The suite is now **292 tests**, all passing. Regression tests were added for
the dedup, grouped-kind, refuted-sweep, schema-echo, report-cap, parser,
prompt, formatter, rename, numeric-target, HEAD-timeout, and merge-anchor paths.

## Next run

Run **run 13** with `max --max-findings all --fix` at concurrency 4. Stop only
when the run is complete (`partial: false`), has fewer than 10 findings, and has
no high/medium severity findings.
