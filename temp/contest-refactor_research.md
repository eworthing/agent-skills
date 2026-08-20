# Raising contest-refactor From Reliable Refactor Loop to Principal-Grade Architecture Recall

## Executive Judgment

The recommended next path is:

```text
benchmark-first
```

Then:

```text
domain-integrity lens
+ Serious+ grounded change-scenario requirement
+ Serious+ minimal tradeoff analysis
+ context-sufficiency honesty and score caps
+ read-only change-coupling candidate evidence
```

Defer expert panels until benchmark data proves they are needed.

The main judgment:

1. The ceiling problem is real. Current AI coding agents are much better at local, low-level, consistency-preserving refactors than at finding and safely resolving deeper architectural defects.

2. contest-refactor already appears to have strong floor-raising mechanisms: evidence tracking, validation gates, anti-churn rules, loop isolation, challenger review, halt discipline, dry-run/resume controls, RED-first eval harnesses, source-status checks, and anti-theater doctrine. More floor work is not the highest-leverage path.

3. The next missing capability is not “more reviewers” or “more process.” It is a benchmark that can measure whether the loop finds seeded principal-grade architecture defects.

4. The benchmark is the keystone. Without it, every proposed improvement risks becoming ceremony, confidence polish, or architecture cosplay.

5. The first benchmark should seed defects that are deep but still inspectable: missing invariant owner, duplicated rule drift, wrong transaction/process owner, wrong consistency boundary, dependency-direction violation with hidden domain rule, and cross-module invariant without a clear owner.

6. Domain-integrity is the highest-confidence post-benchmark lens because it targets ownership, invariants, consistency boundaries, process ownership, and duplicated business rules directly.

7. Change-coupling is worth building, but only as candidate evidence. Co-change data is useful, empirically grounded, and cheap, but too noisy to produce final findings by itself.

8. Serious+ architecture findings should normally require a grounded change scenario. The finding must explain what change or current force makes the structure fail, where that scenario came from, how the current design shears, and why the proposed move wins.

9. Serious+ structural fixes should include a minimal tradeoff record: chosen move, explicit forces, two or three rejected alternatives, and consequences. This is ADR-lite, not a full ceremony.

10. Expert panels should be deferred. Multi-agent systems can increase exploration, but recent evidence also shows minimal gains in some settings and introduces coordination failure modes. Add a panel only when hidden benchmark data proves recall remains low after the benchmark, domain-integrity lens, change-scenario rule, tradeoff rule, honesty caps, and change-coupling artifact are in place.

Final next three steps:

```text
1. Build evals/principal_defects/.
2. Add domain-integrity + change_scenario + tradeoff_analysis + context score caps.
3. Add read-only change-coupling as candidate evidence only.
```

Do not add a generic expert panel yet.

---

## Methodology

This report prioritizes sources that can support implementation decisions rather than vibes.

Source priority:

1. Peer-reviewed or empirical software engineering papers.
2. arXiv papers with clear methodology.
3. SEI / CMU architecture method sources.
4. Classic architecture and modularity sources.
5. Official documentation from reputable platform or architecture teams.
6. Reputable practitioner sources with concrete, inspectable architecture methods.
7. Primary GitHub repositories, used only as method references.
8. Marketplace or secondary sources, used only provisionally.

Excluded or downgraded:

- Generic “add more agents” claims without measurable evaluation evidence.
- Broad competitor inventories.
- Star-count claims unless directly verified.
- Marketplace-only claims.
- Unfound or mismatched repos.
- DDD terminology used as aesthetic modeling rather than evidence of ownership or consistency defects.
- Any recommendation that merely renames existing contest-refactor artifacts or duplicates mechanisms already assumed present.

Important stance:

DDD concepts are useful, but contest-refactor should not assume every project is DDD. The useful generalized concepts are:

- invariant ownership
- business-rule ownership
- aggregate or module consistency boundary
- bounded context or semantic boundary
- transaction owner
- process owner
- domain event
- rule duplication
- rule drift
- adapter or infrastructure leakage
- explicit vs accidental consistency

---

## Evidence Table

| Source | Link | Evidence type | Claim supported | Confidence | Caveats |
|---|---|---|---|---|---|
| Agentic Refactoring: An Empirical Study of AI Coding Agents | https://arxiv.org/abs/2511.04824 | Empirical paper | Agentic refactoring is dominated by low-level/localized edits; high-level design changes are underrepresented. Supports the ceiling-problem diagnosis. | High | Preprint. Refactoring behavior is not identical to architecture-review recall. |
| How do Agents Refactor: An Empirical Study | https://arxiv.org/abs/2601.20160 | Empirical paper | Agent refactorings are less structurally diverse than developer refactorings and skew toward narrow change categories. | Medium-High | Preprint; tool mix may not generalize. |
| “Refactoring Runaway”: Understanding and Mitigating Tangled Refactorings in Coding Agents for Issue Resolution | https://arxiv.org/abs/2605.22526 | Empirical paper | Tangled refactorings reduce compilability and reliability; refactoring-aware refinement helps. Supports tangled-refactor penalties and remedy-track evaluation. | High | Focuses on issue-resolution patches, not principal architecture recall. |
| Where Do AI Coding Agents Fail? An Empirical Study of Failed Agentic Pull Requests in GitHub | https://arxiv.org/abs/2601.15195 | Empirical paper | Failed agent PRs tend to be broader and more CI-fragile. Supports caution around wide, tangled architectural patches. | High | PR merge/CI outcomes are not direct architecture recall measures. |
| Beyond Resolution Rates: Behavioral Drivers of Coding Agent Success and Failure | https://arxiv.org/abs/2604.02547 | Empirical paper | Some tasks fail due to architectural reasoning and domain knowledge gaps, not simply code complexity. | High | Repository-agent benchmark evidence, not contest-refactor-specific. |
| Code Review Agent Benchmark / c-CRAB | https://arxiv.org/abs/2603.23448 | Empirical benchmark paper | Code-review findings should be evaluated against executable or issue-grounded oracles, not text similarity alone. Supports executable principal-defect benchmark design. | High | Code-review benchmark, not architecture-refactoring benchmark. |
| RACE-bench: A Benchmark for Evaluating Repository-Level Code Agents with Intermediate Reasoning on Feature Addition Task | https://arxiv.org/abs/2603.26337 | Empirical benchmark paper | Repository-level agents should be evaluated on intermediate reasoning steps, not only final patch outcomes. Supports scoring detection, localization, remedy, and reasoning separately. | High | Feature-addition benchmark, not architecture-defect benchmark. |
| REAP: Automatic Curation of Coding Agent Benchmarks from Production Data | https://arxiv.org/abs/2604.01527 | Empirical benchmark paper | Realistic benchmark curation, automation, stability checks, and held-out evaluation matter. | Medium-High | Production-assistant setting may differ from contest-refactor. |
| On the Criteria To Be Used in Decomposing Systems into Modules, David Parnas | https://wstomv.win.tue.nl/edu/2ip30/references/criteria_for_modularization.pdf | Classic architecture paper | Modules should hide design decisions likely to change. Supports change-scenario stress testing and roadmap-shear analysis. | High | Classic conceptual work, not empirical agent evidence. |
| SEI Architecture Tradeoff Analysis Method / ATAM collection | https://www.sei.cmu.edu/library/architecture-tradeoff-analysis-method-collection/ | Architecture method | Architecture evaluation should surface risks, tradeoffs, scenarios, and business-goal links. Supports Serious+ scenario and tradeoff requirements. | High | Formal method may be too heavy unless distilled. |
| SEI ATAM method overview | https://www.sei.cmu.edu/library/atam-method-for-architecture-evaluation/ | Architecture method | ATAM uses scenario-driven evaluation to expose architecture risks, tradeoffs, and sensitivity points. | High | Needs lightweight adaptation. |
| SEI Quality Attribute Workshop | https://www.sei.cmu.edu/library/the-sei-quality-attribute-workshop/ | Architecture method | Quality-attribute evaluation requires business/mission goals and scenarios. Supports context-sufficiency caps. | High | Stakeholder workshop, not automated loop design. |
| SEI Quality Attribute Workshop collection | https://www.sei.cmu.edu/library/quality-attribute-workshop-collection/ | Architecture method | Scenario collection and prioritization are core to architecture evaluation. | High | Formal workshop method. |
| Achieving Product Qualities Through Software Architecture Practices | https://pdfs.semanticscholar.org/4b08/fbf54d9076ed9def783d51fc13597577afcc.pdf | Architecture method / training material | Quality attribute scenarios need source, stimulus, environment, artifact, response, and response measure. | High | Not a coding-agent paper. |
| Microsoft Azure: Use tactical DDD to design microservices | https://learn.microsoft.com/en-us/azure/architecture/microservices/model/tactical-domain-driven-design | Official docs | Aggregates define consistency boundaries and transactional invariants; domain and application services have distinct responsibilities. | High | Microservices/DDD framing must be generalized. |
| Microsoft: Domain events design and implementation | https://learn.microsoft.com/en-us/dotnet/architecture/microservices/microservice-ddd-cqrs-patterns/domain-events-design-implementation | Official docs | Domain events are a way to handle business rules and side effects across aggregates. | High | .NET-oriented. |
| Microsoft Azure: Saga distributed transactions pattern | https://learn.microsoft.com/en-us/azure/architecture/patterns/saga | Official docs | Cross-service consistency requires explicit process coordination and compensating actions. Supports transaction/process-owner lens. | High | Distributed-system framing may exceed monolith needs. |
| Microsoft: Microservice domain model | https://learn.microsoft.com/en-us/dotnet/architecture/microservices/microservice-ddd-cqrs-patterns/microservice-domain-model | Official docs | Domain logic should live in the domain model rather than being scattered through infrastructure or transaction scripts. | Medium-High | DDD/microservice framing. |
| Vaughn Vernon, Effective Aggregate Design, Part I | https://www.dddcommunity.org/wp-content/uploads/files/pdf_articles/Vernon_2011_1.pdf | Reputable practitioner essay | Aggregates protect invariants within transactional consistency boundaries. | High | Practitioner essay, not peer-reviewed. |
| Vaughn Vernon, Effective Aggregate Design, Part II | https://www.dddcommunity.org/wp-content/uploads/files/pdf_articles/Vernon_2011_2.pdf | Reputable practitioner essay | Cross-aggregate consistency often requires eventual consistency and explicit responsibility decisions. | High | Practitioner essay. |
| Martin Fowler: Bounded Context | https://martinfowler.com/bliki/BoundedContext.html | Reputable practitioner source | Bounded contexts clarify semantic boundaries and model ownership. | High | Short essay, not evaluation method. |
| Martin Fowler: DDD Aggregate | https://martinfowler.com/bliki/DDD_Aggregate.html | Reputable practitioner source | Aggregates are useful when thinking about consistency and transactional boundaries. | High | Short essay. |
| Martin Fowler: Anemic Domain Model | https://martinfowler.com/bliki/AnemicDomainModel.html | Reputable practitioner source | Misplaced domain behavior can indicate weak domain-rule ownership. | Medium-High | Can be overused as DDD cosplay if not tied to evidence. |
| Practical Guidelines for Change Recommendation using Association Rule Mining | https://www.cs.loyola.edu/~binkley/papers/ase16-mining-guidelines.pdf | Empirical MSR paper | Logical coupling/change recommendation benefits from filtering; large or noisy transactions reduce quality. Supports filtered change-coupling pass. | High | Change recommendation, not architecture finding. |
| Integrating Conceptual and Logical Couplings for Change Impact Analysis in Software | https://www.cs.wm.edu/~denys/pubs/EMSE-MSR%26IR-IA-Preprint.pdf | Empirical MSR paper | Logical coupling is useful when combined with other evidence. Supports co-change as corroborating signal, not final finding. | High | Change-impact focus. |
| Understanding the Interplay between the Logical and Structural Coupling of Software Classes | https://bura.brunel.ac.uk/bitstream/2438/20225/1/FullText.pdf | Empirical paper | Logical and structural coupling are related but distinct; comparing them can reveal mismatches. | Medium-High | Class-level study; module-level use is extrapolation. |
| On the Empirical Evidence of Microservice Logical Coupling | https://arxiv.org/pdf/2306.02036 | Empirical paper | Logical coupling matters for distributed/modular boundaries. Supports microservice co-change diagnostics. | Medium | Preliminary and microservice-specific. |
| Architecture Decision Record organization | https://github.com/architecture-decision-record/architecture-decision-record | Primary repo / architecture method | ADR practice captures architectural decisions, context, and consequences. | High | Documentation method, not proof of agent recall lift. |
| Michael Nygard ADR template | https://github.com/joelparkerhenderson/architecture-decision-record/blob/main/locales/en/templates/decision-record-template-by-michael-nygard/index.md | Primary template | Minimal ADR fields: context, decision, status, consequences. Supports tradeoff_analysis schema. | High | Template, not empirical proof. |
| Martin Fowler: Architecture Decision Record | https://martinfowler.com/bliki/ArchitectureDecisionRecord.html | Reputable practitioner source | ADRs document architecturally significant decisions. | High | Short practitioner source. |
| Microsoft Azure ADR guidance | https://learn.microsoft.com/en-us/azure/well-architected/architect-role/architecture-decision-record | Official docs | Architecturally significant decisions should record rationale, alternatives, and consequences. | High | Documentation practice, not agent-specific. |
| Why Do Multi-Agent LLM Systems Fail? | https://arxiv.org/abs/2503.13657 | Empirical multi-agent failure study | Multi-agent systems can introduce misalignment, coordination failures, and minimal gains over single-agent baselines. Supports deferring expert panel. | High | General MAS evidence, not architecture-refactor-specific. |
| Which Agent Causes Task Failures and When? | https://arxiv.org/html/2604.02460v1 | Empirical multi-agent failure-attribution paper | Debugging and attributing multi-agent failure is itself difficult. Supports avoiding premature critic-panel complexity. | Medium-High | Failure attribution, not refactoring-specific. |
| Self-Consistency Improves Chain of Thought Reasoning in Language Models | https://arxiv.org/abs/2203.11171 | Empirical reasoning paper | Multiple reasoning paths can improve reasoning. Supports possible later disagreement synthesis. | High | General reasoning, not software architecture. |
| AgentLint | https://github.com/0xmariowu/AgentLint | Primary repo | Method reference for agent configuration/instruction linting. | Provisional | Not evidence of principal architecture recall. |
| hamelsmu/claude-review-loop | https://github.com/hamelsmu/claude-review-loop | Primary repo | Method reference for looped review, not proof of ceiling lift. | Provisional | Do not use as empirical evidence. |
| Th0rgal/open-ralph-wiggum | https://github.com/Th0rgal/open-ralph-wiggum | Primary repo | Method reference only. | Provisional | Not efficacy evidence. |
| archgate/cli | https://github.com/archgate/cli | Primary repo | Method reference around architecture/governance checks. | Provisional | Not recall evidence. |
| buildingopen/bouncer | https://github.com/buildingopen/bouncer | Primary repo | Method reference around guardrails/checking. | Provisional | Not recall evidence. |
| trailofbits/skills | https://github.com/trailofbits/skills | Primary repo | Method reference for skills and security review structure. | Provisional | Not principal-refactor benchmark proof. |
| mattpocock/skills | https://github.com/mattpocock/skills | Primary repo | Skill design/method reference. | Provisional | Not architecture recall proof. |
| hyhmrright/brooks-lint | https://github.com/hyhmrright/brooks-lint | Primary repo | Method reference for structured lint/review. | Provisional | Not efficacy evidence. |
| hyhmrright/logic-lens | https://github.com/hyhmrright/logic-lens | Primary repo | Method reference for structured reasoning lenses. | Provisional | Not efficacy evidence. |
| AlabamaMike/forensic-skills | https://github.com/AlabamaMike/forensic-skills | Primary repo | Method reference for forensic-style skill structure. | Provisional | Not architecture recall evidence. |
| fastruby/tech-debt-skill | https://github.com/fastruby/tech-debt-skill | Primary repo | Method reference for tech-debt review skill. | Provisional | Not direct principal-recall evidence. |

No required public repo in the prompt was found to be fabricated or description-hallucinated during this pass. However, these repos should be treated as method references only unless separate empirical data proves efficacy.

---

# Findings

## Finding 1: Whether the Ceiling Problem Is Real

The ceiling problem is real.

The current evidence says AI coding agents are comparatively strong at localized edits, cleanup, and consistency-preserving changes, but weaker at high-level structural reasoning. The most relevant refactoring studies show that agentic refactoring is dominated by low-level changes such as renames, annotation/type edits, or localized cleanups. Human developers perform a broader and more design-diverse mix of refactorings.

This supports the working hypothesis:

```text
Recent contest-refactor commits likely raised the floor:
  honesty
  safety
  traceability
  validation
  non-churn
  halt discipline
  evidence discipline

But they probably did not raise the ceiling:
  wrong aggregate boundaries
  missing invariant owners
  wrong consistency/process boundaries
  roadmap shear
  co-change boundary mismatch
  tradeoff errors under real forces
```

That does not mean the existing mechanisms are unimportant. They are necessary guardrails. But they are not specifically aimed at increasing recall of principal-grade architectural defects.

The broader agent-failure literature reinforces this. Some repository-agent failures appear to come from gaps in architectural reasoning and domain knowledge rather than raw patch difficulty. Failed agent PRs also tend to involve broader, more multi-file, CI-fragile changes, which is consistent with the idea that agents become brittle as the change crosses architectural seams.

Conclusion:

```text
The ceiling problem is sufficiently evidenced to justify a new benchmark and targeted architecture lenses.
```

Caveat:

```text
The exact recall gap inside contest-refactor itself remains unmeasured until evals/principal_defects/ exists.
```

---

## Finding 2: Whether the Benchmark Is the Keystone

Yes. The benchmark is the keystone.

Without a benchmark, contest-refactor cannot distinguish between:

```text
The loop became safer.
The loop became more honest.
The loop became less noisy.
The loop produced nicer findings.
The loop actually found deeper architecture defects.
```

Those are different outcomes.

The strongest benchmark evidence comes from code-review and repository-agent evaluation research:

- c-CRAB converts human review feedback into executable or issue-grounded checks because review text similarity is too weak.
- RACE-bench evaluates intermediate reasoning steps because final-patch success hides where agents fail.
- REAP emphasizes realistic benchmark construction, automation, and stability checks.

contest-refactor needs the same structure for architecture:

```text
seeded principal defect
expected finding
expected non-finding
expected localization
expected remedy family
false-positive penalty
overbuild trap
context-sufficiency oracle
```

The benchmark should not merely check whether the final patch passes tests. It must measure whether the loop:

1. Notices the architectural defect.
2. Names the correct defect family.
3. Grounds the claim in evidence.
4. Localizes the owner/boundary/seam.
5. Avoids decoys.
6. Distinguishes “not found” from “not evaluable.”
7. Proposes a proportionate remedy.
8. Avoids tangled refactors and broad opportunistic cleanup.

Architecture-method sources also support benchmark-first. ATAM and QAW evaluate architectures through scenarios, tradeoffs, risks, and business goals. contest-refactor should not implement full ATAM, but the benchmark should encode the same minimum: source of scenario, current shear, risk, and tradeoff.

Conclusion:

```text
Build evals/principal_defects/ before adding more ceiling-raising logic.
```

This is the anti-theater move. Without the benchmark, every later addition becomes fog-machine engineering.

---

## Finding 3: Which Principal Defects To Seed First

The first fixtures should target defect types that are:

1. Principal-grade.
2. Evidence-inspectable.
3. Cheap enough to run regularly.
4. Hard to fake with generic checklists.
5. Less vulnerable to DDD cosplay.

Recommended first-wave order:

| Order | Defect category | Why it should be seeded early |
|---:|---|---|
| 1 | Missing invariant owner | Deep, common, inspectable, and directly tied to business correctness. |
| 2 | Cross-module invariant without atomic owner | Finds split ownership and wrong consistency assumptions. |
| 3 | Wrong transaction/process owner | Captures missing workflow owner, saga/process-manager absence, and split writes. |
| 4 | Duplicated business rule across UI/persistence/domain | Strong evidence signal; easy to seed drift and decoys. |
| 5 | Wrong consistency boundary | Principal-grade and scenario-rich. |
| 6 | Dependency direction violation with domain rule hidden in infrastructure | Strong static evidence and useful remedy oracle. |
| 7 | Domain rule hidden in adapter/infrastructure | Finds architecture leakage without requiring DDD labels. |
| 8 | Co-changing modules that live apart | Good use of git-history artifacts once change-coupling exists. |
| 9 | Wrong aggregate boundary | Important, but should be tied to invariants or consistency, not abstract aggregate taste. |
| 10 | Missing seam for likely roadmap change | High-value but requires grounded roadmap/context. |
| 11 | Roadmap shear across current module boundaries | High-value but context-dependent. |
| 12 | Temporal coupling with no process owner | Valuable where workflows or async systems exist. |
| 13 | Safety/regulatory invariant lacking owner | Critical but context-heavy. |
| 14 | Over-abstracted shallow pass-through | Already partially covered by anti-shallow doctrine; seed as decoy/regression. |
| 15 | Broad dependency direction violation | Useful, but less ceiling-specific unless tied to rule ownership. |

First fixture pack should emphasize categories 1 through 7.

Reason:

```text
“Wrong aggregate boundary” is too easy to hallucinate.
“Missing invariant owner” is much harder to fake.
```

A strong oracle should say:

```text
Rule X must remain true.
State Y and state Z affect that rule.
Today Y and Z are mutated independently.
No owner is responsible for maintaining X.
The correct finding is missing invariant/process owner, not merely “bad aggregate.”
```

This keeps the benchmark out of DDD theater.

---

## Finding 4: Whether Change-Coupling Is Worth Building

Yes, but only as candidate evidence.

Mining software history for co-change/logical coupling is evidence-backed. Co-change can reveal files or modules that repeatedly change together even though the architecture says they are separate. This is useful for finding:

- hidden coordination
- missing seams
- rule duplication
- feature scattering
- wrong boundary placement
- missing process owner
- modules that evolve together but live apart

But co-change is noisy. Files can change together because of:

- formatting commits
- migrations
- release chores
- dependency updates
- generated files
- mass renames
- test/prod mirror changes
- broad mechanical refactors
- normal workflow coupling
- shared feature work that is not architecturally wrong

Therefore:

```text
change-coupling must not emit final findings.
```

It should emit:

```text
Layer-1 candidate evidence
weak signal
diagnostic artifact
```

It may support a final finding only when corroborated by at least one stronger signal:

```text
domain-integrity evidence
grounded change scenario
structural dependency mismatch
rule duplication/drift
split mutation paths
forbidden dependency direction
incident or test evidence
```

Recommended role:

```text
artifacts/change_coupling.json
artifacts/change_coupling.md
```

Use it to sharpen the Actor’s search path, not to convict the codebase.

---

## Finding 5: Whether Domain-Integrity Lens Should Be Added

Yes. The domain-integrity lens is the highest-value post-benchmark addition.

It directly targets the prompt’s desired principal-grade defects:

- wrong aggregate boundary
- missing invariant owner
- cross-module invariant without atomic owner
- duplicated business rule
- wrong consistency boundary
- wrong transaction/process owner
- domain rule hidden in infrastructure
- safety/regulatory invariant lacking owner

The lens should generalize DDD concepts rather than enforce DDD vocabulary. It should not ask:

```text
Does this project use DDD correctly?
```

It should ask:

```text
What rule must stay true?
Who owns that rule?
What state must change together?
Where is that rule enforced?
Can two modules violate it independently?
Is the consistency model explicit?
Is the process owner explicit?
Is the rule duplicated or drifting?
Is the rule hidden in an adapter, SQL, controller, or worker?
```

Good domain-integrity findings are not aesthetic. They are ownership findings.

Bad finding:

```text
This should use aggregates.
```

Good finding:

```text
The “player cannot be active on two rosters at once” invariant is enforced in the UI and import worker but not in the roster domain service. Both code paths mutate player assignment independently, and the import path can violate the rule. There is no single invariant owner.
```

This lens should explicitly support non-DDD codebases by using plain-language categories:

```text
business rule
rule owner
mutation site
consistency boundary
transaction owner
process owner
duplication
drift
context sufficiency
```

Conclusion:

```text
Add domain-integrity as P0 after the benchmark skeleton exists.
```

---

## Finding 6: Whether Serious+ Findings Should Require Change Scenarios

Mostly yes.

A Serious+ architecture finding should normally include:

1. A grounded likely change or current force.
2. The source of that scenario.
3. How the current structure shears under that change.
4. Why the proposed fix wins under stated tradeoffs.

This is strongly aligned with:

- Parnas’s design-for-change criterion.
- ATAM’s scenario-driven evaluation.
- QAW’s business/mission-grounded scenarios.
- quality-attribute scenario structure.

A grounded scenario is not something the model invents because it sounds plausible.

Valid scenario sources:

```text
CONTEXT.md roadmap
incidents
user prompt
TODOs
changelog
issue history
git co-change data
tests
domain constraints
regulatory/safety requirements
known load/latency constraints
deployment/integration constraints
```

Example grounded scenario:

```text
Source: CONTEXT.md roadmap says regional refund rules are planned.
Scenario: Refund eligibility will vary by region and channel.
Current shear: Refund eligibility is duplicated in controller, repository query, and async worker.
Impact: One rule change requires synchronized edits across three owners.
Fix: Move refund eligibility into a single RefundPolicy owner and have workers consume policy outcomes.
```

Exceptions should exist.

A Serious+ finding may be allowed without a future-change scenario when there is direct current harm:

```text
current correctness bug
active invariant breach
security/safety/regulatory gap
observed incident
test proving drift
forbidden dependency causing current build/runtime pain
current data corruption risk
```

Rule:

```text
If Serious+ is based on future risk, require change_scenario.
If Serious+ is based on current harm, require current_harm evidence instead.
```

Lack of context should cap claims.

If no roadmap, incidents, constraints, or workflow ownership are available, the loop should not pretend to have performed expert-depth architecture review.

---

## Finding 7: Whether Tradeoff Analysis Should Be Required

Yes, but only minimally and only for Serious+ structural fixes.

Architecture is tradeoff work. ATAM exists to reveal risks, tradeoffs, sensitivity points, and business-goal alignment. ADR practice exists to record context, decision, alternatives, and consequences.

contest-refactor should therefore require an ADR-lite record for Serious+ structural changes.

The minimal useful tradeoff record:

```text
forces
chosen move
2–3 rejected alternatives
why rejected
consequences
```

This should be required when the fix changes:

```text
module boundary
aggregate/consistency boundary
transaction owner
process owner
dependency direction
domain rule ownership
integration boundary
safety/regulatory control owner
```

It should not be required for tiny local cleanups.

Do not turn this into scrollwork. The goal is not a formal ADR per patch. The goal is to expose whether the Actor actually considered forces and alternatives.

Bad tradeoff record:

```text
Alternative: Do nothing.
Alternative: Refactor better.
```

Good tradeoff record:

```text
Chosen: Introduce RefundPolicy as single rule owner.

Rejected:
1. Keep duplicated checks and add tests.
   Rejected because it leaves three rule owners and does not stop drift.
2. Use a shared utility.
   Rejected because it reduces duplication but does not establish process ownership.
3. Make every worker call the API synchronously.
   Rejected because it violates latency and availability forces.
```

This directly fights overbuild, because the actor must prove why the smaller option loses.

---

## Finding 8: Whether To Add Expert Panel Now Or Defer

Defer.

The evidence for multiple reasoning paths is real, but the evidence for multi-agent systems is mixed. Multi-agent designs can improve exploration, but they also introduce:

- inter-agent misalignment
- context loss
- agents ignoring each other
- agents withholding or failing to transmit useful information
- verification failures
- termination failures
- orchestration overhead
- higher cost
- new sources of ceremony

Recent multi-agent failure research supports caution. Some controlled comparisons show minimal gains relative to strong single-agent baselines.

Therefore, the proposed sequence is correct:

```text
1. Build principal-defect recall benchmark.
2. Add domain-integrity lens.
3. Add Serious+ change-scenario requirement.
4. Add Serious+ tradeoff analysis.
5. Add context-sufficiency honesty and score caps.
6. Add change-coupling candidate evidence.
7. Measure hidden-fixture recall and precision.
8. Add expert panel only if recall remains low.
```

If added later, the expert panel should not be generic personas.

Do not add:

```text
principal architect critic
senior reviewer
SRE reviewer
DDD expert
security reviewer
```

as loose roles.

Add artifact contracts instead:

```text
domain_integrity_critic
change_force_critic
consistency_process_critic
operability_sre_critic
roadmap_evolution_critic
anti_overbuild_critic
```

Each must answer a narrow, machine-readable question.

Useful critic examples:

```text
domain_integrity_critic:
  Does this finding correctly identify rule owner, mutation sites, and consistency boundary?

change_force_critic:
  Is the change scenario grounded, and does the claimed structural shear follow?

anti_overbuild_critic:
  Is the remedy proportionate, or did the actor invent a framework-shaped cathedral?

consistency_process_critic:
  Does the proposed owner/process model correctly handle atomic vs eventual consistency?
```

Use disagreement synthesis, not majority vote.

A single critic with strong counter-evidence should downgrade or block a Serious+ claim even if other critics vaguely agree.

Go/no-go trigger:

```text
Add expert panel only if, after P0/P1 additions:
  hidden Serious+ recall remains < 0.70
  OR recall improves by < 10 absolute percentage points
  while precision remains >= 0.85
```

These thresholds are engineering gates, not universal research constants. Tune after the first benchmark run.

---

## Finding 9: What Context Must Be Present for Expert-Depth Claims

Some findings can be made from static code alone. Others cannot.

Usually evaluable from code:

```text
duplicated business rule
dependency direction violation
domain rule hidden in infrastructure
multiple mutation sites for same state
missing central validation
over-abstracted shallow pass-through
test/prod rule drift
```

Often not safely evaluable from code alone:

```text
wrong consistency model
wrong aggregate boundary
wrong process owner
missing roadmap seam
roadmap shear
latency tradeoff
availability tradeoff
regulatory sufficiency
team-topology fitness
deployment-boundary fitness
```

For expert-depth review, CONTEXT.md should contain:

```markdown
# CONTEXT.md

## Product / Mission
What the system does and who it serves.

## Primary Workflows
The most important user/system workflows.

## Roadmap / Likely Changes
Known or likely upcoming changes.

## Domain Rules and Invariants
Business rules that must remain true.

## Consistency Requirements
What must be strongly consistent, what may be eventually consistent, and why.

## Data Ownership
Who owns each important data concept.

## Integration Boundaries
External systems, APIs, queues, jobs, imports, exports.

## Deployment Model
Monolith, services, serverless, mobile, edge, batch, etc.

## Load and Latency Expectations
Expected volume, latency budgets, throughput, burst patterns.

## Availability / Failure Expectations
What must keep working during partial failure.

## Regulatory / Safety Constraints
Compliance, safety, privacy, audit, retention, public harm constraints.

## Incident History
Recent bugs, outages, data issues, support escalations.

## Team / Operational Ownership
Who owns what, where handoffs exist, support model.

## Testing and Release Constraints
Critical test suites, release cadence, migration constraints.

## Known Architecture Decisions
Existing ADRs or intentional tradeoffs.

## Out of Scope
Things the review must not redesign.
```

When context is insufficient, contest-refactor should emit:

```text
CONTEXT_INSUFFICIENT_FOR_EXPERT_DEPTH
```

It should distinguish:

```text
NO_ISSUE_FOUND_FROM_AVAILABLE_EVIDENCE
```

from:

```text
ISSUE_CLASS_NOT_EVALUABLE_WITH_AVAILABLE_CONTEXT
```

Score caps:

```text
If context_sufficiency = insufficient:
  max_expert_depth_score = 0.55

If context_sufficiency = partial:
  max_expert_depth_score = 0.75

If context_sufficiency = sufficient:
  no context cap
```

Serious+ findings under insufficient context should be downgraded unless they have current-harm evidence.

---

# Proposed Benchmark Design

## Benchmark Goal

Create a benchmark that measures whether contest-refactor finds principal-grade architecture defects without inflating hallucinations, over-flagging, tangled refactors, metric gaming, or ceremony.

Benchmark location:

```text
evals/principal_defects/
```

The benchmark must measure:

```text
recall
precision
localization quality
remedy quality
overbuild rate
tangled-refactor risk
context-sufficiency honesty
```

## Benchmark Tracks

Use two tracks.

### Track A: Findings Track

Cheap and frequent.

Purpose:

```text
Can the loop detect the seeded principal defect and avoid decoys?
```

Runs on:

```text
every PR touching contest-refactor review logic
nightly
before promoting new lens/gate behavior
```

No patch required. The loop emits findings only.

### Track B: Remedy Track

Smaller and less frequent.

Purpose:

```text
Can the loop make a proportionate architectural fix without tangling unrelated changes?
```

Runs:

```text
weekly
before major release
before accepting new Actor rules
```

Patch allowed. Tests/build must pass.

---

## Folder Layout

```text
evals/principal_defects/
  README.md

  schema/
    fixture.schema.json
    expected_finding.schema.json
    expected_non_finding.schema.json
    localization.schema.json
    remedy.schema.json
    scoring.schema.json

  public/
    mini/
      missing_invariant_owner_order_limit_ts/
        repo/
        context/
          CONTEXT.md
        history/
          repo.bundle
        fixture.json
        oracle.findings.json
        oracle.non_findings.json
        oracle.localization.json
        oracle.remedies.json
        tests/

      duplicated_rule_refund_policy_py/
        ...

      wrong_process_owner_inventory_reservation_rb/
        ...

    medium/
      wrong_consistency_boundary_discount_engine_ts/
        ...

  hidden/
    manifests/
      weekly_pack_a.json
      weekly_pack_b.json
      monthly_pack_architecture.json

    packs/
      pack_a/
        fixture_001/
        fixture_002/

  scripts/
    run_findings_eval.py
    run_remedy_eval.py
    match_findings.py
    score_pack.py
    summarize_results.py

  docs/
    authoring-fixtures.md
    scoring-guide.md
    taxonomy.md
```

---

## Fixture Taxonomy

First-wave fixture categories:

```text
missing_invariant_owner
cross_module_invariant_without_atomic_owner
wrong_transaction_owner
wrong_process_owner
duplicated_business_rule_across_layers
wrong_consistency_boundary
dependency_direction_violation
domain_rule_hidden_in_infrastructure
cochanging_modules_live_apart
wrong_aggregate_boundary
missing_roadmap_seam
roadmap_shear
temporal_coupling_no_process_owner
safety_regulatory_invariant_lacking_owner
over_abstracted_shallow_passthrough
```

Recommended first implementation pack:

```text
3 missing_invariant_owner
3 duplicated_business_rule_across_layers
3 wrong_transaction_or_process_owner
2 wrong_consistency_boundary
2 dependency_direction_violation_with_hidden_domain_rule
2 insufficient_context
2 expected_non_finding_decoy
```

---

## fixture.json Shape

```json
{
  "id": "missing_invariant_owner_order_limit_ts",
  "title": "Missing owner for customer daily order limit",
  "language": "typescript",
  "domain": "commerce",
  "track": "findings",
  "seeded_defects": [
    {
      "id": "D1",
      "category": "missing_invariant_owner",
      "severity": "serious",
      "weight": 1.0,
      "summary": "Daily order limit is enforced in UI and import job but not in the domain/application owner.",
      "requires_change_scenario": true,
      "requires_tradeoff_analysis_for_remedy": true,
      "context_sufficiency": "sufficient"
    }
  ],
  "decoys": [
    {
      "id": "N1",
      "category": "expected_non_finding",
      "summary": "The repository uses a simple DTO and does not need a new aggregate abstraction."
    }
  ],
  "allowed_evidence_sources": [
    "source",
    "tests",
    "context",
    "git_history"
  ],
  "forbidden_shortcuts": [
    "claim DDD aggregate without naming invariant",
    "recommend broad service split",
    "flag DTO as anemic model without rule drift evidence"
  ]
}
```

---

## oracle.findings.json Shape

```json
{
  "expected_findings": [
    {
      "defect_id": "D1",
      "accepted_categories": [
        "missing_invariant_owner",
        "cross_module_invariant_without_atomic_owner"
      ],
      "required_claims": [
        "daily order limit is a business invariant",
        "UI and import job enforce or mutate related state independently",
        "no single owner guarantees the invariant",
        "current structure can drift under a new order-entry channel"
      ],
      "required_evidence": [
        {
          "kind": "source",
          "path": "src/ui/checkout/LimitBanner.tsx"
        },
        {
          "kind": "source",
          "path": "src/imports/orderImport.ts"
        },
        {
          "kind": "source",
          "path": "src/domain/orders/OrderService.ts"
        },
        {
          "kind": "context",
          "path": "context/CONTEXT.md",
          "section": "Roadmap"
        }
      ],
      "severity_floor": "serious",
      "severity_ceiling": "serious"
    }
  ]
}
```

---

## oracle.non_findings.json Shape

```json
{
  "expected_non_findings": [
    {
      "id": "N1",
      "category": "overbuild_trap",
      "claim_to_reject": "Introduce a full aggregate hierarchy or event-sourcing layer.",
      "why_rejected": "The fixture requires a single rule owner, not a broad architecture framework."
    },
    {
      "id": "N2",
      "category": "false_dependency_claim",
      "claim_to_reject": "The UI must not import shared types.",
      "why_rejected": "Shared read-only DTO import is intentional and not the defect."
    }
  ]
}
```

---

## oracle.localization.json Shape

```json
{
  "defect_id": "D1",
  "primary_locations": [
    "src/domain/orders/OrderService.ts",
    "src/imports/orderImport.ts"
  ],
  "supporting_locations": [
    "src/ui/checkout/LimitBanner.tsx",
    "context/CONTEXT.md"
  ],
  "owner_location": "src/domain/orders/OrderService.ts",
  "boundary_locations": [
    "src/domain/orders/",
    "src/imports/"
  ]
}
```

---

## oracle.remedies.json Shape

```json
{
  "defect_id": "D1",
  "acceptable_remedy_families": [
    {
      "id": "central_policy_owner",
      "description": "Introduce or use a central OrderLimitPolicy/OrderService method as the single owner of the invariant.",
      "required_properties": [
        "UI does not enforce final authority",
        "import path uses same owner",
        "tests cover both UI/API/import path behavior"
      ]
    }
  ],
  "forbidden_remedies": [
    {
      "id": "broad_event_sourcing",
      "reason": "Overbuilt for fixture forces."
    },
    {
      "id": "duplicate_test_only",
      "reason": "Tests alone do not establish invariant ownership."
    }
  ]
}
```

---

## Scoring Dimensions

### Recall

```text
recall = weighted_matched_seeded_findings / weighted_seeded_findings
```

A finding matches only if it satisfies:

```text
category match
required claim coverage
evidence anchor coverage
severity within accepted range
```

### Precision

```text
precision = weighted_true_findings / (weighted_true_findings + weighted_false_findings)
```

False positives are weighted by severity.

Example:

```text
minor false positive = 0.25 penalty
moderate false positive = 0.50 penalty
serious false positive = 1.00 penalty
critical false positive = 1.50 penalty
```

### Localization Quality

```text
localization = 0.60 * file_set_f1 + 0.40 * owner_or_boundary_match
```

### Remedy Quality

Remedy track only:

```text
remedy_quality =
  0.35 * behavior_preserved_or_improved
+ 0.30 * owner_boundary_correction
+ 0.20 * minimality
+ 0.15 * scenario_tradeoff_coherence
```

### Overbuild Rate

Penalty triggers:

```text
new framework not required
new generic abstraction with one implementation
new base class / protocol with no current force
event bus introduced without async/process force
broad service split beyond fixture scope
large file-touch radius without scenario justification
```

### Tangled-Refactor Risk

Penalty triggers:

```text
multiple unrelated concern clusters
mixed style cleanup with architecture fix
diff touches unrelated modules
tests updated opportunistically outside defect scope
behavior changes not tied to remedy
```

### Context-Sufficiency Honesty

Reward:

```text
CONTEXT_INSUFFICIENT_FOR_EXPERT_DEPTH on insufficient fixtures
ISSUE_CLASS_NOT_EVALUABLE_WITH_AVAILABLE_CONTEXT when appropriate
NO_ISSUE_FOUND_FROM_AVAILABLE_EVIDENCE when appropriate
```

Penalize:

```text
confident Serious+ claims with insufficient context
invented roadmap
invented regulatory requirement
invented domain invariant
```

---

## Overall Findings Track Formula

```text
overall_findings =
  0.40 * recall
+ 0.20 * precision
+ 0.15 * localization
+ 0.15 * honesty
+ 0.10 * nonfinding_discipline
```

## Overall Remedy Track Formula

```text
overall_remedy =
  0.30 * recall
+ 0.15 * precision
+ 0.10 * localization
+ 0.25 * remedy_quality
+ 0.10 * honesty
- 0.05 * overbuild_penalty
- 0.05 * tangled_penalty
```

---

## Hidden Fixtures and Overfitting Controls

Use public fixtures to teach the schema.

Use hidden fixtures to measure real ceiling movement.

Hidden fixtures should rotate:

```text
domain vocabulary
language
repo shape
framework
file naming
architecture style
fixture size
scenario source
decoy pattern
```

Example domains:

```text
commerce
healthcare scheduling
sports roster management
education enrollment
billing
inventory
permissions
workflow automation
field-service dispatch
audit/compliance
```

Do not let benchmark training become “keyword sniffing.” The same defect should appear under different names.

Example:

```text
missing invariant owner
  commerce: refund eligibility
  sports: player active roster uniqueness
  healthcare: appointment capacity and triage priority
  billing: invoice adjustment approval limit
```

---

# Proposed Change-Coupling Pass

## Role

The change-coupling pass is read-only.

It emits candidate evidence only.

It must not produce final findings.

Artifact outputs:

```text
artifacts/change_coupling.json
artifacts/change_coupling.md
```

## Inputs

```text
git history
module map if available
ignore globs
generated-file globs
static dependency graph if available
CONTEXT.md ownership hints if available
```

## Default Analysis Window

```text
most recent 24 months
OR most recent 3,000 non-merge commits
whichever is smaller
```

## Commit Filters

Exclude or down-rank:

```text
merge commits
formatting commits
lint-only commits
generated file churn
vendored file churn
dependency lockfile-only commits
release/version bump commits
mass renames
large mechanical codemods
broad migrations
test fixture rewrites
commits touching too many files
```

Recommended starting thresholds:

```text
max_files_per_commit_for_pair_signal = 8
max_files_per_commit_for_module_signal = 20
ignore_if_generated_ratio > 0.50
ignore_if_only_lockfiles = true
ignore_if_rename_only = true
ignore_merge_commits = true
```

Commit-message ignore regex starting point:

```text
(fmt|format|lint|prettier|black|rustfmt|release|version bump|lockfile|codemod|rename-only|generated|vendor)
```

## Metrics

Implement simple metrics first:

```text
cochange_count
jaccard_similarity
confidence_a_to_b
confidence_b_to_a
optional_lift
recency_weighted_count
directory_distance
module_distance
static_dependency_status
```

Definitions:

```text
cochange_count(A,B) =
  number of qualified commits touching both A and B

jaccard(A,B) =
  commits(A ∩ B) / commits(A ∪ B)

confidence_a_to_b =
  commits(A ∩ B) / commits(A)

confidence_b_to_a =
  commits(A ∩ B) / commits(B)
```

Recency weighting:

```text
weight(commit) = exp(-age_days / 180)
```

## Candidate Thresholds

Starting point:

```text
qualified_cochange_count >= 3 in 12 months
OR qualified_cochange_count >= 5 in 24 months

jaccard >= 0.30 for file pairs
OR jaccard >= 0.20 for module pairs

max(confidence_a_to_b, confidence_b_to_a) >= 0.35

directory_distance >= 3
OR module_distance >= 2
```

These thresholds are not literature-certified constants. They are engineering defaults to be tuned against the new benchmark.

## Static Dependency Combination

Interpretation matrix:

| Co-change | Static dependency | Interpretation |
|---|---|---|
| High | Expected direct dependency | Usually normal workflow; weak signal. |
| High | No static dependency | Possible hidden coordination or missing seam. |
| High | Forbidden direction | Stronger boundary-tension candidate. |
| High | Bidirectional dependency | Possible boundary collapse. |
| High | Rule duplication present | Potential principal finding if domain lens corroborates. |
| High | Shared process owner documented | Often acceptable; lower suspicion. |
| Low | Strong static dependency | Not a co-change signal; may still be design smell separately. |

## JSON Output Shape

```json
{
  "schema_version": "1.0",
  "repo_head": "abc123",
  "analysis_window": {
    "mode": "recent",
    "max_commits": 3000,
    "max_age_days": 730,
    "actual_commits_analyzed": 842
  },
  "filters": {
    "exclude_merge_commits": true,
    "max_files_per_commit": 8,
    "generated_globs": [
      "dist/**",
      "vendor/**",
      "**/*.g.cs"
    ],
    "message_ignore_regex": "(fmt|format|lint|prettier|black|rustfmt|release|version bump|lockfile|codemod|rename-only)"
  },
  "summary": {
    "candidate_pairs": 12,
    "strong_candidates": 3,
    "commits_filtered": 77
  },
  "pairs": [
    {
      "id": "CC-001",
      "lhs": "src/orders/checkout.ts",
      "rhs": "src/billing/discount_rules.ts",
      "granularity": "file",
      "qualified_cochange_count": 5,
      "jaccard": 0.42,
      "confidence_lhs_to_rhs": 0.56,
      "confidence_rhs_to_lhs": 0.45,
      "recency_weighted_count": 3.1,
      "directory_distance": 6,
      "module_distance": 2,
      "static_dependency": "none",
      "classification": "boundary_tension_candidate",
      "strength": "medium",
      "promotion_allowed": false,
      "promotion_requires": [
        "domain_integrity_corrobation",
        "grounded_change_scenario",
        "structural_dependency_mismatch"
      ],
      "supporting_commits": [
        {
          "sha": "1a2b3c",
          "date": "2026-02-14",
          "summary": "fix promo stacking drift"
        },
        {
          "sha": "4d5e6f",
          "date": "2026-04-02",
          "summary": "refund rule mismatch"
        }
      ],
      "notes": [
        "far_apart_paths",
        "recurrent_recent_pair",
        "no_direct_static_edge"
      ]
    }
  ]
}
```

## Markdown Output

```markdown
# Change-Coupling Candidate Evidence

This artifact is diagnostic only. It must not be treated as a final architecture finding without corroboration.

## Strong Candidates

### CC-001: src/orders/checkout.ts ↔ src/billing/discount_rules.ts

- Qualified co-change count: 5
- Jaccard: 0.42
- Directory distance: 6
- Static dependency: none
- Classification: boundary_tension_candidate
- Promotion allowed: no

Interpretation:
These files repeatedly change together despite living apart and lacking a direct static dependency. This may indicate hidden rule coupling or a missing owner. Use the domain-integrity lens before promoting this to a finding.
```

---

# Proposed Domain-Integrity Lens

File:

```text
lens-domain-integrity.md
```

## Purpose

Find architectural defects in business-rule ownership, invariant ownership, consistency boundaries, transaction/process ownership, and domain rule placement.

This lens is not a DDD compliance checker.

It must not issue findings like:

```text
This needs aggregates.
This is an anemic domain model.
This needs bounded contexts.
```

unless it can tie the claim to concrete evidence:

```text
rule split
rule drift
missing owner
wrong consistency boundary
independent mutation paths
domain rule hidden in infrastructure
```

## Core Questions

```text
1. What business rule or invariant is present?
2. Where is it enforced?
3. Who owns keeping it true?
4. What state must change together?
5. What code paths mutate that state?
6. Is the consistency model atomic, eventual, split, or unknown?
7. If work crosses boundaries, who owns the process?
8. Is the rule duplicated across UI/domain/persistence/workers?
9. Is the rule hidden in infrastructure, SQL, adapters, controllers, or jobs?
10. What evidence proves this is harmful or likely to become harmful?
11. Is available context sufficient for an expert-depth claim?
```

## Evidence Types

Strong evidence:

```text
source code mutation sites
transaction scopes
unit-of-work boundaries
domain services / policy objects
database constraints
worker/job handlers
event handlers
tests
incidents
issue history
roadmap
git co-change
regulatory or safety docs
```

Weak evidence:

```text
naming alone
folder structure alone
generic DDD preference
single duplicated string
one-time co-change
style preference
```

## Finding Schema Extension

```json
{
  "domain_integrity": {
    "rule_statement": "A player cannot be active on two rosters in the same league at once.",
    "rule_kind": "invariant",
    "owner_status": "missing",
    "candidate_owner": null,
    "state_subjects": [
      "PlayerRosterAssignment.player_id",
      "PlayerRosterAssignment.active",
      "Roster.league_id"
    ],
    "mutation_sites": [
      {
        "path": "src/ui/roster/RosterEditor.tsx",
        "kind": "ui_check",
        "evidence": "prevents duplicate assignment in interactive editor"
      },
      {
        "path": "src/import/rosterImport.ts",
        "kind": "batch_mutation",
        "evidence": "creates assignments without calling same rule owner"
      },
      {
        "path": "src/db/rosterRepository.ts",
        "kind": "persistence_mutation",
        "evidence": "upserts active assignments directly"
      }
    ],
    "consistency_model": "unknown_split",
    "transaction_owner": null,
    "process_owner": null,
    "duplication": {
      "detected": true,
      "sites": [
        "src/ui/roster/RosterEditor.tsx",
        "src/import/rosterImport.ts"
      ],
      "consistency": "divergent"
    },
    "cross_boundary": true,
    "domain_rule_hidden_in_infrastructure": false,
    "context_sufficiency": "partial",
    "confidence": "medium",
    "evidence_refs": [
      "code:src/ui/roster/RosterEditor.tsx#L44-L66",
      "code:src/import/rosterImport.ts#L18-L49",
      "test:tests/rosterImport.test.ts#L21-L55"
    ],
    "non_claims": [
      "Does not claim the project needs DDD aggregates.",
      "Does not claim event sourcing is required."
    ]
  }
}
```

## Owner Status Values

```text
owned
missing
split
misplaced
unknown
```

## Consistency Model Values

```text
atomic
eventual
split
unknown
not_required
```

## Context Sufficiency Values

```text
sufficient
partial
insufficient
```

## Promotion Rules

A domain-integrity candidate may become Serious+ only if at least one is true:

```text
current correctness risk is evidenced
tests demonstrate drift or violation
incident history demonstrates drift or violation
change scenario is grounded and shows shear
safety/regulatory context requires ownership
git co-change corroborates recurring split-rule edits
```

It must be downgraded if:

```text
the rule is inferred only from naming
the supposed invariant is not evidenced
the remedy requires roadmap assumptions not present
the claim is mostly DDD vocabulary
```

---

# Proposed Change-Scenario and Tradeoff Schema

## Serious+ change_scenario Requirement

For Serious+ architecture findings, require:

```json
{
  "change_scenario": {
    "required": true,
    "source_type": "roadmap",
    "source_ref": "CONTEXT.md#roadmap",
    "scenario": "Upcoming region-specific refund rules will require channel-specific eligibility exceptions.",
    "grounding_strength": "high",
    "current_shear": "Refund eligibility is duplicated in controller, repository query builder, and async refund worker, so one rule change requires synchronized edits across three owners.",
    "why_fix_wins": "Moving eligibility ownership into a single RefundPolicy owner localizes the change and lets workers consume policy outcomes rather than re-encode rules.",
    "if_context_missing": false
  }
}
```

Valid `source_type` values:

```text
roadmap
incident
user_prompt
todo
changelog
issue_history
git_cochange
test
domain_constraint
regulatory
safety
load_profile
deployment_constraint
integration_constraint
```

Valid `grounding_strength` values:

```text
high
medium
low
insufficient
```

## Serious+ Exceptions

A Serious+ finding may omit future `change_scenario` if it provides `current_harm`:

```json
{
  "current_harm": {
    "required": true,
    "harm_type": "current_invariant_breach",
    "evidence_ref": "test:tests/importAllowsDuplicateActiveRoster.test.ts",
    "summary": "Import path can create two active roster assignments for the same player in the same league."
  }
}
```

Valid `harm_type` values:

```text
current_correctness_bug
current_invariant_breach
current_data_corruption_risk
current_security_gap
current_safety_gap
current_regulatory_gap
observed_incident
test_proven_drift
dependency_violation_causing_current_failure
```

Rule:

```text
Serious+ finding must include either:
  change_scenario
OR
  current_harm
```

## Minimal tradeoff_analysis Requirement

For Serious+ structural fixes:

```json
{
  "tradeoff_analysis": {
    "required": true,
    "forces": [
      "refund rule must remain consistent across API and worker",
      "new regional variants expected this quarter",
      "latency budget does not permit synchronous cross-service join"
    ],
    "chosen_move": "Introduce RefundPolicy as single rule owner and make worker consume policy result events.",
    "rejected_alternatives": [
      {
        "option": "Keep duplicated checks and tighten tests",
        "why_rejected": "Cheapest short term, but leaves three owners and recurring drift risk."
      },
      {
        "option": "Use shared utility library across controller and worker",
        "why_rejected": "Reduces duplication but still leaves process ownership and consistency assumptions split."
      },
      {
        "option": "Force synchronous cross-service validation on each refund",
        "why_rejected": "Improves immediacy but violates latency and availability forces."
      }
    ],
    "consequences": [
      "one-time event contract change",
      "clearer rule ownership",
      "slightly more explicit orchestration"
    ]
  }
}
```

## Gating Rule

```text
If finding.severity >= serious
AND finding.kind is structural
THEN require:
  change_scenario OR current_harm
  tradeoff_analysis if remedy changes owner/boundary/process/consistency model
```

Structural kinds:

```text
module_boundary
dependency_direction
invariant_owner
transaction_owner
process_owner
consistency_boundary
aggregate_boundary
integration_boundary
domain_rule_ownership
safety_control_ownership
```

---

# Proposed CONTEXT.md Schema Extension

```markdown
# CONTEXT.md

## Product / Mission

What this system does, who uses it, and what failure would mean.

## Primary Workflows

List the workflows that matter most.

Example:
- create order
- import roster
- schedule appointment
- approve refund
- sync external account

## Roadmap / Likely Changes

Known or likely upcoming changes.

For each:
- change
- source
- expected timeframe if known
- affected workflows
- confidence

## Domain Rules and Invariants

Rules that must remain true.

For each:
- rule
- owner if known
- state involved
- consistency requirement
- safety/regulatory impact if any

## Consistency Requirements

What must be atomic vs eventual.

For each:
- workflow
- consistency model
- acceptable delay
- failure mode
- owner

## Data Ownership

Important data concepts and owning modules/services.

## Transaction / Process Ownership

Important workflows and their transaction or process owner.

## Integration Boundaries

External systems, queues, APIs, files, imports, exports, webhooks.

## Deployment Model

Runtime shape:
- monolith
- service
- worker
- mobile
- serverless
- batch
- edge
- hybrid

## Load and Latency Expectations

Important volume, concurrency, latency, and burst assumptions.

## Availability / Failure Expectations

What must happen during partial failure.

## Regulatory / Safety Constraints

Compliance, safety, privacy, audit, retention, or public harm constraints.

## Incident History

Recent failures, regressions, support escalations, data corruption, outages.

## Team / Operational Ownership

Who owns what operationally and where handoffs exist.

## Testing and Release Constraints

Important test suites, release gates, migration limits, compatibility constraints.

## Known Architecture Decisions

Links or summaries of ADRs, intentional tradeoffs, or forbidden moves.

## Out of Scope

Things the loop must not redesign.
```

## Context Sufficiency Output

```json
{
  "context_assessment": {
    "status": "partial",
    "missing_fields": [
      "roadmap",
      "consistency_requirements",
      "incident_history"
    ],
    "impact": [
      "Cannot confidently evaluate roadmap shear.",
      "Cannot claim wrong consistency boundary above Moderate without current-harm evidence."
    ],
    "score_caps": {
      "expert_depth": 0.75,
      "serious_structural_claims": "requires_current_harm_or_downgrade"
    }
  }
}
```

---

# Implementation Roadmap

## P0: Principal-Defect Recall Benchmark

Priority:

```text
P0
```

Evidence basis:

```text
c-CRAB
RACE-bench
REAP
ATAM/QAW
agentic-refactoring failure studies
```

Implementation cost:

```text
Medium-High
```

False-positive risk:

```text
Low
```

Expected recall lift:

```text
Very high indirectly
```

Expected precision impact:

```text
Positive, because false positives become visible
```

How to test:

```text
Run current contest-refactor baseline against public + hidden mini fixtures.
Record recall, precision, localization, honesty, overbuild, tangled risk.
```

Before or after benchmark:

```text
This is the benchmark. Build first.
```

Build acceptance criteria:

```text
at least 15 public mini fixtures
at least 10 hidden fixtures
expected non-findings included
localization oracles included
context-insufficiency fixtures included
scoring script works
baseline score recorded
```

---

## P0: Domain-Integrity Lens

Priority:

```text
P0
```

Evidence basis:

```text
DDD aggregate/invariant guidance
domain events
saga/process ownership
Fowler bounded context / aggregate
SEI context sufficiency
```

Implementation cost:

```text
Medium
```

False-positive risk:

```text
Medium if it becomes DDD cosplay
Low-Medium if schema requires evidence and context caps
```

Expected recall lift:

```text
High
```

Expected precision impact:

```text
Neutral to positive with sufficiency caps
```

How to test:

```text
A/B hidden fixtures:
  baseline contest-refactor
  contest-refactor + domain-integrity lens
Measure recall lift and Serious+ false positives.
```

Before or after benchmark:

```text
After minimal benchmark skeleton exists.
```

---

## P0: Change-Scenario Stress Test

Priority:

```text
P0
```

Evidence basis:

```text
Parnas
ATAM
QAW
quality-attribute scenarios
```

Implementation cost:

```text
Low-Medium
```

False-positive risk:

```text
Low
```

Expected recall lift:

```text
Medium
```

Expected precision impact:

```text
Positive
```

How to test:

```text
Use fixtures with grounded scenario, missing scenario, invented scenario, and current-harm exceptions.
Score correct gating behavior.
```

Before or after benchmark:

```text
After benchmark skeleton.
```

---

## P0: Context-Sufficiency Honesty / Score Caps

Priority:

```text
P0
```

Evidence basis:

```text
ATAM/QAW require business and mission context for expert-depth architecture evaluation.
```

Implementation cost:

```text
Low
```

False-positive risk:

```text
Very low
```

Expected recall lift:

```text
Indirect
```

Expected precision impact:

```text
Strong positive
```

How to test:

```text
Insufficient-context fixtures:
  missing roadmap
  missing consistency requirements
  missing incident history
  missing regulatory constraints
Score whether loop downgrades or emits CONTEXT_INSUFFICIENT_FOR_EXPERT_DEPTH.
```

Before or after benchmark:

```text
Same wave as benchmark or immediately after.
```

---

## P1: Tradeoff-Grade Step 2

Priority:

```text
P1
```

Evidence basis:

```text
ATAM
ADR practice
Nygard ADR
Fowler ADR
Microsoft ADR guidance
```

Implementation cost:

```text
Low
```

False-positive risk:

```text
Low
```

Expected recall lift:

```text
Medium
```

Expected precision impact:

```text
Positive for Serious+ fixes
```

How to test:

```text
Remedy-track fixtures:
  correct minimal fix
  overbuilt fix
  wrong alternative rejection
  missing alternative analysis
```

Before or after benchmark:

```text
After benchmark skeleton.
```

---

## P1: Change-Coupling Pass

Priority:

```text
P1
```

Evidence basis:

```text
logical/evolutionary coupling MSR research
change impact analysis
logical + structural coupling studies
microservice logical coupling research
```

Implementation cost:

```text
Medium
```

False-positive risk:

```text
Medium if promoted directly
Low-Medium if candidate-only
```

Expected recall lift:

```text
Medium
```

Expected precision impact:

```text
Neutral if candidate-only
Negative if final-finding generator
```

How to test:

```text
Run hidden fixtures with seeded git histories.
Measure whether candidate appears before finding.
Measure whether false final findings increase.
```

Before or after benchmark:

```text
After benchmark.
```

---

## P2 / Defer: Expert Panel / Multi-Critic Disagreement Synthesis

Priority:

```text
P2 / Defer
```

Evidence basis:

```text
mixed multi-agent evidence
self-consistency benefits
multi-agent failure modes
coordination overhead
```

Implementation cost:

```text
Medium-High
```

False-positive risk:

```text
Medium
```

Expected recall lift:

```text
Unknown
```

Expected precision impact:

```text
Mixed
```

How to test:

```text
Only after P0/P1:
  compare single-loop + lenses
  vs narrow artifact-contract critics
on hidden fixtures.
```

Before or after benchmark:

```text
Only after benchmark and measured trigger.
```

Go/no-go trigger:

```text
hidden Serious+ recall < 0.70
OR recall improvement < 10 absolute points
while precision >= 0.85
```

---

## P2: Refactor-Value Taxonomy

Priority:

```text
P2
```

Evidence basis:

```text
Useful for reporting and scoring clarity, but not strong evidence for recall lift.
```

Implementation cost:

```text
Low-Medium
```

False-positive risk:

```text
Low
```

Expected recall lift:

```text
Low
```

Expected precision impact:

```text
Neutral
```

How to test:

```text
Measure score stability and usefulness in eval reports.
```

Before or after benchmark:

```text
After benchmark.
```

---

## P2 / Conditional: Tangled-Refactor Detector

Priority:

```text
P2 / Conditional
```

Evidence basis:

```text
Refactoring Runaway paper
```

Implementation cost:

```text
Medium
```

False-positive risk:

```text
Low
```

Expected recall lift:

```text
Low
```

Expected precision impact:

```text
Positive for remedy quality
```

How to test:

```text
Remedy-track fixtures with intentionally tangled patches.
Measure compile/test preservation and unrelated touch radius.
```

Before or after benchmark:

```text
After benchmark. Current contest-refactor already has some anti-tangle mechanisms.
```

---

## Reject as Next Path / Conditional: Executable Governance Ingestion

Priority:

```text
Reject as next path / Conditional
```

Evidence basis:

```text
Useful in regulated repos or architecture-governed repos.
Not general principal-recall keystone.
```

Implementation cost:

```text
Medium
```

False-positive risk:

```text
Low if source is explicit
```

Expected recall lift:

```text
Low generally
Medium in regulated domains
```

Expected precision impact:

```text
Positive in governance-heavy repos
```

How to test:

```text
Regulated-domain fixtures with explicit policy-as-code.
```

Before or after benchmark:

```text
Only after benchmark, and only if current governance ingestion is incomplete.
```

---

## Reject as Next Path / Conditional: Harness-Failure vs Code-Failure Distinction

Priority:

```text
Reject as next path / Conditional
```

Evidence basis:

```text
Evaluation hygiene, not direct principal-recall lift.
```

Implementation cost:

```text
Low-Medium
```

False-positive risk:

```text
Low
```

Expected recall lift:

```text
Very low
```

Expected precision impact:

```text
Positive for eval trust
```

How to test:

```text
Benchmark harness logs and forced harness-failure fixtures.
```

Before or after benchmark:

```text
Only if benchmark noise appears.
```

---

# Risks and Counterarguments

## Risk: Benchmark Overfitting

Agents may learn benchmark shape rather than architecture reasoning.

Mitigations:

```text
hidden rotated fixtures
domain vocabulary variation
multiple languages
fixture size variation
decoy patterns
different scenario sources
public teaching fixtures separate from hidden scoring fixtures
```

## Risk: DDD Cosplay

The domain-integrity lens may hallucinate aggregates, bounded contexts, or anemic model complaints.

Mitigations:

```text
ban DDD-label-only findings
require rule_statement
require owner_status
require mutation_sites
require consistency_model
require evidence_refs
require context_sufficiency
```

## Risk: Co-Change Noise

Co-change may reflect normal workflow rather than architectural defect.

Mitigations:

```text
candidate-only artifact
filter mechanical commits
combine with static dependency graph
require corroboration before promotion
explicitly classify test/prod mirror changes
```

## Risk: Expert Panel Ceremony

More critics may create more text, cost, and disagreement without better recall.

Mitigations:

```text
defer panel
require hidden-fixture trigger
use artifact contracts, not personas
use disagreement synthesis, not majority vote
```

## Risk: Overbuild From Serious+ Remedies

Agents may add frameworks, abstractions, or broad restructurings to satisfy architecture prompts.

Mitigations:

```text
overbuild penalty
forbidden remedy families
minimal tradeoff record
anti-overbuild critic later if needed
single-pattern commits remain enforced
```

## Risk: Tangled Refactors

Architecture fixes can sprawl.

Mitigations:

```text
remedy-track tangled penalty
touch-radius limit
concern-cluster detection
build/test gates
single-pattern commit discipline
```

## Risk: Context Insufficiency

The loop may overclaim expert judgment from static code.

Mitigations:

```text
CONTEXT_INSUFFICIENT_FOR_EXPERT_DEPTH
score caps
insufficient-context fixtures
separate no-issue-found from not-evaluable
```

## Risk: Benchmark Gaming

The loop may optimize for fixture keywords.

Mitigations:

```text
hidden fixtures
rotated domains
semantic oracle matching
expected non-findings
overbuild traps
scenario-source variation
```

---

# Final Recommendation

The correct next path is:

```text
benchmark-first
```

Not:

```text
change-coupling prototype first
domain-integrity lens first
expert panel first
no change
```

The reason is simple:

```text
Without a principal-defect recall benchmark, there is no trustworthy way to tell whether any addition raises the ceiling.
```

## Exact Next 3 Implementation Steps

### Step 1: Build `evals/principal_defects/`

Implement:

```text
evals/principal_defects/
  schema/
  public/
  hidden/
  scripts/
  docs/
```

First pack:

```text
3 missing_invariant_owner
3 duplicated_business_rule_across_layers
3 wrong_transaction_or_process_owner
2 wrong_consistency_boundary
2 dependency_direction_violation_with_hidden_domain_rule
2 insufficient_context
2 expected_non_finding_decoy
```

Required scoring:

```text
recall
precision
localization
remedy_quality
overbuild
tangled_refactor_risk
context_sufficiency_honesty
```

### Step 2: Add P0 Lens and Gates

Implement:

```text
lens-domain-integrity.md
domain_integrity finding schema
change_scenario Serious+ requirement
current_harm exception schema
tradeoff_analysis minimal schema
CONTEXT_INSUFFICIENT_FOR_EXPERT_DEPTH
score caps
```

Then run:

```text
baseline vs P0-lens A/B on hidden fixtures
```

Promotion target:

```text
Serious+ recall improves materially
precision does not drop below target
overbuild does not increase
insufficient-context honesty improves
```

### Step 3: Add Change-Coupling Candidate Artifact

Implement:

```text
artifacts/change_coupling.json
artifacts/change_coupling.md
```

Rules:

```text
read-only
candidate evidence only
no final finding generation
filtered commits
co-change + static dependency comparison
promotion requires corroboration
```

Then test:

```text
hidden git-history fixtures
measure candidate usefulness
measure false-positive containment
```

Only after these steps should contest-refactor consider a critic panel.

## Final Build Order

```text
P0. principal-defect recall benchmark
P0. domain-integrity lens
P0. Serious+ change_scenario / current_harm gate
P0. context-sufficiency honesty and score caps
P1. minimal tradeoff_analysis for Serious+ structural fixes
P1. read-only change-coupling candidate artifact
P2. refactor-value taxonomy
P2. tangled-refactor detector if remedy-track shows need
P2/defer. expert panel only on benchmark trigger
Reject as next path. broad competitor inventory
Reject as next path. generic more agents
Reject as next path. broad checklist/reviewer additions
```

The shortest version:

```text
Measure the ceiling before adding new architecture machinery.
Then add the smallest lenses that directly target invariant ownership, consistency boundaries, grounded change forces, and tradeoffs.
Use co-change as radar, not as a judge.
Do not summon the expert-panel hydra until the benchmark proves the single-loop architecture still cannot see deep enough.
```