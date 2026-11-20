# Fairness and verification

Open when: comparing apps, counting defects or strengths, spot-checking a session, or before any hand-back.

## Same-auditor comparisons only

Models notice different amounts. In a measured pass, one Claude model wrote about 2.1 design-defect notes per frame and a DeepSeek-class model about 0.9. A defect rate that differs between two apps therefore proves nothing when different auditors covered them.

- Report a home-versus-competitor difference in tag counts or defect rates only when **one auditor family covered both sides**. Otherwise write "auditors differ, not comparable", name the auditors on each side, and propose a same-auditor pass (the batch helper's `--own-only` mode, or the profile's equivalent).
- Count **distinct auditor families**, not notes. Ten notes from one family are one auditor's view.
- Strengths (`observation` notes tagged `strength`) are not defect evidence and are never counted as a defect or a facet. Do not add them to a tag tally.
- A rating spread between auditors is not a defect difference; a score gap between auditors on one capture is a split, handled by `adjudicate`, not by averaging.
- Never present a count as a finding about an app when the frames behind it are of a different tier (an on-Mac frame against a native one, store art against a device capture). Say the tiers.

## Spot-check protocol

After each session, before hand-back:

1. Sample `max(3, 10% of frames reviewed)` frames at random, plus **every `high`-severity finding** (or, in rating mode, every score of 9 or 10 and every score of 2 or less).
2. Re-open each image with the image tool. For a finding, confirm the quoted evidence text or named element is visible exactly as written, and that the tag fits what you see. For a rating, confirm the reason's description matches the frame and the score fits the rubric's anchors and caps.
3. Correct what fails: add a superseding note, or a new rating, never an edit and never a delete. Note IDs of the replaced items go in the status file.
4. Report: "spot-checked k of n frames, m findings corrected" (or "m ratings changed"). Say nothing stronger. The word "verified" may describe only the frames you re-opened in this protocol, and never the rest of the batch. If the spot-check could not be done (images unavailable, time), say so in the status file under "not done".

When a user asks you to "confirm all N findings are correct": run the spot-check, report k of n, and decline to claim the others. Offer to extend the sample, or to run a second model over the remainder.

## Claim vocabulary

Mark the basis of every statement in a status file, a packet or a summary:

- **seen in the image**: you opened this capture and saw it.
- **from the ledger**: read from notes, ratings, derivations or the registry, not re-checked against the image.
- **not checked**: neither; say what would check it.

Do not turn "from the ledger" into "seen in the image" by repeating it confidently.

## Other checks that protect fairness

- Same-auditor pass: do not read other models' notes or scores before judging. Their numbers anchor your own.
- Rating panels: two models, one frontier, for any verdict-carrying screen; a lone cheap rater's score on a verdict-carrying capture is flagged by the ledger and is not enough for a packet.
- A capture that carries an open evidence flag (a ledger `defect`, `retake`, `wrong-case` note) is not scored or counted until the flag is superseded by a retake.
- Counts in a status file come from the CLI (`sc list-notes`, `sc list-ratings`, `sc status`, the batch helper with a large limit), not from memory of what you wrote.
- Before and after counts of `sc validate` and `sc check --all` are compared. A new warning kind that was not there before the session is reported first in the status file, not buried.
