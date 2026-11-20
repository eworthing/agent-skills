# Hand-back

Open when: the end of a session, when writing the status file, or when stopping early (cap reached, blocker, `NO_VISION`).

## The status file

Name: the invoker's `status=<file>`, else `out-status-<mode>.txt` in the session folder. Write it even when you stop at Step 0. It is plain text, short, and every item below is present, with "none" or "not done" where it applies.

| Field | Content |
| --- | --- |
| Mode and scope | mode, scope, `apply=yes\|no`, profile path, date, your model ID and auditor tag |
| Vision | `OK`, or `NO_VISION` (then stop; nothing else is required but "nothing registered") |
| Frames reviewed | counts by group: home app, competitors (or the scope's own groups) |
| Frames remaining | re-run the batch helper with a large limit and count; give the number |
| Added | findings or ratings added (applied) or staged (dry run) |
| Rejected | count, and why each class was rejected |
| Top tags | the three most common tags in what you wrote |
| Spot-check | "spot-checked k of n frames, m findings corrected" and the IDs of corrections |
| Ledger checks | `sc validate` and `sc check --all` counts before and after, with any new warning kind named first |
| Snapshot | path of the snapshot taken, or "none (dry run)" |
| Manifests | paths of manifests: registered, or dry-run only |
| Hard to judge | frames or cases you could not judge, and which frame would settle each |
| Hard-to-apply rules | rules in the README or rubric you found unclear |
| Authorisations | any prompt authorised for this run, quoted; else "none used" |
| Not done | explicit list: what the invoker asked for that you did not do, and why |

Rating mode adds: the calibration result (PASS or FAIL with the report), the lowest and highest scores given and the screens they went to. Adjudicate mode adds: the capture IDs adjudicated, those left `needs-human`, and the adjudicator author ID. Packet mode adds: the packet IDs and the verdicts.

## Lead-in checks

A pass is incomplete when any of these fail; fix them, or list the item under "Not done".

- Every score below the top of the scale carries `To raise this:` with concrete changes (what to move, resize, relabel, add or remove), ordered by gain, naming the part each lifts, and what a perfect score needs.
- Every score or verdict resting on missing evidence (store art, mid-transition, no playing state, tier D, no device capture) also carries `To be sure of this:` with the capture, state and device that would settle it, and whether the score could move up or down.
- Every top score has one line saying why nothing would improve it.
- Every `defect` finding ends with `To raise this:` and every `question` finding names the frame that would settle it.
- Every packet finding has both lead-ins in `reason` or `next_step` where they apply.

Report in the file: "lead-ins present on k of n scores below top" (count by search for the lead-ins in what you wrote).

## The second artifact

The registered manifest (or the dry-run manifest paths) is the second artifact. A status file without it, or a manifest without a status file, is an incomplete hand-back.

## Before you write it

- Counts come from the CLI and the helpers, not from memory.
- Release the writer claim, and say so.
- Say what the numbers do not support (a tag rate across auditors, a screen's score from scouts alone, a tier C frame's score as final).
- Keep the wording to what you saw in the images and read in the ledger; separate the two ([claim vocabulary](fairness-and-verification.md)).
- Do not mention anything personal visible in a frame.
