# Domain-Aware Scanning Gap — contest-refactor vs levnik audit-suite (P2 STUB)

> **CURRENT-STATE (2026-06-28):** DEFERRED — multi-domain `--domain`; low demand, monorepo handled by most-LOC source root. See [`GAP-AUDIT-AND-IMPROVEMENT-PLAN-2026-06-28.md`](GAP-AUDIT-AND-IMPROVEMENT-PLAN-2026-06-28.md) for the source-verified audit.

Source: `refs/competitors/levnik-skills/shared/references/audit_worker_core_contract.md`. Already mentioned in LEVNIK-AUDIT-SUITE-GAP § Gap E as "defer indefinitely; only useful for multi-domain monorepos."

This is a deliberate STUB doc — minimal scope, low priority. Written to close the coverage gap from LEVNIK-AUDIT-SUITE-GAP without inflating to a full gap-doc treatment.

## Baseline: contest-refactor today

- Scans whole repository OR via `--scope <dir>` flag (single-directory scope)
- All findings tagged uniformly; no domain attribution
- One CURRENT_REVIEW.json per loop covers entire scope

## What levnik does

`audit_worker_core_contract.md`:

> Accepted inputs: `codebase_root`, `runId`, `output_dir`, `summaryArtifactPath`, `tech_stack`, `best_practices`, `domain_mode`, `current_domain`, `scan_path`.
>
> Rules:
> - Domain-aware mode scans only `scan_path` and tags findings with `current_domain`.

Workers accept three modes:

- `domain_mode: "global"` → scans `codebase_root`
- `domain_mode: "domain-aware"` → scans only `scan_path` (typically `services/billing/`, `services/orders/`, etc.) and tags every finding with `current_domain` field

Use case: large monorepos with multiple semi-independent sub-projects. Each domain audited separately; findings don't cross-pollute.

## Strategic insight (why defer)

Most contest-refactor users work on single-domain repos (one Swift app, one Rust crate, one Python service). For these, `--scope <dir>` already covers narrow-focus runs without needing per-finding domain tagging.

Multi-domain monorepos exist (Bazel/Buck/Pants/Turborepo workspaces, microservice repos, design systems with package subdirs) but are a minority of contest-refactor's target use case.

**Cost vs payoff**:
- Adoption cost: schema additions for `domain_mode`, `current_domain`, `scan_path`, per-finding `domain` field; per-domain `CURRENT_REVIEW.json` lifecycle; `findings_registry.json` per-domain partitioning; cross-domain dedup rules
- Payoff: only meaningful for users with ≥3 semi-independent domains in one repo

Defer until concrete user demand surfaces.

## P2 GAPS — what to import IF EVER

### Gap A (defer): Domain mode + per-finding domain tag

When adopted:

**Schema additions** (additive):

```jsonc
{
  "governance_context": {                       // moved from discovery per Codex round 1 N1 (cross-loop, not first-loop-only)
    "domain_mode": "domain-aware",          // enum: global | domain-aware
    "current_domain": "billing",            // required when domain_mode == "domain-aware"
    "scan_path": "services/billing/",       // required when domain_mode == "domain-aware"
    "all_domains": [                        // populated by Step 0; informs HALT_SUCCESS gating
      "billing", "orders", "fulfillment", "auth"
    ]
  },
  "findings": [
    {
      "loop_local_id": "F1",
      "domain": "billing",                  // NEW; null when domain_mode == "global"
      // ... existing fields ...
    }
  ]
}
```

**CLI flag**: `--domain <name>` (sets `domain_mode: domain-aware` + auto-derives `scan_path` from `<name>` lookup in `.contest-refactor.toml § domains[]`).

**Config file additions** to `.contest-refactor.toml`:

```toml
[[domains]]
name = "billing"
scan_path = "services/billing/"
test_command = "cd services/billing && swift test"
lens = "apple"

[[domains]]
name = "orders"
scan_path = "services/orders/"
test_command = "cd services/orders && swift test"
lens = "apple"
```

**HALT_SUCCESS semantics** (when domain-aware):
- Per-domain CURRENT_REVIEW.json (one per domain)
- Whole-repo HALT_SUCCESS requires HALT_SUCCESS on EVERY domain (logical AND)
- New halt subtype: `cross_domain_inconsistency` (when one domain HALT_SUCCESS but another HALT_STAGNATION)

### Gap B (defer + harder): Cross-domain dedup

When the same architectural debt appears in `billing` AND `orders` (e.g., both have shoehorned auth-token storage), should it count as one finding or two?

Levnik's `audit_final_report_contract.md` requires "deduplicate repeated findings across workers, domains, and report files." But contest-refactor's `findings_registry.json` keys on stable_id per occurrence; cross-domain dedup would require either:

- One global registry with domain-tagged occurrences (single source of truth)
- Per-domain registries with synthesizer reconciliation

This is a hard design decision. Defer until Gap A ships AND multi-domain monorepo demand is real.

## What contest-refactor already partially handles

`--scope <dir>` flag covers the cheap case (run only over a directory). It just doesn't tag the resulting findings with domain attribution. For users running contest-refactor sequentially per domain, this is enough — they get one CURRENT_REVIEW.json per invocation, and they can manually correlate cross-domain findings.

Until Gap A ships, document workaround in `references/project-config.md`:

> For multi-domain monorepos, run contest-refactor per-domain using `--scope <domain-path>`. Each run produces independent CURRENT_REVIEW.json / REVIEW_HISTORY.json. Cross-domain finding correlation is manual until domain-aware mode (planned, P2).

## What NOT to import

| Tempting | Why skip |
|---|---|
| Full levnik domain-aware mode for all users | Most users don't need it. Opt-in only. |
| Per-domain LOOP_STATE.json | Adds complexity for minor benefit. One LOOP_STATE.json per loop is fine; the loop happens to scan one domain at a time. |
| Cross-domain finding promotion ("this finding appears in 3 domains, promote to whole-repo P1") | Tempting but conflates architectural pattern with deployment topology. Different domains may need different fixes for the same pattern. Surface as separate findings; let synthesizer (not skill) decide promotion. |
| `findings_registry.json` per-domain partition | Doubles registry surface; complicates fingerprint discipline. One registry with domain-tagged occurrences is cleaner if Gap A ever ships. |

## Pairing with other gap docs

- **LEVNIK-AUDIT-SUITE-GAP Gap E**: this doc is the dedicated landing for that earlier-deferred gap
- **GOVERNANCE-GAP `governance_context`**: domain-specific governance rules (different boundary rules per domain) live in `governance_context.domain_overrides[]` if Gap A ships
- **CLEAN-ENVIRONMENT-VALIDATION-GAP**: per-domain clean validation needs per-domain worktrees; multiplies disk cost

## Adoption order

Deferred indefinitely. Revisit when:

- ≥3 user reports of contest-refactor used on multi-domain monorepos
- OR contest-refactor itself adopts a multi-domain structure (e.g., separate skills for different lenses become a single repo)
- OR levnik audit-suite domain-aware patterns become widely adopted in the ecosystem (current adoption: unclear)

Until then, the `--scope <dir>` workaround documented above is sufficient.

## Why this doc exists despite being deferred

To close the coverage gap LEVNIK-AUDIT-SUITE-GAP § Gap E flagged. Without this stub, future readers might assume domain-aware scanning was analyzed and rejected, when actually it was analyzed and DEFERRED. The distinction matters for revisiting the decision later.
