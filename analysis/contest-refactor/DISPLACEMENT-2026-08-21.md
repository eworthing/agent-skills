# Loop-path displacement: inventory and design note (2026-08-21)

Design note before code, per the convention the item 24 and item 25 notes follow. **No code in
this pass.**

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
