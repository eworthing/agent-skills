# code-review-opencode — Run 16 Triage

> **Naming:** this project is `code-review-opencode`; its command is
> `/code-review-opencode`. Mentions of `/code-review` in this document name
> Claude Code's original command.

Run 16 reviewed the pre-rename `cr-self4` copy: **32 reported / 48 verified
survivors**, `partial: true` because the sweep and semantic-merge children
returned no usable structured output. Every finding below was re-checked
against current `main`; stale line numbers are the run-16 references.

## Fixed

| # | Finding | Fix |
|---|---|---|
| 1 | Branch `--comment` could resolve a PR without a verified diff base | `postComments` now refuses when `pr` is implicit, a branch is recorded, and `diffBase` is missing. Branch tests now carry a verified base. |
| 2 | `--comment` posted findings on lines outside the reviewed diff | `diffSideMap` exposes `hasLine`; posting rejects a known-missing anchor before GitHub returns 422. |
| 3 | Text synthesis matched same-summary findings by file only | Exact matching now also compares the reported line when both sides have one. Regression test added. |
| 5 | Human renderer emitted a filename newline raw | `renderedLocation` escapes control characters; `formatHuman`, outcome summaries, and refuted lines use it. |
| 6 | Invalid `--mode` silently ran a different pipeline | Added an explicit ignored-mode notice naming the valid versions. |
| 7 | Inline cells skipped explicit path validation | Inline/minimal paths now run the same explicit-path existence check as the engine and return the standard error (or bare `[]` under `--json`). |
| 8 | `FIX_LATER` was shown in the user-visible engine report | Removed from the engine body; the `ReportFindings` tool description carries the outcome contract. Inline prompt paths keep their decoration. |
| 9 | Schema-echo detection treated one sample field as an echo | Requires at least two of `file`/`summary`/`failure_scenario` to match the sample. A real finding in `path/to/file.ts` survives. |
| 10 | Re-normalizing a captured report/decisions lost the `truncated` flag | `asReport`/`asDecisions` preserve the tool-boundary flag. Tests added. |
| 12 | Verifier/sweep prompts interpolated candidate filenames raw | Prompt locations use `renderedLocation`; test covers a newline-bearing candidate path. |
| 13 | Conventions headers could consume the whole budget | Header budget is shortened to basenames when it exceeds half; at least a small content share is reserved. |
| 14 | Repo root stripped every trailing CR/LF | Strips exactly one line terminator, preserving a legal path ending in newline. |
| 15 | Renamed-from finding outside every hunk defaulted to RIGHT on the head path | The new `hasLine` check refuses the anchor instead of posting it to unrelated code. |
| 16 | Conventions sized in bytes but budgeted in UTF-16 units | Sizes now come from the decoded text length. |
| 17 | GHE hostname came from origin while repo came from the PR URL | PR URL hostname is authoritative when present. |
| 20 | `sessionMessages` only unwrapped a bare `data` array | Accepts bare, `{data: [...]}`, and `{data: {messages: [...]}}` envelopes, depth-limited. |
| 21 | Schema-result FIFO eviction could delete a live child's result | `setCapped` accepts a protected live-child set and skips it. |
| 24 | Explicit branch targets omitted uncommitted changes | A dirty/empty branch range now adds `git diff HEAD`. |
| 25 | Three copies of the numeric env parser | Shared `envInt` in `finding.ts`; scope/comment/stall use it. |
| 28 | Three prompt-outcome branches repeated the same assembly | Shared `promptOutcome`; all-finders-failed keeps its extra warning. |
| 29 | Outcome-hash cache hand-rolled `setCapped` | Reuses the shared capped insert. |
| 31 | Every verifier rebuilt the full scope/diff preamble | Per-`ScopeBlock` WeakMap cache shared by verifier and sweep prompts. |

## Rejected — deliberate reference or safety behavior

| # | Finding | Why not changed |
|---|---|---|
| 4 | `kindFor` falls back to cleanup for unattributed mixed-lens candidates | Defaulting to correctness would let a cleanup finding outrank a real bug under the cap. Run 15 adopted the conservative fallback intentionally. |
| 11 | Invalid spaced extension value drops the flag token | The flag is a recognized option; only its value is re-read as effort. Re-adding `--driver` to the target leaks option grammar into prose and breaks the documented parser test. |
| 18 | `canonFile` no longer suffix-matches paths | Suffix matching turned a report about unchanged `lib/src/a.ts` into changed `src/a.ts`. Root/prefix/absolute mapping is the safe subset. |
| 19 | `sameDefect` requires failure-scenario agreement for same-line paraphrases | Merging on summary overlap alone hides distinct consequences. The stricter policy is intentional. |
| 22 | `ReportFindings` rejects unknown per-finding properties | The reference schema is strict; a malformed finding rejects the call so the model re-emits the complete list. |
| 23 | `keepSessions` defaults to false | Keeping every child transcript is a debugging aid; `CODE_REVIEW_KEEP_SESSIONS=true` still opts in. |
| 30 | `parseExtensions` duplicates the attached/detached value ladder | Maintainability, not a wrong-output defect; a refactor would touch the command grammar without a parity gain. |
| 32 | `ReportFindings` has defensive branches after schema validation | They are unreachable today but keep the normalizer safe if the schema walk is relaxed. Removing them has no behavioral benefit. |

## Deferred — efficiency only

| # | Finding | Status |
|---|---|---|
| 26 | A commented PR re-fetches URL/head with two `gh pr view` calls | Accepted; no wrong output. Combine into one metadata call when the comment path is next touched. |
| 27 | `--comment` classifies the target twice (`resolveReviewRoot` + `resolveScope`) | Accepted; no wrong output. Pass the classified target into `resolveScope` in a future scope refactor. |

## Verification

- `node --test test/*.test.ts`: **343 passed, 0 failed**.
- New regressions cover line-aware synthesis matching, schema-echo tolerance,
  truncation-flag preservation, nested message envelopes, prompt filename
  escaping, and human-renderer filename escaping.
- The audit fixes from the previous pass remain in place: command session
  model/effort, command attachments, `argumentHint` removal, and the synthetic
  fallback.
