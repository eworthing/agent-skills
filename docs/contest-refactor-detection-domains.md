# `contest-refactor` detection-domain register

What the loop looks for **in the target codebase** — the review domains, their coverage, the
measured evidence about which additions actually help, and the open detection backlog.

**Boundary vs. the review register.** [`contest-refactor-review-register.md`](contest-refactor-review-register.md)
owns the skill's *own* correctness: artifact discipline, validators and gates, certification,
cost, and process. This document owns the skill's *reach*: which classes of defect it can find at
all, and how confident it is in what it reports. A rule of thumb — if the item changes what a
reviewer would say about the target repo, it belongs here; if it changes what `validate-artifact.py`
or the loop's own bookkeeping does, it belongs there. Items that sit on the seam are cross-referenced,
never dual-listed.

**Created 2026-08-21**, seeded by the competitor domain sweep of that date plus the four detection
rows migrated out of the review register's open backlog (rows 23, 24, 25, 27).

## Contents

- [Calibration discipline — read before adding any domain](#calibration-discipline--read-before-adding-any-domain)
  - [Detection-domain promotion bar](#detection-domain-promotion-bar)
- [Current coverage baseline](#current-coverage-baseline)
- [Competitor domain sweep — 2026-08-21](#competitor-domain-sweep--2026-08-21)
- [Named candidates — row 23 decomposition](#named-candidates--row-23-decomposition)
- [Corroborated backlog items](#corroborated-backlog-items)
- [Open detection backlog](#open-detection-backlog)
- [Parked and adjudicated detection levers](#parked-and-adjudicated-detection-levers)
- [Cross-references into the review register](#cross-references-into-the-review-register)

## Calibration discipline — read before adding any domain

The single most important fact in this document, and the reason it is not simply a wish list:

> **Added checklist prose has repeatedly produced a measured recall lift of zero.**

Three independent measurements say so. The advisory eval program (#35–#48) established that those
evals measure *restraint and vocabulary, not recall* — recall lift was 0 on both Sonnet and Haiku
because the seeded defects were legible. The parked W3.2 domain lens measured a recall lift of 0
against a bare rubric that scored 6/6. And the June research doc's domain-integrity lens was parked
on the same result. The Critic is already strong; the marginal checklist line is usually paying for
nothing.

A defect is **legible** when the bare rubric already finds it. Legibility is measured, never
assumed, and it is the property that decides whether a candidate domain can demonstrate anything:
a legible defect leaves no lift for added prose to capture. Every zero above was a legible corpus.

### Detection-domain promotion bar

A candidate domain ships when all six hold. The bar is uniform across every candidate in this
document; each tier below binds to it rather than restating it.

1. **Blind case** — one worked example the current lens misses, naming the lens sections that would
   have had to fire. The bar is *the lens cannot find it*, not *the lens does not name it*: a defect
   the rubric already catches under another name is pure token cost.
2. **Illegible RED** — a seeded defect the bare-rubric control finds in at most 1 of 5 reps.
3. **Measured lift** — the guided arm finds it in at least 4 of 5 reps, with the matches read rather
   than counted; static audits over-rate severity. Harness at `peer-plan-review/evals/`.
4. **Restraint** — at least 2 near-miss fixtures where the domain stays silent, and zero false
   positives across them. Restraint is the axis where added prose has measurably paid.
5. **Budget** — the prose delta measured with `scripts/token-budget.py --check`. An always-included
   lens (`lens-security.md`, `lens-efficiency.md`) spends from **both** loop ceilings; a stack lens
   spends from one. Live headroom on 2026-08-21: **429** tokens on the apple path, **407** on
   generic. A larger delta buys a dated ceiling bump that lands the margin back inside [400, 550).
6. **Adjudicated** — the owner signs the disposition, as with the G17 bar.

Criteria 2 and 3 are one experiment, and it is the expensive one: budget a measurement run per
candidate, not per tier.

## Current coverage baseline

Verified against the lens and rubric files at HEAD on 2026-08-21.

| Domain | Where |
| --- | --- |
| Architecture vocabulary, 19-item smell list, 5 architectural tests (deletion, two-adapter, shallow module, interface-is-test-surface, replace-don't-layer), Unified Seam Policy, dependency categorization, severity/score anchors | `references/architecture-rubric.md`, `architecture-rubric-scoring.md` |
| Ownership & state, hidden state machines, concurrency/runtime safety per language, coupling & leakage, regression resistance, incremental test scoping | `references/lens-generic.md`, `lens-apple.md` |
| Failure modes & observability — silent-swallow audit (per-language grep targets), retry/backoff policy, error-context preservation, adapter-boundary telemetry, panic-recovery on executors | `references/lens-generic.md` § Failure modes, with the same five categories **inlined** in `lens-apple.md` § Failure modes & observability (Apple-flavored) because the Apple load set excludes `lens-generic.md`. Any addition here costs *both* ceilings even though neither file is always-included |
| Security — input validation & deeplinks, secrets, PII in logs, keychain, biometrics, transport, dependency hygiene, plus stack-agnostic SQL/command injection, path traversal, WebView XSS, insecure deserialization | `references/lens-security.md` (always-included) |
| Efficiency D1–D4 — recomputed derived values, sequential independent effects, hot-path/startup blocking, closure-capture retention | `references/lens-efficiency.md` (always-included) |
| Apple-specific — SwiftUI discipline, continuation-bridge audit, feature-flow choreography, sheet/binding symmetry, accessibility audit, cross-platform compile correctness, Authority-Map test-surface cross-check | `references/lens-apple.md` |

**Deliberately out of scope** (rubric's `Ignore:` line): stylistic concerns, naming nits,
micro-optimizations distinct from structural waste, generic filler, unsupported speculation.

## Competitor domain sweep — 2026-08-21

**Method.** Four parallel survey agents over all 51 repos in `refs/competitors/contest-refactor`
(49) and `refs/competitors/shared` (2), each asked for review domains *absent* from the baseline
above. Findings were filtered by criterion 1 of the promotion bar — the lens must be **blind** to
the class, not merely silent about its name — then ranked by cross-batch corroboration. Every
candidate below is a criterion-1 argument awaiting criteria 2–6. All exemplar paths below were spot-verified to exist on
2026-08-21. **`refs/` is gitignored** (`.gitignore:9`) — these are provenance pointers into a local
clone corpus, not tracked files; see [`refs/competitors/README.md`](../refs/competitors/README.md).

### Tier 1 — structurally blind, cross-corroborated

Each was found independently by 3–4 of the four batches. Ordered by contest relevance.

| # | Domain | Why the current lens is blind | Best exemplar |
| --- | --- | --- | --- |
| 1 | **Test-oracle trust** — expected values derived from the implementation's own calculation, assertion-free or snapshot-only proof, tests re-proving framework behavior, mock/emulator contract drift, coverage illusion, sleep-based waits | The rubric audits test *placement* (interface-is-test-surface, Authority-Map, incremental scoping) and never test *strength*. A competitor can ship fake-green tests that score `test_strategy` 9+. The most gameable surface in a contest | `levnik-skills/.../ln-23-test-suite-auditor/SKILL.md` §4; `brooks-lint/skills/_shared/test-decay-risks.md` |
| 2 | **Silent-semantics preservation** — response *shape* unchanged while *meaning* shifts: `count` now excludes soft-deleted rows, sort order falls back to DB default, cents↔dollars, `[]`→`null`, a default flips because a different column is read | Meta-Rule 4 / `risk_boundary_evidence` / G33 cover *declared* risk boundaries. Nothing covers the "dangerous middle" where an existing caller gets a different value for the same input. This is the signature defect class of a refactoring loop | `ngmeyer-skills/.../rigorous-review/references/behavior-preservation.md` |
| 3 | **Fail-open / insecure-default posture** — fail-open when the *check itself* errors, fallback secrets, default credentials, debug features shipped on, production code falling back to mock/stub data, undefined semantics for `timeout=0` / `key=""` | The failure-modes audit is deep on *swallowed* errors but never asks what happens when the guard errors. Cheapest Tier-1 add: one numbered question in the existing audit plus one security-lens bullet | `trailofbits-skills/plugins/insecure-defaults/references/fail-open-security.md`; `shared/anthropic-claude-code/plugins/pr-review-toolkit/agents/silent-failure-hunter.md` |
| 4 | **Persistence & transaction correctness** — transaction-boundary ownership vs. the business operation, lost updates, write skew, idempotency keys, outbox/inbox, cache ownership/invalidation/stampede, resource release under consumer abandonment, migration reversibility, old-code-meets-new-schema deploy ordering | No lens touches any of it. Highest-consequence domain entirely absent. Mostly inert on pure SwiftUI targets — argues for a `lens-generic` section, not always-included | `levnik-skills/.../ln-25-persistence-auditor/SKILL.md` §2–4; `ce-reviewers/reviewers/data-migration-expert.md` |
| 5 | **Authorization & ownership** — session check *and* ownership check of the target resource on every mutation; tenant isolation through HTTP→service→query | `lens-security.md` has no authz domain at all. The formulation worth stealing is procedural, not a checklist: reconstruct how *this* codebase enforces authz, then flag the endpoint that **deviates from the house norm** — the inconsistent handler is the bug more often than the absent one | `sentry-skills/skills/django-access-review/SKILL.md`; `tech-audit-skill/tech-audit/dimensions/D05-multi-tenant-isolation.md` |

### Tier 2 — real gaps, medium cost

| Domain | Note | Best exemplar |
| --- | --- | --- |
| **Suppression & delivery-gate hygiene in the target** — growing lint/type baselines, blanket `noqa`/`swiftlint:disable` without reasons, CI gates that warn but `exit 0`, stale skips, "exit code zero does not prove a shippable build" | Points the skill's own anti-fake-green trust-model instinct at the target's machinery. Strongly on-brand | `code-quality-atlas/skills/auditing-enforcement-and-meta-artifacts/SKILL.md`; `levnik-skills/.../ln-22-codebase-auditor/SKILL.md` §2 |
| **Public-contract back-compat** — field removal/type change, error-shape drift across endpoints, versioning-strategy mixing, pagination compat | Groundable via API-surface diffing tools rather than judgment | `gstack/review/specialists/api-contract.md` |
| **AI/LLM integration trust boundaries** — model output persisted or fetched unvalidated, prompt text advertising tools not actually wired, MCP tool metadata as untrusted input | Increasingly present in target codebases; nothing in any current lens | `code-quality-atlas/skills/reviewing-llm-integration/SKILL.md` |
| **Git-forensic targeting signals** — churn×complexity hotspots, change coupling with an asymmetry test, complexity trend direction | Not a judgment domain but a **selection** input; closed-form formulas over `git log`. Feeds item 24 directly (`audit_cochange.py` already ships change-coupling as candidate evidence) | `forensic-skills/.claude/skills/forensic-change-coupling/SKILL.md` |

### Tier 3 — cheap point additions

- **Enum / closed-set completeness** — when a case is added, read every consumer, allowlist array,
  and branch chain, including code outside the diff. Extends hidden-state-machines.
  `gstack/review/checklist.md`
- **Unit & time correctness at the data-type level** — naive vs. aware datetime, `TIMESTAMP` vs
  `TIMESTAMPTZ`, money-as-float, date-key window assumptions.
  `logic-lens/skills/_shared/logic-risks.md` (L9); `trailofbits-skills/plugins/dimensional-analysis/`
- **Comment rot and stale-ADR-as-finding** — the rubric's CONTEXT.md/ADR awareness currently only
  *suppresses* findings; the reverse direction (code drifted from the recorded decision, comment
  contradicts the code it describes) is missing.
  `shared/anthropic-claude-code/plugins/pr-review-toolkit/agents/comment-analyzer.md`

### Methods worth stealing regardless of domain

- **Per-domain "what not to flag" lists, co-located with each lens section.** Carried by
  `ce-reviewers`, `brooks-lint`, `ngmeyer-skills`, and `sentry-skills` independently. The lenses
  today have one global `Ignore:` line. Cheapest candidate on the board, and it targets restraint —
  the one axis where added prose has measured value. Write each entry with its positive owner
  attached, the way `ce-reviewers` does ("a slower response isn't a contract violation — that
  belongs to the performance reviewer"): a bare prohibition raises the banned behaviour's
  salience, while naming the owner routes it instead.
- **Severity × confidence as independent axes with an asymmetric floor** — suppress below a
  confidence bar *except* the highest-severity class, which must never be silently dropped.
  `tech-audit-skill/tech-audit/templates/finding-phrasing.md`; `ngmeyer-skills/.../scoring-gating-validation.md`
- **Reproducer-based false-positive withdrawal** — a finding whose reproducer *passes* on the
  original code is withdrawn, and "a confident trace is never a reason to skip it."
  `logic-lens/skills/logic-review/SKILL.md` (Execution Verification Gate). **Adopted in principle
  by [row 27](#open-detection-backlog)'s 2026-08-21 adjudication**, which put assurance on the
  Critic's own pass; the registry's `withdrawn` occurrence status is already the sink for it.
- **Grep-the-defense-or-it-doesn't-exist** — "if you cannot point to the line that enforces the
  defense, it does not exist; a constant name is not a verified bound."
  `great_cto/skills/skeptical-triage/SKILL.md`
- **Externalized precedents file for the false-positive filter** — hard-exclusions and precedents as
  user-supplied files so an org tunes them without forking the prompt.
  `anthropic-security-review/.claude/commands/security-review.md`

## Named candidates — row 23 decomposition

Row 23 said *"decompose per lens"* and set its done-when as *"each surviving lens carries its own
promotion-bar entry, so 'expansion' resolves into named candidates that pass or park individually."*
Decomposed 2026-08-21. Every sweep candidate above now has an ID, a **named target file**, its
**budget class**, and the **next unmet criterion** — so a measurement run can be scheduled per
candidate instead of against a vague "detection-lens expansion".

**Budget class** is the fact that decides criterion 5, and it is a property of the *target file*,
not of the domain. Read off `scripts/token-budget.py`'s `loaded_set()`:

| Class | Target files | What it spends |
| --- | --- | --- |
| **both** | `method.md`, `method-critic.md`, `architecture-rubric.md`, `architecture-rubric-scoring.md`, `lens-security.md`, `lens-efficiency.md`, `SKILL.md`, the output-format set, `validation.md` | apple **and** generic ceilings — the binding one is generic, **407** tokens |
| **apple** | `lens-apple.md` | apple ceiling only, **429** tokens |
| **generic** | `lens-generic.md` | generic ceiling only, **407** tokens |
| **both (split)** | a rule that must be written into `lens-apple.md` *and* `lens-generic.md` because the Apple load set excludes the generic lens | one ceiling each — same total as **both**, at twice the drift surface |
| **none** | `startup.md` (main-agent only), `halt-handoff.md` (HALT-emitting loops only), anything in `scripts/` | zero loop-path tokens |

| ID | Candidate | Target | Budget | Next unmet criterion |
| --- | --- | --- | --- | --- |
| **DD-01** | Test-oracle trust (Tier 1 #1) | `architecture-rubric-scoring.md` `test_strategy` anchors | both | **1, contested.** `lens-apple.md` § Authority-Map test-surface cross-check already gates `test_strategy ≥ 9` on *surface* coverage. The blind half is oracle *strength* — an expected value the implementation itself computed, an assertion-free snapshot — which survives the Authority-Map walk intact. Criterion 1 needs a worked example that passes Authority-Map and still proves nothing |
| **DD-02** | Silent-semantics preservation (Tier 1 #2) | `method.md` Meta-Rule 4 | both | **2/3.** Criterion 1 is clean and sharp: Meta-Rule 4 is **risk-triggered** on an enumerated list — actor/isolation, `Sendable`, `#if os`/`canImport`, cross-file visibility, lock ordering. A `count` that silently starts excluding soft-deleted rows crosses none of them, so the trigger never fires and G33 never has a boundary to gate. Highest contest relevance on the board |
| **DD-03** | Fail-open / insecure-default posture (Tier 1 #3) | `lens-security.md`, **not** the failure-modes audit | both | **2/3.** Criterion 1 clean: all five failure-mode categories are about errors *lost*, never about the guard itself erroring. Sweep called this the cheapest Tier-1 add and proposed splitting it across both stack lenses — **decomposition disagrees**: a `lens-generic` + `lens-apple` split costs both ceilings anyway (the Apple lens inlines the five) at twice the drift surface, so one `lens-security.md` bullet is strictly cheaper |
| **DD-04** | Persistence & transaction correctness (Tier 1 #4) | `lens-generic.md`, new section | generic | **5 first, unusually.** Largest prose delta of the set against **407** tokens of generic headroom; the sweep already decided against always-included. Measure the delta before buying the measurement run — a candidate that cannot fit is not worth an experiment |
| **DD-05** | Authorization & ownership (Tier 1 #5) | `lens-generic.md`, **not** `lens-security.md` | generic | **2/3.** Sweep proposed `lens-security.md`; that is always-included, so it would charge every Apple client-only run for a domain inert on it. `lens-generic.md` gets the same reach for one ceiling. The importable part is procedural — reconstruct the house authz norm, flag the *deviating* handler — which is a Step-3 re-derivation shape, not a checklist |
| **DD-06** | Suppression & delivery-gate hygiene (Tier 2) | `scripts/tool_runner.py`, Step-0 sub-step 6c | **none** | **1, restated as a tool spec.** Growing lint baselines, reason-free `noqa`/`swiftlint:disable`, CI gates that warn and `exit 0` are all greppable — this is a wired analyzer, not prose. Criterion 3 collapses for a deterministic detector (lift is 5/5 by construction); criteria 4 and 6 still bind, and every hit stays `promotion_allowed: false` candidate evidence. **Cheapest candidate on the board by budget** |
| **DD-07** | Public-contract back-compat (Tier 2) | `scripts/audit-public-surface.sh`, extended to diff two revisions | **none** | **1, restated as a tool spec.** Same collapse as DD-06. The existing script already enumerates the public surface; back-compat is that enumeration diffed across revisions |
| **DD-08** | AI/LLM integration trust boundaries (Tier 2) | `lens-security.md` | both | **2/3.** Model output persisted or fetched unvalidated is an untrusted-input class the security lens has no bullet for. Note the skill already applies this doctrine to *itself* at 6c (analyzer output never crosses the subagent boundary); the candidate is pointing it at the target |
| **DD-09** | Git-forensic targeting signals (Tier 2) | — | **none** | **Not a standalone candidate — merged into row 24 slice D** (churn prior + escalate-on-hit). The sweep itself classifies it as a *selection* input rather than a judgment domain, `audit-churn.sh` and `audit_cochange.py` already run at Step 0, and slice D already owns "ordering reproducible from a fixed sha, measured against flat ordering". Tracking it twice would be the dual-listing this document forbids |
| **DD-10** | Enum / closed-set completeness (Tier 3) | `lens-generic.md` + `lens-apple.md` § Hidden State Machines | both (split) | **2/3.** One line in each Hidden-State-Machines section. The load-set asymmetry forces the split; there is no single-file home |
| **DD-11** | Unit & time correctness at the data type (Tier 3) | `lens-generic.md` | generic | **2/3.** Naive-vs-aware datetime, `TIMESTAMP` vs `TIMESTAMPTZ`, money-as-float. Largely inert on Apple targets, which is why it is generic-only |
| **DD-12** | Comment rot + stale-ADR-as-finding (Tier 3) | `architecture-rubric.md` § CONTEXT.md / docs/adr Awareness | both | **1, contested.** `architecture-rubric-scoring.md` already scores *vocabulary* drift between code and `CONTEXT.md` under `domain_modeling` (anchors at 10 and 7). The genuinely blind half is narrower than the sweep claimed: code drifted from a **recorded ADR decision** raised as a finding, and a comment that contradicts the code it describes. Criterion 1 needs a worked example that clears the vocabulary-drift overlap |
| **DD-13** | Per-domain "what not to flag" lists, with the positive owner named | every lens section | all, aggregate | **4 and 5 — the bar inverts here.** This is a *restraint* lever, so criteria 2 and 3 (recall lift) do not apply and criterion 4 becomes the experiment. That is the one axis where added prose has measurably paid, which makes it the only candidate whose expected value is not argued against by the calibration discipline above. The aggregate delta across every lens is the risk, not any single entry |
| **DD-14** | Grep-the-defense-or-it-doesn't-exist | `method.md` Meta-Rules | both | **1, contested.** Meta-Rule 1 already forces tool hit → source → behavior, but only for *positive* claims. This candidate is the negative direction — a claimed absence of vulnerability needs a citable enforcing line, and "a constant name is not a verified bound". Criterion 1 turns on whether that asymmetry is real or whether Meta-Rule 1 read generously already covers it |

**Reading the "next unmet criterion" column.** Of fourteen candidates, only **six** — DD-02,
DD-03, DD-05, DD-08, DD-10, DD-11 — have the expensive measurement run as their genuine next step.
The other eight are cheaper than they looked: three (DD-01, DD-12, DD-14) sit at a *contested*
criterion 1, where the sweep's blindness claim survives a heading-level read but not a line-level
one, and clearing them costs a worked example rather than a run; two (DD-06, DD-07) are tool specs
whose criterion 3 collapses because a deterministic detector's lift is 5/5 by construction; one
(DD-04) owes a token count before it can justify an experiment; one (DD-13) inverts the bar toward
restraint fixtures; and one (DD-09) is closed by merge into row 24. That reordering is the useful
output of decomposing — the measurement queue is six items long, not fourteen, and eight items can
advance with no measurement at all.

## Corroborated backlog items

Four competitor "standout methods" are independent reinventions of items already on the backlog.
This is corroboration of the designs, not new work:

| Item | Independent reinvention |
| --- | --- |
| **25** — tool-grounded substrate | `code-quality-atlas/skills/grounding-review-in-tool-output/SKILL.md` — run the repo's own tools under the repo's own config, every hit gets exactly one of confirm/contextualize/dismiss ("passing a hit through unexamined is not a fourth option"), tools that fail to run become a stated coverage limitation |
| **24** — coverage manifest | `alibaba-open-code-review`'s mandatory reviewed/skipped-with-reason accounting; `grill-for-claude`'s rule that a clean area must emit an explicit `[GOOD]` entry naming what was checked — "silence is not allowed" |
| **27** — per-finding disproof | `logic-lens`'s Execution Verification Gate; `great_cto/skills/skeptical-triage/SKILL.md`'s three-round self-challenge with a named crux and confidence-driven severity demotion; `compound-engineering-plugin/.../validator-template.md`'s fresh per-finding validator gated on "is it introduced by THIS diff" |
| **6** — confidence axis (register) | `ngmeyer-skills` and `tech-audit-skill` both ship severity × confidence as independent axes with an asymmetric suppression floor — a concrete design for the unrun experiment |

## Open detection backlog

Migrated from the review register's open-backlog table on 2026-08-21 (rows 23, 24, 25, 27 there).
Row numbers preserved for citation continuity with the retired deep-dive.

| Row | Item | State |
| --- | --- | --- |
| 23 | Detection-lens expansion (latent-premises, retry-safety, operational) | **Decomposed 2026-08-21** into DD-01…DD-14 ([named candidates](#named-candidates--row-23-decomposition)), each with a target file, a budget class, and a next unmet criterion. The done-when is **met for the decomposition**: "expansion" now resolves into fourteen candidates that pass or park individually, of which only six await a measurement run. The row stays open as the parent of that queue and closes when every DD-* is promoted or parked |
| 24 | Deterministic selection + coverage manifest + resumable scan | **Slices A/B/B2 shipped 2026-08-19** ([`ITEM24-COVERAGE-UNIT-DESIGN-2026-08-19.md`](../analysis/contest-refactor/ITEM24-COVERAGE-UNIT-DESIGN-2026-08-19.md)): `--scope` given an effect (guarded by `_flag_effect_selftest.py`), `scripts/coverage_ledger.py` + selftest with derived terminal state and a registry cross-check, and a wording-pinned *Coverage disclosure* section in `halt-handoff.md`. **Open: C** (fingerprint invalidation + resume, gated on B staying stable across ≥5 real loops) and **D** (churn prior, advisory ordering). The 2026-08-21 coverage analyzer measured 302/1313 files cited across all historical BenchHype loops (BenchHypeKit 24%) — uneven-coverage proof for C/D |
| 25 | Tool-grounded substrate + per-language rules | **Half A shipped 2026-08-19** ([`ITEM25-TOOL-SUBSTRATE-2026-08-19.md`](../analysis/contest-refactor/ITEM25-TOOL-SUBSTRATE-2026-08-19.md)): `scripts/tool_runner.py` + selftest, six typed non-run outcomes (`absent`/`not_applicable` are never `clean`), redaction + injection containment, `ruff` wired, `audit_cochange.py` adopted — all in Step-0 sub-step 6c at zero loop-path tokens. **Open: Half B** (per-language rule packs) is budget-blocked, not undesigned: the two packs matching the eval corpus total 3,029 tokens (swift 1,422 + python 1,607) against 429/407 tokens of live headroom. **Adjudicated 2026-08-21 — record the wall, stay blocked.** No measured lift exists to justify a 7× ceiling bump on a judgment lever, and the calibration discipline at the top of this document is the reason: added prose has repeatedly measured a recall lift of zero. Re-open with a measured lift, not with a redraft |
| 27 | Per-finding disproof pipeline | **Adjudicated 2026-08-21 — assurance is owned by the Critic's own pass.** No separate disproof stage, no per-finding fan-out; a finding must survive its own crux-and-reproducer challenge before it is emitted. Two consequences worth recording. (a) **The recording half already ships**: the registry occurrence stub carries `withdrawn` — "the Critic audited the finding and reclassified it as not-a-finding; no code change" (`method.md` Step 1.5) — so what is missing is the *trigger discipline*, not a schema. (b) **The known risk is self-grading**: the arm that found the finding also clears it, which is exactly the correlated-family blind spot the G35/G36 six-provider review caught codex-side. Remaining work is prose on the Critic path, so it enters the promotion bar like any other candidate — and like DD-13 it inverts it, since a disproof gate is a precision lever whose experiment is criterion 4, not 2/3 |

**Sweep candidates not yet promoted to rows** — now carried as DD-01…DD-14 in the
[row 23 decomposition](#named-candidates--row-23-decomposition) rather than as an unnamed set.
Each enters this table once it clears the [promotion bar](#detection-domain-promotion-bar).

## Parked and adjudicated detection levers

Recorded so they read as decisions rather than omissions. Re-open one by clearing the promotion
bar with new evidence; the measured result stands until then:

- **W3.2 domain lens — PARKED** on a measured recall lift of 0 (bare rubric 6/6). Re-measurement
  needs a precision RED, not another lens draft.
- **Domain-integrity lens (June research doc) — PARKED**, same measured result.
- **Serious+ grounded `change_scenario`** and **minimal `tradeoff_analysis`** requirements — never
  built, never formally adjudicated; `git log -S` shows no commit ever introduced either field.
  Non-adoption is evidence-consistent with the judgment-lever program's zero recall lift.
- **Refactor-value taxonomy** and **tangled-refactor detector** — self-deferred (P2/conditional) by
  the June research doc; still deferred.
- **Change-coupling** — the one June-doc detection proposal that *shipped*, as candidate evidence
  (`audit_cochange.py`). The forensic-skills sweep entry above is the natural extension.

## Cross-references into the review register

Seam items that stay in the register because their mechanism lives there, but whose *subject* is
detection reach:

- **[P1] G17 hard gate cannot block an untested deepening refactor** — the gate's subject (interface
  test coverage of a deepening change) is a detection property, and it is the nearest existing gate
  to Tier-1 item 1. Its promotion bar (≥5 applicable runs, ≥1 violation, ≥2 restraint, **≥2
  languages**, zero blind lines, zero false positives, human-adjudicated) and the live adjudication
  packet at [`analysis/contest-refactor/run-kit/G17-ADJUDICATION-2026-08-21.md`](../analysis/contest-refactor/run-kit/G17-ADJUDICATION-2026-08-21.md)
  are register/packet business.
- **Backlog rows 6 and 8** (confidence two-stage experiment; strictness as deterministic
  post-filter) — finding-precision mechanisms, register-owned; see the corroboration table above for
  the competitor designs that bear on row 6.
- **Backlog row 11** (axis-split graders, each declaring the axis it does not judge) — grading
  structure, register-owned, gated on the Tranche-3 comparison. The orthogonality principle behind
  it is independently used by `center-audit`'s multi-lens cascade ("each lens must declare a *does
  NOT look at* list, or all lenses gravitate to the most visible file").
