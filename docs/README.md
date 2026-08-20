# docs/

Cross-skill findings and improvement plans. Analysis scoped to a single skill's competitive
landscape lives in [`analysis/contest-refactor/`](../analysis/contest-refactor/); this directory is
for work that spans `contest-refactor`, `peer-plan-review`, and `quorum-review` together.

| Doc | What it covers |
|---|---|
| [contest-refactor-review-register.md](contest-refactor-review-register.md) | The consolidated `contest-refactor` review register (formerly `contest-refactor-code-review-2026-08-20.md`): five review passes plus the merged still-open findings from the retired deep-dive backlog, behavioral-validation ledger, and June research doc — including the open backlog and the operational measurement state those documents carried, and the cost-ranked work order. |

**Retired 2026-08-20** (merged into the doc above, full text in git history):
`review-skill-deep-dive-2026-08-17.md` (four-pass landscape deep dive + 35-row backlog) and
`behavioral-validation-ledger.md` (LLM behavioral sweeps #1–#4, the paired-arm study, and
promotion bars). Citations to those paths from shipped scripts and prose are provenance
pointers; resolve them with `git log --follow` / `git show`.

## Related

- [`analysis/contest-refactor/GAP-REGISTER.md`](../analysis/contest-refactor/GAP-REGISTER.md) — the consolidated competitive-analysis register (44 files → 5, with per-doc dispositions).
- [`refs/competitors/README.md`](../refs/competitors/README.md) — the clone corpus itself (gitignored), bucketed by the skill each competitor targets.
