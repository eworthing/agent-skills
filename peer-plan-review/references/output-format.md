# Reviewer Output Format

All provider prompts request the same structured output so `parse_structured_review()`
in the vendored `_common/session/io.py` can extract findings uniformly. Include this template verbatim
in every prompt.

## Template

```
### Reasoning
Full analysis of the plan across two lenses:
- **Execution risk** — sequencing, hidden assumptions, missing validation,
  rollback, and dependency gaps.
- **Executability** — could a fresh engineer with no prior context implement this
  as written? Flag tasks too large or coupled to build and verify on their own,
  steps with no stated way to confirm success, under-specification (TBD/TODO,
  "add error handling/validation" without specifics, "same as an earlier task"),
  and references to files, functions, types, or signatures the plan never defines
  or whose names drift between the task that introduces them and the tasks that use
  them.

### Blocking Issues
- [B1] (HIGH|MEDIUM|LOW) Short description of blocking issue
  Section: <plan section name> (lines <N-M>)
  Recommendation: Concrete fix or mitigation

(Write "None" if no blocking issues.)

### Non-Blocking Issues
- [N1] Short description of non-blocking issue
  Section: <plan section name> (lines <N-M>)
  Recommendation: Suggested improvement

(Write "None" if no non-blocking issues.)

VERDICT: APPROVED or VERDICT: REVISE
```

## Rules

- Per-issue confidence (`HIGH`, `MEDIUM`, `LOW`) is **required** on blocking
  issues, optional on non-blocking.
- Section and line references refer to the numbered plan provided in the prompt.
- The final non-empty line of the response must be exactly
  `VERDICT: APPROVED` or `VERDICT: REVISE` — nothing else.
- Each round uses fresh per-round IDs (`B1`, `B2`, `N1`, ...). Do not ask the
  reviewer to continue numbering from a previous round; the host maps cross-round
  findings by content similarity.

## Two-pass variant (only when a Domain context block is present)

When the prompt includes a Domain context block (see SKILL.md → "Domain context"),
replace the single `### Reasoning` section with the two sections below, in this order.
Leave `### Blocking Issues` / `### Non-Blocking Issues` / `VERDICT:` exactly as above —
the parser reads only those two finding sections, so the passes carry reasoning, not
findings.

```
### Pass A - Independent critique
Stress-test the plan on its own merits — both execution risk and executability by a
zero-context engineer (right-sized, independently-verifiable tasks; no under-specification,
placeholders, or references to files/functions/signatures the plan never defines). Do NOT
assume the Domain context criteria are correct or complete; critique as if no criteria had
been supplied.

### Pass B - Domain-criteria critique
For each supplied criterion, state whether the plan meets it. Then challenge the criteria
themselves: flag any that are incomplete, self-serving, or in tension with better
practice, and reflect a wrong criterion in the verdict rather than rubber-stamping it.
```

Findings from BOTH passes go in the single Blocking / Non-Blocking lists below. Optionally
prefix a finding's description (after the `[B1] (HIGH)` tag, never before it) with `(A)`
or `(B)` to mark which pass surfaced it. Omit Pass B entirely if no Domain context block
was supplied — then Pass A is the whole review and `### Reasoning` may be used instead.
