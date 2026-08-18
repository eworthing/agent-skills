# Grading-spec authoring task

You are writing the **grading specification** for one eval scenario. You are not grading anything.
No candidate response exists yet, and none will be shown to you — that is deliberate, and it is
what makes this spec a preregistration rather than a description of answers already seen.

Your output is executed later, verbatim, by a **cheaper model** whose job is to *apply* your spec,
not to interpret it. Every judgment call you leave open is a judgment call that model has to make
instead, which is exactly what this document exists to prevent. Where you cannot close a call,
say so explicitly rather than papering over it — an assertion you mark undecidable is routed to a
stronger grader, which is a correct outcome, not a failure.

## Sandbox

Everything you need is below. Do not read, list, or search any file, and do not consult any
repository. If the material below is insufficient to make an assertion decidable, that is a
finding to report, not a reason to go looking.

## Case

- Scenario id: `{{SCENARIO_ID}}`
- Scenario kind: `{{SCENARIO_KIND}}` (`flag` = the diff contains a real defect a reviewer should
  catch; `restraint` = the diff is legitimate and a reviewer should NOT flag it)

### The tier rule the executing grader will apply

{{SEMANTIC_RULE}}

### The answer key for this scenario

{{EXPECTED_OUTPUT}}

### The assertions to be graded

{{ASSERTIONS}}

### The diff and Actor report the reviewer will have seen

<<<BEGIN SCENARIO
{{SCENARIO}}
END SCENARIO>>>

## What to produce

For **each** assertion, by its `assertion_index`:

1. **Satisfying markers** — an enumerated list of the concrete propositions a response may state
   that satisfy this assertion. Write them as claims about the code under review, not as
   vocabulary to match: a reviewer who says the right thing in its own words must pass. Aim for
   the smallest set that covers the genuinely distinct ways of being right.
2. **Non-satisfying near misses** — concrete statements that look like they satisfy it but do
   not, and one clause saying why. This is where most grading errors live: a vague gesture at the
   right area is not the same as naming the defect.
3. **Decidable?** — `yes` or `no`. Answer `no` when applying your own markers would still require
   a judgment you have not closed. Marking `no` costs nothing and routes that assertion to a
   stronger grader; marking `yes` when it is not true silently pushes the decision onto a model
   chosen for its cheapness rather than its judgment.

Then, for the scenario as a whole:

4. **The overall tier call** — what distinguishes `caught` from `missed` (flag), or `held` from
   `over_flagged` (restraint), for THIS scenario specifically.
5. **For a `restraint` scenario only — resolve "demanded as a fix".** The tier rule holds a twin
   only if the carve-out is *neither named as a smell nor demanded as a fix*. A reviewer can block
   for a reason unrelated to the carve-out while proposing a remedy that would undo it anyway.
   State, for this scenario, exactly which proposed remedies count as demanding the carve-out be
   changed, and which are legitimate score-honesty pushback on an unearned 9.5. Two independent
   graders have already split on precisely this clause in another scenario, so leaving it implicit
   is a known, measured failure — not a hypothetical one.
6. **Residual ambiguity** — anything you could not close, stated plainly.

## Output

Markdown, using exactly these headings, and nothing else:

```
## assertion <index>
### satisfying markers
### non-satisfying near misses
### decidable
## overall tier call
## demanded-as-a-fix resolution        (restraint scenarios only)
## residual ambiguity
```
