# Output Format — per-loop archive compression (Step 3 step 9 only)

The PR-5 per-loop archive-compression format for appending a completed loop to `REVIEW_HISTORY.md`. Used **only at Step 3 step 9** (archive write); never needed during the Step-1 Critic investigation or by the Step-3 reviewer. Carved out of [output-format-markdown.md](output-format-markdown.md) to keep it off the investigation path.

## Per-loop archive format (PR 5, schema_version >= 2)

When a completed `CURRENT_REVIEW.md` is archived to `REVIEW_HISTORY.md` in Step 3 step 9, apply these compressions to the .md archive only (`REVIEW_HISTORY.json` keeps full per-loop fidelity in `loops[]`):

1. **Per-loop divider header**: the archive divider `--- Loop <N> (UTC <ts>) ---` is immediately followed (when the loop had retirement transitions) by a one-line summary listing every `stable_id` whose `status` transitioned to `unresolvable` this loop. Example: `Retired this loop: F-007, F-019.` The line is omitted when no retirement transitions happened.
2. **Discovery section**: omit on loops 2+ (only loop 1's archive carries Discovery; subsequent loops include the line "see Loop 1 Discovery").
3. **Builder Notes**: render only `pattern` per item with link "→ REVIEW_HISTORY.json `loops[N].builder_notes` for full notes".
4. **Simplification Check**: render as a 5-row table (one row per field: structurally_necessary, new_seam_justified, helpful_simplification, should_not_be_done, tests_after_fix) instead of bulleted prose.
5. **Loop N Result + Loop N Implementation Review**: keep verbatim (load-bearing audit chain).
6. **Findings**: keep verbatim (load-bearing structural record).
7. **Scorecard**: keep verbatim (delta basis for next loop's Critic).
8. **Authority Map / Strengths / Final Judge Narrative**: keep verbatim.

Compression applies prospectively from `schema_version >= 2` archives. Pre-version-2 archives in REVIEW_HISTORY.md remain in full prose form (no rewrite). Estimated savings on .md archive size: 15-20% per loop.

The live `CURRENT_REVIEW.md` is never compressed — only the archived copy in REVIEW_HISTORY.md. Downstream tools needing structured access read `REVIEW_HISTORY.json` directly (schema in [output-format-json.md § REVIEW_HISTORY.json schema](output-format-json.md#review_historyjson-schema)).
