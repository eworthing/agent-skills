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
- [Shared-headroom contention](#shared-headroom-contention)
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
   **A bump is authorised separately from when it is applied.** The owner can approve the spend
   before the prose exists — that is what unblocks a candidate for measurement — but the edit to
   `CEILINGS` lands in the same commit as the prose it pays for, sized against the new measured
   actual. A ceiling raised ahead of its prose is unpoliced slack, and unnoticed growth is the
   defect that dict was built to catch.
6. **Adjudicated** — the owner signs the disposition, as with the G17 bar.

### Order of operations — run criterion 2 first

The numbering above is citation-stable and stays as it is, but the **sequence is not the numbering**.
Criterion 2 is the gate; everything else is bookkeeping around it.

1. **Criterion 2 first, alone.** Seed the defect, run the bare-rubric control 5×, read every rep by
   hand. ≥2/5 and the candidate is done — park it.
2. Only then criterion 3, then 4, 5, 6.
3. **Criterion 1 is a pre-filter for token cost, not evidence of blindness.** It is cheap and worth
   keeping — it kills candidates the rubric already names — but it has now been measured as
   *non-predictive* of criterion 2 three times, so never let it justify skipping the run.

Criteria 2 and 3 are one experiment, and it is the expensive one: budget a measurement run per
candidate, not per tier. **Run criterion 2 alone first and let it gate criterion 3** — a legible
fixture spends the expensive half to learn nothing, which is how the three zero-lift results above
were bought.

> **Two 5/5 negatives, chosen to disagree — measured 2026-08-22.** DD-02 and DD-04 were picked for
> *maximally different* illegibility arguments and both came back fully legible. DD-02's gap was
> **"the rule exists but its trigger does not fire"** (Meta-Rule 4's enumerated list); DD-04's was
> **"no lens section covers this at all"** (transaction boundaries), narrowed further to the
> sub-domain with no adjacent rule to generalise from. The catch mechanisms also differed and the
> second is the more general: DD-02's reps borrowed a nearby rule's *spirit*, while DD-04's reps
> used **no lens line at all** — the mandatory doc-vs-code grep, consequence-tracing through an
> unchanged caller, and the Severity Anchors' own worked example were enough.
>
> **This is the fifth and sixth independent measurement pointing the same way** (after the advisory
> eval program, W3.2's domain lens, and the June domain-integrity lens). The reasonable prior is now
> that **this Critic's general machinery reaches these defect classes whether or not prose names
> them**, and that a candidate must show a *behavioural* miss before it is worth prose.
>
> **Three for three, and the third was engineered to win — measured 2026-08-22.** DD-08 was cut as
> narrowly as the class allows: the code shape of the security gate is *identical* before and after,
> only the provenance of the data it trusts changes, with no removed guard and no deleted invariant
> sentence for the doc-vs-code grep to catch. It was deliberately built around the shapes that caught
> DD-02 and DD-04. All 5 reps caught it anyway — and **4/5 found a second seeded-adjacent defect the
> fixture author had not scored, 2/5 a third.** The reviewer was not just meeting the bar; it was
> finding more than the experiment was measuring.
>
> The mechanisms keep coming from outside the lens set: `architecture-rubric.md`'s Dependency
> Categorization table repurposed into a security judgment it does not make, and in one rep,
> MCP-specification knowledge present in no file at all.
>
> **Criterion 1 does not predict criterion 2 — measured 2026-08-22.** DD-02 had the sharpest
> blindness argument on the board: Meta-Rule 4 is risk-*triggered* on an enumerated list, and the
> seeded defect crossed none of its triggers. That argument held textually — and the bare rubric
> still found the defect **5 of 5**, with two reps citing Meta-Rule 4's *spirit* while its trigger
> list stayed silent. **A textual gap in the prose is not a behavioural gap in the reviewer.**
> Criterion 1 is a cheap filter for token cost, not evidence of blindness; only criterion 2 measures
> blindness, and it is the one that must be believed.

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
| Suppression & delivery-gate hygiene in the target — blanket (rule-less) suppressions, lint/type baselines with suppressed-entry counts, CI steps that run a checker then swallow its exit code. Rule-*coded* suppressions are disclosed, never flagged | `scripts/audit_suppressions.py`, Step-0 sub-step 6c (**DD-06**, shipped 2026-08-21; zero loop-path tokens) |
| Public-contract back-compat — public declarations removed or signature-changed since a named revision, classified `removed` vs `changed` | `scripts/audit-public-surface.sh --since <rev>`, Step-0 sub-step 6c (**DD-07**, shipped 2026-08-21; zero loop-path tokens) |

**Deliberately out of scope** (rubric's `Ignore:` line): stylistic concerns, naming nits,
micro-optimizations distinct from structural waste, generic filler, unsupported speculation.

The last two rows are **detectors, not lens prose** — they emit candidate evidence at Step 0 with
`promotion_allowed: false`, and Method Step 3 re-derives every hit against source before it can
become a finding (Meta-Rule 1). They are listed here because they change what the loop can find,
which is this document's subject; they cost nothing on the loop path, which is why they shipped
ahead of the nine candidates still queued behind a measurement run.

## Competitor domain sweep — 2026-08-21

**Method.** Four parallel survey agents over all 51 repos in `refs/competitors/contest-refactor`
(49) and `refs/competitors/shared` (2), each asked for review domains *absent* from the baseline
above. Findings were filtered by criterion 1 of the promotion bar — the lens must be **blind** to
the class, not merely silent about its name — then ranked by cross-batch corroboration. Every
candidate below *entered* as a criterion-1 argument; four were worked on 2026-08-21 and the
[decomposition](#named-candidates--row-23-decomposition) carries each one's current state. All exemplar paths below were spot-verified to exist on
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
| **DD-01** | Test-oracle trust (Tier 1 #1) | — | — | **1 FAILS — PARKED 2026-08-21**, on the candidate's own retraction. Four of six sub-classes were disposed first: sleep-based waits, coverage illusion and snapshot-only proof are already caught (`lens-apple.md:172`, `method.md:37`, `architecture-rubric.md:36`, `architecture-rubric-scoring.md:66`/`:69`), and mock/emulator drift is unreachable by a source-only lens. The remaining tautological-oracle class produced a clean worked example — but `method.md:87`'s Mutation-test mental model **catches it when pointed at it**, trivially, since a tautological oracle misses *every* mutation, and the site is primary-flow so it routes to Noticeable-or-worse. What is missing is a **quantifier** ("name one, anywhere" rather than "for each primary-flow concern"), not a capability. Genuine capability gap identified and left on the record: `lens-apple.md:200`'s Authority-Map step 1 asks only whether an exercising test *file* exists and structurally never asks about oracle validity — but a second gate catching the class is enough for criterion 1, which asks about the lens, not one section. Sharpest artefact of the whole pass: `architecture-rubric.md:104` already carries the right question — *"the assertion would fail if the `target_symbol`'s body were replaced with `fatalError()`"* — scoped by `:100` to transitive coverage of a deepening refactor, so it never engages an ordinary direct unit test. Reported reword costs (not independently verified): `architecture-rubric.md:36` +9, `lens-apple.md:200` +15, `method.md:87` +39 |
| **DD-02** | Silent-semantics preservation (Tier 1 #2) | — | — | **2 FAILS — PARKED 2026-08-22, legible 5/5.** Measured RED-first: a Swift refactor folding three near-duplicate filter chains into one helper, where two call sites already filtered `status != .cancelled` and `orderCount` silently acquires it — shape unchanged, an existing caller renders a different badge, and **no Meta-Rule 4 boundary crossed**, so the criterion-1 argument was sound as written. The bare-rubric control caught it **5 of 5**, precisely: every rep traced the before/after predicates, distinguished the one unsound call site from the two legitimate ones, and named the mechanism. Zero false positives on the clean surrounding change. **Two reps cited Meta-Rule 4's behaviour-preservation clause directly despite the diff crossing none of its trigger boundaries — they applied its spirit, not its trigger list.** Fixture not retuned; a fixture tuned until the control misses measures the tuning |
| **DD-03** | Fail-open / insecure-default posture (Tier 1 #3) | `lens-security.md`, **not** the failure-modes audit | both | **2/3.** Criterion 1 clean: all five failure-mode categories are about errors *lost*, never about the guard itself erroring. Sweep called this the cheapest Tier-1 add and proposed splitting it across both stack lenses — **decomposition disagrees**: a `lens-generic` + `lens-apple` split costs both ceilings anyway (the Apple lens inlines the five) at twice the drift surface, so one `lens-security.md` bullet is strictly cheaper  **PARKED ON CLASS EVIDENCE 2026-08-22, unmeasured.** Three candidates chosen to disagree (DD-02, DD-04, DD-08) all came back legible 5/5, so the prior for an unmeasured classic domain is poor — and here specifically, fail-open posture is classic review material and the failure-modes audit already reasons adjacently about guards. Parked rather than measured to avoid buying the same answer a fourth time at ~500k tokens. **Reversible:** this is a prior, not a result; ask for the run and it gets one. |
| **DD-04** | Persistence & transaction correctness (Tier 1 #4) | — | — | **2 FAILS — PARKED 2026-08-22, legible 5/5.** Sub-domain chosen for maximum illegibility: **transaction-boundary ownership**, the one of three with *no* nearby rule to generalise from (write-skew sits beside the "Reservation after suspension" smell, idempotency beside the retry/backoff check). Fixture: a Python checkout refactor moving `_reserve_inventory` outside the `with conn.transaction():` block, so a stockout leaves a committed pending order and charge with no reservation — a phantom sale — while the unchanged caller reports "rejected"; the docstring stating the atomicity invariant was trimmed rather than updated. All 5 reps caught it as **Likely disqualifier**, quoting the transaction boundary and the deleted docstring, tracing the consequence through the caller. Zero false positives. **The mechanism makes this a stronger negative than DD-02:** no rep reached for any lens line — the catch came from generic Evidence-Chain machinery (the mandatory doc-vs-code grep noticing the deleted docstring, plus consequence-tracing, plus the Severity Anchors' own worked example). Budget work above stands; it is now moot |
| **DD-05** | Authorization & ownership (Tier 1 #5) | `lens-generic.md`, **not** `lens-security.md` | generic | **2/3.** Sweep proposed `lens-security.md`; that is always-included, so it would charge every Apple client-only run for a domain inert on it. `lens-generic.md` gets the same reach for one ceiling. The importable part is procedural — reconstruct the house authz norm, flag the *deviating* handler — which is a Step-3 re-derivation shape, not a checklist  **PARKED ON CLASS EVIDENCE 2026-08-22, unmeasured.** Three candidates chosen to disagree (DD-02, DD-04, DD-08) all came back legible 5/5, so the prior for an unmeasured classic domain is poor — and here specifically, authorization is among the most heavily-reviewed domains in the corpus these models are trained on. Parked rather than measured to avoid buying the same answer a fourth time at ~500k tokens. **Reversible:** this is a prior, not a result; ask for the run and it gets one. |
| **DD-06** | Suppression & delivery-gate hygiene (Tier 2) | `scripts/audit_suppressions.py`, wired at Step-0 sub-step 6c | **none** | **SHIPPED 2026-08-21.** Landed as a detector rather than as a wired `tool_runner.py` entry — that registry runs *external* tools with typed outcomes, and this is a grep over the target, so it joins the `audit_*` family and reuses `audit_boundaries.py`'s filters the way `repo_map.py` already does. Three checks: blanket suppressions, lint/type baselines with suppressed-entry counts, and CI steps that run a checker then swallow the exit code. **The restraint split is the design:** a rule-*coded* suppression (`# noqa: F401` on a deliberate re-export) is disclosed under `counts` and never flagged; only *blanket* ones are hits. Dogfooded on this repo — 35 raw hits before the split, **0 after**, with 36 coded disclosed. `_audit_suppressions_selftest.py` guards all four load-bearing properties, mutation-verified (promoting coded hits, dropping the checker-word gate, and ignoring a prior-line rationale each fail the suite). Zero loop-path tokens, budget unchanged at 87,371/83,293 |
| **DD-07** | Public-contract back-compat (Tier 2) | `scripts/audit-public-surface.sh --since <rev>`, wired at 6c | **none** | **SHIPPED 2026-08-21.** Criterion 1 verified before building rather than assumed: the only back-compat prose in `references/` is `output-format-migrations.md` on the skill's *own* schema versions, and `method.md:85`'s API-surface audit asks whether a `public` decl is *over*-exposed, never whether one vanished. Implemented as a second mode on the existing script — no new file, no checkout, no worktree: a two-pass `awk` over `git diff -U0 <rev>` classifies a removed public declaration as `changed` when its name returns on an added line and `removed` when it does not. A shell read-loop over diff text was written first and replaced; it is fragile about leading dashes and IFS, and awk needs neither. `_audit_public_compat_selftest.py` covers removed, changed, the **restraint** case (an untouched `public var` must not appear), an unknown revision naming itself rather than guessing, and that the original enumeration mode still runs |
| **DD-08** | AI/LLM integration trust boundaries (Tier 2) | — | — | **2 FAILS — PARKED 2026-08-22, legible 5/5.** Chosen as the last candidate plausibly outside the reviewer's trained habits, and cut as narrowly as possible: **MCP tool metadata driving a security decision**, where `requires_confirmation()` keeps the same shape, same fail-safe default and same call site — only the *provenance* of the dict it reads changes, from a git-reviewed local policy file to a live MCP-server response. No removed guard, no deleted invariant sentence, no marker token for the doc-vs-code grep — deliberately engineered around the shapes that caught DD-02 and DD-04. All 5 reps caught it anyway as **Likely disqualifier**, naming the attacker action exactly (a compromised server self-reporting `requires_confirmation: false` on a destructive tool). **4/5 found a second unplanned defect** (server `description` text flowing unsanitised into the system prompt) and **2/5 a third** (silent same-name tool collision). Zero false positives. Mechanism was mostly **not** `lens-security.md`: 3/5 reasoned from `architecture-rubric.md`'s Dependency Categorization `true-external` table, 1/5 from MCP-spec knowledge outside every lens file, and the single rep that did touch `lens-security.md` stretched an existing deeplink bullet rather than needing anything DD-08 would add |
| **DD-09** | Git-forensic targeting signals (Tier 2) | — | **none** | **Not a standalone candidate — merged into row 24 slice D** (churn prior + escalate-on-hit). The sweep itself classifies it as a *selection* input rather than a judgment domain, `audit-churn.sh` and `audit_cochange.py` already run at Step 0, and slice D already owns "ordering reproducible from a fixed sha, measured against flat ordering". Tracking it twice would be the dual-listing this document forbids |
| **DD-10** | Enum / closed-set completeness (Tier 3) | `lens-generic.md` + `lens-apple.md` § Hidden State Machines | both (split) | **2/3.** One line in each Hidden-State-Machines section. The load-set asymmetry forces the split; there is no single-file home  **PARKED ON CLASS EVIDENCE 2026-08-22, unmeasured.** Three candidates chosen to disagree (DD-02, DD-04, DD-08) all came back legible 5/5, so the prior for an unmeasured classic domain is poor — and here specifically, enum/closed-set completeness is a mechanical class the hidden-state-machines sections already reason about. Parked rather than measured to avoid buying the same answer a fourth time at ~500k tokens. **Reversible:** this is a prior, not a result; ask for the run and it gets one. |
| **DD-11** | Unit & time correctness at the data type (Tier 3) | `lens-generic.md` | generic | **2/3.** Naive-vs-aware datetime, `TIMESTAMP` vs `TIMESTAMPTZ`, money-as-float. Largely inert on Apple targets, which is why it is generic-only  **PARKED ON CLASS EVIDENCE 2026-08-22, unmeasured.** Three candidates chosen to disagree (DD-02, DD-04, DD-08) all came back legible 5/5, so the prior for an unmeasured classic domain is poor — and here specifically, unit and time correctness is classic review material with well-known failure shapes. Parked rather than measured to avoid buying the same answer a fourth time at ~500k tokens. **Reversible:** this is a prior, not a result; ask for the run and it gets one. |
| **DD-12** | Comment rot + stale-ADR-as-finding (Tier 3) | `architecture-rubric.md` § CONTEXT.md / docs/adr Awareness | both | **1 CLEARED 2026-08-21, both halves, narrowed — 2/3 next.** (a) **ADR drift** narrows to business-rule ADRs whose violation carries no existing canon smell *and* whose code sits outside the leaf-module sweep's reach: `architecture-rubric.md:157` is purely **reactive** — disclose when the loop's own finding contradicts an ADR — and no step ever checks current source *against* recorded decisions. (b) **Comment rot** narrows to a comment's factual claim being wrong while carrying none of the ten marker tokens `method.md:85`'s mandatory doc-vs-code grep scans for. The contested overlaps were tested and did **not** hold: Meta-Rule 6 (`method.md:41`) and Fake-clean reward (`architecture-rubric.md:36`) are scoring *restraints* — "do not reward a tidy comment" — never verification directives obliging the Critic to check whether the comment is true, and `architecture-rubric-scoring.md:81` scores *naming* drift, not a stated business value being wrong  **PARKED ON CLASS EVIDENCE 2026-08-22, unmeasured.** Three candidates chosen to disagree (DD-02, DD-04, DD-08) all came back legible 5/5, so the prior for an unmeasured classic domain is poor — and here specifically, the mechanism that caught DD-04 *was* the mandatory doc-vs-code grep noticing a trimmed docstring — the exact machinery DD-12 proposes to extend. Parked rather than measured to avoid buying the same answer a fourth time at ~500k tokens. **Reversible:** this is a prior, not a result; ask for the run and it gets one. |
| **DD-13** | Per-domain "what not to flag" lists, with the positive owner named | `lens-generic.md` (+ `lens-apple.md` at `mid`) | 146 apple / 242 generic at `mid` | **5 MEASURED 2026-08-21 — narrowed, `mid` next; the bar inverts (criterion 4, not 2/3).** The sweep framed this as a missing mechanism. It is not missing: `architecture-rubric.md` already carries **7** structured `Carve-out (do not flag): … Maps to <dimension>` entries, `lens-efficiency.md`'s D1–D4 each state their own exclusion inline, and `lens-apple.md` carries owner-attached restraint qualifiers inline per check (`:32` *"`.indices` is acceptable for genuinely static content — not a blanket ban"*, `:34` *"Seeding a local editable draft from a passed value is legitimate; flag only on evidence…"*). The real gap is narrow: **`lens-generic.md` lacks carve-outs `lens-apple.md` already has**, and `lens-security.md` has none *by design* — a false negative there costs more than the restraint buys, so `mid` deliberately leaves it untouched. Scopes: `min` +186 generic (fits, likely too thin to move a measurement); **`mid` +146 apple / +242 generic (fits both)**; `full` +322 apple / +526 generic — **over generic by 119**, and several of its extra entries were flagged low-value independently of budget. Only **one** entry needs double-writing across both stack lenses, which is itself the argument that it belongs in the rubric's canon-smell list instead — half the cost, single write, established pattern |
| **DD-14** | Grep-the-defense-or-it-doesn't-exist | `method.md` Evidence Chain — one clause, **not** a new rule | both | **1 CLEARED 2026-08-21, conditional on the obligation call below.** Two overlaps were tested. (a) `method.md:30` "Do not infer architecture quality from naming alone" does **not** reach it: `architecture_quality` is a canon dimension id (`canon/scorecard-dimensions.toml`) distinct from `domain_modeling`, and `architecture-rubric-scoring.md:41` scopes it to Module/Seam/Adapter/costume-layer vocabulary — an unenforced size bound is a domain-invariant claim, not an architectural one. `architecture-rubric.md:3` ("Use these terms exactly") and G39's rejection of the display label `Architecture quality` in favour of the canon id both confirm the vocabulary is policed. (b) **Compliance is not clearance** is *not* HALT-only as the candidate first argued — it is a named rule at `method.md:82` (Step 3, every loop), re-passed at `method.md:85` and `trust-model.md:73`. But all four sites name an **enumerated project rule** as the trigger, never a bare constant: `method.md:82` sits inside the **Self-imposed-rule audit** (*"enumerate every project-local lint rule, boundary check, or doc-comment-enforced 'executors must not X' rule"*), and `trust-model.md:73` and `halt-verifier.md:126` repeat the `HR-X` / `HR-1` formulation verbatim. A reviewer who reads a constant name and moves on never forms a compliance claim at all, so the rule never engages. The two overlaps therefore fail on **different axes** — `:30` on dimension scope, `:82` on trigger object — and the candidate sits outside both simultaneously, which is a stronger position than either failing on the same axis. Conceded weakness: `domain_modeling`'s 9-anchor ("invariants enforced at construction… not by convention") describes the same failure class, though as a target-state anchor rather than a verification duty. Clause tightened to **42 tokens** (from 88) — 10.3% of the 407 headroom — and verified at that count. Two restraint fixtures drafted, including framework-delegated enforcement (`PHPickerConfiguration.selectionLimit`), which is the one that proves the clause does not license finding-fishing. **Predicted failure mode for the eventual 2/3 run, named by the candidate itself:** a Critic that has internalised *verify-before-crediting* twice across two files may generalise the habit to any claimed defense even though the letter does not require it — in which case the measured lift is zero, exactly as it was for the three levers in the calibration discipline above. That is the specific thing the run should be powered to detect |

**Adjudication pass, 2026-08-21.** The four cheapest-to-advance items were worked with no
measurement run: DD-04's budget was measured, and DD-01, DD-12, DD-14 were put to a worked-example
test of their contested criterion 1, each adversarially instructed that PARK was an acceptable
result. Outcomes are in the rows above. Two findings generalise beyond their own candidates:

- **Contested criterion 1 is worth spending on.** Every one of the three contested candidates came
  back *narrower* than the sweep framed it, and the narrowing was driven by lines the sweep's
  heading-level read had missed. DD-12's original framing — "the ADR awareness only suppresses" —
  survived only for business-rule ADRs outside the leaf-sweep's reach; the rest was already caught.
  Cheap to run, and it shrinks what any later measurement has to cover.
- **Obligation gaps are out of scope for criterion 1 — RESOLVED, and against the candidate that
  raised it.** Both DD-01 and DD-14 hit the same shape: a rule exists and would fire if pointed at
  the case, but its scope or quantifier lets a reviewer discharge it elsewhere. DD-14 sidestepped
  the question by clearing on narrowness instead. DD-01 met it head-on and argued **against its own
  candidate**: `method.md` is full of deliberately sampling-based checks — the Reading-discipline
  preamble trades exhaustive reading for cost control by design, and the Mutation-test model
  defends its own minimality in-line (*"not finding-fishing"*). If "the rule doesn't force the
  reviewer to check *this* site" counted as *"the lens cannot find it"*, nearly every sampling
  check in the method becomes an obligation-gap candidate, and criterion 1 turns from a token-cost
  gate into a piecemeal exhaustiveness mandate — the opposite of its purpose. **Criterion 1 stands
  as written.** Obligation gaps are not worthless, they are a *heavier* claim: they need paired-arm
  evidence that the cheap discharge actually happens at rate on real codebases, not one constructed
  example showing it can. Tracked as a standing lower-priority question, not as a criterion-1 route.

**Method note — verify the agent, not just the claim.** Every candidate above was checked against
source before being recorded, and two of the four reports had load-bearing citation defects that a
grep of their own key phrases exposed: one placed a rule in the HALT-only path when it is named at
`method.md:82` on every loop, and one never examined the sentence immediately preceding its own
proposed insertion point. Both survived on corrected reasoning, but neither would have if the
report had been taken at face value. Cheap check, high yield — the same *compliance is not
clearance* discipline the skill applies to its own targets, applied to its own research.

**Where the queue landed, 2026-08-22.** Of the nine candidates that entered the measurement queue,
**three were measured and all three failed criterion 2 at 5/5**; **five are parked on that class
evidence** rather than buying the same answer at ~500k tokens each; and **two (DD-13, DD-14) never
belonged in this queue** — they are restraint/assurance levers, so criterion 2's "does the control
find the seeded defect" question does not apply to them and **criterion 4** is their experiment.

The honest summary of the detection program to date: **the sweep found real reach gaps in the
*prose*, and measurement found none of them in the *reviewer*.** Every candidate that cleared a
textual blindness argument was nonetheless caught by the bare rubric, repeatedly, often by machinery
that has nothing to do with the domain in question. What did pay in this cycle was everything
*except* the lens additions — two shipped detectors at zero loop-path cost, 4,251 tok/loop returned
by a load-path split, and 22 vacuous assertions closed in the skill's own test suite.

**A by-product worth more than it cost: 15 reps, zero false positives.** Every one of the three
runs carried a deliberately clean change alongside the seeded defect — a `NumberFormatter` cache, a
receipts formatter, a session cache — and across **15 independent reps not one rep flagged any of
them**, each clearing them with correct reasoning rather than silence. That was collected free, as
control-arm hygiene, and it bears directly on **DD-13**: the register calls restraint *"the one axis
where added prose has measurably paid"*, but the bare rubric's restraint on clean code is already
15-for-15. The evidence is suggestive rather than decisive — a clean *surrounding* change is an
easier near-miss than a pattern that genuinely resembles the defect — so DD-13's experiment still
has to use real near-misses. But the same control-first logic applies: **if the control does not
over-flag, added restraint prose has no false positives to remove.**

**Reading the "next unmet criterion" column** (recounted after the 2026-08-21 adjudication pass).
Of fourteen candidates, **nine** now have the expensive measurement run as their genuine next step:
DD-02, DD-03, DD-05, DD-08, DD-10, DD-11, plus DD-12 and DD-14 which reached it by clearing a
contested criterion 1, plus DD-04, now at `mid` scope on an authorised ceiling. The other **five** never need one: DD-01 is
**parked**; DD-06 and DD-07 **shipped 2026-08-21** as detectors, their criterion 3 collapsing
because a deterministic detector's lift is 5/5 by construction; DD-13 inverts the bar toward restraint fixtures; and DD-09
is closed by merge into row 24.

Note the queue got *longer*, not shorter, and that is the pass working correctly. Resolving a
contested criterion 1 does not remove a candidate from the measurement queue — it either parks the
candidate outright (DD-01, one of four) or promotes it into the queue with a **narrower** claim to
test (DD-12, DD-14). The saving is not in the count but in the scope: each of the two promoted
candidates now names a specific, much smaller thing for a run to measure than the sweep's original
framing did, and one candidate was removed from consideration for the cost of a worked example
rather than a run.

## Shared-headroom contention

Criterion 5 is written per candidate, and every candidate has so far been sized on its own against
the live headroom. **The headroom is shared.** Eleven items still want loop-path prose and they all
draw on the same two numbers, so a set of individually-fitting candidates can collectively not fit.
Worked from the measured deltas (2026-08-21):

| State | apple | generic |
| --- | --- | --- |
| Baseline, nothing added | 87,371 / 87,800 — **429 left** | 83,293 / 83,700 — **407 left** |
| + DD-14 clause (42 tok, `method.md`, both paths) | 87,413 — **387 left** | 83,335 — **365 left** |
| + DD-04 `min` (301 tok, generic only) | 87,413 — 387 left | 83,636 — **64 left** |
| + DD-04 `mid` instead, on the authorised 84,200 ceiling | 87,413 — 387 left | 83,800 / 84,200 — **400 left** |

Three things fall out, none visible from any single candidate's row:

1. **DD-14 and DD-04 `min` do not comfortably coexist.** Each fits alone. Together they leave 64
   tokens on the generic path — below `SOFT_MARGIN` 150 (`token-budget.py:348`), so `--check`
   warns. Two candidates that each passed criterion 5 produce a warning when both land.
2. **The authorised +500 buys exactly DD-04 `mid` plus DD-14, and nothing else.** It lands the
   generic margin at 400 — the floor of criterion 5's own [400, 550) band, with nine candidates
   still queued behind it. The authorisation was sized against DD-04 alone, which was the right
   question at the time and is not the whole question now.
3. **A both-paths candidate is charged twice and shows up on the apple ceiling nobody is watching.**
   DD-14's 42 tokens take apple from 429 to 387. That breaks nothing — 387 is far above
   `SOFT_MARGIN` — but it is outside the [400, 550) band, and no apple-side ceiling decision exists
   because every budget conversation so far has been about the binding generic number.

**Adding DD-13 `mid` to the stack** (measured after this table was first written) tightens it
further without breaking it: generic 83,293 + 42 + 465 + 242 = **84,042** against the authorised
84,200, leaving **158** — barely above `SOFT_MARGIN` 150; apple 87,371 + 42 + 146 = **87,559**,
leaving **241**. So the three measured candidates fit together, and the next one to land after them
does not, on either path. That is the whole queue's budget, spent.

**The displacement answer, and why it changes the sequencing question.** Contention this tight
argues for buying headroom rather than rationing it. A loop-path inventory
([`DISPLACEMENT-2026-08-21.md`](../analysis/contest-refactor/DISPLACEMENT-2026-08-21.md)) found
**4,405 tok/loop** of pure file-role misclassification: `provider-adapters.md` is loaded whole at
Step 3 for two of its eleven sections, while `SKILL.md:78`'s own matrix already scopes the Step-3
need to *"(reviewer-spawn profile + read-only allow-list)"* — 882 tokens — and the other sections'
headings name the steps they belong to (`Detection` is *"read by SKILL.md Step -1"*). **Shipped 2026-08-21**: the
split took the generic margin from **407 to 4,658** and apple from 429 to **4,680** — a measured
4,251 tok/loop on both paths — which clears every candidate on this page, measured or not, without
spending the authorised ceiling bump at all. The **shared-headroom contention above is therefore
resolved**, not rationed: the table's arithmetic stands as the record of why it mattered. A second candidate (v5 panel material,
2,634 tok) is held as an owner call because the capability is dormant rather than absent. The
biggest-looking win — the HALT-terminal judgment gates — was **rejected**: none has a script
backstop, and G21 exists because of a documented production failure.

**Consequence for sequencing.** Criterion 5 should be re-checked against the *then-current* headroom
at promotion time, not treated as passed once. The measured delta is a durable fact; the fit is not.
A candidate that cleared criterion 5 months earlier has to clear it again behind whatever landed in
between — which is the same rule the coverage ledger applies to a stale file, for the same reason.

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
