# self-review 18 triage

Run: `max --max-findings all --json --concurrency 6 HEAD~1..HEAD` against the
production-only copy at commit `72a42ee`, on 2026-11-13.

Result: **47 findings**. The sweep child stalled after 36 minutes and was
interrupted, so the run is `partial: true` with no sweep gaps. The 47 findings
below are the verified first-pass survivors; the sweep would only have added
new candidates.

The `--json` contract carries no severity, so severity was assigned during
validation. Findings 1-20 are correctness/security candidates; 21-47 are
duplication/efficiency cleanups.

## Fixed in batch 1

| # | Finding | Fix |
|---|---|---|
| 1 | `git diff*` matched `git difftool` and allowed external programs | Narrowed the allow patterns to `git diff` / `git diff *` in all three agent files and added an explicit `*difftool*` deny. The existing `--ext-diff`/`--textconv` denies remain; config-based default textconv needs a pre-existing local diff driver and is not reachable from a PR. |
| 2 | Sweep known-list used raw `location()` | `renderedLocation()` now escapes control characters in paths before prompt interpolation. |
| 3 | github.com PR URL did not clear a GHE origin hostname | The PR URL now sets the host in both directions; github.com clears the GHE hostname. |
| 4 | Comment posting checked the base branch name but not the merge-base commit | The branch path now compares the reviewed merge-base with `git merge-base <PR base OID> HEAD` and refuses stale bases. |
| 6 | Index plans were applied without checking zero- vs one-based indices | An unambiguous 1-based plan (no zero, max index == item count) is shifted before application. |
| 7 | Candidate dedup picked the longest scenario even when it was cleanup | Correctness candidates now win the representative selection; scenario length is only the tie-break. |
| 9 | Sweep candidates without a category defaulted to correctness | Unattributed sweep candidates now fall back to cleanup, matching `kindFor()`. |
| 10 | `canonFile` rewrote literal backslashes in POSIX names | The unquoted path is checked against the changed-file list before separator normalization. |
| 11 | Locale-sensitive `localeCompare` tie-break | Report ordering now uses deterministic code-unit comparison. |
| 12 | Text synthesis dropped `report.truncated` | `truncatedFrom` is now recorded when the text report was capped. |
| 13 | `envInt` accepted values above Node's maximum timeout | Clamped to 2,147,483,647 ms. |
| 17 | Ignored `--fix`/`--comment` notices only went to the server log | Action notices are now included in the session output (and in `--json` stderr notices). |
| 18 | Dirty branch worktrees could post uncommitted anchors | Branch-shaped `--comment` now refuses a dirty worktree. |
| 19 | `session.create` envelopes were not unwrapped | The child id is read through `sessionRecord()` and a missing id fails the child cleanly. |

## Rejected as deliberate or false positive

| # | Finding | Reason |
|---|---|---|
| 14 | `readCapped` truncates non-ASCII files | The implementation reads `budget * 3` bytes and decodes with `StringDecoder`; three is the maximum UTF-8 bytes per UTF-16 code unit, so the character budget is filled rather than truncated. This is a false positive. |

## Fixed in batch 3

These were initially treated as deliberate reference behavior, but validation
showed the findings describe real recall/output defects. They are now fixed,
with the divergence from the captured reference noted in the code comments.

| # | Finding | Fix |
|---|---|---|
| 5 | v2.1.162 dedup bucket dropped distinct nearby defects | The full normalized claim is now part of the key; only the same claim in the same bucket merges. |
| 8 | Merged entry upgraded a PLAUSIBLE representative using unverified text | When a merged duplicate is the confirmed entry, its claim text and failure scenario are used for the upgrade. |
| 15 | `summary`/`truncatedFrom` never reached the user | Human output shows the cap notice; typed report metadata carries `summary` and a truncation warning. |
| 16 | Engine text reports were capped at 32 though they never call ReportFindings | The 32-entry host cap now applies only to prompt paths; deterministic engine reports honor `--max-findings` above 32. |
| 20 | Unknown transcript envelopes were coerced to `[]` | `sessionMessages` recognizes more envelopes; an unrecognized one is logged and retried, not treated as an empty answer. |
| 22 | Sweep re-implemented finder candidate ingestion | Shared `acceptCandidates()` handles the cap, dropped candidates, and step-limit warnings. |
| 36 | Low/low-minimum prompts duplicated two whole blocks | Shared `LOW_TURN1_WITH_SKIP`/`LOW_TURN2` constants (byte-identical prompts). |
| 37 | Inline xhigh retyped the sweep focus prose | Uses `SWEEP_FOCUS()`; prompt snapshots unchanged. |

## Fixed in batch 2

| # | Finding | Fix |
|---|---|---|
| 23 | Finder prompts re-rendered the scope for every finder | Added a per-`ScopeBlock` cache for both convention variants, matching the verifier cache. |
| 24 | Unused `filesOnly` plumbing | Removed the option, its early return, and its duplicate PR-name fallback; the full-review fallback remains. |
| 25 | xhigh/max cells duplicated field-for-field | Table-local `v318XhighMax`, `v162XhighMax`, and `v221XhighMax` builders. |
| 26 | Branch target re-ran its name-status listing | The first listing is reused by the plan. |
| 27 | Conventions files were read twice (size, then content) | Each source is read once at the total budget and reused for sizing and rendering. |
| 28 | Numstat fallback ran sequentially | Independent numstat calls now run with `Promise.all`. |
| 31 | Grouped verdict normalizer duplicated the single-verdict policy | Shared `verdictWithEvidence()` fallback/downgrade helper. |
| 33 | Positive-integer grammar duplicated in max-findings parsing | Reuses `positiveLine()` at all three sites. |
| 34 | Concurrency parsing duplicated with different invalid handling | Reuses `positiveLine()` and `resolveConcurrency()`. |
| 35 | Attached/separate extension value assignment repeated | Shared `assignExtensionValue()` switch. |
| 39 | Semantic-merge branch duplicated index-synthesis application | Shared `applyIndexSynthesis()` with per-branch fallbacks. |
| 40 | Formatter prompt hard-coded the step-limit placeholder | Uses `STEP_LIMIT_PLACEHOLDER`. |
| 41 | Duplicate `gh pr diff --name-only` fallback | Removed with the files-only path; one full-review fallback remains. |
| 42 | Outcome delivery lacked the prompt fallback | Shared `deliverToSession()` tries synthetic, then prompt. |
| 44 | FIX_LATER suppression keyed on the literal `o5-bmin` | Added `Cell.suppressFixLater`. |
| 45 | Sequential storage reads | `Promise.all`. |
| 46 | Comment posting re-read the origin to recover its hostname | `detectHostDetails()` now supplies both host and hostname. |
| 47 | A pending host wait retained the polling activation | The wait hint writes into a small state object outside the activation. |

## Remaining cleanup findings

21, 29, 30, 32, 38 are duplication/efficiency observations that need either a
larger refactor or are constrained by the agent-file/prompt formats. They are
low severity; none changes observed behavior. Run 19 will decide whether the
remaining set is small enough to close the gate or needs another batch.
