# Review-Skill Deep Dive — 2026-08-17

Deep dive into six external review/audit skills, compared against `contest-refactor`,
`peer-plan-review`, and `quorum-review`, to produce a comprehensive improvement plan.

Sources: four repos cloned today plus two already in the corpus (`brooks-lint`, `logic-lens`)
that were ranked highest by the survey that prompted this work, extended by second and third
passes over the wider held corpus, a fourth pass over a ten-repo expansion, and a fifth pass
over the nine-repo second wave — all cloned the same day, all SHA-pinned in the source inventory
below.

## Evidence discipline

Every claim below is marked:

- **VERIFIED** — read in the upstream source, or checked against our source, at the SHA given.
- **INFERRED** — read once, not cross-checked; treat as a lead.

Claims about *our* implementation were checked by grep/read against the working tree at
`984aa5b`. Where our coverage was confirmed, it says so — several apparent gaps turned out to be
already built, and those are recorded as "no action" rather than dropped.

**What this document is.** A gap analysis and a ranked backlog, not an execution plan.
Statuses read: **Design-ready** = mechanism verified upstream, the design note is the next
deliverable and the gate; **Experiment** = a preregistered protocol precedes any build;
**RFC** = argument before design; **Decompose** = must be sliced before design notes exist; remaining Status-column labels (e.g.
"After items 1, 3, 18", "Delta-audit first") are dependency qualifiers on these four categories,
not additional statuses. None of these statuses means implementation-ready — artifacts, schema changes, acceptance tests, migration, and rollback are
specified nowhere in this document. Every item still gets a
short design note (those five things plus the success metric it will be judged by) before code;
the tranche structure at the end of the plan section states the dependency order; tranche
selection is the owner's call.

### Source inventory

The six primary repos are SHA-pinned in the clone table below. The second and third passes
additionally rely on these already-held clones (all under `refs/competitors/`, refreshed
2026-08-17):

| Repo | SHA | Used for |
|---|---|---|
| `great_cto` | `e6003b03` | Gaps 8, 10, 11, 12 (judge alignment, `pipeline.toml`, DAG grading) |
| `gstack` | `c86e6472` | Gaps 13, 16; context-bill and wtree comparisons |
| `continuous-claude-v3` | `d07ff4b0` | Gap 14 (auto-handoff-stop); second-pass no-action table |
| `trailofbits-skills` | `04b24117` | Gap 9 (grader non-scope contract) |
| `wshobson-agents` | `d6837ae2` | Gap 8 (PluginEval Cohen's kappa); CI-on-eval-results |
| `pauhu-claude-codex-review` | `78022325` | Gap 3 (`.codexignore` pre-dispatch scrub) |

The fourth pass audits the ten repos cloned 2026-08-17 after the third pass:

| Repo | SHA | Used for |
|---|---|---|
| `shared/anthropic-skills` | `f379e5ad` | Official grader/comparator/analyzer contracts; authoring conventions; Gaps 17, 20 |
| `compound-engineering-plugin` | `dec2598e` | Items 6, 11, 14, 15; Gap 18 (A/A floor); accretion-stop; receipts |
| `ce-reviewers` | `3367e288` | Persona ownership boundaries (stale vs the plugin — see hygiene note) |
| `crucible` | `2be110b5` | Gaps 17, 18, 19; items 2, 8, 16; judge-demotion tension |
| `harness-eval` | `88146404` | Judge hygiene (blind, pinned, 3-sample); Gap 19; the `7,0,8` outlier |
| `dsh-skill-eval` | `8288582b` | Item 2 fidelity pin; item 4 hard-negative trigger set |
| `skilllens` | `ce8fcb89` | Gap 20 (paired delta + tautological-item rule); Gap 19 manipulation check |
| `planning-with-files` | `9b7d0a00` | Items 14, 16, 17, 18; attestation; test-must-exec-shipped-artifact |
| `agent-verifier` | `23d73ad3` | Rule-level `[P]`/`[H]` confidence alternative; escape-hatch tables |
| `code-quality-atlas` | `d4ec723d` | D18 no-scalar tension; floor plateau; provenance hashes; literal-string result |

The fifth pass audits the nine-repo second wave, cloned 2026-08-17:

| Repo | SHA | Used for |
|---|---|---|
| `alibaba-open-code-review` | `533f7367` | Gaps 22, 24, 25; the review-filter prompt; coverage manifest; benchmark caveat |
| `opendatahub-agent-eval-harness` | `db0732c3` | Items 19-22 validation (order-bias control + adjacent pairwise machinery); tranche-3 imports |
| `aws-agent-skill-eval` | `13b2277b` | Item 22's in-the-wild violation; static safety scanner (item 29); deterministic-first grading |
| `center-audit` | `b154fb0e` | Gap 24 (evidence grades, trajectory arithmetic); Gap 26 (repair contract); cascade lenses |
| `tech-audit-skill` | `41869d17` | Gap 22 (escalate-on-hit, churn prior); Gap 26 (essentiality ladder); treatment tags |
| `sentry-skills` | `24fdb833` | Gap 21/25 (admission checklists, research-vs-report scope); dangling-route caveat |
| `skillet` | `5b2a7efb` | Gap 21 (latent-premises, retry-safety); Gap 26 (leverage sort, dispositions) |
| `conorbronsdon-agent-skills` | `9e5276b5` | Gap 21 (operational, reference-comparison lenses); enforcement-tier rating |
| `cloudflare-security-audit` | `8bac4200` | Gap 21 (anti-taxonomy agents, multi-run recall); Gap 25 (three-pass pipeline) |

A named mechanism at a pinned SHA is evidence the mechanism **exists**, not evidence it is
**effective**. Effectiveness claims here rest only on the sources' own recorded measurements
(e.g. great_cto's kappa numbers), and adopting any mechanism still requires our own RED-first
measurement per standing practice.

---

## What was cloned, skipped, and not found

| Repo | Status | Notes |
|---|---|---|
| `shadcn/improve` | **cloned** → `contest-refactor/shadcn-improve` (`03369ee`) | 8.9k★, MIT. Biggest by stars in the whole corpus. |
| `bjgreenberg/senior-engineering-partner` | **cloned** → `contest-refactor/senior-engineering-partner` (`6c3eb93`) | 146★, Apache-2.0. |
| `ngmeyer/skills` (`rigorous-review`) | **cloned** → `contest-refactor/ngmeyer-skills` (`701dfb8`) | 2★, MIT. 10 skills; `rigorous-review` is the one of interest. |
| `mhylle/claude-skills-collection` | **cloned** → `contest-refactor/mhylle-skills-collection` (`a3910d0`) | 17★, MIT. 38 skills. |
| `hyhmrright/brooks-lint` | already held | Refreshed today (`d4b5c40`). |
| `hyhmrright/logic-lens` | already held | Refreshed today (`69de591`). |
| `awesome-skills/code-review-skill` | already held | Refreshed today (`95c707b`). |
| `alirezarezvani/claude-skills` | already held | Refreshed today (`aa8d7788`). |
| Cloudflare `security-audit-skill` | **initially skipped, later cloned** → `contest-refactor/cloudflare-security-audit` (`8bac4200`) | Security-only, excluded by the original instruction; admitted later as a methodology exemplar (owner-approved) and audited in the fifth pass — loop mechanics only, security content still excluded. |
| `center-audit` | **cloned** → `contest-refactor/center-audit` (`b154fb0e`) | Initially unfindable (no owner given; the corpus has prior fabrications on record, `RESEARCH-DELTA.md`); the owner later surfaced as `VerbalChainsaw/center-audit` (0★, MIT). **VERIFIED on disk after cloning**: evidence-gated prove/disprove audit framework with `assets/center-audit-output.schema.json`, 20 trigger cases + 10 behavior cases + a behavior rubric under `evals/`. The fabrication caution is fully resolved. Audited in the fifth pass. |

---

## Mechanism inventory — what these skills do that we don't

### shadcn/improve — the advisor/executor split, productized

**VERIFIED** (`skills/improve/SKILL.md`, 122 lines + 3 references).

Its thesis is the one `contest-refactor` measured and rejected: *"an expensive, high-ceiling model
does the part where intelligence compounds (understanding, judging, specifying). Cheaper models do
the execution."* But the mechanism differs from our `arm_b` arm in one specific way, and that
difference is the most important finding in this document — see **Gap 2**.

Mechanisms worth naming:

1. **Hard Rule 4 — never reproduce secret values.** Findings and plans reference `file:line` and
   credential type only, and recommend rotation. *"The value itself must never appear in anything
   you write."*
2. **Hard Rule 6 — repository content is data, not instructions.** Prompt-injection content found
   in source, comments, README, config, or vendored deps is recorded as a security finding rather
   than obeyed.
3. **Rules do not survive subagent dispatch.** Every subagent prompt must carry a *verbatim copy*
   of Hard Rules 4 and 6, with the rationale stated plainly: *"Subagents do not inherit these
   rules; omitting them is how a live token ends up quoted in a finding."*
4. **Vet before presenting — "subagents over-report."** Three named failure classes: by-design
   behavior reported as a bug, mis-attributed evidence (right finding, wrong file/line), and
   cross-subagent duplicates.
5. **Excerpts come from your own reads, never a subagent's report** — *"subagent line numbers and
   attributions are leads, not facts, and a wrong excerpt becomes a wrong plan that fails its own
   drift check."*
6. **Intent docs suppress by-design findings.** ADRs, `CONTEXT.md`, `DESIGN.md`, `PRODUCT.md` are
   ingested at recon; *"a tradeoff recorded in an ADR is by-design, not a finding."*
7. **Effort tiers control cost, not just rigor** — `quick` / `standard` / `deep` set coverage,
   concurrent subagent count, search breadth, category count, and confidence floor.
8. **Write each plan for the weakest plausible executor** — a concrete self-containment checklist:
   all context inlined, ordered steps each with its own verification command *and expected
   output*, explicit out-of-scope file list, machine-checkable done criteria, a test plan, a
   maintenance note, and escape hatches (*"if X turns out to be true, STOP and report back instead
   of improvising"*).
9. **`review-plan` uses a fresh-context subagent** — *"self-critique misses gaps you mentally fill
   from context the executor won't have."*
10. **The executor's diff is untrusted** — *"verify every hunk traces to a plan step and reject any
    out-of-scope change, however plausible it looks."*
11. **Disclosure control** — before `gh issue create`, check whether the repo is public and get
    explicit confirmation before publishing anything describing a vulnerability or credential
    location.

### ngmeyer/rigorous-review — severity × confidence as independent axes

**VERIFIED** (`skills/engineering/rigorous-review/SKILL.md` 255 lines + 3 references + tests).

1. **Two independent axes.** Severity = impact if real (P0–P3). Confidence = how sure it's real
   (0/25/50/75/100). *"A SQL injection you can only half-prove is P0 × 50"* — not a P2. Collapsing
   uncertainty into severity is named as the failure mode.
2. **Confidence anchors are behaviors performed, not vibes.** 100 = traced the full path, no
   plausible guard. 75 = named a concrete observable consequence and traced the path, one branch
   unconfirmed. 50 = verified narrowly, or depends on a runtime condition you can't see. 25/0 =
   pattern-matched — *suppress silently, don't even emit*.
3. **The gate, with a carve-out.** Suppress below confidence 75 — **except a P0 at ≥50 survives**,
   because *"critical-but-uncertain must never be silently dropped"*; it routes to the validator
   wave instead.
4. **Per-lane asymmetric bars.** Security gets a *lower* bar (cost of a miss dominates);
   performance a *higher* one (a false perf finding wastes engineering time on optimization that
   wasn't needed).
5. **`safe` vs `gated` classification** protects a stated behavior-preservation guarantee, with the
   sharp nuance that *authorization fixes are `safe`* — rejecting an unauthorized caller is the
   intent, not a regression.
6. **Independent validator wave, not self-recheck**, plus a test asserting *the superseded V1
   self-recheck phrasing did not survive* — a regression test that retired prose stays retired.
7. **Honest eval scope.** `tests/README.md` states plainly that the harness asserts the *design
   contract* and does **not** measure precision/recall, validator effectiveness, confidence
   calibration, or behavior preservation, and that doing so needs seeded fixture repos.

### bjgreenberg/senior-engineering-partner — evals as a merge gate

**VERIFIED** (`evals/README.md`, `scripts/`, 61 scenarios, model-dated baselines).

1. **`eval-guard` CI check.** *"Fails any PR that makes a substantive SKILL.md change without
   touching `evals/scenarios/`"* — with an explicit `Eval-waiver: <reason>` line in the PR body as
   the documented escape, and metadata-only diffs auto-passing. The gate is itself fixture-tested.
2. **Every scenario encodes a real miss**, most drawn from the changelog: *"the changelog was the
   spec; these are the tests."*
3. **`anti_behavior` field** — a local extension to Anthropic's scenario shape listing what the
   response must **not** do, making "never do this again" explicit rather than implied.
4. **Baselines are per-model and dated** — `2026-07-04-fable`, `2026-07-04-haiku`, `2026-07-01-opus`.
5. **`leakage-guard.sh` + a denylist template** — a standing secret-leak check in the toolchain.
6. Author states the full discipline is ~80 KB and that adherence varies — an honest ceiling.

### brooks-lint — a frozen corpus that grades deterministically

**VERIFIED** (`evals/benchmark-corpus.json`, `scripts/validate-repo.mjs`).

1. **Two suites, explicitly separated.** 57 model-quality scenarios (`evals.json`) *and* a frozen
   30-report corpus for deterministic parser/severity fidelity — with the non-claim stated in the
   artifact itself: *"NOT a model-quality benchmark — that is evals/evals.json."*
2. **9 of the 30 frozen samples are false-positive/tradeoff cases that must stay clean.**
3. **Strictness presets carry expected finding counts** — `strict` 34, `balanced` 54,
   `legacy-friendly` 74, each with a `leadsWithTopFixes` flag. Because the corpus is frozen model
   output and only the parser re-runs, a change that silently makes a preset noisier or quieter
   fails a deterministic test with no model in the loop.
4. **False-positive guidance is structurally required.** `validate-repo.mjs` fails the build unless
   `decay-risks.md` and `test-decay-risks.md` each contain a `### What Not to Flag` section.
5. **Guide-step continuity is validated** — steps must be present, unique, numerically contiguous,
   *and at the right heading level*. The code carries a comment recording why the last clause
   exists: a `## Step 7` at the wrong level was invisible to the label extractor, so the continuity
   check silently skipped it. Their own fail-open bug, fixed and documented.
6. **Platform documentation evenness is derived from disk**, so a harness documented in one place
   and forgotten in another fails validation rather than shipping silently.

### logic-lens — per-phase lazy loading

**VERIFIED** (`skills/logic-review/SKILL.md:61-64`), same author as brooks-lint.

Loading rules are stated per phase, not per skill: read the shared `common.md` only for the named
concerns, read *only the relevant guide step as you reach it*, and load the risk/checklist/template
references only at the phase that needs them. Evals are split by purpose into `trigger` (does the
skill fire), `content`, and `real-world`, with frozen benchmark runs under `benchmarks/`.

### mhylle/codebase-audit — partitioned traversal with resume

**VERIFIED** (`skills/codebase-audit/SKILL.md`, 224 lines).

Partition plan (monorepo workspaces → top-level `src` dirs) proposed to the user and **stopped for
approval**, then per-partition reports, with `--resume`, `--only <partition>`, and `--force`. As
the survey noted, it leans on Claude-specific task primitives, so the *implementation* is not
portable — but the partition/resume model is.

---

## Gap analysis against our implementation

### Gap 1 — No confidence axis (contest-refactor) · **VERIFIED gap**

We score severity against `canon/severity-anchors.toml`. There is no independent confidence
dimension: grep for `confidence` across `canon/*.toml`, `references/method*.md`, and
`references/validation.md` returns only incidental prose (`method-critic.md:11` — "not confidence
of completion").

Consequence: an uncertain-but-severe finding has nowhere to go except into severity, so it either
gets inflated (noise) or demoted (a miss). rigorous-review's carve-out — *P0 at confidence ≥50
survives the gate and routes to the validator* — is precisely the case our current model cannot
express.

`severity-anchors.toml` already establishes the pattern; a `confidence-anchors.toml` with the
four behavioral anchors, a field on the finding, and a gate that suppresses below the bar *except*
for high-severity-low-confidence findings — routed to a dedicated per-finding validator, **not**
the HALT_SUCCESS challenger, whose contract validates a terminal state — would land in the
existing shape, at moderate rather than small cost. That shape is now one *candidate* rather
than the design: the fourth pass surfaced three shipped confidence models (finding-level
anchors, rule-level `[P]`/`[H]` tiers, binary burden-of-proof with a separate
executor-uncertainty channel), so item 6 is a two-stage experiment — first establish that the
Evidence Chain actually loses information, then compare the three designs on the same labelled
findings. Only the winner touches schema, canon, or gates.

**Interaction to check first**: our Evidence Chain already demands Claim → Source → Consequence →
Remedy, which forces some of what confidence-75 asks for. The honest question is whether confidence
adds a distinction the Evidence Chain cannot already carry — and that decision should be a labelled
comparison, not a discussion: collect real findings, label which ones the Evidence Chain
mis-represents, and build only if the mis-represented set clears a preregistered prevalence or
decision-impact threshold — a single exotic counter-example does not justify a schema axis.

### Gap 2 — Our cheaper-executor rejection may have tested the wrong variable · **VERIFIED, high value**

The `arm_b` measurement (2026-06-28) put `claude-haiku-4-5` in the executor seat and rejected it:
safe on mechanical revert, unsafe on risk-boundary judgment. `Execution-unfuse` has been BLOCKED
since.

`shadcn/improve` ships that same split to 8.9k stars — but the handoff artifact is a completely
different object. Ours is a backlog item; theirs is a plan document written *"for the weakest
plausible executor"* with all context inlined, per-step verification commands and expected output,
an explicit out-of-scope file list, machine-checkable done criteria, and escape hatches instructing
the executor to stop rather than improvise.

**So the rejected arm confounded two variables: executor capability and handoff specification.** A
cheap executor failing on risk-boundary judgment is exactly what an escape hatch (*"if X turns out
to be true, STOP and report back"*) is designed to catch, and our arm had none.

This does not overturn the rejection — it identifies that the experiment cannot distinguish "cheap
models can't do this" from "our backlog under-specifies the job." Re-running `arm_b` with a
self-containment contract on the handoff is a genuinely new measurement, and it is the only item
here that could unblock a decision we have parked.

Two cautions before that run. First, 8.9k stars is popularity, not validation — shadcn's split
shipping widely says nothing about whether it is *safe*. Second, escape hatches can convert unsafe
execution into safe refusal without improving completion, so the protocol must score safety and
completion as separate, preregistered metrics — a safe stop is not a success — on a matched task
corpus, with fixed model versions, repeated trials, and the accept/reject decision rule written
down before the first run. And the design correction from the second review: re-running only the
cheap-executor arm with a richer handoff tests a new configuration — it cannot separate executor
capability from handoff quality from model drift. The experiment is a contemporaneous **2×2
factorial** — {weaker, stronger executor} × {backlog, self-contained handoff} — on one
randomized task corpus, with safety, completion, refusal, escalation, and cost as separate
outcomes and the interaction term (or its decision rule) preregistered as the thing that
unblocks `Execution-unfuse`.

### Gap 3 — Evidence quotes can persist secrets into committed artifacts · **VERIFIED gap, security class**

`lens-security.md` covers secrets as a *review topic*, and `project-config.md` refuses config
entries that look like API keys. Nothing governs what the Critic may **quote**.

A finding whose evidence quotes a hardcoded credential writes that value into `CURRENT_REVIEW.md`,
`CURRENT_REVIEW.json`, and then the `REVIEW_HISTORY` archive — which we commit. A transient chat
leak becomes a permanent repository leak, and the rotation advice arrives in the same commit that
republishes the secret.

Three independent sources in this batch converged on the same rule, which is unusual enough to be
worth weighting: shadcn Hard Rule 4 (never reproduce the value), pauhu's `.codexignore`
pre-dispatch scrub, and senior-engineering-partner's `leakage-guard.sh` + denylist.

The fix is mechanizable: an evidence-redaction clause (cite `file:line` + credential
*type*, never the value) plus a gate that pattern-scans emitted artifacts for common credential
shapes — `project-config.md:88` already carries a usable pattern list (`AKIA`, `sk-`, `xoxb-`).

Two scope notes from review. There is no trusted serializer mediating artifact writes today —
the model writes the files — so nothing can mechanically promise redact-*before*-write. The honest
architecture is layered: the redaction **rule** is the preventive control, and the scanner gate is
a post-write, pre-commit quarantine over every persistence sink (`CURRENT_REVIEW.md`,
`CURRENT_REVIEW.json`, the `REVIEW_HISTORY` archive, `findings_registry.json`, any event or log
file) — on a hit it blocks the commit and quarantines the artifact (non-destructive and
fail-closed; the design note picks the exact mechanics, and neither scanner output nor quarantine
metadata may contain the matched value), and its own diagnostics must never reproduce a match; a
scanner that prints what it found re-leaks it. Fixtures include a
direct write that bypasses the normal archive path, and the scanner's false-positive rate is
tracked. And the rule is forward-looking only: shipping it does nothing for values already
persisted, so item 1 also carries a one-time confidential audit of existing committed artifacts
and history, with rotation advice for anything found — run as a separately tracked
incident-response task, *alongside* the gate, so its duration, findings, or authorization needs
never delay prevention of new persistence. History rewriting, if ever warranted, is a separate,
explicitly-authorized decision. The fixture corpus
needs positive, negative, and transformed cases — the supported transformations named exactly
(base64-encoded and simple string-concatenation splits; nothing beyond them is implied) — all
using fake credentials.

### Gap 4 — A skill edit can ship without an eval · **VERIFIED gap, governance**

Our repo has strong artifact gates (43 of them) and a pre-commit hook running `sync_common`, module
size, and ruff. Nothing requires that a change to a skill's *prose* ship a guarding eval.

Our own standing discipline says prose changes must be micro-tested against a no-guidance control
before shipping, and that static audits over-rate severity. That discipline currently lives in
memory and habit. senior-engineering-partner's `eval-guard` is the same rule as machinery: a
substantive `SKILL.md` diff with no `evals/scenarios/` change fails CI unless the PR body carries
`Eval-waiver: <reason>`.

Adapting it to this repo (pre-commit hook rather than PR gate, since we commit straight to main)
would make the discipline enforceable rather than remembered. The waiver escape matters — without
it the gate becomes a nuisance and gets bypassed wholesale.

A local hook alone is advisory — `--no-verify` skips it — and because this repo commits straight
to main, CI is detection *after landing*, not prevention: an unevaluated change is already on main
when the check fires. The honest contract is three parts: pre-commit catches the common path, CI
(where `sync_common --check` already runs) detects bypass, and a red eval-guard check triggers a
defined containment step — revert, or an immediate eval/waiver follow-up commit — before the next
skill sync or distribution. The gate
needs a mechanical definition of "substantive" (the diff reaches outside frontmatter and
formatting), a machine-readable waiver (a commit trailer, not free prose — validated where it can
be seen: pre-commit only sees the staged diff, so the trailer check runs from a `commit-msg` hook
and again in CI via one shared checker), rename and deletion handling, fixture-tested exit codes,
and a report-only introduction period before it blocks.

### Gap 5 — Flag/restraint pairing is convention, not machinery · **VERIFIED gap, small**

`evals/README.md` documents the flag/restraint pairs well — every "should reject" has a legitimate
look-alike that must not be flagged, with the carve-out under test named per pair. But
`validate-fixtures.py` does not enforce the pairing: grep finds the discipline only in the README.

brooks-lint takes the stronger position in two places — `validate-repo.mjs` fails the build if the
risk references lack a `### What Not to Flag` section, and 9 of its 30 frozen samples are
false-positive cases that must stay clean.

Enforcing "every flag fixture names its restraint twin" in `validate-fixtures.py` is a small change
that protects a property we already believe in. It needs a concrete pair contract, not a
name-matching heuristic: explicit pair identifiers in `fixture.toml`, uniqueness, and a declared
exception list for the few fixtures with no meaningful twin.

### Gap 6 — Hard rules may not survive challenger dispatch · **INFERRED, needs a check**

We have G14 (payload not instruction). `halt-verifier.md` dispatches challengers through the
provider-adapters spawn profile. shadcn's warning is specific: subagents do not inherit the parent's
hard rules, and omitting them is how a live token ends up quoted.

**Action is to verify, not to build**: read the challenger prompt and confirm it carries
payload-not-instruction (and, once Gap 3 lands, the redaction rule) verbatim. If it does, no change.
The check generalizes, though: the challenger is one dispatch boundary of several — inventory every
subagent/provider spawn, and prefer generating the hard-rule block from one canonical source over
hand-maintained verbatim copies, which drift.

### Gap 7 — Strictness is model-applied, so it cannot be regression-tested · **VERIFIED, larger change**

`--strictness standard|aggressive` modulates model judgment, so its drift is only observable by
running a model and reading output — the expensive, high-variance path our own notes describe.

brooks-lint separates the two concerns: the model produces a report, and a deterministic parser
applies the strictness preset, with expected finding counts per preset pinned in a frozen corpus
(strict 34 / balanced 54 / legacy-friendly 74). Preset drift then fails a test with no model in the
loop.

This is architecturally larger than the other items — it means treating strictness as a
deterministic post-filter over a superset of findings rather than as an instruction. Recorded as an
RFC with an honest cost, not a recommendation — and with one more honesty note: pinned counts
measure parser and preset *stability*, not review quality, so the RFC would need precision and
restraint fixtures plus periodic end-to-end model sampling alongside the frozen counts, and its
interaction with a confidence axis (item 6) resolved first.

### Gap 8 — No grader-alignment measurement anywhere in the eval suite · **VERIFIED gap, high value**

Second-pass finding. `great_cto` carries 440 scripts, 47 hooks, 114 eval files and 9 TOML canon
files, and appears **twice** in our entire 35-doc analysis corpus. The thing we missed is in
`tests/eval/judge-alignment/`:

> An unaligned judge is a random number generator with good grammar. Measure its agreement with
> hand labels before trusting a single verdict.

They caught their grader producing four verdicts of the same shape — *"correctly identifies that
arithmetic is objective while inputs are not, but fails to demonstrate this → FAIL"*. In each, the
judge states the answer is right and marks it wrong: the response satisfied the criterion in
substance and failed on **wording or placement**. Measured result: 20 hand-labelled cases,
agreement 45%, **kappa 0.00** — 11 of 20 verdicts that had driven prompt edits that day were false
failures.

Three rules follow, and all three transfer:

1. **"A criterion describes what the answer must ESTABLISH, never the words it must use."** When a
   verdict turns on phrasing, the defect is in the criterion or the judge — fix one, record which.
2. **Enrich for disagreement when diagnosing.** *"Two graders agreeing on an easy case says
   nothing about either"* — but a disagreement-only set understates real agreement, so it
   diagnoses failure shapes; the headline number comes from a representative set (below).
3. **The routing rule** — *"a verdict whose reason contains 'correctly identifies… but does not
   name' is a judge finding, not an agent finding. Route it here rather than into a prompt edit."*

Rule 3 is the operationally important one, because the failure it prevents is self-concealing: a
false failure invites softening the criterion, *"which is how a suite quietly stops measuring"* —
they record it happening three times in one session before anyone named it.

`wshobson-agents` corroborates the agreement-measurement machinery independently: PluginEval
reports **Cohen's kappa** across judges when `judges > 1` — though cross-judge kappa measures
reliability *between judges*, not alignment with human correctness. Two independent
implementations of agreement measurement in the corpus; neither appears in any of our 22 gap docs.

**Our exposure is real but narrower than theirs.** Layers 2/3 grade semantically via a `grader.md`
subagent, and `evals/README.md:154` states the measured axis is **"restraint + vocabulary, NOT
recall"**, with criteria of the form *"does `flagged_smells` name the canon smell"*. Naming is
partly legitimate here in a way it was not for great_cto — canon smell names **are** the artifact,
consumed by gates and dedup, so requiring the name is substantive, not cosmetic. But we have no
measurement of whether our grader agrees with a human on the cases where it matters, and
`evals/README.md:248-249` already concedes the point: the current measurement is *"within-judge
robustness, not lift over a bare model and not external validity (that needs more scenarios + a
second judge)."*

So this is a named-but-unbuilt next step, and great_cto supplies the diagnostic half of the
design: hand-label the disputed cases with reasoning, report agreement and kappa, and state
honestly what the number is not. Their own honesty note is worth copying too — the labels were written by the author
of the criteria, so *"a second labeller who did not write them would be worth more than another
twenty cases from this one."*

The full design, leakage-safe — with the selection-bias correction from the second review: the
raw cases are split three ways **before any with/without outcome is observed** (a case selected
for its measured treatment delta is selected for responsiveness, and a holdout built that way
overestimates lift by construction). Two mechanisms, never conflated: **prospective
eligibility** — static case properties only (the case has an outcome criterion both arms can
satisfy, its input/fixture artifacts parse — malformed *candidate output* stays a counted
candidate failure under Gap 19) — may exclude cases from any set *before execution*; trial
validity is knowable only after execution, so an invalid trial stays attached to its admitted
case — retried under a preregistered policy or marked unscoreable for that paired unit, counted
in the invalid/error-rate reporting — and **never removes the case from the corpus** (removing
it would recreate the denominator shrinkage Gap 19 exists to prevent); the
**treatment-discrimination rule** is fitted on development outcomes, where paired results may be
freely observed, and on validation and holdout it only *labels* cases retrospectively — it never
excludes one or changes a denominator, because discrimination requires treatment outcomes and so
can never be an outcome-independent inclusion rule. If a previously-discriminating-cases
benchmark is kept, its estimand is labelled explicitly as *conditional* performance. The three
sets: a diagnostic/development set for finding failure shapes and designing rules — the only
set where disagreement enrichment is permitted — and a stratified validation set and final
holdout whose strata are sampled proportionally or reported under prespecified weights, so their
estimates stay representative; the holdout is evaluated **once** after the design is locked — never edited against; a failed candidate is rejected, and any edited
successor needs a fresh holdout. Labels come from two blinded labellers with adjudication;
report intervals, not point estimates; record the current grader's verdicts on all three sets
first, the holdout baseline stored blinded, so lift is measurable at all.

### Gap 9 — Graders don't declare the axis they do *not* judge · **VERIFIED gap, cheap**

Second-pass finding, from `trailofbits-skills` (142 eval files; our docs cite its hooks and SARIF
output, not its grader contract). A grader spec there is typed and weighted (`type: llm`,
`weight: 0.5`) and closes with an explicit non-scope:

> The exact vocabulary does not matter; addressing each requirement separately does.
> …
> This grader is about coverage and not about correctness. A wrong verdict on §3.2 still passes
> here — the `senior-branch-unenforced` grader is what judges that.

One axis per grader, the acceptable answer *forms* enumerated (verdict word, table row, or an
unambiguous sentence), and a pointer to the grader that owns the axis this one ignores. That is
Gap 8's rule implemented at the level of a single file, and it independently corroborates it.

Our Layer-2/3 grading collapses axes into one semantic judgement per case. Splitting graders by
axis and requiring each to state its non-scope is a small change to the eval harness that isolates
the *source* of a disagreement — the design note still owes aggregation rules, conflicting-axis
outcomes, missing-grader handling, and the extra per-case call cost.

### Gap 10 — State transitions live in prose, not in canon · **VERIFIED gap, medium**

`canon/states.toml` is 11 lines: a flat list of six state names. Every transition rule — which
flag routes where, which steps are skipped, what must run before escalating — lives in SKILL.md
prose (`Step 1 Routing (mandatory)`), with legality enforced *after the fact* on artifacts by G9's
presence table, G34's HALT-tail, and G35's handoff shape.

`great_cto/shared/pipeline.toml` externalizes the whole machine:

```toml
[transitions.architect]
on = ["APPROVED", "DONE"]
gate = "gate:arch"
next = ["pm"]
skip_next_when = "depth=small"
```

State → accepted terminal signals → gate → next states, plus conditional skips. That shape would
let a validator answer *"was this transition legal?"* mechanically instead of inferring it from the
artifact that resulted, and it fits our existing SSOT convention (`canon/*.toml` read by
`_canon.py`).

Worth noting what this is not: `STATE-MACHINE-COMPOSITION-APPENDIX.md` sequenced *proposed* new
intercept points into the existing loop. It never proposed making the transitions themselves
declarative. That is the miss.

Adopting it means specifying, up front: a versioned schema, the guard-expression grammar
(`depth=small` is a language, however small), where transition events come from, and what a
validator does on an illegal transition — reject the artifact, or flag and continue.

### Gap 11 — No cost-proportional stage skipping · **VERIFIED gap, ties to an open audit**

`great_cto` gates whole stages on project size. Its `decision-eval` skill refuses to run when
*"project_size is nano (overhead exceeds value)"*, and `pipeline.toml` carries
`skip_next_when = "depth=small"`.

contest-refactor has `--scope`, `--strictness`, and `--cap`, all of which tune *rigor* or
*extent* — none of which skips a phase because the work is too small to justify its cost. With
`RUNTIME-COST-AUDIT-2026-08-14` open (`analysis/contest-refactor/RUNTIME-COST-AUDIT-2026-08-14.md`,
opened 2026-08-14, not yet consolidated), an explicit "this stage is not worth running at this
size" rule is directly relevant, and it is the cheapest form of cost control available: not
running a step beats running it more efficiently. The audit's completion contract, for item 13
to consume: per-step token and latency figures and per-stage cost shares, so skip thresholds are
derived from measured numbers rather than intuition.

Sequencing constraints: skip rules read the state model, so item 12 precedes item 13; thresholds
come out of the runtime-cost audit, not intuition; safety-relevant stages (build verification, the
secret gate) are never skippable; and every skip is logged with its reason so silence never means
"ran clean" when it means "didn't run".

### Gap 12 — Holistic judge calls where a decision graph would be reproducible · **VERIFIED, high value**

Third-pass finding, and it is the *implementation* Gaps 8 and 9 were missing. Same repo that
supplied the alignment set — `great_cto/tests/eval/dags/security-officer-finding-gate.dag.json`:

> The old judge scored this whole rubric in one 0-1 call and returned 0.72 against a 0.80 bar, with
> the sibling adversarial-prompt eval at 0.44 against 1.00. **Every question below is one a judge
> can answer the same way twice; the score is computed from the path, not sampled.**

The rubric becomes a graph: `root`, `nodes` (each a single `question` with `edges: {yes, no}`), and
`leaves`. The score falls out of the traversal rather than being sampled from a holistic
judgement. Their root node is worth quoting in full because it is our flag/restraint discipline
expressed as one answerable question:

> Does the DIFF ITSELF show a confirmed vector — attacker-controlled input reaching a sink, or a
> committed credential — as opposed to a TODO, a rename, a keyword, or a CVE whose path is not
> exercised?

`no` routes to `restraint-held`: *"Given there is no confirmed vector, did the agent avoid raising
a Finding…"*. Flag and restraint are the two branches of one question, not two separately-graded
cases.

This attacks the kappa-0.00 problem structurally rather than by only measuring it — with a
boundary worth stating precisely: the graph makes score *aggregation* deterministic given the node
answers; the node answers are still model answers. A narrow binary question is *more* repeatable
than a holistic 0–1 score, not guaranteed repeatable, and an ambiguous root question destabilizes
every path below it. So DAG adoption carries its own measurement — node-level repeatability,
sampled per question, with unstable nodes rewritten or mechanized. It composes with Gap 9 (one
axis per grader) and Gap 15 below (mechanize the structural part) into a single coherent redesign
of Layer-2/3 grading — which is currently one semantic verdict per case from a `grader.md`
subagent — as designs to compare against the frozen baseline, not as automatically cumulative
changes.

### Gap 13 — The verification oracle is self-reported · **VERIFIED gap, high value**

Step 1 opens with *"Run primary test/build command"*, and everything downstream rests on it: the
build-flake guard (re-run once, second run is canonical), the minimal build-failure review, and
score-bearing evidence citing *"failing command + first failing line of stderr"*. G4 requires a
score-proof citation — but the citation is authored by the same model that claims to have run the
command. Nothing outside the model witnesses what executed or what it returned.

`gstack` ships the missing piece as a tool: `gstack-evidence run --label <lane> -- <cmd>`
transparently wraps any test command and records it, *"the child's exit code always passes
through"*. The wrapper, not the agent, is the author of the record.

This is the one gap in this document where the failure mode is not noise or drift but
**fabrication**: a loop that reports a passing build it never ran will converge, emit
`HALT_SUCCESS_candidate`, and pass every gate we have, because every gate reads model-authored
artifacts. The challenger panel re-reads the claim; it does not re-run the command.

The design constraint that matters is the trust boundary: an "append-only" file the model can
write — or delete and recreate — is not independent evidence, and neither is a path the loop's
prose rules tell the model not to touch; an instruction does not authenticate a file. The ledger
must be **host-attested** — written by a mechanism the model cannot invoke with arbitrary content
(a harness hook, or a host-enforced protected location). Each record binds run ID, the configured
command, cwd, source revision/fingerprint, timestamp, exit status/signal, and an output digest
(truncated output *redacted*); the artifact cites the record's event ID and the gate asserts the
linkage. Where a given harness offers no such boundary, the ledger downgrades honestly to a
consistency check and says so — it is an anti-fabrication control only when attested. The RED fixtures
are adversarial by nature: a missing record, a forged record, a replayed record from an earlier
run, a mismatched exit code. Cost is higher than a bare wrapper, but still low relative to being
the only control in the design that attests execution *results* — hook-observed tool invocation
(item 16's evidence) can attest that a command ran, never what it returned.

### Gap 14 — No halt state for context or budget exhaustion · **VERIFIED gap**

`canon/halt-subtypes.toml` carries exactly five subtypes — `no_progress`, `oscillation`,
`user_decision`, `no_backlog`, `verification_blocked` — all of them descriptions of *rubric
progress*. Grep across `SKILL.md`, `references/*.md`, and `canon/*.toml` finds nothing matching
context limit, context exhaustion, or budget exhaustion.

So a loop that dies because it ran out of context mid-Step-3 has no honest tail. G34/G35/G36
enforce the shape of a HALT tail *when a halt state is emitted*; a context death emits nothing at
all, and the run is indistinguishable from a crash. We already learned the general lesson on the
eval side — death-by-spend-limit is not a MISS — but the loop itself has no state for it.

`continuous-claude-v3` treats this as a first-class transition: `auto-handoff-stop.py` is a Stop
hook that blocks at ≥85% context and directs the session into a handoff, reading the percentage
from the same temp file the status line uses so the number the hook acts on is the number the user
sees. It is backed by `continuity_ledger`, `create_handoff`, and `resume_handoff` skills.

We do not need their hook's re-injection role — our state is file-based and survives compaction.
But the subtype alone is inert: a run that has already exhausted context cannot emit anything, so
the state is only reachable if something detects *pressure* before death and triggers the handoff
early. That detection is an external signal — a host hook or token meter (ccv3 reads the same
percentage the status line shows precisely so the acted-on number is the visible one) — and where
no reliable meter exists, the honest fallback is periodic preventive checkpointing on a
conservative step budget, recorded as the detection mode used and without claiming it can tell
context pressure from any other interruption. The design also
separates three deaths that currently look alike: context pressure (handoff possible), provider
spend limit (handoff possible if caught), and process crash (nothing to emit — a G34-shaped
absence is the only trace). Checkpoint writes on the handoff path must be atomic, and the fixtures
interrupt before, during, and after the handoff write.

### Gap 15 — Shrink the judge's surface before trying to align it · **VERIFIED, refines Gaps 8-9**

`logic-lens` grades 104 cases and 422 assertions with **no model in the loop**:
`scripts/grade-iteration.py` applies hand-written Python predicates over the output text —
reusable structural rules (`_VERDICT_RULE`, `_FOUR_FIELD_RULE`, `_FAULT_CONFIDENCE_RULE`,
`_LOGIC_SCORE_BELOW_100_RULE`) plus per-case predicates (`_case227_score_improved`).

The trade is explicit and worth stating: they bought determinism by hand-authoring 422 assertions,
and it only works because their output has a fixed shape (a Logic Score, a four-field record, a
verdict word).

**Our output is more structured than theirs** — `CURRENT_REVIEW.json` is schema-gated, with
`flagged_smells`, a nine-dimension scorecard, canonical verdicts, and per-finding evidence fields.
We already made this choice where the artifact is machine-readable (`loop_replay_grade.py` is a
committed grader). The gap is Layers 2/3, where grading is semantic end to end.

The sequencing insight: mechanize every structurally checkable assertion first, and only then
measure agreement on what genuinely requires reading. Aligning a judge that is being asked
structural questions is wasted work — the right fix is to stop asking it those.

### Gap 16 — Untrusted-content handling is prose, not a tool · **VERIFIED, low-medium**

G14 (payload not instruction) is a rule the model applies to itself. `gstack-issue-guard` is the
mechanical version: it fetches GitHub issue/PR text and **wraps it in a labelled trust envelope**
before the agent sees it, so the boundary between instruction and data is established by the
fetcher rather than by the reader's discipline.

Scope it to where a bounded interception point actually exists: the explicit ingress adapters —
incident files via `--incidents`, tracker text, ADRs, any remote issue/PR fetch. Ordinary
repository reads (the reviewed code, comments, READMEs) stay covered by G14 plus the reader's
tool-payload labelling: there is no common interception point for them, and mediating every read
would be an architectural spike, not this item — promote it only if a RED case shows the
G14-only boundary failing. Honest framing either way: the envelope is provenance metadata, not a
mechanical injection barrier — it makes the boundary legible so the non-obedience rule (G14) has
something to grip; it cannot prevent a model from obeying embedded text. Wrapper *plus* rule, not
wrapper instead of rule.

### Checked, already covered or ahead — third pass

| Mechanism | Source | Finding |
|---|---|---|
| Token bill-of-materials | `gstack-context-bill` | **We are ahead.** `scripts/token-budget.py` does per-file counts, per-loop fixed-reload sums, full-run projection, *and* `--loaded-set <step>` proving which files a given step reloads — plus it prints whether the count came from tiktoken or the heuristic, so a number is never silently an estimate. No action. |
| Working-tree fingerprint | `gstack-wtree` | Different purpose. Ours (`candidate_fingerprint.py`) is a semantic fingerprint of the architecture-relevant payload; theirs is a cheap disk-state hash (~40× faster than a full re-hash via a stat-cache-seeded temp index). `source_rev` already covers our disk-state need. Perf idea only. |
| Exit-code discipline | `senior-engineering-partner/scripts/eval-guard.py` | Not a new gap — the *fix shape* for the `exec_replay_grade.py` exit-code split. It exits **0 pass / 1 fail / 2 git plumbing error**, and documents that "CI and a local run are byte-identical". That third code is precisely what `exec_replay_grade.py` is missing when it folds "inputs missing" into "invariant failed". |

### Checked, already covered — second pass

| Mechanism | Source | Why no action |
|---|---|---|
| PreCompact continuity hook | `continuous-claude-v3/.claude/hooks/pre-compact-continuity.sh` | Our loop state is file-based (`LOOP_STATE.json`, `REVIEW_HISTORY`), so it survives compaction without a hook. Their hook re-injects state a session holds in context. |
| File-ownership claims for parallel agents | `continuous-claude-v3/.claude/hooks/file-claims.sh` | Already captured in `PARALLEL-CRITIC-ARTIFACT-CONTRACT-GAP` via wshobson's file-ownership model. |
| Confidence intervals on eval results | `wshobson-agents` PluginEval (Wilson / Bootstrap / Clopper-Pearson) | Already captured in `SCHEMA-GAP` continuous scoring. |

### Already covered — no action

| Mechanism | Where we already have it |
|---|---|
| Drift detection on a stamped commit | `source_rev`, `candidate_fingerprint`, G31 fingerprint integrity, G28 checkpoint freshness |
| Rejected findings not re-audited | `findings_registry.json` fuzzy-match + per-finding retirement (G30) |
| Independent validator, not self-recheck | v5 staged 3-member HALT_SUCCESS challenger panel (shipped 2026-08-07) |
| Asymmetric thresholds by cost-of-miss | Layer-3 reviewer-judgment asymmetric thresholds |
| Restraint/look-alike testing | Layer-2 flag/restraint pairs (documented; see Gap 5 for enforcement) |
| Intent docs consumed | `project-config.md`; ADR ingestion is narrower than shadcn's but present |
| Diff-scoped implementation review | Step 3 implementation reviewer, G15/G16/G17 |

### Recorded tension — partitioned scanning

`DOMAIN-AWARE-SCANNING-GAP.md` is DEFERRED here. levnik **abandoned** its `domain_mode` /
`scan_path` implementation in the Skills v2 rewrite. mhylle **keeps** partitioning and builds
resume around it. Two of three exemplars now point away from it; the third is the only one whose
product is long-running full-repo audit. Our deferral stands, and now has evidence on both sides.

---

## Fourth pass — the ten-repo expansion (2026-08-17)

Ten repos cloned after the third pass, audited by four parallel readers (one bucket each);
every quote below was spot-verified against the clone before inclusion. Two of the ten are far
more substantial than their stars suggested: `code-quality-atlas` (605 files, a generation
pipeline with per-subsection provenance hashes, ~302 tests, a cross-model eval harness with a
precision/recall split) and the Compound Engineering plugin (40 skills — the only repo in the
corpus that *ships* several of our backlog items).

### Corrections this pass forces on earlier passes

- **Item 6 has a shipped reference implementation.** CE's `ce-code-review` uses discrete
  anchors `0/25/50/75/100` with behavioral criteria embedded in the findings JSON schema,
  severity and anchor as declared-independent axes (*"a P0 finding can be anchor `50` if it is
  an important concern you could not fully verify"*), and mechanical suppression below 75
  *except P0* (`findings-mechanics.py:201-208`) — the same carve-out rigorous-review argues for,
  running in production. Plus a coupling we had not designed: an anchor ≥ 75 with no quoted
  evidence line is force-capped to 50 in code. They migrated *away* from float confidence after
  observing round-value clustering. The labelled comparison now tests whether *this* design
  carries a distinction the Evidence Chain cannot, rather than inventing a design first.
- **Item 14's honest-downgrade contract is CE's receipt rule, verbatim**: model identity *"is
  verified only by such a receipt — never by the request parameters or the model's own text —
  and outputs without one are labeled as requested-but-unverified"* (`CONCEPTS.md:131`).
  planning-with-files supplies the artifact-side half: SHA-256 attestation where the executable
  command allowlist rides *inside* the hashed plan, so tampering breaks the hash and the hooks
  refuse injection until re-approval.
- **Item 15 gains a removal datapoint.** CE built premise-dependency graphs over findings and
  deleted them (2026-08-13): *"elaborate structure resting on a classification the model was not
  yet doing well."* A different object than great_cto's grading DAG — theirs synthesized
  findings, ours grades rubric questions — but it hardens the tranche-3 order: measure the
  classification before building a graph on it. harness-eval independently supplies the
  node-repeatability evidence: one judge criterion sampled three times returned `7,0,8 → median
  7` on the same artifact. Median-of-N is a band-aid, not alignment.
- **Item 11 has a live counter-pressure.** CE's doctrine demands per-finding parallel validators
  (*"a single batched validator looking at all findings together pattern-matches across them"*),
  yet their shipped orchestration now puts everything in **one** validator batch for cost and
  determinism — and the learning doc was never updated. harness-eval implements the clean form:
  each of five criteria gets its own conversation. Both endpoints run in production. Item 11's
  design note must name the cost pressure and separate two independent decisions — conversations
  per grading axis, and findings per validator call — measuring cost, cross-item contamination,
  repeatability, and accuracy for each.

### What lands on existing items

| Item | Fourth-pass evidence |
|---|---|
| 2 (eval-guard) | crucible runs the behavioral suite on any PR touching `.claude/**` — path-triggered, no waiver path. dsh-skill-eval adds the missing half: a **fidelity pin** — a test that fails when the eval harness drifts from the production artifact it claims to evaluate (their catalog renderer must match the pinned upstream template byte-for-byte). |
| 4 (flag/restraint) | CE names *"new-only restraint negatives"* as a first-class fixture class (*"a rule that fires on everything is as broken as one that fires on nothing"*). dsh-skill-eval ships a 20-case trigger set for a code-review skill whose hard negatives — refactor requests, security audits, design-doc review — are directly liftable. Anthropic's skill-creator requires 8-10 *near-miss* negatives per eval set ("obviously irrelevant" negatives test nothing). |
| 8 (strictness RFC) | crucible's accept-gate is the strongest found shape: an **ordered vector of named filters** (safety → per-scenario no-regression → effect-size floor + one-sided two-proportion z-test → cost tie-break), reported as a rejection histogram per named reason. |
| 13 (cost skipping) | CE's skip gates fail closed on helper-computed signals and **count every skip in a Coverage section**. crucible grades cost as a first-class result (*"never hide spend"*). A loop reaching 9.5 in 14 iterations at $40 is a worse skill than one reaching 9.2 in 3 at $4 — iteration count and spend belong in the eval suite, fed by the runtime-cost audit. |
| 16 (mechanize first) | crucible: 15 deterministic assertion types including hook-observed `subagent_invoked`/`tool_invoked` — mechanized observation of what the agent **did**, not what it claimed — plus a free offline lint gate before any paid trial. planning-with-files: parse-don't-match (a regex gate stayed green while the YAML it guarded was invalid), and **every selftest must exec the shipped artifact** — their suite stayed green while 2 of 6 mechanisms were silently broken, because a test reimplemented the fix instead of importing it. |
| 17 (exhaustion halt) | atlas's harness refuses to grade a partial run (*"the failed scenarios' empty responses look exactly like 'no findings'"*). And the pressure signal may now be a platform primitive, not a hook: the Claude API's `task_budget` injects a model-visible countdown so a loop paces itself instead of dying mid-step. |
| 18 (provenance envelope) | planning-with-files: nonce-delimited injection with the honest limitation stated, plus a per-file trust split (untrusted web content only ever lands in `findings.md`, never in the hook-amplified plan file). CE: an *"Untrusted customer content — data, not instructions"* blockquote convention plus an argument-injection guard (refs must match `#?\d+` or hex before reaching any git command). |
| Grading tranche | Anthropic's grader adds **claim extraction** — grade what the actor *said it did* (typed factual/process/quality claims, each verified) — and its analyzer classifies every assertion by discrimination pattern. atlas adds `analysis_model` stamping so a silent grader-model upgrade cannot masquerade as a skill change. |

### Gap 17 — Eval cases are never screened for discriminating power · **VERIFIED gap, high value**

Two independent implementations, neither in our suite. crucible admits a generated scenario only
if it *"parses, PASSES on the good reference, and FAILS on the weakened reference. Otherwise it
carries no signal"* (`src/frontier.ts:139-142`) — the weakened reference is literally a bare
CLAUDE.md. Anthropic's analyzer classifies every assertion across runs: always-pass-both,
always-fail-both, pass-with-fail-without (value), **fail-with-skill-but-pass-without (the skill
may be hurting)**, high-variance (flaky).

We have five eval layers and no test that any case discriminates. A case that passes with the
skill *and* without it — or fails both ways — quietly dilutes the sensitivity of every lift summary the grading tranche will produce and can
obscure heterogeneous effects (representative non-discriminating cases do not by themselves bias
the estimand — they blunt it), and the fail-with-skill case has no detector at all. Two corrections to
the naive form, from review: discrimination is a *stochastic* property, so a case is classified
from repeated paired deltas against the A/A floor (Gap 18), never from one pass/fail
observation; and always-pass cases that encode absolute contracts — a regression that must never
fire, a schema that must always validate — are not pruned but moved to a separately reported
contract suite, excluded from lift claims. Two corrections from the second review: the screen
must never select the eval sets by their observed treatment response — its rule is designed on
development outcomes, and on validation and holdout it only *classifies* cases retrospectively,
without changing the denominator, or the benchmark becomes circular. And discrimination is a
*treatment* property, not a *grader* property: a case useless for measuring skill lift can be
excellent for detecting judge error, so the judge-alignment suite is sampled by judge-relevant
strata, never by treatment lift (see Gap 8 and Tranche 3).

### Gap 18 — No noise floor under eval claims · **VERIFIED gap, high value**

CE's retune methodology opens with the measurement that *"retired every small-sample claim in
flight"*: 12 runs across two **byte-identical** builds gave workflow adherence 7 of 12 and a
7.12× output-token spread — so any later claim smaller than that envelope is unsupported.
crucible encodes the same discipline as code: a one-sided two-proportion z-test plus an
effect-size floor in its accept-gate, because *"a fixed pass-rate threshold at small k cannot
tell a real improvement from binomial noise -- 4/5 vs 3/5 looks like a win but is well inside
the variance."* harness-eval flags any ranking whose top-two ±σ ranges overlap as
**inconclusive** rather than publishing an ordering.

Our standing micro-test discipline (5+ reps, read the matches) has the right instinct and no
statistical floor. Before tranche 3 reports any lift, run the A/A arm and pin the floor — keyed
to model/version, grader prompt, sampling settings, harness revision, tool configuration, and
scenario corpus, and recomputed when any of those change. The accept rule must match the
experiment's shape: crucible's two-proportion z-test assumes *independent* arms; our
with/without design (Gap 20) is **paired**, so the preregistered test is exact McNemar on paired
binary outcomes (or a paired permutation procedure for non-binary scores) — with the unit of
analysis defined first: the independent unit is the case; repeated trials and repeated judge
samples are aggregated *within* the unit before the test; slot-swapped judging is an order-bias
control inside the judge protocol, **not** itself the McNemar table; and dependence across units
takes a cluster-aware alternative. Minimum effect, alpha, power/sample size,
multiple-comparison handling, and an explicit *inconclusive* outcome are all stated before the
first run.

### Gap 19 — An invalid trial is indistinguishable from a failing one · **VERIFIED gap**

The suite-wide generalization of the `exec_replay_grade.py` exit-code split, implemented four
independent ways in the new corpus: skilllens voids the trial (`valid: False`, scores `null`,
never 0) when a deterministic **manipulation check** fails — the with-skill arm didn't invoke
the skill, or the without-skill arm did; harness-eval's `countable()` excludes ungradeable
trials from normalization entirely; crucible classifies **infra-failure vs candidate-failure**
(auth/rate-limit regexes over run errors, deliberately conservative — *"only an explicit
runError is inspected, never a normal assertion failure"*); atlas refuses to grade partial runs.
A rate-limited run scored as a failing refactor silently poisons the dataset — and our Layers
2-5 currently have no invalid-trial concept at all.

One boundary correction against skilllens's design, from review: `invalid` is reserved for
**exogenous harness failures** — rate limits, auth errors, infrastructure timeouts, lost
artifacts. A correctly-supplied skill that failed to trigger or was not followed is an
**adherence failure the suite must count**, not an invalid trial; voiding it would erase exactly
the failure a trigger eval exists to see. Candidate-induced timeouts, malformed output, and
runaway spend likewise count against the candidate unless independently classified as
infrastructure. Invalid counts are reported per arm with machine-readable reasons, and a
comparison with excessive or asymmetric invalidity is itself void.

### Gap 20 — No paired baseline, and no guard against tautological criteria · **VERIFIED gap, high value**

Anthropic's skill-creator makes the baseline structural: *"For each test case, spawn two
subagents in the same turn — one with the skill, one without"* — including snapshotting the
pre-edit skill as the baseline when improving an existing one. skilllens scores the *delta*
(floored at zero, voided if the manipulation check fails) and contributes the sharpest
rubric-design rule in the whole expansion: a criterion the baseline arm structurally cannot
satisfy *"verifies that the skill's methodology was executed, not whether the task goal was
completed at high quality ... making this an invalid evaluation item."*

Both halves bite us. Our suite reports absolute scores — nothing separates "the loop found
this" from "the model would have found it anyway" (our own advisory-eval history — recall lift
0 because the defects were too legible — is this lesson, learned once and not yet mechanized).
And our Layer-2/3 criteria of the form "does `flagged_smells` name the canon smell" sit exactly
on the tautology boundary the skilllens rule polices: legitimate where the name is the consumed
artifact, invalid the moment a criterion rewards our vocabulary over the outcome.

### Recorded tensions — fourth pass

1. **The scalar rubric now has two shipped counter-examples.** atlas considered and rejected
   per-dimension scores (D18): teams optimize the number, *"a score can rise while real defects
   are reworded to survive detection,"* and a scalar erases the *kind* of problem — replaced by
   three categorical axes (severity/tier/valence) plus severity-count trends. CE likewise ships
   a 3-value verdict, no score. Our 9.5-convergence stays defensible as an *internal*
   convergence signal rather than a reported grade — but the design rationale should say so and
   engage D18 directly. atlas also documents the floor-plateau lesson: escalating strictness
   round-over-round *"suppressed real Major regressions ... just because the PR had taken a few
   rounds"* — convergence must come from only-new-findings, not from raising the bar.
2. **Alignment vs demotion.** crucible's standing rule: deterministic assertions are hard gates;
   *"Never let an LLM-judge result fail a CI gate by itself."* The alternative to aligning a
   judge is demoting it to a non-gating signal. Tranche 3 should state explicitly why we keep
   judges gate-adjacent where we do: Layers 2/3 measure judgment itself, which cannot be demoted
   without giving up the measurement — and everything demotable is what item 16 mechanizes.
3. **Three shipped confidence designs, not zero.** CE's finding-level anchors (expressive,
   evidence-coupled, self-assessed — gameable in principle); agent-verifier's rule-level
   `[P]`/`[H]` tiers (un-gameable — the tier is stamped on the rule at authoring time — but
   carrying zero per-finding information); Anthropic's binary burden-of-proof (*"the burden of
   proof to pass is on the expectation"*, *"No partial credit"*) with executor-declared
   `uncertainties[]` as a separate channel. Item 6's design note now chooses among three live
   designs rather than inventing one.

These tensions are design-note obligations, not commentary: the grading design note must justify
any scalar it keeps and any gating role a judge holds — naming which deterministic failures
remain hard gates — and item 6's note must run the three-way comparison before any schema work.

### Smaller learnings recorded

- **Accretion-stop for review-fix loops** (CE, measured): a two-condition step absorbed 24 bot
  findings over nine rounds — most against text a previous round had added — before being
  restated as the two conditions it began as. Their rule: on the second round against the same
  block, stop patching and restate the block as goal + done condition + safe direction. Applies
  to our own skill-prose review cycles more than to the runtime loop.
- **The literal-string result** (atlas, measured): recall 65%→75% by giving the model a concrete
  string for the second case (`Not applicable:` beside `No findings`) after three
  judgment-prose rewrites had failed — and a follow-up worked example *destabilized* a
  thematically-near scenario, so any example edit demands a full-suite re-gate.
- **Independence is a property of the execution context** (CE): *"Two personas reasoned inside
  one context are two perspectives, not two witnesses"* — and where dispatch is unavailable,
  adversarial roles **block rather than run inline** (*"an orchestrator grading its own
  experiment is not a measurement"*). Directly load-bearing for the challenger panel.
- **Corpus hygiene warning**: `ce-reviewers` is ~4.5 months behind the CE plugin and materially
  divergent (float confidence the plugin abandoned, a deprecated mode, a dangling schema
  reference). Persona-style reference only; the plugin's own `references/personas/` is current.

---

## Fifth pass — the second wave, and the capability backlog (2026-08-17)

Nine repos, four parallel auditors, every quote below spot-verified against the clone. This
batch inverts the fourth pass: it is rich in **object-level capability** — new ways to detect,
rate, and improve code — and thin on eval machinery, which is exactly the rebalancing the
backlog needed. Gaps 21-26 and items 23-29 below are the capability backlog; per the standing
priority, they concern what the Critic *finds and fixes*, not how the skill is measured.

### Claims that did not survive contact

| Repo | What the survey/README said | What the clone shows |
|---|---|---|
| `tech-audit-skill` | "13-dimension framework", "~250-line spine", "5-7 hour full audit" | A **16**-dimension registry; a **143**-line spine; and the execution file replaced hours with *"Scope, not clock"* — the README is stale in three directions. Plus a dead routing column (`cuts/deep.md` maps through a "Topics" column the registry doesn't have) and a red test as cloned. |
| `cloudflare-security-audit` | "one run finds ~half" | The quote is real (`SKILL.md:37`) — and there is **no methodology, sample size, or data anywhere in the repo** behind "Testing shows". The mechanism (run-numbered dirs, prior-run gap targeting) is real; the statistic is marketing. Also: ~60% of the repo is security content, so "methodology-only" undersold it — four of its twelve hunting lenses (sad-path, implicit trust, parser disagreement, round-trip survival) are pure correctness lenses. |
| `alibaba-open-code-review` | Vendor benchmark: higher precision/F1, ~1/9 tokens | **Nothing in-repo substantiates it** — no dataset, harness, scorer, or matching rubric; four PNGs and an external link. The ~1/9 token figure is plausibly confounded by pre-LLM file exclusion. Also: `ocr scan` has **no coverage manifest by design** (`RunManifest returns nil`), and "smart file bundling" is extension/directory grouping, not semantics. |
| `sentry-skills` | security-review routes into 5 language + 5 infrastructure guides | **Six of eleven routed files do not exist** (`languages/` has only python+javascript; `infrastructure/` only docker) — dangling routes in a 924★ production skill. Copy only routes that resolve. |
| `center-audit` | "24 sections", self-validating | The output format defines **21** sections, and the repo **fails its own validator** (a prose example `references/foo.md` trips the resource check; SKILL.md is 503 lines against its own 500 limit). The mechanisms are real regardless. |
| `aws-agent-skill-eval` | "reliability via trigger precision"; hard/soft/baseline assertion levels | `trigger_precision` is **recall** and `no_trigger_precision` is **specificity** — mislabeled in the shipped API while their own RESULTS.md uses the right words. The assertion levels are **docstring fiction** (zero implementation). `style_score` is `outcome_score` counted twice; the golden dataset is calibrated on itself and then reported as "100% accuracy". |
| `conorbronsdon-agent-skills` | ships `repo-audit` (Enforced/Advisory/Guidance) | **Absent from the clone** — it lives in a separate upstream repo. The methodology exists in-clone as `eval-integrity`'s PRESENT/PARTIAL/ABSENT ratings, with the two good rules attached (a rating with no `file:line` is a guess; a grep miss alone does not establish ABSENT). |

### Items 19-22, validated against shipped prior art

`opendatahub-agent-eval-harness` (~30k LOC, mature) is the closest prior art to the tranche-3
instrumentation, and it independently built adjacent machinery: its pairwise judging runs every
case twice with slots swapped, a side wins only if it wins both orderings, ties are excluded —
an **order-bias control** whose win/loss tallies resemble a discordant-pair table, gated only by
a bare `min_win_rate` with no test. The resemblance is instructive but not an equivalence:
McNemar applies to one properly defined paired binary outcome per independent unit (Gap 18), not
to slot-swap verdicts. Item 20 completes the statistical layer this machinery gestures at. Their judge-sample aggregation (median-low over N samples,
instability preserved with all rationales) is a *judge-level* noise floor that composes with our
*arm-level* A/A floor — both are needed to attribute a delta to the skill rather than the judge.
And their degenerate-design guards (returning `p_value: None` with a reason instead of a number
when variance is zero or F is non-finite) are the post-hoc cousin of our a-priori
discriminating-power screen. What they lack is precisely items 19-22: no A/A floor, no paired
test, no power, no trial-validity taxonomy — a timed-out run is scored as a content failure
(zero `exit_code` filtering sites), which is the exact conflation Gap 19 names.

`aws-agent-skill-eval` demonstrates, in published form, the failure each item exists to
prevent: its headline +100% results come from criteria the control arm **structurally cannot
satisfy** (*"Only with-skill can see the SKILL.md to find the API key!"* — celebrated as "the
cleanest proof of skill value"; item 22's violation in the wild); its accept rule is
`mean_with >= mean_without` with no floor (+0.001 passes; item 20); harness timeouts grade as
0% quality (item 19); and its golden dataset does all three of our three sets' jobs at once,
unblinded, with assertions tuned to the instrument (the design our
split-before-outcome-observation ordering exists to prevent).

Five imports into tranche 3 from this pair: a **coverage gate against denominator shrinkage**
(`max_error_rate` — our `invalid` category creates the survivor-metric hazard it solves: nine
voided trials and one pass must not report 100%); a **broken-instrument detector** (when a judge
fails every case, check whether its referenced fields still exist before reading it as a
regression); **deterministic-first grading with per-assertion `method` provenance** (AWS's
deterministic tier measured 100% accurate; its LLM tier produced the only inconsistency);
**judge-sample stability** as a persisted per-case artifact; and — only where outcomes are
continuous and approximately meet its assumptions — repeated-measures ANOVA with case as a
blocking factor if the design ever exceeds two arms (Cochran's Q or a GEE model for binary and
ordinal outcomes; and their min-p-across-coefficients hazard noted as the thing not to copy).

### Gap 21 — Detection breadth: missing lens families, and no agent outside the taxonomy · **VERIFIED gap, capability**

Four lens families with no counterpart in our canon, each fully specified upstream: skillet's
**latent-premises** (contract / environment / ordering / cardinality / input — unenforced
assumptions, admitted only when *"genuinely unenforced AND you can name what concretely breaks
when it fails"*); **retry-safety** (second-run safety over migrations, payments, queues, with
the expand-migrate-contract deploy-window checks); conorbronsdon's **operational** lens (retry
budgets, cost-at-scale, deployment-config drift — it caught the P0 that five rounds of
line-level review missed); and **reference-comparison** (drift from the SDK/protocol reference:
missing steps, reordered steps, default mismatches). On top of the families, Cloudflare
contributes the *structural* fix for any finite taxonomy: a **Wildcard agent** given no category
(*"your job is to find the thing nobody thought to look for. Read code that looks boring"*)
paired with an **"obvious things" agent** (*"the dumb stuff… everyone assumes someone else
already checked"*), plus **multi-run recall as a mechanism** — run-numbered output dirs, prior
runs read as negative priors (skip known findings, weight toward unhunted categories), and
honest coverage disclosure when no prior runs exist. Sentry adds the scope rule that makes
breadth affordable: **research the entire codebase to build confidence; report only in scope.**

### Gap 22 — No deterministic selection, coverage manifest, or resumable traversal · **VERIFIED gap, capability**

alibaba ships several of the component mechanisms, deterministically (its coverage manifest covers diff review only — its full-repo scan has none by design): five ordered per-file gates each
returning a **typed exclusion reason** (surfaced per file as `will_review` + `exclude_reason`);
a run manifest where *"selected … equals the disjoint union of completed, reused, failed and
waived"* and the terminal state is **derived from coverage, never stored**; typed 8-value
failure classes; two identities per item (stable `ItemID` vs content `Fingerprint`); and
fingerprint-keyed JSONL resume where a `failed` record retracts an earlier `done`. tech-audit
adds the traversal *prior*: a git churn heatmap biasing deep reads toward the top-30 most-touched
files, and **registry treatment tags** (`always-deep / default-deep / scan / release-only`)
where scan-tier dimensions escalate to deep only when a finding fires — constant-cost sweep
everywhere, expensive pass only where the sweep bites. Notably, *nobody* in all 55 clones has
partitioned whole-repo traversal with a coverage ledger — alibaba's manifest covers diff review
only (scan returns nil by design), tech-audit samples, center-audit forbids it by doctrine. The
gap is real and unfilled; closing it is genuine differentiation, and the pieces above assemble
it.

### Gap 23 — No tool-grounded substrate, and no per-language rules · **VERIFIED gap, capability**

Our Critic generates findings with no deterministic analyzer output in the loop. The pattern across the wave: **run cheap deterministic
tools first, and forbid the model from duplicating them.** tech-audit's tool matrix orders
twelve tools cheapest-first (gitleaks → native audit → linters → typecheck → trivy → semgrep)
with an interrupt rule ("if a fast tool surfaces a 🔴, escalate immediately") and a context rule
(tool output to a file, summarize counts — never dump raw output into context). alibaba's
per-language rule docs are the authoring template: a **precision preamble** (*"Favor precision
over recall… A false positive costs reviewer trust"*), an explicit **negative clause on every
bullet** (the thing *not* to flag), **version-conditioned rules** (Go 1.22 loopvar, Go 1.23
timer semantics — something a generic smell taxonomy cannot express), and the anti-duplication
mandate (*"Do not duplicate findings that `go vet`, Staticcheck… can determine reliably"*).
Sentry's grep-patterns-per-reference-file show the complementary framing: every taxonomy entry
carries its own mechanical detector, **explicitly labeled a lead, not a finding**.

One boundary from the second review, non-negotiable: the tool substrate inherits Tranche 1's
controls, or it reopens them. A secret scanner's raw output *contains the secrets it found*;
analyzer output is attacker-influenced repository-derived text. So item 25 depends explicitly on
items 1, 3, **and 18** (18 is not in slice 1a — the dependency is on all three, not the
slice): adapters run tools in redacted modes where available, and a tool with no redacted mode
**fails closed** — its output is sanitized before any use, or the tool is skipped and disclosed
under coverage; raw output is untrusted data under the payload-not-instruction rule and is never
written to a durable file — only sanitized summaries plus output digests persist, *attested*
only where item 14's boundary exists and otherwise carrying item 14's honest
requested-but-unverified downgrade; and the RED fixtures include analyzer output carrying
planted credentials and injected instructions.

### Gap 24 — Evidence is asserted prose, not computed fact · **VERIFIED gap, capability**

Two shipped mechanisms turn evidence chains into checkable objects. alibaba: the model **never
emits line numbers** — it emits the code quote verbatim, and a deterministic resolver computes
the lines (sliding-window match, deterministic cross-file relocation *before* any LLM
re-anchoring — because the LLM fallback *"overwrites the one piece of evidence pointing at the
real code"* — and `start_line == 0` as an honest unanchored state). center-audit: evidence
carries a **strength grade** (A executed/reproducible, B direct anchored, C corroborating
inference, D hypothesis) and an **`independence_group`** field with an enumerated
non-independence list (*"two agents that received the first agent's conclusion and repeated
it"*) — making double-counted corroboration a schema-detectable error — plus **trajectory
arithmetic**: *"One material unproven link forbids `CERTAIN`. Two sequential unproven links make
the path a hypothesis, not a finding."* Our Claim→Source→Consequence→Remedy chain has none of
this: no computed anchoring, no strength grades, no independence accounting, no gap arithmetic.

### Gap 25 — Findings pass one gate, not a disproof pipeline · **VERIFIED gap, capability**

Cloudflare runs three passes with an independence boundary at each: dedup **by shared root
cause** first (overlap is the recall strategy; dedup is the cost control), then a **separate
disproof agent per finding** (*"hunting agents are biased toward finding things; the validation
agents are biased toward killing false positives"*), then a **fresh-agent verification** pass
(*"You did NOT write this finding"*) with a ternary `VERIFIED / CORRECTED: [field] / REJECTED`
verdict that also checks whether the **remediation would actually work**. skillet's bug-hunt
states the admission contract most sharply: the verifier's job is to REFUTE, *"no trigger, no
bug"*, refuted findings are dropped silently and reported only as a count. alibaba's
review-filter is the precision complement, applied at synthesis: an **asymmetric loss function**
stated in the prompt (*"Removing a correct comment silently destroys a real finding… nobody
learns that it was dropped"*), exactly **two grounds for removal**, **protected subjects vetoed
before correctness is even judged**, and a field-ordering trick (analysis serialized before
IDs) that measurably stopped the model from removing findings it had just called protected. Our
challenger panel certifies a terminal state; nothing in our loop runs per-finding disproof, and
nothing protects findings from over-zealous filtering.

### Gap 26 — Remediation is untyped, and repair re-validation is unrecorded · **VERIFIED gap, capability**

tech-audit types every fix at the title level with the **essentiality ladder** (`delete: →
stdlib: → native: → yagni: → shrink:`) plus a re-routing boundary (deletion findings in
correctness/security/a11y territory route to the owning dimension instead — the classic
simplification-critic failure, prevented structurally). skillet closes each finding with
**exactly one disposition** (guard / document / encode-in-type — *"a wall of options is a
punt"*) and sorts the merged backlog by **severity × effort leverage** — the sort key our
findings lack. Scope corrections from review, both rounds: our loop already *applies and re-verifies* fixes —
Step 1's build verification and the Step-3 implementation reviewer (G15-G17) establish that the
build passes and the diff matches intent. What is missing is narrower and still real: a
**typed, invariant-specific, independently recorded** repair-revalidation record — pre-edit
invariant confirmation, post-fix invariant result, lifecycle verdict — so item 28's design note
begins with an inventory of what existing verification already establishes and adds only the
missing fields. And the two upstream taxonomies are two *different axes*, neither a universal
remediation contract — the essentiality ladder types *simplification* strategies, the
disposition arrows close *latent premises*; ordinary repairs (dependency upgrades, data
migrations, configuration changes, algorithm fixes, test additions) fit neither. The finding
contract therefore carries separate fields — remediation strategy, owning dimension, chosen
disposition, effort, revalidation outcome — with expressibility fixtures proving every major
finding family has a valid representation. center-audit contributes the two deepest pieces: a
**repair contract** whose
consumer must *independently re-validate the invariant before editing* (*"failing-before tests
must be authored… against the audit's invariant, not against the proposed fix's diff"*), closed
by a 4-value `repair_revalidation` field (`INVARIANT_HOLDS / DRIFTED / REPLACED /
CONTRACT_REJECTED`); and a **5-condition promotion test** for when a local fix may escalate to
structural refactor (*"Do not redecorate the cathedral"*) — the inverse of our mandate, and
therefore exactly the gate our loop should pass before it refactors instead of patches.

### The finding-assurance model (decide once, before items 26 and 27)

Three mechanisms in this backlog describe overlapping properties of a finding — item 6's
*confidence* (an experiment that may conclude no field is warranted), item 26's *evidence
strength* (per evidence link), and item 27's *disproof* (a lifecycle verdict) — and building
them independently produces contradictory gates or serial schema migrations. One shared design
decision precedes both items — and it decides *relationships*, not the winner of item 6's
experiment. Four concepts stay separate until that experiment selects a design: evidence
strength (per link, A-D), **execution-context independence** (which agent ran in which dispatched
context — provable by the orchestrator, which stamps context and source identifiers),
**source/causal independence** (whether two pieces of evidence rest on independent underlying
observations — *not* provable by dispatch records; it needs deterministic lineage where
available and adjudication where not), and confidence itself, whose shape — finding-level
anchors, rule-level tiers, or a separate uncertainty channel — is exactly what item 6 compares.
The deterministic derivation (assurance ceiling = min over link strengths combined with Gap 24's
trajectory arithmetic) applies **only if finding-level anchors win**. Disproof verdicts have
mechanical, verdict-specific transitions: `VERIFIED` advances the finding unchanged; `CORRECTED`
supersedes it, preserving lineage and identity history; `REJECTED` retires it — **into the
findings registry, not into silence**: the rejected identity and reason persist, keyed to the
relevant source/candidate fingerprint — suppression holds while that fingerprint stands, and the
finding reopens for revalidation when the code it concerned changes — while the user-facing
report suppresses it. These transitions hold under any confidence design. Item 27's
fallback if confidence is rejected is strength-plus-disproof alone.

### Where we remain ahead

None of the nine runs anything like our loop: alibaba has **zero quality evals** (100+ Go test
files, none asserting finding quality) and a bare 4-value severity enum; Cloudflare has zero
tests of any kind; center-audit and Cloudflare both stop at the contract boundary — neither
applies a fix and re-verifies, which is precisely where the Actor-Critic loop lives; skillet's
eval runner is a stub (2 of 36 skills have evals); sentry's review skills ship no evals at all.
Severity anchors, mechanical gates, the findings registry, the challenger panel, and the 5-layer
suite have no counterpart anywhere in the wave. The capability gaps above are additive to that
position, not corrective of it.

## Improvement backlog (ranked at discovery)

| # | Change | Skill | Value | Cost | Status |
|---|---|---|---|---|---|
| 1 | Evidence-redaction rule + credential-shape quarantine gate; retrospective audit tracked separately | contest-refactor | High (security) | Low-Moderate | Design-ready |
| 2 | `eval-guard` gate, pre-commit + CI with a defined containment step on bypass: substantive skill-prose change requires an eval touch or a waiver trailer; acceptance includes a fidelity pin — the harness fails when it drifts from the artifact it evaluates | repo-wide | High | Low-Moderate | Design-ready |
| 3 | Verify hard-rule propagation at every dispatch boundary (challenger first), generated from one canonical source | contest-refactor | Medium-High | Low | Check first |
| 4 | Enforce flag/restraint pairing in `validate-fixtures.py` | contest-refactor | Medium | Low | Design-ready |
| 5 | `arm_b` 2×2 factorial: {weak, strong executor} × {backlog, self-contained handoff}, preregistered interaction decision rule | contest-refactor | High if it moves | Moderate-High | Experiment protocol first |
| 6 | Confidence: two-stage experiment — does the Evidence Chain lose information; then finding-level anchors vs rule-level tiers vs binary burden-of-proof + `uncertainties[]` | contest-refactor | Medium-High | Moderate-High | Two-stage experiment |
| 7 | Assert retired prose stays retired — first target: the unreachable Check-3 sub-severity note rule deleted at `1abea0c`; inventory further retirements from the git log | contest-refactor | Low-Medium | Low | Design-ready |
| 8 | Strictness as a deterministic post-filter with pinned per-preset counts | contest-refactor | Medium | High | RFC only |
| 9 | **Judge-finding routing rule** — a verdict reading "correct in substance, wrong in wording" goes to an alignment set, never into a criterion edit | contest-refactor evals | High | Very low | Design-ready (second pass) |
| 10 | **Grader-alignment measurement** — diagnostic + validation + untouched-holdout sets, two blinded labellers, agreement + kappa with intervals and an explicit non-claim | contest-refactor evals | High | Moderate | Design-ready (second pass) |
| 11 | Split graders by axis; each states the axis it does *not* judge — two separated decisions: conversations per axis, and findings per validator call | contest-refactor evals | Medium-High | Low-Moderate | Candidate in T3 comparison |
| 12 | Declarative transition table in `canon/states.toml` | contest-refactor | Medium | Moderate | Design call (second pass) |
| 13 | Cost-proportional stage skipping (`skip_when` by size) | contest-refactor | Medium | Moderate | After item 12 + cost audit |
| 14 | **Host-attested execution-evidence ledger** — the record of what ran lives outside the model-writable boundary; downgrades to a consistency check where no attestation exists | contest-refactor | High (anti-fabrication) | Moderate | **DESIGN DONE 2026-08-18** (`analysis/contest-refactor/ITEM14-HOST-ATTESTATION-DESIGN-2026-08-18.md`). Finding: **no harness offers a genuine attestation boundary as deployed** — all five fire hooks at the *same OS privilege* as the agent's own shell. Claude Code (managed settings) and Copilot CLI (`policy.d`) have admin-only tiers, both needing org/MDM deployment this repo lacks; this repo has zero hook config for any harness. So `attestation_status` can only ever read `consistency_check` or `unavailable` today, never `attested` — the honest-downgrade field is the deliverable, not a placeholder for a boundary that arrives later. Also surfaced a real defect in the obvious reuse path: `source_rev` is HEAD-sha-only and `candidate_fingerprint` hashes the artifact payload, so neither binds working-tree content — a pre-fix passing run could replay as post-fix evidence while Step 3's fix is uncommitted. Needs a new working-tree fingerprint. Does NOT defeat a model that deliberately forges a matching-format record at the wrapper's own privilege |
| 15 | **DAG-shaped grading** — rubric as a graph of binary questions, score computed from the path | contest-refactor evals | High | Moderate | Conditional on node-pilot |
| 16 | Mechanize structural assertions before aligning the judge; acceptance: every selftest execs the shipped artifact, never a reimplementation | contest-refactor evals | Medium-High | Moderate | Sequencing (third pass) |
| 17 | Halt subtype for context/budget exhaustion + handoff fields | contest-refactor | Medium-High | Low-Moderate | **Representation SHIPPED 2026-08-18** as `HALT_EXHAUSTION` — a terminal state sibling to `HALT_LOOP_CAP`, *not* a `halt_subtype` (`halt_subtype` means rubric stagnation; filing a resource death there would corrupt G37's semantics). New `canon/exhaustion-kinds.toml`, gate **G45** (record shape + the detection↔kind honesty coupling: a `preventive_step_budget` detection may claim only `kind: unknown`), G34/G37 extended, handoff template + three-deaths note + atomic-write rule in `halt-handoff.md`. **Pressure signal still undesigned** — no threshold ships or is read from config, so preventive checkpointing is a judgment call with its weakness stated in prose (a run near its limit is least able to notice); `host_meter` deliberately omitted from canon until a producer exists |
| 18 | Provenance envelope at the explicit ingress adapters (`--incidents`, trackers, remote fetches); whole-read mediation only as a future spike | contest-refactor | Low-Medium | Low-Moderate | Design-ready (third pass) |
| 19 | **Discriminating-power classifier** — fitted on development outcomes; labels validation/holdout lift cases retrospectively (never excludes); absolute-contract cases live in a separately reported contract suite, excluded from lift claims | contest-refactor evals | High | Low-Moderate | **MACHINERY SHIPPED 2026-08-18**; fitting deferred with the A/A sweep (ledger). All 5 categories incl. `fail_with_skill_but_pass_without` — the one Gap 17 says had no detector. Never-excludes proved by identical pre/post denominators; `fit_discrimination_rule()` raises on any non-development record; contract cases gated at `compute_lift()`, the single choke point. Judge-alignment contamination is **structurally impossible**, not merely documented — the module is typed to `LiftResult`, which reviewer-cases cannot produce. Only one free parameter exists (`min_direction_consistency`); the rest are inherited or definitional |
| 20 | **A/A noise floor + paired significance gate** — identical-build distribution pinned per keyed config; exact McNemar or paired permutation with preregistered effect/alpha/power and an explicit inconclusive outcome | contest-refactor evals | High | Moderate | **MACHINERY SHIPPED 2026-08-18**; the A/A run itself is deferred to a batched sweep (ledger). Exact McNemar (not the z-test — our arms are paired), paired permutation for continuous scores, 6-field floor key where any mismatch fails loudly, case as the unit of analysis (pseudo-replication selftested). `evals/noise_floor.json` ships **empty**: absence of a floor makes a lift claim `unreportable`, never floor=0. α=0.05 two-sided so a *harmful* skill is detectable |
| 21 | **Trial-validity taxonomy** — `invalid` reserved for exogenous harness failures, reported per arm with reasons; adherence failures always count; asymmetric invalidity voids the comparison | contest-refactor evals | Medium-High | Moderate | **SHIPPED 2026-08-18** — `canon/trial-validity.toml` (4 exogenous reasons, closed; 5 adherence/candidate modes recorded as deliberately unrepresentable), `scripts/_trial_validity.py`, void thresholds preregistered-and-unfitted (0.20 per-arm, 0.10 asymmetry), denominator preservation and `historical_validity() -> not_recorded` both selftest-pinned. Measured baselines were **not** back-filled — 8 files took a `schema_version` bump only, no rep record touched. **Follow-up, now well-specified:** give `exec_replay_grade.py` the real 0/1/2 split it lacks (deep-dive:686) and have it consume this taxonomy rather than reinvent one; deferred because classifying its missing-inputs cases needs harness dispatch context |
| 22 | **Paired with/without baseline** — same-turn paired runs scoring the delta; outcome criteria both arms can satisfy, skill-contract criteria reported separately, never mixed into lift | contest-refactor evals | High | Moderate | **SHIPPED 2026-08-18** (`49a2c48` mechanism + `de02426` corpus). Delta is **signed, not floored at zero** — a deliberate divergence from skilllens, because flooring hides Gap 17's "skill may be hurting" category. Manipulation failure **counts, never voids** (item 21's boundary, seam selftested both ways). 165 assertions classified 151 outcome / 14 skill_contract; tautology screen gated in validate-repo.py, 70 declared exceptions, 0 undeclared |
| 23 | **Detection-lens expansion** — latent-premises, retry-safety, operational, and reference-comparison lens families; Wildcard + "obvious things" anti-taxonomy agents; run-numbered multi-run recall with prior-run gap targeting | contest-refactor | High | Moderate | Decompose per lens (fifth pass) |
| 24 | **Deterministic selection + coverage manifest + resumable scan** — ordered gates with typed exclusion reasons; disjoint coverage sets with derived terminal state; fingerprint-keyed resume; churn prior; escalate-on-hit | contest-refactor | High | Moderate-High | Decompose; coverage-unit design first |
| 25 | **Tool-grounded substrate + per-language rules** — cheap-first tool ladder; don't-duplicate-deterministic-tooling mandate; precision preambles with explicit negative clauses and version-conditioned rules; inherits items 1/3/18's redaction + payload controls (no durable raw tool output; digests attested per item 14 or downgraded) | contest-refactor | High | Moderate | Decompose; after items 1, 3, 18 |
| 26 | **Computed evidence anchoring + strength grades** — model emits the quote, engine computes the lines; A/B/C/D strength per link; two independence fields (execution-context provenance; source/causal lineage with an `unknown`/`needs-adjudication` state); trajectory gap arithmetic | contest-refactor | High | Moderate | Design-ready (fifth pass) |
| 27 | **Per-finding disproof pipeline** — root-cause dedup → separate disprover → fresh-agent VERIFIED/CORRECTED/REJECTED (incl. remediation check); asymmetric-loss synthesis filter with protected-subject vetoes | contest-refactor | High | Moderate-High | After the finding-assurance decision |
| 28 | **Remediation contract + typed repair-revalidation record** — discriminated schema: strategy and revalidation general, simplification/latent-premise fields conditional on finding family; begins with an inventory of what G15-G17 already establish; leverage sort; refactor-promotion test | contest-refactor | Medium-High | Moderate | Design-ready (fifth pass) |
| 29 | **Static safety/structure scan of skill artifacts** — the rule sets in `aws-agent-skill-eval@13b2277b` `skill_eval/audit/{security_scan,structure_check,permission_analyzer}.py` (SEC-001..009, 20 STR codes); adopted only after a rule-by-rule delta against our 43 gates, with suppressions, FP targets, and a report-only→enforce rollout | repo-wide | Medium | Low-Moderate | Delta-audit **done 2026-08-17: measured, not adopted** — 22 NEW rules were dormant or 100% FP against documented conventions; 2 micro-patches (STR-015 token ceiling, literal secret prefixes) fold into eval-skill.py; see `analysis/contest-refactor/AWS-RULE-DELTA-2026-08-17.md` |

### Execution order

The table ranks by value at discovery; the tranches below are the dependency order to execute in.
Per the scoping note up top, every item gets a short design note before code, and anything that
touches grading, transitions, or halt states ships **shadow-first** — dual output compared against
current behavior, schema changes versioned rather than mutated — with telemetry on the new path
(scanner hits without values and scanner false-positive rate, waiver use, grader node
disagreements, transition violations, skip reasons, ledger-attestation failures, pressure-signal
availability, handoff/resume success, retrospective-audit disposition, invalid-trial counts and
rates by arm and reason, comparison-void events).

**Tranche 0 — prep, split per workstream (new).** Each tranche starts when *its own*
prerequisites are done, not when all of tranche 0 is. For slice 1a: the secrets/untrusted-text
threat model (items 1, 3, 18), the persistence-sink and dispatch/ingestion boundary inventory,
and the compatibility decisions — nothing more. For item 14: the evidence-fabrication threat
model. For tranche 3, immediately before it and blocking nothing else: build the
instrumentation (trial-validity semantics, then the paired-arm harness — items 21, 22), then
**split the raw cases before any with/without outcome is observed**; design the A/A floor and
the discrimination classifier (items 20, 19) on the development set only. Forward-going sets
admit cases by prospective structural eligibility alone (static properties — trial validity is
post-execution and never removes an admitted case); discrimination is applied to them
retrospectively, as labels. Record the current grader's
verdicts on all three sets before any redesign — the final-holdout baseline stored through a
blinded evaluator, so redesign authors never inspect it before selection — and freeze the
current artifact schemas. The compatibility policy, stated once: committed reviews and history stay readable;
validators dual-read across schema versions.

**Tranche 1 — evidence and persistence: items 1, 3, 14, 18, as two independently releasable
slices.** Slice 1a — the secret controls (items 1, 3): urgent, no host dependency. The
forward-looking quarantine gate ships as soon as its fixtures pass; the retrospective history
audit runs alongside as a separately tracked incident-response task and never delays it.
Slice 1b — the attested ledger (item 14), which waits on the host-attestation design. Item 18
ships independently of both slices once its bounded ingress adapters and RED cases are ready —
only item 14 needs the attestation boundary. Item 14 is the only control in the plan that
attests a command's *result and exit status* (item 16's hook-observed tool execution attests
that commands ran, not what they returned) — every existing gate reads model-authored artifacts,
so a fabricated build result passes all 43 of them; that is a different class of risk from
everything else here.

**Tranche 2 — governance: items 2, 4, 7.** Report-only first, then enforce; the pre-commit rule
mirrored in CI, with the honest caveat that direct-to-main means CI detects after landing — a
bypass triggers the defined containment step (revert, or an immediate eval/waiver follow-up).

**Tranche 3 — the grading redesign, instrumentation first.** Three suites are separated up
front, because treatment discrimination and grader alignment are different properties: the
**contract suite** (absolute invariants, excluded from lift), the **skill-lift suite** (paired
with/without outcomes), and the **judge-alignment suite** (sampled by judge-relevant strata —
disagreement shapes, verdict classes — never by treatment lift). The instrumentation order is
**21 → 22 → 20 → 19**: trial-validity semantics before the paired harness; the A/A floor on
that harness; then the discriminating-power work — whose rules are *designed* on development
outcomes and applied to validation and holdout only retrospectively, classifying cases without
ever changing the denominator (no validation or holdout lift case is excluded for its observed
delta). Then the redesign, with 9 in force throughout: **16 → 10 setup → variant definition →
comparison → lock → 10 holdout report**. Mechanize the structural assertions first (16); then
item 10's *setup phase* — the comparison cannot select a winner without the measurement
machinery it is meant to use, so the label protocol, the development and validation labels, the
alignment metrics, and the sealed holdout labels are all established over the semantic residue
**before** any variant is compared. Then define the graph-free node questions and the
axis/conversation variants *together*, and compare no-DAG, axis-split, conditional-DAG, and any
justified combination on the validation set — 15 and 11 are candidate designs inside that
comparison, never a mandatory cumulative sequence, with graph machinery built only if the node
classifiers clear a preregistered accuracy/repeatability threshold. Item 11's design note
separates conversations-per-axis from findings-per-validator-call. The selection sequence,
stated once: prototype on development, **select on validation, lock the design, then score the
sealed holdout once as item 10's final report** — never as input to another edit. Item 9 — the cheapest
high-value change in the list — is the routing rule protecting the loop throughout: a "correct
in substance, wrong in wording" verdict is a judge finding, never a criterion edit. Doing item 10's *setup* before item 16 would align a judge against questions it should never
have been asked — the documented 16 → 10-setup order is deliberate.

**Tranche 4 — state model: item 12, then 13 and 17.** Transitions become declarative before
anything reads them to skip a stage or to reach a new halt state.

**Tranche 5 — capability, decomposed into independently verifiable slices.** No item in this
tranche ships as one change. Item 23 splits into per-lens slices (each lens is its own change),
the anti-taxonomy agent pair, and multi-run orchestration — whose cross-run state must be
resolved against the findings registry and item 24's fingerprints before it exists. Item 24
splits into selection + coverage manifest, resume/invalidation, and traversal priors — and needs
its design note to define the coverage unit, the snapshot/invalidation model, crash-consistency,
and the relationship to `--scope`, `--cap`, and the registry. Item 25 splits into a bounded tool
runner (with defined behavior for absent, version-incompatible, timed-out, and partially
successful tools) and per-language rule packs, scoped initially to the two or three languages
the eval corpus actually exercises. Item 27 splits into root-cause dedup, shadow disproof,
verification, and synthesis filtering — designed together with the assurance mechanism selected
by item 6 (if any) and the finding-assurance model above, with state ownership, independence
guarantees, batching policy, and a cost ceiling stated. Every slice carries a deterministic acceptance test, a cost ceiling,
a promotion threshold, and a rollback trigger; item 26's output contract lands **before** any
new lens emits production findings. Tranche-5 telemetry: coverage conservation, resume
equivalence, stale-fingerprint invalidation, tool availability and duplication rates,
anchored/ambiguous/unanchored evidence rates, unresolved and adjudicated source-independence
claims, disproof rejection and correction rates, remediation-check accuracy, per-slice cost, and
measured paired lift. Ordering within the
tranche, as an explicit chain: **24 and 25 run as infrastructure in parallel with item 6's
experiment** (25 only after items 1, 3, and 18); **the finding-assurance decision follows the
experiment and gates the finalization of item 26's assurance semantics and all of item 27**;
then the item 26 evidence contract and item 28's general remediation fields → 23's lenses in
shadow → 28's family-conditional behavior → 27's disproof/verification pipeline. Item 29's
delta audit alone may run at any point, with its enforcement following its own staged gate. The bridge to tranche 3 stands, with the baseline
named precisely: **each new lens is admitted on measured *incremental* lift — the candidate
skill paired against the frozen pre-change skill on identical cases** (the no-skill arm measures
total skill value only), with detection, restraint, cost, and cross-lens interaction
preregistered as separate outcomes per lens and for the anti-taxonomy and multi-run slices,
evaluated under Gap 8's rules so admission is never scored on a benchmark selected for
responsiveness — and each lens design note specifies holdout hygiene (rotation, a reuse cap, or
a fresh sealed holdout for materially edited successors), so repeated admissions cannot quietly
consume the skill-lift holdout. Tranche-3 additions from the fifth pass: the
`max_error_rate` coverage gate on the `invalid` category, the judge-failed-every-case
broken-instrument detector, deterministic-first grading with per-assertion `method` provenance,
judge-sample stability as a persisted artifact, and — for continuous outcomes meeting its
assumptions — repeated-measures ANOVA (case as blocking factor) if the design ever exceeds two
arms, with Cochran's Q or GEE as the binary/ordinal alternative.

**Experiments, not tranches: items 5 and 6.** Each needs a protocol with a preregistered decision
rule before any run — Gap 2's cautions for item 5, the labelled Evidence-Chain comparison for
item 6. **Item 8 stays an RFC.**

## Deliberately not adopted

- **Cloudflare security-audit** — originally excluded by instruction (security-only); later cloned as a **methodology exemplar** with the owner's approval and audited in the fifth pass. Its security *content* (attack classes, vulnerability references) remains excluded; only its loop mechanics (adversarial validation, multi-run recall, anti-taxonomy agents) were mined.
- **mhylle's task primitives** — Claude-specific (`TaskCreate`/`TaskUpdate`, subagent types,
  `context: fork`); the partition/resume *model* is portable, the implementation is not.
- **senior-engineering-partner's ~80 KB standing doctrine** — the author acknowledges adherence
  varies at that size. Our progressive-disclosure split (`references/*.md` loaded per phase) is the
  better shape, and logic-lens's per-phase loading rules are a closer model to copy than this one.
- **brooks-sweep's auto-apply mode** — applies safe fixes automatically. Our Actor/Critic separation
  with an implementation reviewer before commit is the stronger posture; nothing to import.
