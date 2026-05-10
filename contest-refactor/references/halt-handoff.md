# Halt Handoff

When the loop terminates, the subagent emits two things to main:

1. **JSON** for routing (per `references/trust-model.md` Loop Isolation subagent return contract).
2. **User-facing handoff text** the main agent reads aloud to the user when reporting the halt.

The handoff is **plain language**. It explains *why* the loop stopped, *what* remains, and *what the user can do next*. Halts without handoff text leave the user staring at a flag with no path forward.

This file defines the handoff for each halt state and subtype.

## Schema (PR 4, schema_version >= 2)

At schema_version >= 2, the handoff is emitted as a structured `halt_handoff` object (per [output-format.md § halt_handoff](output-format.md#halt_handoff-object-pr-4-schema_version--2)) with `text` (user-facing prose) and `expected_actions[]` (HandoffAction objects matching the menu options in the handoff text).

For each menu option in the handoff templates below, the loop subagent emits a corresponding HandoffAction with:
- `action_id`: kebab-case derived from the menu option's verb + object (e.g., menu "Split file X" → `action_id: "split-file-x"`)
- `description`: the menu option's user-facing text
- `match_keywords`: substrings that would appear in a commit subject if the user took this action (e.g., `["split", "X"]`)
- `match_paths`: file paths that would appear in the commit's changed files (when the menu option references specific paths)
- `match_kind`: `all_of` if `match_paths` non-empty (default); `any_of` if keyword-only fallback; `no_drift_expected` if the action is "accept halt; no commits expected"

Step -1 step 4a (next invocation, on drift) reads `expected_actions[]` from prior CURRENT_REVIEW.json and matches commits in the drift range against each action.

At schema_version 1, only the prose `halt_handoff_text` is emitted; no structured action matching.

---

## HALT_SUCCESS

Triggered when every scorecard category reaches 10, OR 9.5+ with `accepted` residual disposition (per `architecture-rubric.md` Score Anchors).

### Subagent records
- `system_flag: "HALT_SUCCESS"`
- `unresolved_reason: null`
- `halt_subtype: null`

### Handoff template

```
Loop N ended at HALT_SUCCESS — every scorecard category is at 10 or 9.5+ with an
accepted residual. The codebase meets the contest target.

Final scorecard: <list dimensions and scores from CURRENT_REVIEW.json>

Accepted residuals (won't be revisited unless you ask):
  - <category>: <residual_blocking_10> — <residual_rationale>
  ...

Next step options:
  (a) Tag the commit and move on.
  (b) Spot-check one accepted residual — say "verify <category>" and I'll re-read
      the cited source.
  (c) Reset and run again from current source — type "/contest-refactor --reset"
      (useful if the codebase has changed materially since this halt).
```

---

## HALT_STAGNATION

Triggered when the loop cannot make further progress under the rubric. Four distinct subtypes — each means something different to the user.

### Subagent records
- `system_flag: "HALT_STAGNATION"`
- `halt_subtype: "no_progress" | "oscillation" | "user_decision" | "no_backlog"`
- `unresolved_reason: <subtype-specific explanation>`

### Subtype: `no_progress`

**Condition**: 3 consecutive loops with no scorecard category UP, AND remaining backlog items don't pass Simplify Pressure Test.

**What it means in plain language**: The loop hit a structural wall. The remaining issues exist but every proposed fix either fails the deletion test, fails Unified Seam Policy, or would add ceremony (costume layer / fake-clean reward). Continuing would over-engineer without raising scores.

#### Handoff template

```
Loop N ended at HALT_STAGNATION (subtype: no_progress).

What this means: I've made N loops and the scorecard hasn't moved up in the last
3. The remaining backlog items don't pass the Simplify Pressure Test — every
proposed fix either fails the deletion test, would add a costume layer, or only
polishes the surface without changing structure. Forcing more loops would
over-engineer without raising scores.

Current scorecard: <list dimensions and scores>

Remaining backlog (carried forward):
  - <Priority 1 finding ID + title> — <one-line why it stopped me>
  ...

Next step options:
  (a) Accept the halt — current source is contest-grade-enough. The remaining
      items are local polish, not winnable structural findings.
  (b) Resolve manually — fix the blocking finding outside the loop (e.g., make
      a product/ownership decision, change a contract), then re-invoke
      /contest-refactor. I'll re-validate and resume.
  (c) Scope down — re-invoke as "/contest-refactor --scope <dir>" to refactor
      only one module that may have winnable structural moves.
  (d) Reset and try a different angle — "/contest-refactor --reset" archives
      this halt and starts fresh from current source.
```

### Subtype: `oscillation`

**Condition**: Same finding reappears as Priority 1 twice after a "fix". Indicates the fix didn't actually resolve the smell — it relocated it or surface-polished it.

#### Handoff template

```
Loop N ended at HALT_STAGNATION (subtype: oscillation).

What this means: Finding F<id> ("<title>") came back as Priority 1 after a
prior loop claimed to fix it. The fix didn't resolve the smell — it relocated
or surface-polished it. Continuing would loop on the same fake fix.

The fix attempted: <loop M loop_result.what_changed>
Why it didn't stick: <subagent's analysis from current CURRENT_REVIEW.md>

Next step options:
  (a) Resolve manually — the finding needs human judgment about the right fix.
      Read CURRENT_REVIEW.md finding F<id>; decide on a structural change; then
      re-invoke /contest-refactor.
  (b) Demote the finding — if you accept the residual, edit CURRENT_REVIEW.md
      to mark F<id> as accepted residual (per Score Anchors), then re-invoke.
  (c) Reset — "/contest-refactor --reset".
```

### Subtype: `user_decision`

**Condition**: Top Structural Finding requires product/ownership decision the loop cannot make (per Guardrails "Stop on ambiguity").

#### Handoff template

```
Loop N ended at HALT_STAGNATION (subtype: user_decision).

What this means: The blocking finding requires a decision I can't make
unilaterally. It's not a code question; it's a product/ownership question.

The question: <subagent's open_question_for_user>

Context (from CURRENT_REVIEW.md F<id>):
  - <one-paragraph summary>

Next step: answer the question, then re-invoke /contest-refactor with the answer
in your message. I'll resume the loop with your answer as the resolved decision.
```

### Subtype: `no_backlog`

**Condition**: `[STATE: CONTINUE]` with empty Improvement Backlog while not at 9.5+ after Residual Accounting Pass/G23. Every score below 9.5 names a source-backed blocker that keeps the dimension's 9-anchor unmet and cannot honestly become a backlog item or accepted residual. If a dimension's 9-anchor is met and the only leftovers are Cosmetic for contest, ADR-carved-out, framework-constrained, or SPT-failing candidates, this subtype is illegal for that dimension; those leftovers are accepted residuals and should normally produce `HALT_SUCCESS`.

#### Handoff template

```
Loop N ended at HALT_STAGNATION (subtype: no_backlog).

What this means: Scorecard is at <X>/10 average — not at 9.5+ — and the
remaining blockers keep one or more dimensions below the 9-anchor. I cannot
generate a backlog item that passes the evidence chain or Simplify Pressure
Test, and the blockers are not acceptable residuals.

Current scorecard: <list>

Residual accounting:
  - <category>: <blocker> — why it is not backlog-worthy and not accepted

Next step options:
  (a) Accept the halt — the rubric and the codebase don't agree on what's left
      to fix; trust the rubric's silence.
  (b) Inspect manually — read CURRENT_REVIEW.md and ask "why isn't <concern>
      flagged?" I'll re-check that specific area.
  (c) Switch lens — if the wrong lens was selected (e.g., Generic on a Swift
      codebase), re-invoke as "/contest-refactor --force-lens <name>".
  (d) Reset.
```

---

## HALT_LOOP_CAP

Triggered when loop counter reaches cap (default 10; override via env var or directive).

### Subagent records
- `system_flag: "HALT_LOOP_CAP"`
- `halt_subtype: null`
- `unresolved_reason: "loop counter reached cap of <N>"`

### Handoff template

```
Loop N ended at HALT_LOOP_CAP — I made <N> loops, the configured maximum.

Progress so far: <delta from loop 1 scorecard to loop N scorecard, summarized>

Current Priority 1 (carried forward):
  - F<id>: <title> — <one-line why>

Next step options:
  (a) Bump cap and resume — "/contest-refactor --cap <N+5>" continues from here.
  (b) Accept current state — <N> loops landed substantial improvements; current
      source is the new baseline.
  (c) Reset — "/contest-refactor --reset".
```

---

## Re-validation handoff (on drift)

When Resume Detection finds the codebase has moved past the prior halt sha, the main agent runs a fresh Step-1 critic pass and emits one of three results.

### Drift + fresh pass returns CONTINUE with new backlog

```
Detected <K> commit(s) since the prior HALT (<halt_sha>..HEAD). I re-ran a fresh
critic pass against current source.

New Priority 1 finding: F<id> — <title>

The prior halt is no longer current; resuming the loop with the new finding.
```

### Drift + fresh pass returns same HALT_STAGNATION subtype

```
Detected <K> commit(s) since the prior HALT (<halt_sha>..HEAD). I re-ran a fresh
critic pass against current source.

Prior handoff actions detected as completed:
  - <action_id>: addressed by commit <sha> ("<commit subject>") — matched via <kind>
  - <action_id>: no commits in range; matches "no_drift_expected"
  (or "none of the prior expected_actions matched commits in the drift range" if 0 matched)

Result: same halt — HALT_STAGNATION (<subtype>). Recorded re_validated_at_sha
<HEAD> in CURRENT_REVIEW.json so we don't re-revalidate against this same state.

Why the halt persists: <why_halt_persists from main agent's re-validation pass>

<emit the subtype's standard handoff template>
```

The "Prior handoff actions detected" list comes from `re_validation_context.prior_handoff_actions_taken[]` (PR 4, schema_version >= 2), populated by Step -1 step 4a. The "Why the halt persists" sentence comes from `re_validation_context.why_halt_persists`, composed by the main agent in Step -1 step 4b after the fresh critic pass.

### Drift + fresh pass returns HALT_SUCCESS

```
Detected <K> commit(s) since the prior HALT (<halt_sha>..HEAD). I re-ran a fresh
critic pass against current source.

Result: HALT_SUCCESS — the changes since the halt brought every scorecard
category to 10 or 9.5+ with accepted residuals.

<emit HALT_SUCCESS standard handoff template>
```

---

## Reset handoff

When user invokes `/contest-refactor --reset` or selects a reset option from a halt menu, main agent performs the reset and emits this confirmation:

```
Reset complete. Archived prior CURRENT_REVIEW.md to REVIEW_HISTORY.md with
divider "--- HALT_<state> reset by user (UTC <timestamp>) ---". Cleared
CURRENT_REVIEW.json. Loop counter reset to 1. Removed any <!-- loop_cap: N -->
directive.

Starting fresh from current source. Running Step 0 Discovery now.
```
