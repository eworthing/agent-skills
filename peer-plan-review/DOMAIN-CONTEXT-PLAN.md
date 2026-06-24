# Plan: optional "Domain context" block for `peer-plan-review`

> **Status:** IMPLEMENTED + validated, 2026-06-24. Design reached via two rounds of
> cross-agent peer review (see [Review provenance](#review-provenance)); built TDD via
> `writing-skills` (RED→GREEN evidence in [Build outcome](#build-outcome)). Shipped in
> `SKILL.md` ("Domain context (optional)" + Round 1 step 3) and
> `references/output-format.md` (two-pass variant).

## Problem

The reviewer prompt is assembled from three parts only: verdict contract +
line-numbered plan + structured-output template. Nothing conveys the domain skills the
host had loaded. A plan authored against a domain skill (e.g. `swiftui-native-ux`) gets
critiqued with the reviewer's base model knowledge — held to a lower domain standard
than it was written to.

## Goal

Give the reviewer the host's domain grounding **without** letting the plan author define
the standard they're judged by, and **without** non-reproducible behavior.

## Why not the obvious alternatives (settled in review)

| Rejected | Reason |
|----------|--------|
| Auto-inject full skill content | Prompt bloat; reviewer can't reliably operationalize it; kills independence |
| Just name the skills ("use `swiftui-native-ux`") | Headless reviewers can't invoke their Skill tool (`codex exec` doesn't auto-activate; Claude reviewer has no `Skill` tool in `--tools`) → becomes a training-data name-drop |
| "If you have skill X installed, read it" soft pointer | Nondeterministic; some runs silently pull local context, host can't tell which → non-reproducible reviews |
| Do nothing | Loses real domain-catch value on platform/framework plans |

## Design

### 1. Inclusion rule — when the block is added at all

Add a Domain-context block **only** when the plan depends on platform/framework-specific
conventions that materially affect correctness, UX, or compliance. Default **off**; pure
logic/backend plans get no block. Per-run **opt-out** always available (e.g. a maximally
independent adversarial pass).

### 2. Block contents — criteria, not prescriptions

Host distills 3–6 plain-prose, **checkable criteria** from its loaded skills that bear on
*this* plan. Criteria state the *standard*, never the solution the host already chose.

Enforced by a **negative constraint** in the host's authoring step:

> When writing the Domain-context block: do NOT reference the specific files, classes, or
> architectural choices you made in the plan. Output only the abstract rules the plan must
> satisfy. 3–6 bullets, one checkable rule each.

Example block:

```
## Domain context (review criteria — challenge these if wrong)
- Navigation uses NavigationStack / NavigationSplitView, not a custom router.
- All interactive text supports Dynamic Type; no fixed font sizes.
- Every actionable control has a VoiceOver label.
- No web-port patterns (no manual routing tables, no div-style nesting).
```

### 3. Injection placement

Order in the prompt assembly:

```
verdict contract → numbered plan → [Domain context block] → output template
```

Block sits **between the plan and the output template** — plan in attention first,
criteria adjacent to the output schema that consumes them.

### 4. Two-pass reviewer critique, schema-enforced

Prose instruction alone collapses into one biased pass (anchoring). So the output
template (`references/output-format.md`) gains two mandatory, physically-separated
sections:

```
### Pass A — Independent critique
Stress-test the plan on its own merits. Do NOT assume the Domain-context
criteria are correct or complete. (If no Domain-context block was supplied,
this is the whole review.)

### Pass B — Domain-criteria critique
Only if a Domain-context block was supplied. For each criterion: does the plan
meet it? Then explicitly challenge the criteria themselves — flag any that are
incomplete, self-serving, or in tension with better practice.

### Blocking Issues
- [B1] (HIGH|MEDIUM|LOW) ...  (tag each finding [A]/[B] for which pass it came from)
...
### Non-Blocking Issues
...
VERDICT: APPROVED or VERDICT: REVISE
```

Pass A runs **always** (block present or not), so the no-block path is unchanged. Pass B's
mandate to challenge the criteria is what preserves independence — the reviewer can reject
a biased block, not just apply it.

## Files touched

- `SKILL.md` — new "Domain context (optional)" section: inclusion rule, negative-constraint
  authoring instruction, injection placement in "Round 1".
- `references/output-format.md` — add the Pass A / Pass B sections; note Pass B is
  conditional. Confirm `parse_structured_review()` still scopes correctly to
  `### Blocking Issues` / `### Non-Blocking Issues` (the new Pass A/B sections sit above and
  must not be parsed as findings).
- No `run_review.py` change — block is host-authored prose, not runner logic (no
  skill-enumeration API exists; only the host knows which skills are loaded).

## Validation — Iron Law, fail first

`writing-skills` governs this edit: baseline must fail before the skill is written. **Three
arms:**

| Arm | Prompt |
|-----|--------|
| (a) control | no domain block |
| (b) block only | domain block, single-pass output |
| (c) full design | domain block + schema-enforced two-pass |

Across **≥1 domain-heavy plan** (SwiftUI) **and ≥1 non-UI plan** (e.g. a backend
migration), on **≥2 reviewer CLIs** (codex + gemini). Measure:

1. **Catch** — does (b)/(c) catch domain issues (a) misses? (proves the block earns its place)
2. **No overfit** — does (c) still surface broad architectural issues *outside* the supplied
   criteria, vs (a)? (proves Pass A stays independent)
3. **Reproducibility** — is behavior stable across runs/CLIs? (proves dropping the soft
   pointer worked)

Ship only if (c) beats (a) on catch **without** regressing on overfit.

## Open risk (kill switch)

If the 3-arm baseline shows (c) ≈ (a) on catch — the block adds nothing the model didn't
already know — **don't ship**. The feature is net prompt-weight for no gain. The baseline is
the kill switch, not a formality.

## Review provenance

| Round | Reviewer | Verdict | Contribution |
|-------|----------|---------|--------------|
| 1 | codex / gpt-5.4 / high | REVISE | Fixed the concept: two-pass critique (host must not define the review standard unchallenged); criteria-not-prescriptions; dropped the nondeterministic "if installed, read it" pointer; broadened validation beyond one SwiftUI case. |
| 2 | gemini / gemini-3.1-pro-preview / xhigh | REVISE | Hardened the mechanics: two-pass must be **schema-enforced** in the output template or it collapses to one biased pass; negative constraint to stop prescription leakage; specify injection placement. |

Both reviewers endorsed the direction; objections shrank from "wrong shape" to "nail the
template" → converged. No outstanding conceptual objection. Next step is the TDD build.

## Build outcome

TDD with a real reviewer (codex / gpt-5.4 / medium), per arm read manually.

**RED, attempt 1 — well-known domain (SwiftUI), 3 control reps.** The control did NOT
fail: the reviewer caught every planted native-UX violation (custom router/ZStack, non-
semantic controls, custom toggle, fixed font sizes, missing Form/List) unaided, all 3
reps. Per the Iron Law, "if the control doesn't exhibit the failure, there is nothing to
fix." This proved the kill-switch case and **refined the inclusion rule** (§1): the block
earns its place only for conventions a strong base model would NOT already apply — not
well-known platform idioms. That refinement was folded into `SKILL.md`.

**RED, attempt 2 — bespoke project rules, 3 control reps.** Control failed as required.
Zero reps mentioned the project-specific primitives (audit store, model registry); one
rep explicitly endorsed the violation ("the project accepts direct modelContext usage").
The unregistered-`@Model` data-loss bug was missed by all three.

**GREEN — same bespoke plan + Domain context block + two-pass template, 2 reps.** Both
reps:
- Pass B caught both project-specific violations the control missed (direct writes bypass
  the audit store; unregistered model → silent migration data loss).
- Pass A stayed independent — surfaced the same broad issues as the control (predicateJSON
  opacity, naming, testing) without leaning on the criteria, so the two-pass did not
  collapse into one biased pass (gemini B1 risk did not materialize).
- Pass B challenged the criteria themselves (e.g. "SeedStore naming is misleading for a
  write boundary"), confirming the independence guardrail.

**Parser safety.** `parse_structured_review()` run against the real two-pass output
extracted 8–9 findings cleanly; Pass A/Pass B reasoning was not mis-parsed as findings;
optional `(A)`/`(B)` origin prefixes preserved without breaking the `[Bn] (CONF)` regex.
Full skill suite 119/119 pass; vendored `_common` byte-identical; eval-skill 13/13 (100%).
