# Reviewer Output Format

All provider prompts request the same structured output so `parse_structured_review()`
in `ppr_io.py` can extract findings uniformly. Include this template verbatim
in every prompt.

## Template

```
### Reasoning
Full analysis of the plan covering sequencing, hidden assumptions,
missing validation, rollback, and dependency gaps.

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
