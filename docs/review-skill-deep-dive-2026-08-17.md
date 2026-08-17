# Review-Skill Deep Dive — 2026-08-17

Deep dive into six external review/audit skills, compared against `contest-refactor`,
`peer-plan-review`, and `quorum-review`, to produce a comprehensive improvement plan.

Sources: four repos cloned today plus two already in the corpus (`brooks-lint`, `logic-lens`)
that were ranked highest by the survey that prompted this work.

## Evidence discipline

Every claim below is marked:

- **VERIFIED** — read in the upstream source, or checked against our source, at the SHA given.
- **INFERRED** — read once, not cross-checked; treat as a lead.

Claims about *our* implementation were checked by grep/read against the working tree at
`984aa5b`. Where our coverage was confirmed, it says so — several apparent gaps turned out to be
already built, and those are recorded as "no action" rather than dropped.

---

## What was cloned, skipped, and not found

| Repo | Status | Notes |
|---|---|---|
| `shadcn/improve` | **cloned** → `contest-refactor/shadcn-improve` | 8.9k★, MIT. Biggest by stars in the whole corpus. |
| `bjgreenberg/senior-engineering-partner` | **cloned** → `contest-refactor/senior-engineering-partner` | 146★, Apache-2.0. |
| `ngmeyer/skills` (`rigorous-review`) | **cloned** → `contest-refactor/ngmeyer-skills` | 2★, MIT. 10 skills; `rigorous-review` is the one of interest. |
| `mhylle/claude-skills-collection` | **cloned** → `contest-refactor/mhylle-skills-collection` | 17★, MIT. 38 skills. |
| `hyhmrright/brooks-lint` | already held | Refreshed today (`d4b5c40`). |
| `hyhmrright/logic-lens` | already held | Refreshed today (`69de591`). |
| `awesome-skills/code-review-skill` | already held | Refreshed today (`95c707b`). |
| `alirezarezvani/claude-skills` | already held | Refreshed today (`aa8d7788`). |
| Cloudflare `security-audit-skill` | **skipped** | Security-only, excluded by instruction. |
| `center-audit` | **not found** | No owner given in the source material. `gh search repos`, `gh search code`, and name variants all return nothing matching the description (evidence IDs, trajectory validation, calibrated confidence, repair contracts). Treat as unverified until an owner/path surfaces — the corpus has prior fabrications on record (`RESEARCH-DELTA.md`). |

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

This is not a large change. `severity-anchors.toml` already establishes the pattern; a
`confidence-anchors.toml` with the four behavioral anchors, a field on the finding, and a gate that
suppresses below the bar *except* for high-severity-low-confidence (routed to the HALT_SUCCESS
challenger, which we already have) would land in the existing shape.

**Interaction to check first**: our Evidence Chain already demands Claim → Source → Consequence →
Remedy, which forces some of what confidence-75 asks for. The honest question is whether confidence
adds a distinction the Evidence Chain cannot already carry — decide that before building.

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

The fix is small and mechanizable: an evidence-redaction clause (cite `file:line` + credential
*type*, never the value) plus a gate that pattern-scans emitted artifacts for common credential
shapes — `project-config.md:88` already carries a usable pattern list (`AKIA`, `sk-`, `xoxb-`).

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

### Gap 5 — Flag/restraint pairing is convention, not machinery · **VERIFIED gap, small**

`evals/README.md` documents the flag/restraint pairs well — every "should reject" has a legitimate
look-alike that must not be flagged, with the carve-out under test named per pair. But
`validate-fixtures.py` does not enforce the pairing: grep finds the discipline only in the README.

brooks-lint takes the stronger position in two places — `validate-repo.mjs` fails the build if the
risk references lack a `### What Not to Flag` section, and 9 of its 30 frozen samples are
false-positive cases that must stay clean.

Enforcing "every flag fixture names its restraint twin" in `validate-fixtures.py` is a small change
that protects a property we already believe in.

### Gap 6 — Hard rules may not survive challenger dispatch · **INFERRED, needs a check**

We have G14 (payload not instruction). `halt-verifier.md` dispatches challengers through the
provider-adapters spawn profile. shadcn's warning is specific: subagents do not inherit the parent's
hard rules, and omitting them is how a live token ends up quoted.

**Action is to verify, not to build**: read the challenger prompt and confirm it carries
payload-not-instruction (and, once Gap 3 lands, the redaction rule) verbatim. If it does, no change.

### Gap 7 — Strictness is model-applied, so it cannot be regression-tested · **VERIFIED, larger change**

`--strictness standard|aggressive` modulates model judgment, so its drift is only observable by
running a model and reading output — the expensive, high-variance path our own notes describe.

brooks-lint separates the two concerns: the model produces a report, and a deterministic parser
applies the strictness preset, with expected finding counts per preset pinned in a frozen corpus
(strict 34 / balanced 54 / legacy-friendly 74). Preset drift then fails a test with no model in the
loop.

This is architecturally larger than the other items — it means treating strictness as a
deterministic post-filter over a superset of findings rather than as an instruction. Recorded as an
option with an honest cost, not a recommendation.

### Gap 8 — No grader-alignment measurement anywhere in the eval suite · **VERIFIED gap, high value**

Second-pass finding. `great_cto` carries 450 scripts, 57 hooks, 114 eval files and 9 TOML canon
files, and appears **twice** in our entire 21-doc analysis corpus. The thing we missed is in
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
2. **Measure agreement only on disagreement cases.** *"Two graders agreeing on an easy case says
   nothing about either."*
3. **The routing rule** — *"a verdict whose reason contains 'correctly identifies… but does not
   name' is a judge finding, not an agent finding. Route it here rather than into a prompt edit."*

Rule 3 is the operationally important one, because the failure it prevents is self-concealing: a
false failure invites softening the criterion, *"which is how a suite quietly stops measuring"* —
they record it happening three times in one session before anyone named it.

`wshobson-agents` implements the machinery version independently: PluginEval reports **Cohen's
kappa** across judges when `judges > 1`. Two independent implementations in the corpus; neither
appears in any of our 21 gap docs.

**Our exposure is real but narrower than theirs.** Layers 2/3 grade semantically via a `grader.md`
subagent, and `evals/README.md:154` states the measured axis is **"restraint + vocabulary, NOT
recall"**, with criteria of the form *"does `flagged_smells` name the canon smell"*. Naming is
partly legitimate here in a way it was not for great_cto — canon smell names **are** the artifact,
consumed by gates and dedup, so requiring the name is substantive, not cosmetic. But we have no
measurement of whether our grader agrees with a human on the cases where it matters, and
`evals/README.md:248-249` already concedes the point: the current measurement is *"within-judge
robustness, not lift over a bare model and not external validity (that needs more scenarios + a
second judge)."*

So this is a named-but-unbuilt next step, and great_cto supplies the design: keep only the disputed
cases, hand-label them with reasoning, report agreement and kappa, and state honestly what the
number is not. Their own honesty note is worth copying too — the labels were written by the author
of the criteria, so *"a second labeller who did not write them would be worth more than another
twenty cases from this one."*

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
axis and requiring each to state its non-scope is a small change to the eval harness that makes a
mixed verdict impossible to produce by accident.

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

### Gap 11 — No cost-proportional stage skipping · **VERIFIED gap, ties to an open audit**

`great_cto` gates whole stages on project size. Its `decision-eval` skill refuses to run when
*"project_size is nano (overhead exceeds value)"*, and `pipeline.toml` carries
`skip_next_when = "depth=small"`.

contest-refactor has `--scope`, `--strictness`, and `--cap`, all of which tune *rigor* or
*extent* — none of which skips a phase because the work is too small to justify its cost. With
`RUNTIME-COST-AUDIT-2026-08-14` open, an explicit "this stage is not worth running at this size"
rule is directly relevant, and it is the cheapest form of cost control available: not running a
step beats running it more efficiently.

### Gap 14 — Holistic judge calls where a decision graph would be reproducible · **VERIFIED, high value**

Third-pass finding, and it is the *implementation* Gaps 8, 9 and 11 were missing. Same repo that
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

This attacks the kappa-0.00 problem structurally rather than by measuring it: a narrow binary
question is one a grader answers the same way twice, so agreement stops being a variable to
estimate. It composes with Gap 9 (one axis per grader) and Gap 17 below (mechanize the structural
part) into a single coherent redesign of Layer-2/3 grading — which is currently one semantic
verdict per case from a `grader.md` subagent.

### Gap 15 — The verification oracle is self-reported · **VERIFIED gap, high value**

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

Cost is low relative to the exposure — a wrapper that records command, exit code, and truncated
output to an append-only lane file, plus a gate asserting that score-bearing build evidence has a
matching ledger entry.

### Gap 16 — No halt state for context or budget exhaustion · **VERIFIED gap**

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

We do not need their hook — our state is file-based and survives compaction. We need the **state**:
a halt subtype for pressure-death plus the handoff fields we already require elsewhere, so an
exhausted run terminates honestly instead of silently.

### Gap 17 — Shrink the judge's surface before trying to align it · **VERIFIED, refines Gaps 8-9**

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

### Gap 18 — Untrusted-content handling is prose, not a tool · **VERIFIED, low-medium**

G14 (payload not instruction) is a rule the model applies to itself. `gstack-issue-guard` is the
mechanical version: it fetches GitHub issue/PR text and **wraps it in a labelled trust envelope**
before the agent sees it, so the boundary between instruction and data is established by the
fetcher rather than by the reader's discipline.

Relevant to us at exactly one place — wherever contest-refactor ingests text it did not author
(incident files via `--incidents`, tracker text, ADRs). A wrapper is more reliable than a rule,
though the rule is not wrong.

### Checked, already covered or ahead — third pass

| Mechanism | Source | Finding |
|---|---|---|
| Token bill-of-materials | `gstack-context-bill` | **We are ahead.** `scripts/token-budget.py` does per-file counts, per-loop fixed-reload sums, full-run projection, *and* `--loaded-set <step>` proving which files a given step reloads — plus it prints whether the count came from tiktoken or the heuristic, so a number is never silently an estimate. No action. |
| Working-tree fingerprint | `gstack-wtree` | Different purpose. Ours (`candidate_fingerprint.py`) is a semantic fingerprint of the architecture-relevant payload; theirs is a cheap disk-state hash (~40× faster than a full re-hash via a stat-cache-seeded temp index). `source_rev` already covers our disk-state need. Perf idea only. |
| Exit-code discipline | `senior-engineering-partner/scripts/eval-guard.py` | Not a new gap — the *fix shape* for plan item 3. It exits **0 pass / 1 fail / 2 git plumbing error**, and documents that "CI and a local run are byte-identical". That third code is precisely what `exec_replay_grade.py` is missing when it folds "inputs missing" into "invariant failed". |

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

## Ranked improvement plan

| # | Change | Skill | Value | Cost | Status |
|---|---|---|---|---|---|
| 1 | Evidence-redaction rule + credential-shape gate on emitted artifacts | contest-refactor | High (security) | Low | Ready |
| 2 | `eval-guard`-style pre-commit gate: substantive skill-prose change requires an eval touch or an explicit waiver | repo-wide | High | Low | Ready |
| 3 | Verify the challenger prompt carries hard rules verbatim | contest-refactor | Medium-High | Very low | Check first |
| 4 | Enforce flag/restraint pairing in `validate-fixtures.py` | contest-refactor | Medium | Low | Ready |
| 5 | Re-measure `arm_b` with a self-containment contract on the handoff | contest-refactor | High if it moves | Moderate | Needs design |
| 6 | Confidence as a second axis + `confidence-anchors.toml` + P0-at-low-confidence carve-out | contest-refactor | Medium-High | Moderate | Decide vs Evidence Chain first |
| 7 | Assert retired prose stays retired (regression test on superseded instructions) | contest-refactor | Low-Medium | Low | Ready |
| 8 | Strictness as a deterministic post-filter with pinned per-preset counts | contest-refactor | Medium | High | Option only |
| 9 | **Judge-finding routing rule** — a verdict reading "correct in substance, wrong in wording" goes to an alignment set, never into a criterion edit | contest-refactor evals | High | Very low | Ready (second pass) |
| 10 | **Grader-alignment set** — disputed cases only, hand-labelled, agreement + kappa reported with an explicit non-claim | contest-refactor evals | High | Moderate | Ready (second pass) |
| 11 | Split graders by axis; each states the axis it does *not* judge | contest-refactor evals | Medium-High | Low | Ready (second pass) |
| 12 | Declarative transition table in `canon/states.toml` | contest-refactor | Medium | Moderate | Design call (second pass) |
| 13 | Cost-proportional stage skipping (`skip_when` by size) | contest-refactor | Medium | Low-Moderate | Ties to RUNTIME-COST-AUDIT (second pass) |
| 14 | **Independent execution-evidence ledger** — a wrapper, not the agent, authors the record of what ran and what it returned | contest-refactor | High (anti-fabrication) | Low-Moderate | Ready (third pass) |
| 15 | **DAG-shaped grading** — rubric as a graph of binary questions, score computed from the path | contest-refactor evals | High | Moderate | Ready (third pass) |
| 16 | Mechanize structural assertions before aligning the judge | contest-refactor evals | Medium-High | Moderate | Sequencing (third pass) |
| 17 | Halt subtype for context/budget exhaustion + handoff fields | contest-refactor | Medium-High | Low | Ready (third pass) |
| 18 | Mechanical trust envelope for ingested foreign text | contest-refactor | Low-Medium | Low | Ready (third pass) |

Items 1–4, 9, and 11 are independent and small. Item 5 is the one that could unblock a parked
decision. Items 6, 8, and 12 need a design call before any code.

**Item 9 is the cheapest high-value change in the list**: it is a triage rule for reading grader
output, costs nothing to adopt, and prevents the specific failure — softening a criterion in
response to a false failure — that makes an eval suite stop measuring without anyone noticing.

**Items 9, 10, 11, 15 and 16 are one project, not five.** The order matters: mechanize the
structural assertions (16), reshape what remains into binary questions on a graph (15), give each
grader one axis and a declared non-scope (11), *then* measure agreement on the residue (10), with
the routing rule (9) protecting the loop throughout. Doing 10 first would align a judge against
questions it should never have been asked.

**Item 14 is the one that is not about measurement.** Every gate we own reads model-authored
artifacts, so a fabricated build result passes all 43 of them. That is a different class of risk
from everything else in this table.

## Deliberately not adopted

- **Cloudflare security-audit** — excluded by instruction (security-only).
- **mhylle's task primitives** — Claude-specific (`TaskCreate`/`TaskUpdate`, subagent types,
  `context: fork`); the partition/resume *model* is portable, the implementation is not.
- **senior-engineering-partner's ~80 KB standing doctrine** — the author acknowledges adherence
  varies at that size. Our progressive-disclosure split (`references/*.md` loaded per phase) is the
  better shape, and logic-lens's per-phase loading rules are a closer model to copy than this one.
- **brooks-sweep's auto-apply mode** — applies safe fixes automatically. Our Actor/Critic separation
  with an implementation reviewer before commit is the stronger posture; nothing to import.
