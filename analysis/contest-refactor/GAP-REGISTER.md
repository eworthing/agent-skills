# Gap Register — contest-refactor competitive analysis, consolidated

**Created 2026-08-20** by consolidating this directory from 44 files (~9,700 lines) to 5.
Every retired file was validated against HEAD before retirement; each row below records the
06-28 audit verdict and the disposition re-checked 2026-08-20. **Full text of every retired
file is in git history** (`git log --follow -- analysis/contest-refactor/<name>` and
`git show <sha>:<path>`); citations into retired files from shipped code and prose stay
resolvable the same way. Gate numbers **G37+** inside the retired corpus are UNBUILT
proposals from May — they are not the G37–G46 that later shipped with the same numbers.

**Surviving files:** this register, `ITEM14-HOST-ATTESTATION-DESIGN-2026-08-18.md` (design
done, unbuilt — backlog row 14), `ITEM24-COVERAGE-UNIT-DESIGN-2026-08-19.md` (row 24),
`ITEM25-TOOL-SUBSTRATE-2026-08-19.md` (row 25), `RUNTIME-COST-AUDIT-2026-08-14.md` (open
audit; the loop-path P2 finding in `docs/contest-refactor-code-review-2026-08-20.md` is its
sharpest consequence).

## Competitor corpus (was `INVENTORY.md`, `SOURCE-STATUS.md`)

47 repos cloned depth-1 for source inspection, pruned 2026-08-17 to **32 clones (~284 MB)**
under gitignored `refs/competitors/`, bucketed per skill; deleted clones listed with
upstream URL + SHA in `refs/competitors/README.md`. Most-load-bearing sources: levnik-skills
(audit-suite, hash-verified editing), anthropic code-review plugin (parallel agents +
confidence), trailofbits (fp-check, SARIF), wshobson-agents (3-layer eval),
alirezarezvani (context-fork, signal router), grill-for-claude (`[GOOD]` enum,
untrusted-content rule), forensic-skills (hotspot×complexity), claude-review-loop
(stop-hook Actor-Critic). Fabrications/hallucinations caught during sourcing are recorded
in the retired `INVENTORY.md` preamble and `CLAIM-DELTA-2026-05-25.md`.

**Do-not-import list (doctrine, kept live):** 50-agent org chart, parallel editors,
always-on deep security review, universal no-delete-without-failing-test, cloud-VM-mandatory
validation, markdown-only findings, parent-repo-stars-as-skill-stars, literature decoration,
generic senior-engineer prompts.

## Gap docs — verdicts (06-28 audit) and dispositions at HEAD (2026-08-20)

| Retired file | 06-28 verdict | Disposition at HEAD |
| --- | --- | --- |
| `SCHEMA-GAP-CONTEST-REFACTOR.md` | PARTIALLY-COVERED | SARIF shipped (`export_sarif.py`); `confidence` field deferred (see Schema decisions below); parallel-critic halves still gated on a mode that does not exist |
| `CRITIC-INDEPENDENCE-GAP.md` | OPEN (Gap A fusion) | Adjudicated: arm_b cheaper-executor measured 2026-06-28 → REJECTED (unsafe on risk-boundary judgment); Execution-unfuse BLOCKED. Post-hoc complements since strengthened: challenger/reviewer isolation recording (`a9ad8f3`/`e3f5aa8`), still report-only — see the independence P1 in the code review |
| `GOVERNANCE-GAP.md` | PARTIALLY-COVERED | `audit_boundaries.py` shipped; declarative `[[boundary_rules]]` + lint/CI ingestion still open-low-value, no consumer |
| `TRACEABILITY-GAP.md` | DEFERRED | File-level tie-back shipped; per-hunk `changed_hunks[]` stays deferred (Schema decisions) |
| `HALT-STATE-GAP.md` | DEFERRED | Partially overtaken: `HALT_EXHAUSTION` shipped 2026-08-18 (backlog item 17, sweep-#2 validated). Worktree isolation remains by-design exclusion; session-spanning handoff still absent-low-value |
| `GATES-GAP.md` | COVERED | G20/G15 artifact-level equivalent; Stop-hooks unportable. Still cited from `validation.md:32` (provenance; resolves via git) |
| `CROSS-MODEL-CRITIC-GAP.md` | DEFERRED | Re-measured 2026-06-30 (W1.1: 0/2 differential, 4/12 restraint false-overturns) → parked again; needs a same-family-blind-spot corpus |
| `CLEAN-ENVIRONMENT-VALIDATION-GAP.md` | OPEN (Gap A) | Fresh-checkout oracle still absent at HEAD; adjacent to (not covered by) the two dirty-tree P1s in the code review |
| `SKILL-TDD-FIXTURES-GAP.md` | PARTIALLY-COVERED | The genuinely-open half (end-to-end bad-codebase loop replay) has since SHIPPED: `evals/loop-fixtures/` + `loop_replay_baseline.json` + graders. Closed |
| `TWO-LAYER-DETECTION-GAP.md` | PARTIALLY-COVERED | Residual largely closed since: `check_g3_evidence_chain_cross_reference` mechanizes the cross-reference |
| `LEVNIK-AUDIT-SUITE-GAP.md` | COVERED | — |
| `SPECIALTY-LENS-DISPATCH-GAP.md` | DEFERRED | Static lens set by design; lens-efficiency became always-included 2026-07-13 on its own evidence |
| `ROI-PRIORITIZATION-GAP.md` | DEFERRED | ROI tiers stay deferred (Schema decisions); `audit_cochange.py` is coupling, not ROI |
| `ROUTING-DISCIPLINE-GAP.md` | DEFERRED | Deliberate simplicity; judge-finding routing (a different thing) shipped in `evals/README.md` + `judge-alignment-log.md` |
| `CONTINUOUS-SCORING-AUGMENTATION-GAP.md` | DEFERRED | No consumer; binary gates remain the contract |
| `PARALLEL-CRITIC-ARTIFACT-CONTRACT-GAP.md` | DEFERRED | Self-gated on parallel-critic mode, which was never built |
| `PHASE-CONTEXT-ISOLATION-GAP.md` | DEFERRED | Subagent-per-loop already isolates; measure-first |
| `MULTI-HARNESS-ADAPTER-GAP.md` | DEFERRED | Symlink install held; no 6th harness has landed |
| `DOMAIN-AWARE-SCANNING-GAP.md` | DEFERRED (stub) | `--scope` workaround; `--scope` behavioral probe (ledger P1) never ran |
| `ADOPTION-SIGNAL-TRACKING-GAP.md` | REJECTED | Meta-discipline, not a skill feature |
| `ARXIV-AGENTIC-REFACTORING-GAP.md` | REJECTED | Empirical context only; its thesis (agents do low-level refactors) is what the June research doc and the paired-arm study later engaged directly |

## Support docs retired

| Retired file | Disposition |
| --- | --- |
| `GAP-AUDIT-AND-IMPROVEMENT-PLAN-2026-06-28.md` | The dual-peer-reviewed audit that stamped every verdict above; its W1–W4 plan was executed/adjudicated by the principal-plan work (W2.1/W3.1-tier-1/W4.1/W4.2 shipped; W1.1/W3.2 parked with measurement; W1.2/W3.3 owner-gated) |
| `STATE-MACHINE-COMPOSITION-APPENDIX.md` | Superseded proposal — its G45–G47 + `canon/loop-phases.toml` never shipped; the G45/G46 that exist today are unrelated gates that reused the numbers |
| `RESEARCH-DELTA.md`, `CLAIM-DELTA-2026-05-25.md`, `CLAIM-DELTA-2026-05-25-pt2.md`, `AWS-RULE-DELTA-2026-08-17.md` | Historical claims-vs-source verification records (the AWS delta is backlog row 29: measured, not adopted — 22 new rules dormant or 100 % FP). Archival; git |
| `CLAIM-DELTA-2026-08-17.md` | Verification record **plus seven still-open ADOPT calls** — carried forward below |
| `REVIEW-PROMPT.md`, `SOURCE-VERIFICATION-PROMPT.md` | Operational prompts for the May review rounds; obsolete |
| `TOKEN-USAGE-AUDIT.md` (2026-06-26) | Estimate-grade cost baseline; superseded by the shipped tiktoken `token-budget.py` guard with enforced ceilings, and by `RUNTIME-COST-AUDIT-2026-08-14.md` (kept) |
| `PROVIDER-SURFACE-AUDIT-2026-08-19.md` | Executed and fully acted on: codex phantom flags fixed `d165a45`, bare opencode ids + class guard `b2b96ef`, agy decision recorded `8e33d6a`; `provider-adapters.md` is the re-verified SSOT |
| `LEVER-F-MICROTEST-2026-08-14.md` | Pre-registered cost microtest for the reading-discipline recipe; **no recorded run** — the recipe shipped in `method.md` regardless. Reopen only under cost pressure, with its frozen pass criteria (in git) |
| `ITEM1-RETROSPECTIVE-AUDIT-2026-08-17.md` | Credential retrospective — executed; G44 shipped and sweep-#1 validated (0/5 vs 5/5 leak) |
| `ITEM3-HARD-RULE-PROPAGATION-2026-08-19.md` | Verified shipped; the enumerated-sites residual is recorded in the code review's inherited section |
| `ITEM26-EVIDENCE-ANCHORING-2026-08-19.md` | Measured 2026-08-19 → not warranted |
| `ITEM28-REMEDIATION-INVENTORY-2026-08-18.md` | Executed; G46 + `repair_revalidation` shipped, sweep-#2 validated (typed field's marginal value = machine-readability) |

## Open ADOPT calls carried from `CLAIM-DELTA-2026-08-17.md`

Seven calls were made 2026-08-17 against refreshed upstream corpus material and have no
recorded execution. Each needs its stated precondition verified before adoption; full
rationale in the retired file (git).

1. Unavailable reviewer ⇒ declared-degraded verdict path (verify verdict path first).
2. Pre-dispatch credential scrub with a repo-local ignore file, applied once at the shared boundary.
3. Bound re-review scope on retry (verify current scope first; adopt only if free-roaming).
4. Bounded fail-open audit across the gate catalog.
5. Mechanical audit protecting relied-upon numbers.
6. Axis-separation where an eval suite already conflates axes (selective, not a rewrite).
7. Derived-from-disk registry check (adopt only if cheap).

## Schema decisions (live doctrine — was `SCHEMA-DECISIONS.md`, 2026-06-30)

**Doctrine:** new finding/artifact fields ship OPTIONAL, additive on the current schema
(the G33 precedent). A field ships only when a pre-registered measurement shows the current
artifact cannot express the information AND a consumer exists. Absent a consumer the honest
disposition is **DEFER (cost/consumer, not doctrine)**.

| Field | Disposition | Rationale |
| --- | --- | --- |
| `confidence` (per-finding enum or 0–100) | DEFER | No in-loop consumer; severity anchors + reviewer verdict already gate promotion |
| ROI tiers (hotspot × complexity) | DEFER | Tie-breaker at most, never a gate; speculative inputs; promoting an audit to a score violates `promotion_allowed: false` |
| per-hunk `changed_hunks[]` | DEFER | File-level traceability shipped; refinement with no consumer |
| `refactoring-patterns.toml` + `[Pattern]` commit prefix | SKIP | Pure vocabulary; no output gain |
| `cross_model_scoring` | **RESERVED for v5** | Co-owns the single v4→v5 migration table with `session_spanning_handoff`; do not persist this name without merging that table. W1.1 deliberately used `halt_success_challenge.challenger_family` instead |

**Unblock condition (every DEFER row):** a concrete consumer exists AND a pre-registered
RED measurement shows the current artifact cannot already express it. Until both hold, the
field stays deferred and out of fixture `expected.*` surfaces.
