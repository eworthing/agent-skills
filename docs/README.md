# docs/

Cross-skill findings and improvement plans. Analysis scoped to a single skill's competitive
landscape lives in [`analysis/contest-refactor/`](../analysis/contest-refactor/); this directory is
for work that spans `contest-refactor`, `peer-plan-review`, and `quorum-review` together.

**Split of the two `contest-refactor` registers:** the *review* register owns the skill's own correctness (artifact discipline, gates, certification, cost); the *detection-domain* register owns the skill's reach (which defect classes it can find at all). Seam items are cross-referenced, never dual-listed.

| Doc | What it covers |
|---|---|
| [contest-refactor-review-register.md](contest-refactor-review-register.md) | The consolidated `contest-refactor` review register (formerly `contest-refactor-code-review-2026-08-20.md`): five review passes plus the merged still-open findings from the retired deep-dive backlog, behavioral-validation ledger, and June research doc — including the open backlog and the operational measurement state those documents carried, and the cost-ranked work order. |
| [contest-refactor-detection-domains.md](contest-refactor-detection-domains.md) | The `contest-refactor` detection-domain register: what the loop looks for **in the target codebase** — current lens coverage, the 2026-08-21 competitor domain sweep over all 51 cloned competitors, the calibration discipline that governs adding a domain (measured recall lift of zero from added checklist prose), and the open detection backlog (rows 23/24/25/27, migrated from the review register). |
| [peer-plan-review-audit-2026-08-21.md](peer-plan-review-audit-2026-08-21.md) | Three-skill audit of `peer-plan-review` (skill-writer + writing-for-agents + skill-creator lenses) against commit `5be2de1`: all validation gates verified live and green; open findings concentrated in the 2026-08-21 eval scaffolding — eval 0 asserts the two-pass output contract for a standard review, `evals.json` deviates from the skill-creator tooling schema it claims, an unbacked 194-invocation provenance claim in EVAL.md, and the router-table rewording dropped the provider-reference branch condition. Single-skill scope by explicit request; charter note inside. |

**Retired 2026-08-20** (merged into the review register, full text in git history):
`review-skill-deep-dive-2026-08-17.md` (four-pass landscape deep dive + 35-row backlog) and
`behavioral-validation-ledger.md` (LLM behavioral sweeps #1–#4, the paired-arm study, and
promotion bars). Citations to those paths from shipped scripts and prose are provenance
pointers; resolve them with `git log --follow` / `git show`.

## Related

- [`analysis/contest-refactor/GAP-REGISTER.md`](../analysis/contest-refactor/GAP-REGISTER.md) — the consolidated competitive-analysis register (44 files → 5, with per-doc dispositions).
- [`refs/competitors/README.md`](../refs/competitors/README.md) — the clone corpus itself (gitignored), bucketed by the skill each competitor targets.
