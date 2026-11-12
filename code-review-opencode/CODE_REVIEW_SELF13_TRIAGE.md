# code-review-opencode — Self-review 13 triage and fidelity audit

Run 13: `max --max-findings all --fix`, concurrency 4, DeepSeek V4.1 Flash.
Report `660a91d6-8b7a-43ec-8acd-d87f5c40b5a9`, complete (`partial: false`, no
warnings), 32 findings, 22 correctness / 10 cleanup.

Severity rubric: **high** = crash, data loss, security, or corrupt core output;
**medium** = wrong behavior, silent loss, broken contract, partial or
unpostable result; **low** = cleanup, docs, naming, efficiency.

## Findings

| # | Location | Finding | Severity | Confidence | Status |
|---|---|---|---|---|---|
| 1 | `json.ts:164` | decisions/group-verdict schema echo replaces the real result | high | CONFIRMED | fixed |
| 2 | `engine.ts:235` | 40-char file-level dedup key merges distinct defects | high | CONFIRMED | fixed |
| 3 | `engine.ts:381` | 0.5 Jaccard merges distinct same-line bugs | high | CONFIRMED | fixed |
| 4 | `engine.ts:1251` | any-token synth anchor attaches the wrong claim | high | CONFIRMED | fixed |
| 5 | `engine.ts:1264` | synth file paths not canonicalized; verified finding dropped | medium | CONFIRMED | fixed |
| 6 | `json.ts:729` | decisions capped at 64 with no truncation signal | medium | CONFIRMED | fixed |
| 7 | `scope.ts:1027` | remote-only branch silently ignored, wrong diff reviewed | high | CONFIRMED | fixed |
| 8 | `json.ts:213` | echo + bare array discards every real candidate | high | PLAUSIBLE | fixed |
| 9 | `index.ts:248` | dry-run/JSON still told fixes are being applied | high | PLAUSIBLE | fixed |
| 10 | `comment.ts:78` | `isGitLabRemote` overmatches `gitlab-*` hosts | medium | CONFIRMED | fixed |
| 11 | `comment.ts:161` | `samePrBase` accepts only origin/upstream | medium | CONFIRMED | fixed |
| 12 | `prompts.ts:534` | GitHub comment prompt omits GHE `--hostname` | medium | CONFIRMED | fixed as a documented prompt adaptation |
| 13 | `index.ts:376` | numeric PR target resolved as a path for host detection | medium | CONFIRMED | fixed |
| 14 | `prompts.ts:181` | low-effort `--json` emits prose (reference behavior) | medium | CONFIRMED | reference behavior preserved; README exception documented |
| 15 | `scope.ts:372` | `unquoteGitPath` drops `\a` | medium | CONFIRMED | fixed |
| 16 | `engine.ts:180` | `canonFile` corrupts git-quoted paths | medium | CONFIRMED | fixed |
| 17 | `prompts.ts:666` | semicolon split breaks a quoted pathspec | medium | CONFIRMED | fixed |
| 18 | `runner.ts:522` | missing baseline settles a retry too early | medium | PLAUSIBLE | fixed |
| 19 | `index.ts:558` | floating progress rejection can terminate the process | high | PLAUSIBLE | fixed |
| 20 | `runner.ts:51` | trailing `#` creates an empty model variant | medium | PLAUSIBLE | fixed |
| 21 | `comment.ts:188` | GHE hostname lost; comments can target github.com | high | PLAUSIBLE | fixed |
| 22 | `parse.ts:147` | empty attached value masks env fallback/later flag | medium | CONFIRMED | fixed |
| 23 | `reportfindings.ts:168` | rejection reports the level note, not the finding error | low | CONFIRMED | fixed |
| 24 | `parse.ts:236` | non-string target `.split` throws | medium | PLAUSIBLE | fixed |
| 25 | `artifact.ts:49` | artifact omits the engine summary | low | CONFIRMED | fixed |
| 26 | `README.md:97` | medium recipe contradicts the dispatch table | low | CONFIRMED | docs corrected to ≤10 (floor 5) |
| 27 | `json.ts:216` | quadratic bracket scan can freeze the plugin | medium | CONFIRMED | fixed |
| 28 | `runner.ts:508` | no backoff on an updated-only host | low | CONFIRMED | fixed |
| 29 | `runner.ts:373` | redundant baseline transcript fetch per child | low | CONFIRMED | fixed |
| 30 | `comment.ts:194` | three `gh pr view` calls for one PR | low | CONFIRMED | fixed |
| 31 | `index.ts:731` | decisions tool promises tolerance, normalizer is strict | low | PLAUSIBLE | description now states strict reject-and-retry |
| 32 | `review-sweep.md:12` | shell policy copy-pasted across three agents | low | PLAUSIBLE | guarded by an equality test |

Totals: 9 high, 15 medium, 8 low.

## Fidelity audit

The reference is Claude Code v2.1.318: the captured prompt corpus under
`sources/skill-code-review/`, the dispatch/cell table, the ReportFindings
schema, and the recovered phase rules. The audit used the pre-run-13 tree
reconstructed from `combined-093736.patch`, the current main tree, and the
`--fix` turn's copy.

### Checks that pin reference behavior

- **Prompt corpus hashes:** every captured fragment still matches its recorded
  SHA-256 (`prompt corpus integrity` test).
- **Assembled prompts:** `lowPrompt("json", 4)` is byte-for-byte
  `sources/skill-code-review/low.md`; high/xhigh and the other captured
  variants still match (`bundled skill reference files match the assembled
  prompts`).
- **Dispatch and caps:** the cell table still resolves the reference cells and
  caps (`low` 4, `medium`/`high` 10 with floor 5 for `o48-high-v1`, `xhigh`
  15/floor 7, `max` 15). The medium README row now matches that table instead
  of the old ≤8/floor 4 claim.
- **Schemas and failure behavior:** ReportFindings remains the 32-entry
  contract; the decisions tool now **rejects an invalid plan and re-prompts**
  instead of silently dropping entries, matching the reference's strict
  structured-output loop. The earlier tolerant variant was reverted.
- **Full suite:** 315 tests pass.

### Changes by fidelity category

**Reference-faithful corrections** (restore the captured intent; no reference
contract changed): findings 1, 5, 7, 8, 10, 13, 15, 16, 17, 18, 19, 20, 22, 23,
24, 27, 28, 29, 30. These fix parsing, path, host, scope, and retry bugs; the
normal review path and its caps/phases are unchanged.

**Port-specific fallback calibration** (no reference algorithm exists; the
reference dedups semantically in the model): findings 2, 3, 4. The 0.55
threshold keeps the strong-paraphrase merge case (Jaccard 0.571) while keeping
the exact 0.5 distinct case ("missing response check" vs "missing response
await") separate. The file-level key now uses the full normalized summary, and
the any-token synth anchor is used only when a line has a single unclaimed
finding. These can change borderline duplicate decisions only when the
deterministic fallback is active (semantic merge off or failed); they do not
change the reference's model-driven merge path.

**No reference effect:** finding 6 raises the decisions cap from 64 to 256; the
reference caps findings at 15, so the cap never binds. Findings 25 and 32 are
port-only artifact and test-hygiene changes.

**Documented prompt adaptation:** finding 12 adds one sentence to
`GITHUB_COMMENT` telling the prompt-only path to pass `--hostname` on GitHub
Enterprise. The captured `Us` block has no such sentence; this is comment-only
and does not change the review prompt or findings. It is now recorded in
`CODE_REVIEW_ORCHESTRATION_MAP.md` (`Us` = ADAPTED),
`CODE_REVIEW_EQUIVALENCE_REPORT.md`, and `CODE_REVIEW_CONFIDENCE_MAP.md`, with
a source comment in `prompts.ts`.

**Reference exception preserved:** finding 14. The captured low prompt emits
one-line prose even with `--json`; the port keeps that prompt verbatim and
documents the exception in the README. The `lowPrompt("json") === low.md`
check still passes.

### Rejected drift from the `--fix` turn

The `--fix` turn's copy (`cr-self4`) is **not** the source of truth. Its diff
replaced the low-effort `--json` output with a JSON array and weakened the
reference equality test to compare only the prompt prefix. That would change
low-effort output from the captured prose to JSON. It was not merged; main
keeps the exact captured prompt and the exact-equality test.

The same turn independently changed the decisions tool description to the
strict reject-and-retry wording; that part was adopted. Its broader
best-overlap text-synthesis and `for-each-ref` branch helpers are alternative
implementations, not fidelity requirements; main keeps the validated,
conservative versions.

### Verdict

**No significant outcome drift in the reference-specified review path.** The
captured prompts, dispatch, caps, schemas, phases, and ranking behavior are
unchanged and pinned by tests. The only prompt-text deviation is the documented
GitHub Enterprise comment sentence. The one change that would have altered
low-effort outcomes — the `--fix` turn's JSON low prompt — was found and
rejected.

## Follow-ups

1. Sync the validated main tree to `cr-self4`, overwriting the `--fix` turn's
   low-prompt drift.
2. Run the full suite in the synced copy.
3. Restart the port 49403 server and rerun the self-review.
4. If the GHE prompt adaptation is unacceptable, revert the one sentence and
   record finding 12 as a known port limitation instead; the engine comment
   path already passes `--hostname`.
