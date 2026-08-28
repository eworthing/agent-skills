# Continue Prompt — Contest-Refactor Assessment Validity

Continue the assessment-validity research in
`/Users/Shared/git/agent-skills` on `main`. Do not implement the improvement
spec or commit changes yet.

## Read first

1. Repository `AGENTS.md` and applicable skills.
2. `contest-refactor/plans/assessment-research-prompt.md`.
3. `docs/contest-refactor-assessment-validity-research-2026-08-28.md`.
4. `contest-refactor/plans/assessment-validity-improvement-spec.md`.

The last two documents are provisional because competitor analysis is pending.
Preserve unrelated worktree changes. The expected untracked files are the
research prompt, report, spec, and this continuation prompt.

## Current checkpoint

- Bound repository revision:
  `784eeb5cc6b9bac7f057b86dff972f191e8b26cb`.
- Research-prompt SHA-256:
  `f49a6ac7e76ad693429a068359321ad20102d8d18d21c71998ee6cee54c353f4`.
- Seven gaps are accepted: three P0, three P1, one P2.
- Current decision: report-only Refactor Quality assessment; no headline
  aggregate and no certification.
- Proposed smallest design: extend `CURRENT_REVIEW.json` to v6, one new canon
  file, one validator module, and G51/G52.
- Current validation passed: repository validator, 102 artifact fixtures, 26
  gold-corpus packs, and the automated skill evaluator with three pre-existing
  warnings.
- The local competitor corpus contains 47 repositories under
  `refs/competitors/contest-refactor/`.
- That corpus is not indexed and has not been substantively compared. Do not
  describe the research or spec as complete until it is.

## Required competitor work

Use codebase-memory graph tools first for code discovery. Call `list_projects`;
index a competitor repository before structural exploration; use
`search_graph`, `trace_path`, and `get_code_snippet`; check index coverage for
every cited implementation path. Use direct text search only for READMEs,
specifications, configuration, literal values, or graph gaps.

First perform a cheap maturity and relevance triage across all 47 repositories.
Use repository metadata, current source layout, tests, releases/changelog,
assurance documents, and executable validators. Do not assume popularity or a
project name proves maturity. Select the smallest subset that has direct,
implemented answers to one or more accepted gaps.

At minimum, explicitly triage likely relevant candidates such as:

- `agent-verifier`;
- `agentlint`;
- `alibaba-open-code-review`;
- `archgate-cli`;
- `aws-agent-skill-eval`;
- `harness-eval`;
- `opendatahub-agent-eval-harness`;
- `prism`;
- `crucible`;
- `skilllens`;
- `brooks-lint`;
- `trailofbits-skills`.

The list is a starting set, not a required winner list. Add or remove candidates
based on evidence.

For every adopted or rejected competitor mechanism, record:

1. repository and bound revision;
2. exact source/test/spec evidence;
3. accepted gap addressed;
4. construct and claim ceiling;
5. applicability and coverage behavior;
6. decision role: detect, score, gate, report, delegate, defer, or exclude;
7. evidence identity and invalidation behavior;
8. calibration or validity evidence;
9. failure handling and visibility;
10. runtime, model, engineering, and maintenance cost;
11. what is stronger than the provisional design;
12. adoption, adaptation, delegation, or rejection decision.

Distinguish executable enforcement from documentation-only claims. Run the
smallest relevant tests or validators for mechanisms that would materially
change the spec.

## Questions to answer

- Does any competitor already separate assessment constructs and named
  assurance profiles more cleanly?
- Does any competitor bind evidence, policy, tools, model, corpus, and subject
  more completely without a second trust mechanism?
- Is there a stronger canonical evidence schema or finding/projection identity
  model?
- Does any competitor make applicability and multidimensional coverage a
  visible validity gate?
- Is there a measured semantic-judge calibration method with valid trial and
  cost accounting?
- Is there a more complete failure taxonomy that preserves stage-local causes?
- Can the provisional v6 design be made smaller by reusing an existing pattern?

## Required document updates

Update the research report with:

- a competitor selection method and coverage statement;
- a comparison matrix mapped to all seven accepted gaps;
- evidence-backed adopted and rejected mechanisms;
- any changed finding, claim ceiling, cost, or invalidation conclusion;
- an explicit residual uncertainty statement for unexamined competitors.

Then revise the improvement spec:

- keep only mechanisms that survive comparison;
- cite the competitor evidence that materially shaped a design choice;
- reduce file/schema/gate count when a simpler existing pattern works;
- keep certification and aggregation omitted unless new calibration evidence
  actually clears the research requirements.

Do not produce a task-by-task implementation plan until the revised spec is
reviewed and approved by the user.

## Final checks

Run:

```bash
python3 -B contest-refactor/scripts/validate-repo.py
python3 -B contest-refactor/scripts/validate-fixtures.py contest-refactor/evals/fixtures
python3 -B contest-refactor/scripts/validate-gold-corpus.py contest-refactor/evals/gold-corpus
python3 .claude/skills/skill-evaluator-1.0.0/scripts/eval-skill.py contest-refactor
git diff --check
```

Check every local Markdown link and remove unfinished markers, placeholder
claims, and unqualified certification language. Report exact competitor coverage,
validation output, remaining uncertainty, and worktree status. Do not commit
without an explicit user request.
