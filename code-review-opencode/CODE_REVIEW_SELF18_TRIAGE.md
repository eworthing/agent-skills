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
| 5 | v2.1.162 dedup key uses a 5-line bucket | This is the reference workflow's dedup contract; changing it would stop being v2.1.162. |
| 8 | Merged entry upgrades a PLAUSIBLE representative to CONFIRMED | The strongest verified verdict for the same root cause wins; the representative text is retained. |
| 14 | `readCapped` truncates non-ASCII files | The implementation already reads `budget * 3` bytes and decodes with `StringDecoder`; the byte budget is intentionally larger than the UTF-16 budget. |
| 15 | Human/ReportFindings renderers omit `summary` and `truncatedFrom` | The captured v2.1.318 renderer (`jt`) renders only the findings list and count. The synthesis summary is an artifact field. |
| 16 | Non-JSON runs apply the 32-entry cap even though the engine renders text | The 32-entry cap is the reference `ReportFindings` host-schema contract; the engine result is still the same report, and the cap is required when a host renders the typed payload. |
| 20 | Unknown `session.context` envelopes become `[]` | There is no recoverable transcript shape to parse. The runner logs the empty response and retries; inventing a mapping would risk reading an unrelated array. |

## Pending: cleanup findings 21-47

The duplication/efficiency group is being handled in a separate batch. It
includes repeated agent permission tables (format-level constraint), sweep
candidate ingestion, scope re-rendering, unused `filesOnly` plumbing,
duplicated cell definitions, sequential git/numstat calls, duplicated comment
guidance, verdict/decision normalizers, prompt-block duplication, synthesis
branch duplication, and the wait-reaction retention leak.
