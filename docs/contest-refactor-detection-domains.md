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
- [Current coverage baseline](#current-coverage-baseline)
- [Competitor domain sweep — 2026-08-21](#competitor-domain-sweep--2026-08-21)
- [Corroborated backlog items](#corroborated-backlog-items)
- [Open detection backlog](#open-detection-backlog)
- [Parked and adjudicated detection levers](#parked-and-adjudicated-detection-levers)
- [Cross-references into the review register](#cross-references-into-the-review-register)

## Calibration discipline — read before adding any domain

The single most important fact in this document, and the reason it is not simply a wish list:

> **Added checklist prose has repeatedly produced a measured recall lift of zero.**

Three independent measurements say so. The advisory eval program (#35–#48) established that those
evals measure *restraint and vocabulary, not recall* — recall lift was 0 on both Sonnet and Haiku
because the seeded defects were too legible for the bare rubric to miss. The parked W3.2 domain lens
measured a recall lift of 0 against a bare rubric that scored 6/6. And the June research doc's
domain-integrity lens was parked on the same result. The Critic is already strong; the marginal
checklist line is usually paying for nothing.

Consequences for everything below:

1. **A domain earns its place only if the current lens could not find the defect *in principle*** —
   not merely "does not name it." Naming a defect the rubric already catches is pure token cost.
2. **RED fixtures must be drawn from the illegible end of the class.** A defect a bare rubric finds
   6/6 cannot demonstrate a lift no matter how many reps are run.
3. **Micro-test against a no-guidance control before shipping** — 5+ reps, read the matches, per the
   standing rule that static audits over-rate severity. Harness at `peer-plan-review/evals/`.
4. **Restraint is the axis where added prose has actually paid.** Negative rules ("what not to flag")
   have measurable value where positive rules do not; see the method note at the end of the sweep.

## Current coverage baseline

Verified against the lens and rubric files at HEAD on 2026-08-21.

| Domain | Where |
| --- | --- |
| Architecture vocabulary, 19-item smell list, 5 architectural tests (deletion, two-adapter, shallow module, interface-is-test-surface, replace-don't-layer), Unified Seam Policy, dependency categorization, severity/score anchors | `references/architecture-rubric.md`, `architecture-rubric-scoring.md` |
| Ownership & state, hidden state machines, concurrency/runtime safety per language, coupling & leakage, regression resistance, incremental test scoping | `references/lens-generic.md`, `lens-apple.md` |
| Failure modes & observability — silent-swallow audit (per-language grep targets), retry/backoff policy, error-context preservation, adapter-boundary telemetry, panic-recovery on executors | `references/lens-generic.md` § Failure modes |
| Security — input validation & deeplinks, secrets, PII in logs, keychain, biometrics, transport, dependency hygiene, plus stack-agnostic SQL/command injection, path traversal, WebView XSS, insecure deserialization | `references/lens-security.md` (always-included) |
| Efficiency D1–D4 — recomputed derived values, sequential independent effects, hot-path/startup blocking, closure-capture retention | `references/lens-efficiency.md` (always-included) |
| Apple-specific — SwiftUI discipline, continuation-bridge audit, feature-flow choreography, sheet/binding symmetry, accessibility audit, cross-platform compile correctness, Authority-Map test-surface cross-check | `references/lens-apple.md` |

**Deliberately out of scope** (rubric's `Ignore:` line): stylistic concerns, naming nits,
micro-optimizations distinct from structural waste, generic filler, unsupported speculation.

## Competitor domain sweep — 2026-08-21

**Method.** Four parallel survey agents over all 51 repos in `refs/competitors/contest-refactor`
(49) and `refs/competitors/shared` (2), each asked for review domains *absent* from the baseline
above. Findings were filtered by the "blind in principle" test in the calibration section, then
ranked by cross-batch corroboration. All exemplar paths below were spot-verified to exist on
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
  today have one global `Ignore:` line. This is the cheapest candidate on the board *and* it targets
  restraint — the one axis where added prose has measured value.
- **Severity × confidence as independent axes with an asymmetric floor** — suppress below a
  confidence bar *except* the highest-severity class, which must never be silently dropped.
  `tech-audit-skill/tech-audit/templates/finding-phrasing.md`; `ngmeyer-skills/.../scoring-gating-validation.md`
- **Reproducer-based false-positive withdrawal** — a finding whose reproducer *passes* on the
  original code is withdrawn, and "a confident trace is never a reason to skip it."
  `logic-lens/skills/logic-review/SKILL.md` (Execution Verification Gate)
- **Grep-the-defense-or-it-doesn't-exist** — "if you cannot point to the line that enforces the
  defense, it does not exist; a constant name is not a verified bound."
  `great_cto/skills/skeptical-triage/SKILL.md`
- **Externalized precedents file for the false-positive filter** — hard-exclusions and precedents as
  user-supplied files so an org tunes them without forking the prompt.
  `anthropic-security-review/.claude/commands/security-review.md`

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
| 23 | Detection-lens expansion (latent-premises, retry-safety, operational) | Decompose per lens. The 2026-08-21 sweep supersedes the *shortlist* — Tier 1 above is the evidence-ranked replacement — but the decompose-per-lens instruction stands |
| 24 | Deterministic selection + coverage manifest + resumable scan | **Design done** ([`ITEM24-COVERAGE-UNIT-DESIGN-2026-08-19.md`](../analysis/contest-refactor/ITEM24-COVERAGE-UNIT-DESIGN-2026-08-19.md)), unbuilt. The 2026-08-21 coverage analyzer measured 302/1313 files cited across all historical BenchHype loops (BenchHypeKit 24%) — uneven-coverage proof for this item |
| 25 | Tool-grounded substrate + per-language rules | **Unblocked, design done** ([`ITEM25-TOOL-SUBSTRATE-2026-08-19.md`](../analysis/contest-refactor/ITEM25-TOOL-SUBSTRATE-2026-08-19.md)), unbuilt |
| 27 | Per-finding disproof pipeline | Gated on the finding-assurance decision |

**Sweep candidates not yet promoted to rows** — Tier 1 items 1–5, Tier 2's four, and Tier 3's three
above. None has a RED fixture or a micro-test yet; none should ship without one.

## Parked and adjudicated detection levers

Recorded so they read as decisions rather than omissions, and are not re-litigated:

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
