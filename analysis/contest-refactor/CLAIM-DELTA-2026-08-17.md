# Claim Delta — 2026-08-17 (first competitor refresh since 2026-07-13)

Trigger: `refs/competitors/` was refreshed for the first time since the July clone pass. 22 of 48
clones advanced; after the same-day prune, **18 surviving clones carry new upstream work**. This doc
records what changed, which of our skills it touches, and the adopt / reevaluate call for each.

Scope note: unlike the 2026-05 deltas, findings here land across **all three workflow skills**
(contest-refactor, peer-plan-review, quorum-review), because the corpus is now bucketed per skill.

**Evidence discipline** — every finding marked **READ** was verified by reading the upstream source
or diff at the SHA given. Findings marked **SUBJECT-ONLY** are inferred from commit subjects and
have *not* been source-verified; do not act on one without reading it first.

---

## Adopt candidates

### 1. Reviewer failure must not read as approval — **READ**

**Upstream**: levnik `plugins/review-suite/skills/ln-11-plan-reviewer/SKILL.md:104` @ `5bf66c5`

> Treat reviewer unavailability, tool failure, rate limits, or questions as coverage limitations,
> not evidence that the plan is sound.

Paired with an output-contract line requiring the reviewer to *emit* its coverage limitations:
"Independent challenge: one round, selected perspectives, and coverage limitations."

**Touches**: `peer-plan-review`, `quorum-review`.

**Why it matters here**: our transport already retains partial output on timeout and sweeps orphans,
so we survive a dead reviewer *mechanically*. The open question is whether the **verdict** path
treats a reviewer that never returned as an absence of evidence or silently as a non-blocker. A
5-reviewer quorum where 2 died is not a 3-reviewer quorum; it is a 5-reviewer quorum with a hole,
and the artifact should say so. This is the fail-closed analogue of the standing
"single APPROVED is false comfort" position.

**Call**: **ADOPT** — verify the verdict path first, then encode "unavailable reviewer = declared
coverage limitation, never a pass" and surface it in the artifact. Small change, fail-closed.

### 2. Scrub secrets before dispatching to an external agent — **READ**

**Upstream**: pauhu `skills/codex-review/SKILL.md` @ `7802232` (rewritten this cycle)

> **Pre-dispatch gate: don't leak secrets to Codex** — check for a `.codexignore` file in the repo
> root (same syntax as `.gitignore`). If present, honor it. Codex **must not receive** API keys,
> tokens, passwords, `.env` contents, or other credential material. Scrub these from the diff/scope
> before dispatch. If a blocked or sensitive path is in scope, remove it or narrow the prompt.

**Touches**: `peer-plan-review` (6 external CLIs), `quorum-review` (same, times N reviewers).

**Why it matters here**: we hardened the *inbound* direction (opencode read-only, deny policies, so
the reviewer cannot write). The **outbound** direction is unguarded: we hand a plan or diff to
Codex / Copilot / agy / Gemini / opencode with no credential filter. Every reviewer added multiplies
the exposure. This is the one finding in this pass that is a security gap rather than a quality
improvement.

**Call**: **ADOPT** — a pre-dispatch scrub with a repo-local ignore file, applied once in the shared
transport so both skills inherit it.

### 3. Escalate the executor inside the cap, don't just count rounds — **READ**

**Upstream**: superpowers `skills/subagent-driven-development/SKILL.md:375-386` @ `b36e082`

- Rounds 1-3: resume the **original** implementer (context intact).
- Rounds 4-5: fresh implementer **on a more capable model**, framed as
  *"A prior implementer attempted this task [N] times; you own it now. Read the report file for
  what was tried."*
- Rationale given: "A loop that survives three resumes usually means the implementer cannot see its
  own problem — fresh eyes and a capability bump in one move."

**Touches**: `contest-refactor`.

**Why it matters here**: we measured the *downward* substitution (arm_b cheaper executor,
claude-haiku-4-5, 2026-06-28) and rejected it — safe on mechanical revert, unsafe on risk-boundary
judgment. The **upward** move at a late round is the unmeasured inverse, and it is aimed at a
failure mode we already model (converged vs exhausted cap, G37 residual accounting). Fresh-context
reset and tier bump are two separable levers; upstream ships them fused.

**Call**: **MEASURE, don't ship** — this is a judgment lever, and the standing result is that
judgment levers park or lighten under RED-first measurement. Needs a corpus of runs that reach
round ≥4 before it can be scored. Separate the two levers if measured.

### 4. A re-review that structurally cannot extend the loop — **READ**

**Upstream**: superpowers `skills/subagent-driven-development/SKILL.md:397-404` @ `b36e082`

> The re-reviewer verdicts each finding ADDRESSED or NOT ADDRESSED and flags new breakage **in the
> fix diff only**. New Critical/Important breakage in the fix diff joins the open findings list.
> Out-of-scope observations go to the ledger as deferred minors — **they never extend the loop**.

**Touches**: `contest-refactor`.

**Why it matters here**: this is loop-termination by construction rather than by cap. A critic that
may raise anything on re-review can keep a loop alive indefinitely without any single step looking
wrong; scoping the re-review to the fix diff removes that path. Worth checking whether our Critic's
re-review is diff-scoped or free-roaming.

**Call**: **ADOPT if not already covered** — verify current re-review scope first. If free-roaming,
this is a small prose + gate change with a real termination payoff.

### 5. Sweep the gates for fail-open, one tripwire per gate — **READ**

**Upstream**: gstack `94993f74` (v1.61.0.0) @ `c86e647`

> fix wave: guards failing open / silent failures (9 fixes, 4 community PRs absorbed)
> **Every fix ships with a tripwire that proves the guard actually guards.**
> Every new test was first run against the unfixed code and confirmed failing, then confirmed
> passing after the fix.

The bug class they name: "guards and tools that reported success while doing nothing." Their worked
example is a destructive-command guard that inspected only the *last* `rm` in a chain, so
`rm -rf /; rm -rf node_modules` was waved through by its safe trailing target.

**Touches**: `contest-refactor` (G1–G36).

**Why it matters here**: we have hit this exact class repeatedly but always singly and always by
accident — the G30 double-fire caught by codex in the G35/G36 six-provider review, and the
token-gate false-pass that G33 was built to kill. The method worth importing is not a fix, it is the
**sweep**: enumerate every gate, ask "what input makes this report PASS while doing nothing", and
leave a failing-first tripwire behind. RED-first is already our house style, so only the
enumeration is new.

**Call**: **ADOPT the method** — a bounded fail-open audit across the gate catalog. Moderate cost,
and the cost is knowable up front (one probe per gate).

### 6. Make every eval metric classify errors the same way — **READ**

**Upstream**: wshobson `d0b9448e` — "stop counting errored runs as activations" @ `d6837ae`

An errored SDK run whose result carried diagnostic text ("API error") returned `activated=True` and
`errored=True`, so one run counted in **both** `n_activated` and `n_errored` — inflating the
activation rate and the triggering contribution to the composite score. The fix's reasoning is the
transferable part:

> That also left the activation path as the odd one out: output consistency and token efficiency
> already filter on `not r.errored`, and run_simulation's own except branch reports a failed run as
> activated=False. An SDK-reported error now looks the same as a transport exception.

**Touches**: `contest-refactor` eval suite (all 5 layers).

**Why it matters here**: this is the same bug class as our own "spend-limit death ≠ MISS" — a
harness that mistakes *failure to run* for *a result*. We fixed ours at one site. Upstream's framing
is the generalization: the defect is **inconsistency across metrics**, so the audit is "does every
layer classify every error state identically", not "is this one probe right".

**Call**: **ADOPT the audit** — cheap, mechanical, and it protects numbers we already rely on.

### 7. Split graders per case into activation / recall / precision — **READ**

**Upstream**: trailofbits `plugins/variant-analysis/evals/<case>/graders/` @ `04b2411`, from the
"convert the skill to a dynamic workflow" series (5 skills converted this cycle).

Each eval case ships `prompt.md` plus separate graders:
`skill-fired.md` (activation), `recall-cross-api-variants.md` (recall),
`precision-safe-sites-ruled-out.md` (precision).

**Touches**: `contest-refactor` evals.

**Why it matters here**: our standing finding is that the advisory evals measure restraint and
vocabulary rather than recall, and that recall lift is 0 on Sonnet and Haiku because the planted
defects are too legible. That distinction currently lives in prose and in our heads. Making it
structural — a per-case grader for each axis — means the harness reports which axis moved instead of
requiring the reader to know which axis a suite was ever capable of measuring.

**Call**: **ADOPT selectively** — worth it where a suite already conflates axes. Not a rewrite.

### 8. Scan installed third-party skills for prompt injection — **READ**

**Upstream**: skills-janitor v1.6 `skills/janitor-security/SKILL.md` @ `4a4c013`

Heuristic scan across every scope (user, project, codex, plugin) for: injection phrases
("ignore all previous instructions", "do not tell the user"); imperative text hidden in HTML
comments; zero-width and bidi unicode between plain characters; large decodable base64 blobs.
Cites Snyk's ToxicSkills (2026) finding prompt injection in roughly a third of tested community
skills.

**Touches**: our install posture, not a skill we ship.

**Why it matters here**: we symlink ~20 third-party skills into five agent directories, including
three Apple auth skills we deliberately never edit — exactly the trust shape this scans for.

**Call**: **RUN IT, don't build it.** One-off consumption of someone else's tool.

### 9. Fail validation when a platform is documented unevenly — **READ**

**Upstream**: brooks-lint, "test: fail validation when a platform is documented unevenly" @ `d4b5c40`

> Adding dsh meant hand-syncing nine places… Nothing checked that, so a platform documented in
> English and forgotten in Korean would have shipped silently — the same failure mode that let the
> localized version badges go stale. Two checks in validate-repo.mjs, both **deriving their inputs
> rather than restating them**.

**Touches**: repo conventions (CLAUDE.md documents five harness install directories; README carries
the catalog).

**Why it matters here**: we have the same shape — a skill must be symlinked into five agent dirs and
listed in the README, and nothing checks that a new skill reached all of them. The transferable
detail is "derive the list from disk, never restate it".

**Call**: **ADOPT if cheap** — a derived-from-disk check, not a new hand-maintained list.

---

## Reevaluate

### 10. levnik abandoned the artifact contract we modeled a gap doc on — **READ**

Already written into the four affected gap docs today. Summary: the "Skills v2" rewrite (`5967ec7f`,
2026-07-11) deleted every `shared/references/*_contract.md`; no JSON envelope, `summaryArtifactPath`,
`schema_version`, or `output_dir` survives. The replacement is in-band markdown — all 25 skills
declare an **Execution contract** whose Definition of Done is an ordered checklist, and each returns
a `Checklist: X/Y complete` + `Incomplete: <item — reason; impact; next action>` header.

Scale moved the same way: **137 skills → 25**, and `codebase-audit-suite` went from 35+ narrow
workers to **5 broad auditors**.

**Implication**: PARALLEL-CRITIC-ARTIFACT-CONTRACT-GAP models prior art its author has since
replaced with prose, and the "decompose the Critic into many specialty workers" direction now has
its main exemplar moving the other way. Both docs already carry the drift note. The strategic read —
that consolidation beat decomposition here — deserves a decision, not just a footnote.

### 11. A serious shop dropped required SKILL.md body sections — **READ**

trailofbits `#216` dropped the "When to Use" / "When NOT to Use" requirement and deleted the
`REQUIRED_SKILL_SECTIONS` check from `validate_plugin_metadata.py`.

**Precision matters**: that is a check on **body sections**, not on the description. Our
`eval-skill.py` requires a "Use when…" trigger *in the description*, which is what drives routing.
The two are not in conflict, and this is not a reason to weaken our description convention.

Read it instead as one more datapoint for the standing position: judge by practical output, not by
validator hardening.

### 12. PPR transport — upstream converged on our design, then widened it — **READ**

sub-agents-skills @ `c7c84dc` refactored to a `_BACKEND_SPECS` table mapping each backend to
(arg builder, permission map, effort-option flag): `codex → model_reasoning_effort`,
`claude/glm/kimi → --effort`, `grok → --reasoning-effort`, `opencode → --variant`,
`cursor-agent/gemini → none`. New backends this cycle: **Kimi**, alongside GLM, Grok, cursor-agent.

This is the same shape as our `common/common/providers/registry.py` — convergent design, arrived at
independently, which is mild validation of the vendoring split. The optional part is breadth: Kimi /
GLM / Grok / cursor-agent are backends we do not offer.

**Call**: no structural change. Add backends only on demand.

---

## Directional, not actionable

- **trailofbits: skills → dynamic workflows.** Five skills converted this cycle (variant-analysis,
  insecure-defaults, audit-context-building, spec-to-code-compliance, semgrep scan fan-out), each
  landing with an eval suite. A security shop moving orchestration out of prose and into scripted
  workflows is a directional signal for contest-refactor's own orchestration. — **SUBJECT-ONLY**
  beyond the eval-directory listing.
- **levnik: risk-scaled panel size.** "Run exactly **one** independent review round… one blind
  reviewer for small low-risk work, two distinct reviewers" for larger. Compare to quorum-review's
  operator-chosen N with a threshold. A risk-scaled default is a cheap policy question. — **READ**.

## Checked, no signal

| Clone | New work this cycle | Verdict |
|---|---|---|
| `alirezarezvani-claude-skills` | 58 commits — GTD/weekly-review/meetings/deep-work productivity plugins | Off-mission |
| `awesome-code-review` | Ruby/Rails review guide (964 lines) | Off-mission |
| `anthropic-claude-code` | AWS gateway example deployment assets | Off-mission |
| `logic-lens` | zh-locale output regressions; execution verification became the default | Minor |
| `fastruby-tech-debt-skill` | Self-contained HTML report, Trivy, color-coded score | Presentation only |
| `coderabbit-skills` | Gemini CLI extension + Antigravity CLI packaging | Distribution only |
| `archgate-cli` | 68 commits — `--strict`, SARIF output, severity tiers, ADR sandbox boundary | GOVERNANCE-GAP Gap C already settled; SARIF/severity tiers are minor — **SUBJECT-ONLY** |
| `mattpocock-skills` | 149 commits, mostly prose polish; "stop skills from calling other user-invoked skills" is the one item worth a later look | **SUBJECT-ONLY** |
| `open-code-review` | Dashboard child-env inheritance with a criteria-governed denylist — convergent with our opencode deny policy | **SUBJECT-ONLY** |
| `gstack` (rest) | 42 commits; the fail-open wave above is the transferable part | Rest is product work |
| `brooks-lint` (rest) | DeepSeek Harness support; "stop model-invoked skill wrappers from looping" | Minor — **SUBJECT-ONLY** |

---

## Ranked shortlist

| # | Action | Skill | Value | Cost |
|---|---|---|---|---|
| 2 | Scrub secrets before outbound dispatch | peer-plan-review, quorum-review | High (security) | Low |
| 1 | Reviewer failure = declared coverage limitation | peer-plan-review, quorum-review | High | Low |
| 6 | Audit error classification across all 5 eval layers | contest-refactor | Medium | Low |
| 4 | Confirm the re-review is diff-scoped | contest-refactor | Medium-High | Low |
| 5 | Fail-open sweep across G1–G36, one tripwire each | contest-refactor | Medium-High | Moderate |
| 8 | Run janitor-security against installed skills | (install posture) | Medium | Low |
| 7 | Per-case activation / recall / precision graders | contest-refactor | Medium | Moderate |
| 9 | Derived-from-disk harness coverage check | repo | Low-Medium | Low |
| 3 | Escalate executor at rounds ≥4 | contest-refactor | Unknown | Needs a corpus first |
