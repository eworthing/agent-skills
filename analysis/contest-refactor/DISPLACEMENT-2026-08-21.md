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

## 10. The vacuous-assertion sweep — moved

§8's third finding (a probe that had silently stopped testing anything) turned out to be a class,
not a one-off. The sweep it triggered grew past what belongs in a displacement note and now has its
own record: [`VACUOUS-SWEEP-2026-08-22.md`](VACUOUS-SWEEP-2026-08-22.md). Headline: **68 of 72
selftests mutation-tested, 23 proven vacuous, 21 fixed.**
