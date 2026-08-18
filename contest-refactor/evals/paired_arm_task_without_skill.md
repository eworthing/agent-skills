# Paired-arm measurement task — without_skill arm

You are acting as an independent code reviewer (a "Critic") on one completed refactor loop.

## Sandbox — read this first

You have been given exactly one attached file for this task:

- `scenario.md` — the diff the Actor made this loop, and the Actor's own report (the Actor
  considers the work done and reports tests green).

That is your **only** input. Do not read, list, or search any other file. Do not read the live
repository, its git history, its skills, or any documentation about how a reviewer "should" work.
Do not attempt to browse the filesystem beyond the one attached file. Base your review entirely
on what `scenario.md` shows you.

## Your task

Review one completed /contest-refactor loop. `scenario.md` shows the change the Actor made this loop and the Actor's report (the Actor considers it done and tests are green). Independently assess the refactor against current source — do not just echo the Actor's report. Save your verdict to ./review-verdict.md: prose reasoning first (what you found, or what you cleared and why), then end the file with one fenced ```json block with exactly these fields: {"verdict": "approved|rejected|conditional", "blocks_95": true or false (does a finding block accepting the touched dimension at the 9.5 threshold), "blocking_severity": the rubric severity anchor or null, "dimension_scores": {dimension name: 0-10} for the dimension(s) this loop touches, "flagged_smells": [named smells] or [], "evidence_demanded": [evidence you would require before accepting] or []}.

## Output

Write your full response — prose reasoning, then the single fenced ` ```json ` verdict block
described above — to `./review-verdict.md`. Do not write anything else. Do not fabricate a rubric
vocabulary you were not given; describe findings in your own words if you have no other basis.
