# Output Format — schema migrations (resume / old-artifact path only)

Historical schema-version migration notes for `CURRENT_REVIEW.json` / `REVIEW_HISTORY.json` / `findings_registry.json`. **Loaded only on the resume path** (Step -1, when reading an artifact whose `schema_version` is below current) — a loop emitting a fresh current-schema artifact never needs this. Kept out of the per-loop investigation payload. The current-schema field definitions live in [output-format-json.md](output-format-json.md); the gates that apply these defaults live in [validation.md](validation.md) (G29).

## Adding a required field — the rule that governs every bump below

A new **required** field or record introduced at an *existing* `schema_version` retroactively
invalidates every artifact already written at that version. `schema_version` cannot distinguish
"v4 before the field existed" from "v4 after", so a validator has no way to judge an old artifact
by the rules that were actually in force when it was written.

The v2 → v3 bump is the pattern to follow: it added gates G27/G28/G29 **and** bumped the version
**and** shipped the default-fill table below, so old artifacts stayed readable.

So, when a new gate needs a field that did not exist before, do one of:

1. **Bump the schema version** and add a default-fill entry here (the v2 → v3 precedent); or
2. **Scope the gate** to artifacts written at or after the ruleset that introduced it, read from
   `skill_rev` (G19) via `scripts/_ruleset_epoch.py` — which is why that field exists; add an entry
   to that module's `REQUIREMENT_EPOCHS` table (data, not an inline `if` in the checker — see
   "Ruleset epochs" below); or
3. **Make the field optional**, and gate only its *shape* when present — the shipped precedent is
   **G19** (`_artifact_history.py:307`), whose docstring states this exact reasoning: *"TYPE-only, not
   presence: a reader cannot tell 'this version omitted it' from 'this run predates the field', so
   presence is a Step -1 emit obligation (startup.md)."* Copy that shape.

Never a fourth option. A required field added silently at an existing version is a retroactive
invalidation of committed history, and the repo's compatibility policy — committed reviews and
history stay readable, validators dual-read across schema versions — cannot be delivered without
one of the three above.

**Resolved 2026-08-20 (backlog item [I1]):** G43 (2026-08-06) and G46 (2026-08-18) both added
required v4 records/fields without a bump or a default-fill entry — this skill's own dogfood
artifact (`CURRENT_REVIEW.json` at the repo root, loop 15, committed 2026-08-05) failed
`validate-artifact.py --mode strict` on 10 issues that did not exist as rules when it was written.
Fixed by option 2 above: `scripts/_ruleset_epoch.py` scopes both checks to artifacts it classifies
CURRENT epoch; the dogfood artifact now passes strict with zero issues. See "Ruleset epochs" below.

## Ruleset epochs — the `skill_rev` scoping mechanism (option 2, mechanized)

`scripts/_ruleset_epoch.py` is the one classifier every epoch-scoped checker calls, so option 2
above is an import, not a repeated inline `if`. It reads `current_review["skill_rev"]` — the only
field naming *which ruleset* produced an artifact (G19) — and returns one of two epochs:

- **`current`** — `skill_rev` is present and looks like a real git short SHA (`[0-9a-f]{4,40}`).
- **`legacy`** — anything else: absent, `null`, empty, non-string, or malformed.

Only two epochs, not one per commit that ever adds a requirement. `skill_rev` carries no
timestamp, and ordering two arbitrary short SHAs against each other requires a live git repository
containing both commits — unavailable for a fixture's synthetic `skill_rev`, unavailable for an
artifact from a different clone's history, and wrong to depend on inside a selftest that must run
standalone. The evidence only supports one boundary: does this artifact carry proof it was emitted
by a loop that already attested to its own ruleset, or not. A finer boundary (e.g. "at-or-after
G43 but before G46") gets a third `EPOCHS` entry the day a requirement actually needs one — not
before.

`REQUIREMENT_EPOCHS` is the compatibility matrix: a plain dict mapping a requirement name to the
epoch it is owed at. G43 (`G43_CONVERGENCE_PASS`) and G46 (`G46_REMEDIATION_FIELDS`) are both
`current`; a requirement absent from the table is not epoch-gated at all (unconditional at its own
`schema_version` floor — e.g. G19's own type check, which stays TYPE-only per option 3, never
presence). Add new requirements as table entries — independence/reviewer isolation fields,
transitions, rounds, G29 version equality, and G17 are the named future clients — never as a new
epoch `if` scattered into the checker.

**Fail-closed direction.** This classifier backs *retroactive* requirements only (a field added
after artifacts already existed, judged against artifacts already on disk). An artifact that
cannot be *proven* current is legacy, never the reverse: a marker-less artifact goes unchecked
rather than a genuinely-legacy artifact being wrongly failed. The cost is symmetric under-coverage,
not false failure — and it lands broadly today, because no fixture or checker selftest in this
corpus carries a `skill_rev` yet. `_g43_selftest.py` and the G46 remediation-fields selftest go
fully silent on their "must fire" cases under this scoping (they assert directly against the
checker functions with marker-less synthetic artifacts); `evals/fixtures/g43-clean-streak-restated`,
`g43-clean-streak-reworded-note`, `g43-convergence-pass-missing`, and
`g46-remediation-drift-notes-empty` flip from failing to passing for the same reason.
**The fix for each is to add a valid `skill_rev` to the fixture/case, not to exempt it** — see
`evals/fixtures/g46-current-epoch-fields-missing` for a fixture proving the shape still fails once
the marker is present. Closing the gap for good is an **emitter** obligation: `skill_rev` capture
is already mandatory at `schema_version >= 4` (startup.md Step -1); this validator-side classifier
cannot compel presence any more than G19 can, for the identical reason.

## Schema version 4 → 5

Additive. A persisted **v4** candidate finishes under the legacy
single-challenger contract; **v5** artifacts use panels. Mixed-version
`REVIEW_HISTORY.json.loops[]` entries are legal — each entry carries its own
`schema_version`. No artifact is rewritten in place.

v5 **emission** is gated by the default-deny `panel_certification` capability
([provider-adapters.md § panel_certification capability manifest](provider-adapters.md#panel_certification-capability-manifest-v5-panel-authorization);
SSOT `canon/panel-certification.toml`) — an un-entried provider + exact model +
`protocol_digest` combination keeps writing v4 indefinitely, forever if never
measured.

**Rollback** clears the capability entry but the v5 **reader** stays: a
previously-written v5 artifact remains readable, and a failed v5 panel is never
reinterpreted as a v4 success.

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
- New `loop_result.changed_paths[]` (paths the loop touched; narrow-revert targets classified as tracked/untracked by `LOOP_STATE.pre_step3_blob_shas`).
- New `LOOP_STATE.json` artifact for mid-Step-3 checkpointing.
- New gates G27 (retry envelope), G28 (checkpoint freshness), G29 (schema v3 invariants); new quality pass Q8 (per-loop progress line).
