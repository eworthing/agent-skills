# Schema Decisions — contest-refactor finding/artifact fields

> **CURRENT-STATE (2026-06-30):** records the disposition of every proposed-but-not-shipped
> finding/artifact field surfaced by the gap corpus, so future fixture surfaces and reviews
> are bounded by a settled decision instead of re-litigating each one. Each row cites its
> source. This is the W3 half of the [`GAP-AUDIT-AND-IMPROVEMENT-PLAN-2026-06-28.md`](GAP-AUDIT-AND-IMPROVEMENT-PLAN-2026-06-28.md)
> improvement plan, recorded per the principal-plan W0.2.

**Doctrine:** new finding/artifact fields ship as OPTIONAL, additive on the current
`schema_version: 4` (solo-beta — no migration table; the G33 `risk_boundary_evidence`
precedent). A field is shipped only when a pre-registered measurement shows the current
system lacks it AND a consumer exists. Absent a consumer, the honest disposition is
**DEFER (cost/consumer, not doctrine)** — not silent omission.

## Deferred fields (additive when a consumer appears; not blocked by doctrine)

| Field | Disposition | Rationale | Source |
|---|---|---|---|
| `confidence` (per-finding reviewer confidence enum `HIGH`/`MED`/`LOW` or 0–100) | **DEFER** | No in-loop consumer today; the rubric's severity anchors + the implementation-reviewer verdict already gate promotion. Cost-not-doctrine. | `SCHEMA-GAP-CONTEST-REFACTOR.md` Gap 1; `GAP-AUDIT…2026-06-28.md` W3 |
| ROI tiers (hotspot × complexity backlog ordering) | **DEFER** | Useful only as a Step-2 tie-breaker, **never** a hard gate or score; speculative effort inputs; no consumer. Promoting any audit to a score violates the `promotion_allowed: false` co-change doctrine. | `ROI-PRIORITIZATION-GAP.md`; `GAP-AUDIT…2026-06-28.md` W3 |
| per-hunk `changed_hunks[]` (line/hunk-level traceability) | **DEFER** | `loop_result.changed_paths[]` already gives file-level causal traceability tied to `stable_id` via the G22 commit-subject pattern; per-hunk is a cost-not-doctrine refinement with no current consumer. | `TRACEABILITY-GAP.md`; `GAP-AUDIT…2026-06-28.md` W3 |

## Skipped items (not planned — no measurable output gain)

| Item | Disposition | Rationale | Source |
|---|---|---|---|
| `refactoring-patterns.toml` + `[Pattern]` commit prefix (named-refactoring vocabulary) | **SKIP** | Pure vocabulary; no practical-output gain over the existing ICA architectural-test taxonomy (`test_failed` enum). Uncontested by reviewers. | `RESEARCH-DELTA.md`; `GAP-AUDIT…2026-06-28.md` W3 |

## Reserved (do not reuse the name)

| Name | Status | Note |
|---|---|---|
| `cross_model_scoring` | **RESERVED for v5** | Co-owns the single v4→v5 migration table with `session_spanning_handoff`; do not persist under this name without merging that table first. The cross-family challenger (principal-plan W1.1) deliberately uses `halt_success_challenge.challenger_family` instead, staying additive on v4. | `SCHEMA-GAP-CONTEST-REFACTOR.md` § Schema-version sequencing |

## Unblock condition (applies to every DEFER row)

Ship a deferred field only when: (1) a concrete consumer exists (a gate, a report, or a
loop decision that reads it), AND (2) a pre-registered RED measurement shows the current
artifact cannot already express the information. Until both hold, the field stays deferred
and out of fixture `expected.*` surfaces.
