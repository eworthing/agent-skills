# Loop-path displacement: inventory and design note (2026-08-21)

Design note before code, per the convention the item 24 and item 25 notes follow.

> **Status 2026-08-21: candidate A is SHIPPED.** Measured saving **4,251 tok/loop** on both paths
> (the estimate was 4,405; the new file's header and the two pointer stubs account for the
> difference). Apple 87,371 → **83,120**, generic 83,293 → **79,042**. Candidate B remains an owner
> call — **declined 2026-08-21**, see §9. §8 records what the split actually cost.

## 1. Why now — the constraint moved

The detection backlog's binding constraint is no longer detection reach. It is loop-path tokens.
[`docs/contest-refactor-detection-domains.md`](../../docs/contest-refactor-detection-domains.md)
carries fourteen named candidates; eleven still want loop-path prose, and the three that have been
measured (DD-04 `mid`, DD-13 `mid`, DD-14) consume **the entire authorised headroom between them**,
landing the generic margin at 158 of 84,200. Six queued candidates have never been measured and
there is no room for them.

So the useful question stopped being *"which domain is the lens blind to"* and became *"what is the
loop paying for on every iteration that it does not need on every iteration."*

## 2. The precedent this follows

Two files already came off the reload path by being **scoped**, not cut:

- `references/startup.md` — main-agent only, Step 0 work, never reloaded by the loop subagent.
- `references/halt-handoff.md` — scoped in prose to "when emitting any HALT state". Most loops are
  CONTINUE, so it is excluded from the reload set and recorded in `DECLARED_DIVERGENCES`.

The shape to hunt is therefore **content whose trigger is conditional but whose loading is
unconditional**. The two candidates below are that shape. The rejected list is mostly things that
*look* like that shape and are not.

## 3. Candidate A — `provider-adapters.md` is loaded whole for two of its eleven sections

**Saving: 4,405 tokens per loop, on both ceilings. Judgment risk: none. This is the proof of
concept.**

`loaded_set()` puts the whole 5,287-token file on Step 3. SKILL.md's own Reference Load Matrix
already says Step 3 needs less than that — `SKILL.md:78` scopes it to *"(reviewer-spawn profile +
read-only allow-list)"*, which is **882 tokens** of the file.

The rest is not ambiguous about who it belongs to. Its own headings name the step:

| Section | Line | Declared owner |
| --- | --- | --- |
| Detection | `:20` | **"read by SKILL.md Step -1 step 0.5"** |
| Reviewer read-only shell allow-list | `:34` | **Step 3 — keep** |
| Loop-spawn profile | `:44` | **"Step 0 onward"** |
| Reviewer-spawn profile | `:98` | **"Step 3 step 6" — keep** |
| Challenger-spawn profile + v5 panel manifest | `:145` | **"Step-1 HALT_SUCCESS challenge"** |
| Helper-spawn profile, Model overrides, When to upgrade, Skill-dir resolution | `:189`–`:238` | main-agent / Step 0 |

This is a **file-role misclassification, not a judgment call**: the scoping already exists in prose,
and `token-budget.py`'s divergence check simply cannot see inside a file to enforce it. The loop
subagent is charged 4,405 tokens per iteration for spawn profiles belonging to steps it never runs.

**Mechanism.** Split the two Step-3 sections into `references/provider-adapters-reviewer.md` and
have the Step-3 row load that. The remaining file keeps everything else and becomes main-agent
scoped. To avoid the drift this repo has been bitten by before, the new file is **canonical** for
those two sections and the parent references rather than restates them — the pattern already marked
at `architecture-rubric.md:112` for the Unified Seam Policy.

## 4. Candidate B — v5 panel material is live machinery for a dormant capability

**Saving: 2,634 tokens per loop. Judgment risk: real. Owner call, not an implementation detail.**

Four blocks describe a `schema_version: 5` panel shape: the v5 changelog in `output-format-json.md`
(1,315), G32's v5 portion in `validation.md` (763), and rules #6 and #36 in
`output-format-json-rules.md` (322 + 234).

No loop can legally emit v5 today. `provider-adapters.md:183-187` is explicit: *"**Zero entries are
recorded today.** … every profile therefore emits v4, and the machinery is live while the capability
is not."*

**Why this is not simply free.** "No loop can emit v5 today" is a statement about today, and a
single recorded capability entry silently makes it false. Displacing the v5 prose off the reload
path converts a dormant-but-ready capability into one that needs a load-path change before it can be
used — a capability regression wearing a token saving's clothes. The mitigating fact is that G32's
v5 portion has a script backstop (`scripts/_artifact_panel.py`), so a missed reload fails loudly at
pre-commit rather than emitting a bad artifact silently. That caps the blast radius; it does not
make the decision.

**Recommendation: hold B until A has shipped and proven the mechanism**, then decide it on its own
merits with the panel-certification owner.

## 5. Rejected — and why the biggest-looking win is the one to leave alone

**HALT-terminal judgment gates** (G21, G23, G30, G37, G38, G41, G45 — ~3,262 tokens in
`validation.md` alone) have exactly the conditional-trigger/unconditional-load shape, and are
individually larger than candidate B. They are still rejected:

- None has a script backstop. `validation.md` was grepped for `Mechanical:` / `Code owner:`
  citations; G16, G44, G47, G48 and G32-v5 have one, these seven do not. A missed reload on a
  backstopped gate is a loud pre-commit failure; on these it is a silently wrong terminal verdict.
- **G21 exists because of a documented production failure** — *"the agent reaching for HALT_SUCCESS
  when the backlog empties at sub-9.5 average"* (`validation.md:72`). Moving it off the
  unconditional path risks reintroducing that failure at the one moment per run where it is most
  consequential and least visible: the terminal verdict nobody re-derives.

A displacement pass that trades correctness for headroom is worse than a blocked backlog.

**False conditionals** — read as optional, fire on nearly every loop: G28 checkpoint freshness; G34
HALT-tail invariants (must check null-ness on CONTINUE too); G39/G42/rule-31/rule-34 backlog
attribution (G9 requires a non-empty backlog on every CONTINUE loop). **`implementation-reviewer.md`
in full** — it is the reviewer's verbatim spawn prompt and only the final halting loop skips Step 3.

## 6. Slice contract

| Slice | Acceptance | Ceiling | Promotion | Rollback |
| --- | --- | --- | --- | --- |
| **A. Split `provider-adapters.md`** | `_token_budget_selftest.py` green against an updated Reference Load Matrix; `--loaded-set step3` no longer lists the parent file; no section text duplicated across the two files | −4,405 tok/loop, both paths | ships on the matrix's own wording — Step 3's need was already declared narrower than its load | revert the split; one matrix row and one file move |
| **B. Displace v5 panel material** | v5 blocks load only where v5 can be emitted; `_artifact_panel.py` still fails a malformed v5 panel | −2,634 tok/loop | **owner call** — see §4 | restore the blocks to the reload path |

## 7. What A alone buys

Generic 83,293 → 78,888 against 83,700: margin **407 → 4,812**. Apple 87,371 → 82,966 against
87,800: margin **429 → 4,834**. That is roughly twelve times today's headroom from one file split,
and it clears every measured candidate plus the six that have never been measured — without the
authorised ceiling bump being spent at all.


## 8. What shipping candidate A actually took — three consumers the inventory missed

The split itself was one file move and one matrix row, as predicted. The consumers were not all
visible to a markdown-link grep, and the repo's own guards caught every one:

1. **`_provider_detection_selftest.py`** asserted against `provider-adapters.md` for the codex
   `--sandbox read-only` flag and the opencode `permission` config — both in the moved reviewer
   profile. It failed loudly and correctly. Fixed by reading **both** halves: they are still "the
   provider adapters" for the assertions' purposes, and a guard that silently stops covering the
   profiles it exists to protect is worse than a failing one.
2. **`_reviewer_baseline_selftest.py`** failed on the prompt pin. Two of the repointed references
   sit inside `implementation-reviewer.md`'s **verbatim reviewer prompt**, so the split changed the
   prompt's sha. Re-pinned per the guard's own remediation instruction, with a sixth entry appended
   to `measurement.prompt_staleness` recording that the allow-list content moved byte-identically
   and the edit is unmeasured like the five before it.
3. **The soft-margin probe in `_token_budget_selftest.py` was a test that could not fail.** It set
   its probe ceiling to `shipped_ceiling - 400`, which only lands inside the soft margin while the
   measurement sits near its ceiling. Cutting 4.3k tok/loop moved the measurement far below, and the
   probe silently stopped exercising the soft margin at all. Rewritten to pin against the **current
   measured value** (`actual + 100`). This is the DD-01 tautological-oracle shape — an assertion
   that passes regardless of the behaviour it names — found in this repo's own suite, by a change
   that had nothing to do with looking for it.

**Lesson for candidate B and any later slice.** A displacement inventory that greps markdown links
finds the *documentation* consumers. Scripts that read a reference file as data are invisible to
that search and are the ones that actually break. Run the full selftest suite against a stash of the
change before believing a saving is free.


## 9. Candidate B — declined

Candidate A alone took the generic margin from 407 to **4,658** and apple to **4,680**. Every queued
detection candidate now fits, including the six never measured, so the headroom pressure that
motivated a displacement pass is gone.

B was always the riskier half: it trades a **dormant but ready** capability for tokens. *"No loop can
emit v5 today"* is a statement about today that one recorded `panel_certification` entry silently
falsifies, and the cost of being wrong lands on the HALT_SUCCESS panel — the least-observed path in
the system. Paying that risk to buy headroom the skill no longer needs is a bad trade at any price.

**Declined, not deferred.** Re-open it only if the loop path tightens again *and* the panel
capability is still dormant at that point. If the capability has landed by then, B is off the table
permanently and the 2,634 tokens are simply the cost of a live feature.

## 10. Outstanding — the vacuous-assertion sweep (blocked, not done)

§8's third finding — a probe that had silently stopped testing anything — is a **class**, not a
one-off, and this skill ships **72** `_*_selftest.py` files. A sweep of all of them was launched and
**died on an account spend limit before producing anything**; it is outstanding work, not a
completed clean bill.

**Method, for whoever picks it up.** A finding must be *proven by mutation*: break the behaviour the
test names, re-run it, and only report it if it still passes. Work on a copy of the tree so parallel
mutation is safe, and restore between mutations. Prioritise by stakes — a vacuous guard on a hard
gate or on redaction matters more than one on a reporting helper. Finding nothing is a good result;
an honest empty report beats a padded one.

**Batch 1 (serial, 2026-08-21) — 5 tested, 1 proven vacuous.** A second real one, in the panel
half of rule #6 exception (d): `_artifact_panel.py:652`'s
`if stable_ids and findings_count in (1, 2) and len(stable_ids) != findings_count:` could be deleted
outright (`if False:`) and **no test in the entire 72-file suite noticed**. The two fixtures the
coupling selftest's own docstring cites as pinning that rule each trip a *different* check first —
one the per-member `finding_stable_id not in findings[]` check, the other the separate `{1,2}` cap —
so the distinct-id comparison itself was never isolated. Closed by one fixture where every other leg
holds (`STABLE_A` present in `findings[]`, `findings_count` 2 inside the cap) so only the count
mismatch can fire; verified to kill the mutation.

Worth noting *how* it hid: not a drifted threshold like the first one, but **two neighbouring checks
that shadow the third**. Every fixture aimed at the rule was absorbed by a cheaper check upstream.
That is a distinct failure mode and a harder one to spot by reading.

**Batch 2 (drift guards) — 6 tested, 0 findings.** `_retired_prose`, `_ref_tree_lint`, `_canon`,
`_flag_effect`, `_schema_compat`, `_transition_table` all killed both mutations. `_retired_prose`
turned out to be self-guarding against the failure predicted for it: renaming its target file fires
*"a rename would silently blind this check"* rather than going quiet. Two judgment calls were made
correctly and are recorded so they are not re-raised as findings: a **paraphrased** (non-verbatim)
reintroduction does slip past `_retired_prose`, but its contract is a literal substring from a named
commit — the same shape as the method.md-heading non-finding above; and `_transition_table`'s
legality check, when disabled, fails five assertions at once, which is the opposite of the shadowing
problem.

**A latent version of the class, worth knowing about.** `_schema_compat_selftest.py` reads a dogfood
artifact at `REPO_ROOT/CURRENT_REVIEW.json` — one level *above* the skill dir. It exists today, so
the test exercises its real path. If it were ever removed the test would fall to its skip branch and
still exit 0. It does announce the skip in its output (*"dogfood artifact absent; retroactive check
skipped"*), which is the repo's own `absent != clean` discipline honoured — but a runner that reads
only exit codes would see full coverage. Not a defect today; a thing to not be surprised by.

**Batch 3 (HALT/terminal gates) — 6 tested, 0 findings.** `_g17`, `_halt_tail`, `_g37`, `_g41`,
`_g45_exhaustion`, `_risk_evidence` all hold. Three results worth keeping:

- **`_g17` is the best-engineered test in the repo on this axis** and took three mutations, all
  killed hard. It asserts on *printed diagnostics* rather than the `REPORT_ONLY` return value
  specifically to avoid a vacuous pass, and every malformed-citation fixture perturbs exactly one
  field so a broken check cannot hide behind a neighbour — the anti-shadowing discipline, already
  applied, before anyone went looking for it. This matters beyond the sweep: G17 is a **[P1]** item
  with a live adjudication packet, and its guard being sound is a precondition for that packet
  meaning anything.
- **`_risk_evidence` (G33) verifiably closed the bug it was written for.** The historical
  free-text token-match false-pass was reconstructed and dies on exactly the FAKE-evidence case
  whose docstring names it. A guard written to close a vacuous check, confirmed to have done so.
- **`_halt_tail`'s three per-field blocks do not shadow each other** — isolating the null-otherwise
  half of rule #18 killed exactly one case and nothing else.

**Bearing on the displacement analysis.** §5 refused to move this bundle off the unconditional load
path partly because none of these gates has a script backstop. That argument assumed the gates were
soundly tested; the assumption now has evidence behind it rather than being taken on trust.

**Covered so far — 20 of 72; 2 proven vacuous, both fixed:**

| Selftest | Mutation applied | Result |
| --- | --- | --- |
| `_g44_selftest.py` (credential quarantine) | `hits.append` → no-op; `_CREDENTIAL_PATTERNS` → empty | both **killed** |
| `_redaction_dispatch_selftest.py` | redaction rule inverted (`never the value` → `always the value`) | **killed** |
| `_token_budget_selftest.py` | — | **proven vacuous**; fixed in §8 |
| `_tool_runner_selftest.py`, `_g47`, `_g48`, `_g32_panel` | two each (batch 1) | all **killed** |
| `_g32_panel_coupling_selftest.py` | dedup-count comparison → `if False:` | **SURVIVED** — fixed by an isolating fixture |

One near-miss worth recording so it is not re-raised: renaming method.md's *"Credential redaction."*
heading **survives** `_redaction_dispatch_selftest.py`. That is **not** a vacuous assertion — the
test's contract is that the redaction *rule* is forwarded verbatim into dispatch prompts, and
inverting the rule is caught. A heading is not the rule. Reporting it would be the false positive
the method above exists to prevent.
