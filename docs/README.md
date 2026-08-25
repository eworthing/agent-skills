# docs/

Cross-skill findings and improvement plans. Analysis scoped to a single skill's competitive
landscape lives in [`analysis/contest-refactor/`](../analysis/contest-refactor/); this directory is
for work that spans `contest-refactor`, `peer-plan-review`, and `quorum-review` together.

**Split of the two `contest-refactor` registers:** the *review* register owns the skill's own correctness (artifact discipline, gates, certification, cost); the *detection-domain* register owns the skill's reach (which defect classes it can find at all). Seam items are cross-referenced, never dual-listed.

| Doc | What it covers |
|---|---|
| [contest-refactor-review-register.md](contest-refactor-review-register.md) | The `contest-refactor` standing review register (formerly `contest-refactor-code-review-2026-08-20.md`): five review passes' still-open findings merged from the retired deep-dive backlog, behavioral-validation ledger, and June research doc, plus the coverage snapshot, ponytail/duplication audits, and cost-ranked work order. The dated run-by-run record split out to `contest-refactor-run-log.md` on 2026-08-25. |
| [contest-refactor-run-log.md](contest-refactor-run-log.md) | The `contest-refactor` chronological run log: a dated entry per production run or root-caused incident (fleet run 2026-08-20, the run kit, run_id/G17 packet, instrumented runs #5–#8), appended to as they happen. Split out of the review register on 2026-08-25 so new entries stop crowding out its standing reference material. |
| [contest-refactor-detection-domains.md](contest-refactor-detection-domains.md) | The `contest-refactor` detection-domain register: what the loop looks for **in the target codebase** — current lens coverage, the 2026-08-21 competitor domain sweep over all 51 cloned competitors, the calibration discipline that governs adding a domain (measured recall lift of zero from added checklist prose), and the open detection backlog (rows 23/24/25/27, migrated from the review register). |
| [contest-refactor-gold-corpus-2026-08-25.md](contest-refactor-gold-corpus-2026-08-25.md) | Validated external feedback proposing a `contest-refactor` eval gold corpus built from real expert-reviewed Swift refactoring PRs (swift-collections #688/#298/#488, swift-nio #2486/#2959/#1801/#814, swift-async-algorithms #185, TCA #3460/#3845, Vapor auth tests) with RED/GREEN/NEAR-MISS/MUTANT sibling derivation, executable hidden oracles, a `must_not_find` negative oracle, and a provenance schema that treats "gold" as provenance (`accepted_state`/`gold_confidence`) rather than truth. All twelve sources and four benchmarks verified against upstream across three review rounds — including the reversal of the #814/Kitura-NIO#81 causality claim (#814 participates in the #837 + #814 fix chain, it was not the cause) — and adapted to serve restraint, calibration, execution, and scanner controls rather than reopening the closed detection programme. |
| [peer-plan-review-audit-2026-08-21.md](peer-plan-review-audit-2026-08-21.md) | Remediated multi-skill audit of `peer-plan-review` against commit `5be2de1`. All seven actionable findings are resolved by deleting the orphan eval scaffold, removing its unsupported provenance claim, and restoring the provider-selection pointer; three style-only findings remain rejected. Runtime gates are green, with the cross-tooling `argument-hint` validator mismatch recorded as a non-target gap. |

**Retired 2026-08-20** (merged into the review register, full text in git history):
`review-skill-deep-dive-2026-08-17.md` (four-pass landscape deep dive + 35-row backlog) and
`behavioral-validation-ledger.md` (LLM behavioral sweeps #1–#4, the paired-arm study, and
promotion bars). Citations to those paths from shipped scripts and prose are provenance
pointers; resolve them with `git log --follow` / `git show`.

## Related

- [`analysis/contest-refactor/GAP-REGISTER.md`](../analysis/contest-refactor/GAP-REGISTER.md) — the consolidated competitive-analysis register (44 files → 5, with per-doc dispositions).
- [`refs/competitors/README.md`](../refs/competitors/README.md) — the clone corpus itself (gitignored), bucketed by the skill each competitor targets.
