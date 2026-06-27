# Output Format — schema migrations (resume / old-artifact path only)

Historical schema-version migration notes for `CURRENT_REVIEW.json` / `REVIEW_HISTORY.json` / `findings_registry.json`. **Loaded only on the resume path** (Step -1, when reading an artifact whose `schema_version` is below current) — a loop emitting a fresh current-schema artifact never needs this. Kept out of the per-loop investigation payload. The current-schema field definitions live in [output-format-json.md](output-format-json.md); the gates that apply these defaults live in [validation.md](validation.md) (G29).

## Schema version 3 changelog

`CURRENT_REVIEW.json`, `REVIEW_HISTORY.json`, and `findings_registry.json` bump `schema_version: 2 → 3`. `LOOP_STATE.json` is a new file on its own track at `schema_version: 1`. Backward compatibility:

- v2 artifacts on disk at re-invocation are honored read-only by Step -1; missing v3 fields default per the table below.
- A loop running at v3 writes v3 artifacts; mixed-version `REVIEW_HISTORY.json.loops[]` entries are legal (each entry carries its own `schema_version`).
- G29 in [validation.md](validation.md) enforces these invariants.

### v2 → v3 default-fill table (when reading a v2 artifact)

| Missing v3 field | Default |
|---|---|
| `dry_run` (top-level CURRENT_REVIEW.json) | `false` |
| `discovery.test_scope` | `"full"` |
| `discovery.test_filter` | `null` |
| `discovery.working_tree_dirty_paths` | `[]` |
| `implementation_review.retry_count` | `1` |
| `implementation_review.retry_cause` | `null` |
| `implementation_review.retry_attempts` | `[{"attempt": 1, "outcome": "ok", "error": null, "duration_ms": null}]` |
| `loop_result.changed_paths` | `[]` |

### v3 changes (additive; no breaking changes)

- New halt state `HALT_DRY_RUN` (state enum extended); `halt_subtype: null`.
- New top-level field `dry_run` (boolean, audit only — re-invocation reads the user's CLI flag, not this field).
- New discovery fields `test_scope`, `test_filter`, `working_tree_dirty_paths`.
- New `implementation_review` fields `retry_count`, `retry_cause`, `retry_attempts[]` (transient retry metadata; substantive verdict stays in `reason`).
- New `loop_result.changed_paths[]` (paths the loop touched; restore source for narrow revert in conjunction with `LOOP_STATE.pre_step3_blob_shas`).
- New `LOOP_STATE.json` artifact for mid-Step-3 checkpointing.
- New gates G27 (retry envelope), G28 (checkpoint freshness), G29 (schema v3 invariants); new quality pass Q8 (per-loop progress line).
