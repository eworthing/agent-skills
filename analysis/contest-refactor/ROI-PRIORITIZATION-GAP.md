# ROI-Weighted Backlog Prioritization Gap — contest-refactor vs forensic-skills

Source: `refs/competitors/forensic-skills/.claude/skills/forensic-hotspot-finder/SKILL.md` + `forensic-refactoring-roi/SKILL.md`. Verified by RESEARCH-DELTA.

## Baseline: contest-refactor today

- Backlog priority is integer rank (`priority: 1, 2, 3...`)
- Implicit ordering rule: Critic emits findings sorted by Priority, then Actor picks `priority: 1` finding to fix
- Severity influences priority but isn't combined with cost-of-fix or change-frequency
- No churn/complexity/defect-history signal
- `findings_registry.json` tracks per-finding occurrences but not file-level hotness metrics

## What forensic-skills does (source-verified)

### Hotspot formula (`forensic-hotspot-finder/SKILL.md:49-56`)

```
Risk Score = Normalized Change Frequency × Normalized Complexity Factor
```

Both factors normalized to 0-1 before multiplication. Cites Microsoft + Google research: files in top 10% of BOTH change frequency AND complexity show 4-9x higher defect rates.

Inputs:
- Change Frequency: `git log --pretty=format: --name-only | sort | uniq -c | sort -rn`
- Complexity Factor: cyclomatic complexity OR LOC OR npath count

Output: ranked Mermaid table `Risk Score | Changes | LOC | File`.

### ROI tiers (`forensic-refactoring-roi/SKILL.md:50-68`)

```
ROI = (Annual Savings / Investment Cost) × 100
```

| Tier | ROI | Break-even |
|---|---|---|
| QUICK WINS | >500% | <3 months |
| HIGH PRIORITY | 300-500% | <6 months |
| STRATEGIC | 150-300% | <12 months |
| LOW | <150% | n/a |

### Effort formula (`forensic-refactoring-roi/SKILL.md:72-86`)

```
Base Effort = (LOC / 100) × Complexity Multiplier
```

Adjustment factors (multiplicative): test coverage, dependency count, criticality tier, team familiarity. Each factor ranges 0.5x (favorable) to 2x (unfavorable).

### Output format

Per-finding tagged with ROI tier + effort estimate + payback. Final report includes:
- Executive summary by tier
- Quadrant matrix (effort vs ROI, 4 quadrants)
- Phased roadmap with milestones (per quarter)

## Strategic insight

Contest-refactor's priority integer is a 1-dimensional ordering. ROI prioritization adds dimensions:

1. **Change frequency** → biases toward files actually being touched (low-churn files are lower priority even if structurally bad)
2. **Complexity** → biases toward genuinely hard-to-change files
3. **Effort cost** → biases toward fixable findings (a `Likely disqualifier` requiring 3 months refactor may rank below a `Serious deduction` fixable in 1 week)
4. **Investment vs return** → makes priority defensible to stakeholders (not just "Critic says so")

The arXiv falsifier (`ARXIV-AGENTIC-REFACTORING-GAP.md`) shows agents naturally tend to low-effort edits. ROI prioritization can CALIBRATE this: low-cost rename/retype edits should rank high when their target file is high-churn (high payoff for low effort). Currently contest-refactor doesn't have this signal.

## Gap matrix

| Mechanism | contest-refactor | forensic-skills |
|---|:--:|:--:|
| Priority field per backlog item | ✓ integer rank | partial (implicit via ROI) |
| Severity field | ✓ 4-tier | ✓ critical/high/medium/low |
| Change frequency input | — | ✓ `git log` derived |
| Complexity input | — | ✓ cyclomatic/LOC/npath |
| Risk Score = freq × complexity | — | ✓ normalized formula |
| Effort estimate | — | ✓ Base Effort × adjustment factors |
| ROI calculation | — | ✓ annual savings ÷ investment |
| ROI tiers as enum | — | ✓ 4 tiers |
| Quadrant visualization | — | ✓ Mermaid |
| Phased roadmap output | — | ✓ per-quarter milestones |
| Per-finding tier annotation | — | ✓ in final report |

## P1 GAPS — what to import

### Gap A (P1): Add `roi_score` + `effort_estimate` + `roi_tier` to backlog entries

**Schema additions** (additive, `schema_version: 4`):

```jsonc
{
  "backlog": [
    {
      "priority": 1,                                  // existing — kept
      "title": "Collapse navigation duplicate authority",
      "kind": "structural",
      "rank": "needed for winning",
      "why_it_matters": "...",

      // NEW fields (all optional; populated only when governance_context provides hotspot data)
      "hotspot_risk_score": 0.78,                     // 0-1; from Normalized Change Frequency × Normalized Complexity Factor
      "effort_estimate": {
        "base_effort_hours": 16,                      // (LOC / 100) × complexity_multiplier
        "adjustment_factors": {
          "test_coverage": 1.5,                       // weak coverage → higher effort
          "dependency_count": 1.2,                    // many dependents → higher effort
          "criticality": 1.0,
          "team_familiarity": 0.8                     // familiar → lower effort
        },
        "adjusted_effort_hours": 23                   // base × product(factors)
      },
      "roi": {
        "annual_savings_estimate_hours": 120,         // saved future-touch hours per year
        "roi_percent": 521,                           // 120/23 × 100
        "tier": "quick_wins",                         // enum: quick_wins | high_priority | strategic | low
        "break_even_months": 2
      }
    }
  ]
}
```

`priority` integer stays as ground truth for Actor's "what to fix next" decision. `roi_score` + `roi_tier` ride alongside as audit data and (optionally) inform the Critic's `priority` assignment when ROI data is available.

### Gap B (P1): Backlog ordering rule extension

Method.md update — Critic's backlog ordering becomes:

> Backlog priority is set by:
> 1. Severity (Likely disqualifier > Serious deduction > Noticeable weakness > Cosmetic for contest) — primary axis
> 2. Within same severity: by `roi_tier` if populated (quick_wins > high_priority > strategic > low) — tie-breaker
> 3. Within same severity + ROI tier: by `hotspot_risk_score` descending — final tie-breaker
>
> When `governance_context.refactoring_priorities[]` provides hotspot data for backlog items, Critic MUST populate the optional fields above. Without governance_context data, falls back to severity-only ordering (current behavior).

### Gap C (P1): `governance_context.refactoring_priorities[]` integration

Pairs with GOVERNANCE-GAP `governance_context` durable container. Step 0 invokes a hotspot-analysis script and seeds:

```jsonc
{
  "governance_context": {
    "refactoring_priorities": [
      {
        "file_pattern": "src/Auth/TokenStore.swift",
        "hotspot_risk_score": 0.78,
        "annual_change_frequency": 47,
        "complexity_score": 24,
        "annual_savings_estimate_hours": 120,
        "computed_at": "2026-04-12T08:00:00Z"
      }
    ]
  }
}
```

Recomputed on demand (`--recompute-hotspots` flag) OR cached for N days (default 90).

### Gap D (P2): Per-loop quadrant artifact

Each loop emits Mermaid quadrant alongside `CURRENT_REVIEW.md`:

```
quadrantChart
    title Backlog effort vs ROI
    x-axis "Low effort" --> "High effort"
    y-axis "Low ROI" --> "High ROI"
    quadrant-1 "Strategic"
    quadrant-2 "Quick Wins"
    quadrant-3 "Low priority"
    quadrant-4 "Hard sells"
    F1: [0.2, 0.9]
    F2: [0.8, 0.7]
```

Audit-only; doesn't affect scoring or gates. Helps human readers triage.

### Gap E (defer): Phased roadmap output for HALT_LOOP_CAP

When HALT_LOOP_CAP fires (loop_cap reached), emit a phased roadmap showing what's left + estimated quarters per backlog item. Pairs with halt_handoff to give the user a "next 3 months of work" plan.

## Implementation notes

1. **Hotspot analysis script**: ship `scripts/compute-hotspots.py` (stdlib-only). Wraps `git log --name-only --pretty=format:` + cyclomatic-complexity-approximation (count `if`/`else`/`for`/`while`/`case` keywords as fallback when no per-language AST tool installed).
2. **Caching** (per Codex round 1 B2 — HEAD-SHA-only key invalidates every loop because contest-refactor commits every loop via G22): cache result in `.contest-refactor/hotspots-cache.json` keyed by `(git log --since=<cache_age_cutoff> shortstat content-hash, content-hashes of source-root files)`. Recompute incrementally when `loop_result.changed_paths[]` intersects source_roots (re-tally affected files' churn + complexity). Full rebuild only on `--recompute-hotspots` flag OR cache > 90 days OR no prior cache. Hotspot scores for unchanged files carry forward; commit-per-loop is cheap.
3. **Language-aware complexity** (Phase 2): per-lens override. `lens-apple.md` uses `swift-format`-style complexity if installed; `lens-generic.md` uses LOC fallback.
4. **Validation gate G37** (new): When `backlog[].roi.tier` populated for one item, MUST be populated for all items in same loop's backlog (consistency). When `governance_context.refactoring_priorities[]` empty, all `backlog[].roi.*` MUST be null (no fake ROI).

## What contest-refactor wins vs forensic-skills

- **Cross-loop finding identity** (`findings_registry.json` + stable_id + fingerprint): forensic-skills operates per-run, no persistence. Contest-refactor's finding identity makes ROI calculations COMPARABLE across runs.
- **Per-finding rubric anchors**: forensic-skills' ROI is finding-agnostic (a refactoring "candidate" is identified by path + cost). Contest-refactor's ICA-grounded `test_failed` enum + scorecard dimensions tie ROI to architectural value, not just file-level churn.

## What NOT to import

| Tempting | Why skip |
|---|---|
| Replace `priority` integer with ROI tier | Priority is Actor's "what to fix NEXT" decision. ROI is one input. Don't conflate. Keep priority as ground truth, ROI as data. |
| Forensic-skills' phased per-quarter roadmap as core output | Roadmap is human-facing reporting (Gap E). Don't embed in core artifact; defer to optional HALT_LOOP_CAP handoff. |
| LLM-judged ROI estimation | ROI inputs (change frequency, LOC, complexity) are deterministic. Hotspot script computes; LLM shouldn't estimate hours-saved (that's where motivated reasoning enters). Effort estimate adjustment factors can be LLM-suggested but must be capped at known ranges (0.5x-2x). |
| Ship 4-tier ROI enum without effort estimate | ROI without effort isn't ROI. If effort estimate can't be computed (no LOC, no complexity tool), don't populate `roi.tier`. Falsifies less. |
| Per-finding test-coverage-from-codecov integration | Coverage tool integration is per-team. Keep `test_coverage` adjustment factor as Critic-prose-judged (or skill-config-supplied) for now. |

## Pairing with other gap docs

- **GOVERNANCE-GAP `governance_context`**: ROI lives in `governance_context.refactoring_priorities[]`; Gap C populates it
- **HALT-STATE-GAP `HALT_STAGNATION/no_backlog`**: ROI tier helps Actor distinguish "no backlog because clean" from "no backlog because everything is `low` tier" — latter is `HALT_STAGNATION/no_economic_case`, a new subtype to consider
- **SKILL-TDD-FIXTURES-GAP fixture #5 (theater-rename-only)**: should test ROI calculation on rename-heavy refactor (high ROI per hour because low effort)
- **ARXIV-AGENTIC-REFACTORING-GAP**: low-level rename refactors should rank HIGH in ROI (low effort × high frequency × moderate savings), validating that arXiv's low-level baseline is economically rational, not just model-limited
- **LEVNIK-AUDIT-SUITE-GAP specialty lens dispatch**: hotspot-finder could be one specialty lens type (`forensic_hotspot_lens`)

## Adoption order

**Cross-doc serialization (per Gemini Pro peer review round 1, N1):** Phase 3 schema bump MUST ship before SKILL-TDD-FIXTURES Phase 4 (fixtures #1-4 that assert ROI tiers). Phase 3 has no dependency on SKILL-TDD-FIXTURES Phase 2 (fixture #5 uses refactoring_types ratio only, no ROI assertion).

| Doc | Phase | Depends on |
|---|---|---|
| ROI-PRIORITIZATION Phase 1 (compute-hotspots.py) | first | none |
| ROI-PRIORITIZATION Phase 2 (governance_context.refactoring_priorities) | second | GOVERNANCE-GAP Gap A (governance_context container) |
| ROI-PRIORITIZATION Phase 3 (schema bump) | third | schema_version 4 in flight |
| ROI-PRIORITIZATION Phase 4 (G37 + Method ordering) | fourth | Phase 3 |
| SKILL-TDD-FIXTURES fixture #5 | parallel with ROI Phase 1-2 | TRACEABILITY Gap A + A.1 (NOT ROI) |
| SKILL-TDD-FIXTURES fixtures #1-4 | AFTER ROI Phase 3 | ROI Phase 3 + Phase 4 |

1. **Phase 1**: Ship `scripts/compute-hotspots.py` standalone. Generates `.contest-refactor/hotspots-cache.json`. No schema change yet.
2. **Phase 2**: Wire Step 0 to read hotspots into `governance_context.refactoring_priorities[]`.
3. **Phase 3**: Schema bump to schema_version 4 adding `backlog[].hotspot_risk_score` + `effort_estimate` + `roi`.
4. **Phase 4**: Method.md backlog ordering rule extension + G37 validation gate.
5. **Phase 5** (defer): Quadrant Mermaid output (Gap D) + phased roadmap on HALT_LOOP_CAP (Gap E).

## Risk flags

1. **Hotspot calculation is repo-specific**: shallow clones or new repos have weak `git log` data. Mitigation: `scripts/compute-hotspots.py` falls back to LOC-only score when commit history < N commits.
2. **ROI estimates are speculative**: "annual savings hours" is a fudge factor. Mitigation: never use ROI as a HARD GATE; only as backlog-ordering tie-breaker.
3. **Effort estimate gaming**: Critic could low-ball effort to inflate ROI tier. Mitigation: G37 enforces consistency; Implementation Reviewer's regression check can flag "estimated 4h actually took 16h" patterns over time.
4. **Hotspot data drift**: cached hotspots stale within 90 days. Mitigation: incremental recompute on changed_paths[] (per Codex B2 fix above); explicit `--recompute-hotspots` flag forces full rebuild.
