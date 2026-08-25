# analysis/contest-refactor/

Point-in-time analysis and measurement artifacts for `contest-refactor` specifically — design
notes for a single backlog item, feasibility gates, sweep reports, and the run-kit's generated
output. Living registers and durable records (including ones that span multiple skills) live in
[`docs/`](../../docs/README.md) instead.

## Retirement rule

Quoting `GAP-REGISTER.md` directly: *"The three design docs retire here when their rows ship or
are declined."* In practice that means a design doc's content gets folded into `GAP-REGISTER.md`
once every row it covers reaches a terminal disposition (shipped or declined), with the design
doc itself deleted and its full text recoverable from git history (`git log --follow` /
`git show`) — the same pattern the register documents use for their own retired sources.

## Naming

Three shapes are in use, none of them enforced mechanically:

- **`SCREAMING-KEBAB-YYYY-MM-DD.md`** — dated, point-in-time analysis: design notes and
  feasibility gates (`ITEM14-HOST-ATTESTATION-DESIGN-2026-08-18.md`,
  `ITEM24-COVERAGE-UNIT-DESIGN-2026-08-19.md`, `ITEM25-TOOL-SUBSTRATE-2026-08-19.md`,
  `TIER3-FEASIBILITY-GATE-2026-08-20.md`, `DISPLACEMENT-2026-08-21.md`,
  `VACUOUS-SWEEP-2026-08-22.md`, `run-kit/G17-ADJUDICATION-2026-08-21.md`).
- **Undated `SCREAMING-KEBAB.md`** — living documents with no single as-of date: the consolidated
  register (`GAP-REGISTER.md`) and the run-kit's launch checklist (`run-kit/PREDECLARATION.md`).
- **Lowercase, dated** — generated output under `run-kit/reports/`, written by the run-kit
  scripts rather than authored by hand.

This describes the convention as it stands; nothing here is renamed to fit it.

## Index

| File | Purpose | Status |
|---|---|---|
| `GAP-REGISTER.md` | Consolidated competitive-analysis register (44 files → 5 → 4); per-doc dispositions, schema decisions, open ADOPT calls | Living, current |
| `ITEM14-HOST-ATTESTATION-DESIGN-2026-08-18.md` | Design note for host-attested execution evidence (backlog row 14) | Tier 1 shipped 2026-08-21 (`attested_run.py`, G47); Tier 2 privilege separation still open by design — not due for retirement |
| `ITEM24-COVERAGE-UNIT-DESIGN-2026-08-19.md` | Design note for deterministic selection + coverage manifest + resumable scan (backlog row 24) | Slices A/B/B2 shipped 2026-08-19; slices C (fingerprint invalidation/resume) and D (churn-prior ordering) still open — not due for retirement |
| `ITEM25-TOOL-SUBSTRATE-2026-08-19.md` | Design note for tool-grounded substrate + per-language rule packs (backlog row 25) | **Both halves terminal — due for retirement into `GAP-REGISTER.md`.** Half A shipped 2026-08-19; Half B adjudicated 2026-08-21 as budget-blocked (re-open only with a measured lift) |
| `TIER3-FEASIBILITY-GATE-2026-08-20.md` | Feasibility gate for the five-phase validator + host hook | PASSED/GO 2026-08-20 for the automatic-invocation threat model; the build itself is unstarted, priced by the owner |
| `DISPLACEMENT-2026-08-21.md` | Loop-path token-displacement inventory and design note | Candidate A shipped; Candidate B declined-not-deferred; §10 spun the vacuous-assertion sweep out into its own doc |
| `VACUOUS-SWEEP-2026-08-22.md` | Mutation-testing sweep of the selftest suite | Complete: 68 of 72 selftests mutation-tested, 23 proven vacuous, 22 fixed, 1 recorded-by-design, 1 withdrawn |
| `run-kit/posthoc_gate_sweep.py` | Builds a phase-to-gate matrix from artifact history by subprocessing the shipped validator | Validated against full BenchHype history (May→Aug, 4 runs) |
| `run-kit/coverage_citations.py` | Item-24 decision data: measures real file-citation coverage against the repo inventory | Validated against the same corpus |
| `run-kit/cost_accounting.py` | Reads opencode's sqlite session store read-only for cost/resident-token accounting | Validated against the Aug-19 run's 6 sessions |
| `run-kit/observe-tools.ts` | Observe-only opencode plugin logging `tool.execute.before/after` to JSONL; never blocks | Validated in a scratch opencode session (PASS) |
| `run-kit/PREDECLARATION.md` | D4 predeclaration: M1–M8 measurement definitions + launch checklist for the instrumented run | Living |
| `run-kit/G17-ADJUDICATION-2026-08-21.md` | G17 promotion-bar adjudication packet: 4 candidate datapoints (2 true violations, 1 expected-blind, 1 proposed false positive), all Swift | **Live — all four disposition checkboxes are unchecked; human adjudication is pending** |
| `run-kit/reports/benchhype-cost-run4-2026-08-21.{md,json}` | Generated cost-accounting report for the Aug-19 BenchHype run | Generated output |
| `run-kit/reports/benchhype-coverage-2026-08-21.{md,json}` | Generated coverage-citation report — the source of the 302/1313 files-cited / BenchHypeKit-24% figures that `contest-refactor-detection-domains.md` row 24 now owns | Generated output |
| `run-kit/reports/benchhype-posthoc-sweep-2026-08-21.{md,json}` | Generated phase-to-gate matrix report feeding the Tier-3 validator design | Generated output |
