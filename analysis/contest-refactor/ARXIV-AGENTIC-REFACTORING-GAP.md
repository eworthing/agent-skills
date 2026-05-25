# arXiv:2511.04824 Empirical Falsifier — contest-refactor positioning risk

Source: Horikawa, K., Li, H., Kashiwa, Y., Adams, B., Iida, H., & Hassan, A. E. (2026, submitted Nov 6 2025). "Agentic Refactoring: An Empirical Study of AI Coding Agents." arXiv:2511.04824.

Not a gap against a competitor — a **falsifier against contest-refactor's stated premise**. Dataset: 15,451 refactoring instances across 12,256 pull requests + 14,988 commits, AIDev dataset, Java open-source projects. Closest-to-source empirical study of what AI coding agents (Codex, Claude Code, Cursor) actually do when they refactor.

## Key empirical findings (verbatim from abstract)

| Finding | Number |
|---|---|
| Refactoring is targeted in N% of commits | **26.1%** |
| Change Variable Type | 11.8% |
| Rename Parameter | 10.4% |
| Rename Variable | 8.5% |
| Motivation: Maintainability | 52.5% |
| Motivation: Readability | 28.1% |
| Class LOC median Δ for medium-level changes | **-15.25** |

Verbatim from abstract: *"agentic efforts are dominated by low-level, consistency-oriented edits, such as Change Variable Type (11.8%), Rename Parameter (10.4%), and Rename Variable (8.5%), reflecting a preference for localized improvements over the high-level design changes common in human refactoring."*

## Implication for contest-refactor

Contest-refactor positions itself as an **autonomous architecture-first refactoring loop targeting contest-grade quality (9.5+ in every scorecard dimension)**. The arXiv paper challenges the assumption that AI agents — even with Actor-Critic discipline + validation gates + persistent loop state — actually produce high-level architecture changes in practice.

Stated differently: even the BEST CASE for agentic refactoring across 12k+ PRs shows the top 3 refactoring types are all **rename/retype operations**. Combined: 30.7% of all refactoring instances are renames or type-narrowing. None of contest-refactor's 5 architectural tests (Deletion test, Two-adapter rule, Shallow module, Interface-as-test-surface, Replace-don't-layer) target rename/retype.

## Two possible readings

### Reading A: contest-refactor is fighting model-class limits

If agents tend toward low-level edits because that's what current models can verify safely, then contest-refactor's pressure for high-level edits via the 9.5+ scoring threshold + Actor-Critic discipline may produce one of:

1. **Honest stagnation** — loop halts at `HALT_STAGNATION` because high-level findings keep getting rejected by Implementation Reviewer (correct behavior; nothing to fix in contest-refactor)
2. **Architecture theater** — Critic invents structural findings to score points (Q3, fake-clean reward) when the underlying model can't produce honest high-level diffs. THIS is the failure mode contest-refactor explicitly opposes per doc § 7.
3. **Genuine high-level edits** — rare; possibly disproportionately attempted by users running contest-refactor (who self-select for ambition).

Reading A says: contest-refactor's discipline is correct but may produce more HALT_STAGNATION than expected. That's an honest outcome and the existing halt taxonomy handles it.

### Reading B: contest-refactor's premise is overscoped

If 70%+ of agentic refactor value is in low-level consistency edits (renames, retypes, dead-code removal), then a refactor loop targeting high-level architecture is solving the wrong problem. Contest-refactor would deliver more value if it ACCEPTED low-level refactoring as the primary mode and treated architecture findings as opt-in.

Reading B says: contest-refactor should reframe.

## Recommended response (neither Reading A nor B in full)

### Adopt arXiv finding as a calibration anchor, not a falsifier

The paper measures **what agents currently do across the corpus**; contest-refactor measures **what agents should do** under its rubric. The paper's finding is data, not verdict. But ignoring it would be intellectually dishonest.

**Concrete adoption**:

1. **Add empirical baseline citation** to contest-refactor's `references/architecture-rubric.md` § Severity Anchors:

   > Per Horikawa et al. (arXiv:2511.04824, Nov 2025), AI agents in production target rename/retype operations (Change Variable Type 11.8%, Rename Parameter 10.4%, Rename Variable 8.5%) far more often than structural changes. contest-refactor's `test_failed` enum targets structural changes specifically; expect findings authored under this rubric to be rarer per loop than the agentic baseline. Loops emitting only rename/retype findings should consider whether the Critic is operating below the rubric's intent OR the codebase genuinely lacks structural debt — `HALT_STAGNATION/no_backlog` is the correct halt for the latter.

2. **Track refactoring-type distribution per loop** as audit-only field (no behavior change):

   ```jsonc
   {
     "loop_result": {
       // ... existing fields ...
       "refactoring_types": [          // NEW audit-only field
         {"type": "Change Variable Type", "count": 0},
         {"type": "Rename Parameter", "count": 0},
         {"type": "Rename Variable", "count": 0},
         {"type": "Extract Method", "count": 1},
         {"type": "Move Field", "count": 0},
         // ... pairs with TRACEABILITY-GAP Gap A.1 canonical pattern vocabulary
       ]
     }
   }
   ```

   Populated by Implementation Reviewer (it already parses the diff). Over many loops, accumulated in `REVIEW_HISTORY.json` lets users see whether their contest-refactor runs match the arXiv low-level pattern or genuinely produce structural changes.

3. **Honest disclaimer in SKILL.md** description:

   Append to the description block:

   > Empirical context: AI agents typically produce low-level refactorings (renames, retypes — see Horikawa et al. 2025). contest-refactor's architecture-first rubric biases toward structural findings; runs may halt at `HALT_STAGNATION` when the codebase has no remaining structural debt the agent can address.

## What this DOES NOT change in contest-refactor

The arXiv finding is not a structural critique of contest-refactor's mechanics:

- Actor-Critic split (CRITIC-INDEPENDENCE Gap A) — still correct independent of refactor-type distribution
- Halt taxonomy + loop state machinery — handles low-level outcomes via HALT_STAGNATION/no_backlog
- Causal traceability (TRACEABILITY-GAP Gap A `changed_hunks[]`) — useful regardless of refactor type
- Validation gates G1-G31 — orthogonal to refactor type
- Severity enum — `Cosmetic for contest` already covers low-level edits

The 9.5+ scoring threshold is the only mechanism that interacts directly: if low-level edits genuinely reach 9.5+ scores, the threshold gates pass; if they don't, HALT_STAGNATION fires. Both are correct outcomes.

## What this challenges (worth user discussion)

1. **`test_failed` enum bias**: all 5 architectural tests target structural change (Deletion test, Two-adapter rule, Shallow module, Interface-as-test-surface, Replace-don't-layer). None covers rename/retype. If the arXiv distribution holds, the enum may be wrong about where contest-refactor will produce most findings. Options:
   - Add new `test_failed` values: `Name precision`, `Type narrowness`, `Identifier consistency`
   - Acknowledge the bias and keep enum focused on architectural; document that rename/retype findings live under `Cosmetic for contest` severity by default
2. **Verdict enum tone**: contest-refactor's verdicts ("Strong contender", "Promising, but architecturally immature") are architecture-themed. If a codebase scores 9.5+ via clean low-level hygiene + reasonable architecture (not great, not bad), no verdict fits. Options:
   - Add `"Industrially solid, architecturally conservative"` verdict
   - Keep verdicts as-is; rely on HALT_SUCCESS at 9.5+ to convey acceptance
3. **Scorecard weight bias**: 6 of 9 scorecard dimensions are architecture-adjacent (`architecture_quality`, `state_management`, `concurrency`, `domain_modeling`, `data_flow`, `framework_idioms`). 2 are tangential (`simplicity`, `credibility`). 1 explicit (`test_strategy`). If the agent mostly produces rename/retype changes, those affect `simplicity` + `credibility` strongly but leave the 6 architecture dimensions stagnant. **The scorecard may UNDERWEIGHT low-level value**. Consider adding `code_hygiene` dimension covering rename/retype/dead-code as 10th dimension.

## Risk flags

1. **Java-only generalization risk**: arXiv study is Java-only. Swift/Rust/Go/Python may have different distributions. Don't over-anchor on 11.8% / 10.4% / 8.5% specifically.
2. **Publication recency**: paper submitted 2025-11; not yet peer-reviewed at time of contest-refactor analysis. Findings may revise.
3. **Selection bias**: AIDev dataset is open-source PRs where agents were used. Excludes proprietary contexts, agent-assisted dev that didn't ship PRs, refactoring outside PR boundaries.

## Adoption order

1. **Phase 1 (free)**: Add citation block to `references/architecture-rubric.md` § Severity Anchors. Honest acknowledgment in SKILL.md description.
2. **Phase 2 (small)**: Add `loop_result.refactoring_types[]` audit-only field. Implementation Reviewer populates.
3. **Phase 3 (medium)**: After 10+ contest-refactor runs accumulate refactoring_types data in `REVIEW_HISTORY.json`, analyze whether contest-refactor produces structural findings disproportionately to arXiv baseline. If yes, position validated. If no, revisit Reading B.
4. **Phase 4 (defer, philosophical)**: Consider 10th scorecard dimension `code_hygiene` and verdict + `test_failed` enum extensions per § "What this challenges" above. Requires user discussion.

## Pairing with other gap docs

- **TRACEABILITY-GAP Gap A.1 (refactoring-pattern canonical vocabulary)**: arXiv's refactoring-type categories (Change Variable Type, Rename Parameter, Rename Variable, Extract Method, Move Field, etc.) suggest a canonical Fowler-derived enum that pairs with Gap A.1's commit-subject pattern naming
- **SCHEMA-GAP severity_anchors**: `Cosmetic for contest` is where rename/retype findings live today; arXiv data suggests this severity tier will dominate
- **HALT-STATE-GAP `HALT_STAGNATION/no_backlog`**: arXiv's low-level-dominance supports current halt taxonomy — when no structural debt remains, this is the correct halt
- **LEVNIK-AUDIT-SUITE-GAP specialty lenses**: levnik's ln-624 (code-maintainability-hotspot-auditor) targets exactly the low-level edits arXiv measures; a `lens-hygiene.md` specialty lens (extending SPECIALTY-LENS-DISPATCH-GAP) would catch what contest-refactor's architecture-first rubric overlooks
