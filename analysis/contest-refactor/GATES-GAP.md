# Forced-Completion Gates Gap — contest-refactor vs trailofbits fp-check

> **CURRENT-STATE (2026-06-28):** COVERED — continuation discipline enforced by G20/G15 at artifact level; plugin Stop-hooks are Claude-Code-only and unportable for a cross-provider skill, so the gate is the portable equivalent. See [`GAP-AUDIT-AND-IMPROVEMENT-PLAN-2026-06-28.md`](GAP-AUDIT-AND-IMPROVEMENT-PLAN-2026-06-28.md) for the source-verified audit.
> Gate numbers **G37+** cited below are UNBUILT proposals — G33–G36 have since SHIPPED (2026-06-29); the live catalog (`contest-refactor/canon/validation-gates.toml`) now stops at **G36**. *(Re-verified 2026-06-30.)*

Compares contest-refactor's gate machinery (31 hard gates G1-G31 + 8 quality passes Q1-Q8 in `references/validation.md`, validated by `scripts/validate-artifact.py`) against Trail of Bits fp-check (`refs/competitors/trailofbits-skills/plugins/fp-check/`) which uses Claude Code's Stop + SubagentStop hook system with LLM-judge prompts.

## Baseline: contest-refactor today

**31 hard gates G1-G31** + 8 quality passes Q1-Q8. All validated by `scripts/validate-artifact.py` (Python stdlib).

**Validation surface:**
- Run AT EMIT (Step 1 emit, Step 3 step 7/8)
- Run PRE-COMMIT (Step 3 step 11)
- Run POST-RESUME (Step -1)
- All checks are STRUCTURAL: schema validation, enum exact match, field-presence, cross-file invariants
- Some gates are SEMANTIC-IN-CONTENT (G12 friction proof citation, G24 test-surface cross-check, G25 continuation-bridge audit, G26 anchor-to-source) — validator checks for presence of evidence; LLM is expected to author the evidence truthfully

**Failure surface:** validator returns errors → loop subagent revises → re-runs validator. Deterministic, sub-second runtime, no LLM in loop.

**Per-gate `skip-when-X` rules** (e.g., G4/G8 suspended when `unverifiable_due_to_build_failure: true` during build-failure path).

## Baseline: trailofbits fp-check

**6 gates** (Process, Reachability, Real Impact, PoC Validation, Math Bounds, Environment) defined in `references/gate-reviews.md`. **Enforced via 2 Claude Code hooks** in `plugins/fp-check/hooks/hooks.json`:

- **`Stop` hook** (matcher `*`, type `prompt`, timeout `30`s): LLM-judge re-reads entire conversation, checks all 7 items (Phases 1-5 + Gate Review + Verdict) for EVERY bug, returns `block` or `approve` with structured English gap list.
- **`SubagentStop` hook** (matcher `*`, type `prompt`, timeout `30`s): LLM-judge identifies subagent type (`data-flow-analyzer | exploitability-verifier | poc-builder`) from conversation, validates per-agent required sections (e.g., poc-builder must include Phases 4.1-4.5 with pseudocode mandatory, executable PoC conditional with explicit skip justification).

**Failure surface:** hook blocks agent termination with English message; agent must redo work. No bypass. Crash behavior undocumented (implicit safe-fail).

## Gap matrix

Legend: **✓** = present, **partial** = weaker form, **—** = absent.

| Mechanism | contest-refactor | ToB fp-check |
|---|:--:|:--:|
| Gate count | 31 hard + 8 quality | 6 gates + 13 challenge Qs + per-phase checks |
| Validator implementation | ✓ Python stdlib script | LLM prompt inside hook |
| **Schema / structural validation** | ✓ exhaustive | — (semantic only) |
| **Cross-file invariants** (registry, archive, commit subject) | ✓ G16/G18/G22 | — |
| Pre-emit blocking | ✓ G1-G29 at Step 1 emit | — |
| Pre-commit blocking | ✓ G15/G22 at Step 3 step 11 | — |
| Post-resume re-validation | ✓ at Step -1 | — |
| Per-finding validation | ✓ G3/G4/G5/G6/G16 | partial (whole-batch only) |
| Per-gate `skip-when-X` rules | ✓ (e.g., build-failure path) | — |
| Block payload structure | ✓ validator error message | partial (LLM-generated English) |
| Determinism | ✓ deterministic Python | — (LLM-dependent, model + temp drift) |
| Runtime | ✓ subsecond | partial (30s timeout per hook) |
| Gate definitions in code | ✓ `_canon.py` + canon/*.toml | partial (markdown + hook prompt) |
| **Hook-based blocking at Claude Code Stop event** | **—** | ✓ Stop hook |
| **Per-subagent output completeness check** | partial (Reviewer-only, G15 field presence) | ✓ SubagentStop validates per-agent-type structure |
| **Semantic gap-detection at AGENT level** | partial (semantic gates rely on LLM to author honest evidence; validator only checks presence) | ✓ LLM judge re-reads conversation |
| Bypass / override mechanism | partial (some gates have `skip-when` rules) | — |
| Hook crash recovery posture | n/a (deterministic Python) | undocumented |

## Strategic insight

These are **complementary** layers, not competing:

- Contest-refactor's gates = **artifact-level structural validation** (deterministic, Python, runs at known checkpoints, validates what was written)
- ToB's hooks = **agent-level semantic gating** (LLM-judgment, runs on Claude Code Stop event, validates what the agent is about to do)

Contest-refactor's 31 gates are strictly more rigorous on structure/cross-file invariants. ToB's hooks catch a layer contest-refactor doesn't: when the agent attempts to terminate prematurely (Stop event), or when a subagent returns incomplete output. Contest-refactor's G20 (Continuation Discipline) already runs immediately after Step 3 step 11 in inline mode, but it is still a post-commit artifact/routing check rather than a Stop-event intercept.

The biggest single ToB hook payload — verbatim from `hooks.json`:

```json
"hooks": {
  "Stop": [{
    "matcher": "*",
    "hooks": [{
      "type": "prompt",
      "prompt": "You are a verification completeness checker... Scan the conversation for evidence of ALL of the following for EVERY bug...",
      "timeout": 30
    }]
  }],
  "SubagentStop": [{
    "matcher": "*",
    "hooks": [{
      "type": "prompt",
      "prompt": "You are an output completeness checker for fp-check verification agents... Identify which agent type this is from the conversation context and verify completeness...",
      "timeout": 30
    }]
  }]
}
```

Type `"prompt"` makes the hook an LLM judge; 30s timeout bounds runtime; matcher `"*"` fires on every Stop/SubagentStop event; the hook prompt internally short-circuits ("If the conversation is not about fp-check verification at all, return 'approve'") to avoid blocking non-fp-check workflows.

## P0 GAPS — what to import

### Gap A: Stop hook for continuation discipline (catches premature inline stop at system level)

G20 today re-reads `CURRENT_REVIEW.json` post-commit and verifies the agent re-enters Step 1. But G20 still runs **after** the loop has already reached its post-commit routing point; it does not intercept the Stop event itself. ToB's Stop hook model is the missing intercept point.

**Adopt:** add `hooks/hooks.json` to contest-refactor, but make the Stop check an **executable command hook**, not a prompt hook. This check needs to read `CURRENT_REVIEW.json` from disk, and the current hook payload uses the wrong field name (`backlog`, not `improvement_backlog`):

```json
{
  "description": "Enforce contest-refactor continuation discipline — prevent premature inline-mode stop",
  "hooks": {
    "Stop": [{
      "matcher": "*",
      "hooks": [{
        "type": "command",
        "command": "./hooks/check-continuation-stop.sh",
        "timeout": 10
      }]
    }]
  }
}
```

`check-continuation-stop.sh` performs a deterministic JSON read of `state`, `loop`, `loop_cap`, `spawn_isolation`, and `backlog`, then blocks only when inline mode is about to stop with `state == "CONTINUE"` and non-empty backlog.

Low risk, high value: catches the single most common production failure mode (inline-mode premature stop after a successful commit). G20 stays as the artifact-level enforcement; the hook is the system-level intercept that fires even if the LLM never re-reads the artifact.

**Important companion import from `agentlint`:** Stop hooks need a circuit breaker (`STOP_HOOK_ACTIVE`-style guard) or they can loop forever. Any real adoption of Gap A should carry that guard from day one.

### Gap B: SubagentStop hook for Implementation Reviewer output completeness

G15 today verifies `implementation_review` field is present and verdict is in `{approved, rejected}`. The current schema's `checks.reality|honesty|regression` are enum statuses (`passed|failed|skipped`), not free-text bodies, so the first draft overstated what a completeness hook could validate without first changing the reviewer contract.

**Adopt carefully:** if a SubagentStop hook is added, scope it to **raw reviewer JSON completeness** (valid verdict, required keys present, `conditions[]` non-empty when `conditional`) rather than pretending the committed artifact already carries prose bodies for each check.

```json
{
  "SubagentStop": [{
    "matcher": "*",
    "hooks": [{
      "type": "prompt",
      "prompt": "You are an output completeness checker for contest-refactor Implementation Reviewer subagents.\n\nIdentify whether this subagent is the Implementation Reviewer (look for the prompt's first line marker 'IMPLEMENTATION REVIEWER v1'). If yes, verify the returned JSON contains all of:\n- verdict ∈ {approved, conditional, rejected}\n- reason (non-empty string)\n- checks: keys {reality, honesty, regression} with values in {passed, failed, skipped}\n- regressions: array (may be empty when verdict == approved)\n- conditions: array (must be non-empty when verdict == conditional)\n\nIf any required field is missing or malformed: return 'block' with specific missing items.\nIf the subagent is NOT the Implementation Reviewer, return 'approve'.",
      "timeout": 30
    }]
  }]
}
```

Pairs with a stable first-line marker in the reviewer prompt. If contest-refactor ever wants prose-per-check completeness, it first needs to change the reviewer JSON contract rather than assuming those bodies already exist.

### Gap D: Bounded timeout for validator subagent (cross-link to Schema Gap)

Schema Gap recommended a validator subagent per finding. ToB's 30s timeout is the right reference for this LLM-based path. Today contest-refactor's deterministic Python validator needs no timeout; the validator-subagent does.

**Adopt** when validator subagent ships: `references/provider-adapters.md` adds:

```toml
[validator_subagent]
per_finding_timeout_seconds = 30
on_timeout = "retry_once"   # retry_once | treat_as_confirmed | treat_as_rejected
on_second_timeout = "treat_as_confirmed"   # don't block on infrastructure failure
```

### Gap C: Semantic Evidence-Chain compliance hook (defer; validator subagent covers it)

ToB's Stop hook re-reads conversation to check whether evidence was actually substantive, not just present. Contest-refactor's G3 checks Evidence Chain field presence; a finding with `title: "Bad code", evidence: ["src/foo.swift:42"], why_weakens_submission: "It's bad", minimal_correction_path: "Fix it"` passes G3 but fails the spirit.

The validator subagent (Schema Gap Gap C) is the right place to enforce evidence substantiveness — sequential per-finding, structured verdict, can downgrade severity. Converting it to a Stop hook gives no additional capability and gives up determinism.

**Recommendation:** keep the semantic check as a sequential validator subagent, not a hook.

### Gap E: Gate override mechanism (philosophical; defer)

Production failure: LLM gets stuck in revise-loop when validator keeps rejecting. ToB has no override either. Contest-refactor today has `--reset` (whole-loop) and `--cap 1` (limit) but no per-gate "I know this fails G24, proceed."

Override would let humans intervene without nuking state — but erodes the autonomy contract. Possible shape:

```bash
/contest-refactor --gate-override G24=<rationale>
```

Records `gate_overrides: [{gate: "G24", rationale: "...", overridden_by: "user", overridden_at: "<ts>"}]` in a top-level durable field (not `discovery`, which is first-loop-only). Overridden gates emit `G_OVERRIDDEN` warnings in Builder Notes. HALT_SUCCESS still requires ALL gates green even with overrides recorded — override only lets the loop CONTINUE past the gate, not terminate at SUCCESS while ignoring it.

**Defer.** Big philosophical decision; surface to user before adopting.

## Gate-provenance discipline (agentlint, added 2026-05-25 per Codex Class 2 MC3)

`refs/competitors/agentlint/README.md:102-109` ships a discipline that pairs naturally with contest-refactor's gate philosophy: **"Every check is backed by data, not opinions"** — sources cited per check include "265 versions of Anthropic's Claude Code system prompt", "Claude Code source code" (for hard-limit boundaries), production audits, and 6 academic papers. The hard rule at line 109: **"If a check can't cite a source, it doesn't ship."**

**Why this matters for contest-refactor's gates**: contest-refactor's 31 hard gates (G1-G31, with G35+G36+G41+G45+G48 reserved per other gap docs) are deterministic structural checks, but their *anchoring* — why this specific invariant is worth a gate — is implicit in the schema-design rationale, not surfaced per-gate. agentlint's discipline would have each gate file (or registry entry) name the source-of-truth for the invariant: a specific design doc section, a documented incident, a paper, or a competitor's documented behavior.

**Adoption recommendation** (P1, low-effort): augment `references/validation.md` so each gate row gets a `source` column citing the design-doc anchor that motivated the gate. Concrete shape:

```markdown
| Gate | What it checks | Failure modes | Source-of-truth |
|---|---|---|---|
| G1 | finding `evidence[]` non-empty when severity ≥ Serious | empty evidence + serious severity | `references/method.md § Evidence Chain` + post-mortem of loop-2026-03-14 (Critic emitted Serious finding with no evidence and the Actor couldn't act on it) |
| G16 | registry+CURRENT_REVIEW consistency | duplicate stable_id, missing path | `output-format-state-schemas.md § findings_registry.json` + ToB `fp-check` discipline (cited in TWO-LAYER-DETECTION-GAP) |
| ... | ... | ... | ... |
```

This is a doc-hygiene win, not a behavior change — but it forces each gate to be defensible against "why does this gate exist?" cold-read questions. Pairs cleanly with [REVIEW-PROMPT.md § Class 2](REVIEW-PROMPT.md) reviewer's job of pressure-testing gate justifications. Defer if the doc-update cost is large; can land alongside G35/G36 addition.

**Status: APPLIED 2026-05-25** — landed in [`contest-refactor/references/validation.md`](../../contest-refactor/references/validation.md) as per-gate `*Source:*` continuation lines (G1–G31), not the column-table shape sketched above. Rationale for the shape deviation: `validation.md` uses a checkbox list (not a table) and the gates carry long multi-paragraph bodies with embedded sub-bullets and tables of their own. Converting to a single Source column would have required a structural rewrite and lost the in-body cross-references each gate already carries; `*Source:*` continuation lines preserve every gate body byte-for-byte while delivering the same per-gate audit-trail value. Cold-read defensibility test ("where does this invariant come from?") now passes per-gate.

## What contest-refactor already wins (do not regress)

1. **31 deterministic Python gates** > LLM-judgment hooks for schema/structural validation. Field-presence checks don't need an LLM.
2. **Cross-file invariants** (G16 registry consistency, G18 REVIEW_HISTORY append, G22 commit subject) — ToB has none of these.
3. **Pre-emit + pre-commit + post-resume** multi-point validation. ToB only intercepts at Stop event.
4. **Sub-second runtime** vs 30s LLM-judge timeout. Validation is cheap when deterministic.
5. **Per-gate `skip-when-X` rules** (e.g., build-failure path suspending G4/G8) — surgical exemption discipline ToB lacks.
6. **Per-finding validation** for G3/G4/G5/G6/G16 — granular failure surface.

## What NOT to import

| Tempting | Why skip |
|---|---|
| Replace G1-G31 with LLM-judgment hooks | Deterministic Python > LLM for schema validation. Don't trade determinism for "smarter" hooks. |
| Per-finding LLM Stop hook | Validator subagent (Schema Gap Gap C) is sequential, structured, returns verdict. Hooks fire on agent terminate events, not per-finding emit. Different intercept points. |
| ToB's "scan whole conversation" prompt model | Conversation-scanning at Stop is expensive (full transcript re-read). Contest-refactor's artifact-based validation is cheaper and more precise. Use hooks ONLY for cases where artifact doesn't yet exist (premature stop). |
| 30s as universal timeout | Sync Python validator is sub-second. Reserve 30s timeout only for LLM-validator-subagent path. |
| Single-hook-file for all skills | Hooks file is `hooks/hooks.json` at plugin root; matcher `*` fires globally. Each hook implementation MUST internally short-circuit when the run is not about contest-refactor (prompt hook returns `approve`; command hook exits cleanly) — same pattern ToB uses. Don't omit this; it's why their hooks coexist with other plugins. |
| Bypassing the artifact validator in favor of hooks | Hooks fail open more easily (LLM judge can be wrong); artifact validator fails closed (Python check is deterministic). Keep artifact-level as primary; hooks as supplementary. |

## Adoption order

1. **Gap A (Stop hook for continuation discipline)** — small hook, 10s timeout, catches premature inline stop at system level. Carry an `agentlint`-style circuit breaker from day one.
2. **Gap B (SubagentStop hook for Reviewer completeness)** — extends Gap A with a reviewer-only completeness check, but only for the fields the current reviewer JSON actually has.
3. **Gap D (30s timeout for validator subagent)** — cross-link to Schema Gap Gap C; defer until validator subagent ships.
4. **Gap C (semantic Evidence-Chain hook)** — defer; validator subagent covers same need with better design.
5. **Gap E (gate override mechanism)** — philosophical; defer to user discussion.

## Minimal hook file for Gaps A+B (the immediate wins)

Create `contest-refactor/hooks/hooks.json` (new file; new directory; symlink-friendly):

```json
{
  "description": "contest-refactor: enforce continuation discipline (G20) and Implementation Reviewer output completeness (G15)",
  "hooks": {
    "Stop": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "timeout": 10,
            "command": "./hooks/check-continuation-stop.sh"
          }
        ]
      }
    ],
    "SubagentStop": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "prompt",
            "timeout": 30,
            "prompt": "Implementation Reviewer output-completeness check. Identify whether this subagent is the contest-refactor Implementation Reviewer (look for prompt marker 'IMPLEMENTATION REVIEWER v1' from references/implementation-reviewer.md). If yes, verify returned JSON has: verdict ∈ {approved, conditional, rejected}; reason (non-empty); checks keys {reality, honesty, regression} with values in {passed, failed, skipped}; regressions[] array; conditions[] non-empty when verdict == conditional. Any missing/malformed required item: return 'block' with specific missing items. If subagent is NOT the Reviewer: return 'approve'."
          }
        ]
      }
    ]
  }
}
```

Also update Implementation Reviewer prompt template in `references/implementation-reviewer.md` to start the prompt with the literal marker line:

```
IMPLEMENTATION REVIEWER v1
```

This is the scoping signal SubagentStop reads to know which subagent it's gating. If Gap A is adopted, add a loop-prevention guard to the Stop-hook script (`STOP_HOOK_ACTIVE` or equivalent) before merging it.

Installation note (per `CLAUDE.md` symlink pattern): when users symlink the skill into `~/.claude/skills/contest-refactor`, the hooks at `hooks/hooks.json` are discovered automatically by Claude Code's plugin system. No registration in `.claude/settings.json` required for plugin-resident hooks.
