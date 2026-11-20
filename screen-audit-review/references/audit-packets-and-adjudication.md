# Audit packets and adjudication

Open when: the mode is `packet` (one per-case verdict) or `adjudicate` (settle split ratings).

## Packet mode

A packet is one reviewed judgment about one question, with one finding per case. Read the README section "Visual audits" for the exact schema; the shape is:

| Field | Meaning |
| --- | --- |
| `id`, `title`, `reviewer`, `date`, `question` | the packet's own identity and the question it answers |
| `findings[]` | one per case: `case_id`, `scope`, `reason`, `next_step`, `verdict`, and up to six `evidence` entries |
| `evidence[]` | each has `capture_id` and `original_sha256` (copy both from the ledger; never type a hash from memory) |
| `scorecard` (optional) | two to six `parts` in priority order and one row per scored app, with parallel `scores` and `notes`; the declared winner must lead on total, then on the first differing part; explain a remaining tie in `tiebreak` |

Verdict values are the ones the README lists: the home app leads, `competitor-leads`, `reference-leads`, `tradeoff` and `insufficient-evidence`. `competitor-leads` and `reference-leads` need `preferred_app`.

### Steps

1. Profile, vision check and writer claim as in SKILL.md. Find the cases and apps in scope from the invoker's request.
2. For each case read, without copying numbers from memory: `sc list-ratings --case <case> --by screen`, `sc list-notes --case <case> --open`, and `sc explain --app <app> --case <case>` for the derivation behind each score (rater tier, role, weight, policy, escalation state).
3. Open the evidence images you will cite. A packet is a judgment about screens: re-open every capture you name in `evidence`, and no capture you did not open.
4. Pick the verdict from what the images show, not from the average. If the evidence is thin, one auditor family only, or a verdict-carrying capture rests on scouts alone, the verdict is `insufficient-evidence` or `tradeoff`, and `next_step` names what would settle it.
5. In every `reason`, give the evidence tier letter beside each capture you mention (tier A native installed, B simulator or fixture, C on-Mac run, D store art or archived or demo). Tier D store art is never upgraded to a device capture. An on-Mac frame keeps "recapture on device" in the reason or `next_step`.
6. Write `<session>/packet-<case or topic>.json`, then `sc add-audit --record <session>/packet-....json`. Run `sc snapshot` first under `apply=yes`; without it, leave the file and say it was not added.
7. Say how the verdict could change. Put it in each finding's existing `next_step` (and `reason` for the gap), under the lead-ins `To raise this:` and `To be sure of this:`: for a case where the home app or the preferred app is below the best possible screen, the concrete screen changes that would lift it (move, resize, relabel, add, remove), largest gain first, naming the rubric part each lifts, and what a perfect screen would need; for a verdict resting on thin evidence (tier C or D, scouts only, no device capture), the capture, state and device that would settle it and whether the verdict could flip. A `tradeoff` or `insufficient-evidence` verdict always has the second lead-in. A scorecard row below the top score gets the first in its `notes`. No schema change is assumed.
8. A changed judgment is a new dated packet with its own `id`, never an edit of an earlier one.
9. `sc validate`; `sc check --all`; counts into the status file.

Comparisons between apps inside a packet follow `fairness-and-verification.md`: same-auditor evidence only, otherwise the packet says the auditors differ and the comparison is not drawn.

## Adjudicate mode

An adjudication settles a capture whose current agent ratings disagree by 2 or more points (state `needs-adjudication`). A frontier adjudicator's rating then decides the capture's score. Route: Claude (or the model the invoker names as adjudicator), never the cheap bulk model.

1. Find the captures: `sc list-ratings --state needs-adjudication --json`. Write their IDs to `<session>/items.json` (a JSON list, or one ID per line).
2. Run the harness in adjudicator role with `--emit-requests`: `python3 <tool.harness> run --role adjudicator --endpoint <endpoint file> --project <ledger.project> --items <session>/items.json --emit-requests <ADJ_DIR>`. The harness freezes the ratings shown to you in its plan; it never shows the owner's.
3. Open each request's image and the ratings it lists (rating ID, author, tier, role, score, reason, tags, failed checks). Judge the screen from the image first, then decide which ratings you side with. Answer in the structured reply the request describes, including the `adjudication` object: `adjudicates` (two or more rating IDs, all among those shown), `sides_with` (possibly none), `final_score` (must equal your score), and optional `excluded`.
4. A reason that repeats a rater's reason is refused. Write your own, and give it the `To raise this:` and (when evidence is missing) `To be sure of this:` lead-ins as in `ratings.md`, since the adjudicated score is the one that counts.
5. Use your own author ID for the adjudicator, never a panel rater's: reusing a rater's author supersedes that rater's own rating on the capture. The harness warns; heed it.
6. `python3 <tool.harness> run --ingest-responses <ADJ_DIR>` applies the gates, including the adjudication gate (checked once, retried once), and writes `<ADJ_DIR>/manifest.json`.
7. Register the admission record and the run, in this order, each as a dry run first: the admission record from the harness's adjudicator-record command (`sc register --manifest ADMISSION.json`), then `sc register --manifest <ADJ_DIR>/manifest.json`. Apply only under `apply=yes`, after `sc snapshot`. If the profile or the invoker has not authorised you as adjudicator, write the admission as a draft and say so; admission is the owner's call.
8. A capture with fewer than two current agent ratings, or one already adjudicated, stops the run before any call. A split that remains after adjudication becomes `needs-human`: list it in the status file, do not resolve it yourself.
9. `sc validate`; `sc check --all`; counts into the status file.

Packet and adjudicate runs are verdict-carrying work: always a second model reads the cheap model's input, and the status file says which model did which step.
