# Rating mode

Open when: the mode is `rating` (1 to 10 scores per capture, v1 or v2).

The scale, anchors, profiles, caps, the frame-state rules and the rulings live in the tool README section "Screen ratings" and in the rubric file, both named in the profile. Read them at the start of the session. Do not copy the anchors into a note, a prompt or your reasoning as a new scale, and do not paraphrase them into your own wording of the scale.

## Setup

1. Profile, vision check and writer claim as in SKILL.md.
2. Open the rubric file and the README rulings the profile names. Note which checks and caps apply to each case profile (live play versus setup).
3. `sc check --all`; note counts. With `apply=yes`, `sc snapshot` first.

## Anchors study (no ratings written)

Run the profile's batch helper in anchors mode (`<helpers.batch> --anchors > <session>/anchors-out.json`). Open each anchor image, read its reference score and reason, and use them to set your scale. Do not write ratings for anchors. If the first anchor image will not open as pixels, that is the vision failure: `NO_VISION`, stop.

## Calibration

1. `<helpers.batch> --set calibration --limit 10 > <session>/calib.json`; rate every item as below; write `<session>/calib-out.json`.
2. `<helpers.calib_report> <session>/calib-out.json`. If it says FAIL, stop: write the report to the status file and do not rate further.
3. If it passes, ingest the calibration batch as a dry run (or applied under `apply=yes`) with the run name the profile gives. Report both outputs.

## Batch loop

Repeat until the batch helper returns nothing or `session_caps.rating_frames` is reached:

1. `<helpers.batch> --limit <batch_size> > <session>/batch.json`. The helper skips captures you already rated.
2. For each item, open the image first and look at the whole of it; read the `task` and the `profile` (live or setup). Answer in the order the README gives: checks if the route uses them, frame state (`complete` or `partial`), tags (only from the rubric, only what you can point to), dimension scores, the overall score, the reason.
3. Write `<session>/batch-out.json`, a JSON array with one object per item and `capture_id` copied exactly.
4. Ingest as a dry run (`<helpers.ingest_ratings> <session>/batch-out.json --run <run name>`); read the output; fix only rejected items and rerun them. Add `--apply` only under `apply=yes`.
5. If the helper refuses a batch because every score is equal, you are not rating: re-open the images and rate again. Never pad scores to get past the check.

## Rules specific to ratings

- **Never write `created_at`** anywhere. The tools add it. A made-up later time outranks your own later ratings and withdrawals and `check` reports it as future-dated.
- **Reason is required from agents**, in your own words, at most 400 characters: what is visible, the main weakness, what you could not judge. Do not repeat the task text.
- **Rate each screen on its own**, never relative to the others in the batch, and use the full range. Cheap models tend to be too kind to weak screens: a screen with a clear problem belongs where the rubric's anchors and caps put it, not in the middle.
- **Your score must agree with your checks.** The caps in the rubric (a missing task control, contradictory indicators, no large Stop while sound plays, a gate where the task is picking a result) bind the score. The rubric file lists them; apply them as written.
- **The number rates the screen, not the evidence.** A blurry, mislabelled or wrong-case capture gets a flagging note (see `findings.md` for the ledger `defect` use), not a low score.
- **Tier C and D frames are provisional.** Device scale, empty space and store framing never move the score.
- **Withdrawals** use `score: null`, never an edit and never a delete. Parts are not allowed with a null score.
- **Humans and agents are never averaged together.** Do not add, mix or reconcile an owner's rating into yours.
- **Do not read other models' scores** before rating when the pass is same-auditor.

## Say how to raise the score, and how sure it is

A score without the way up is not useful. The tool has no field for it, so no schema change is assumed: it goes in the rating's `reason`, under fixed lead-ins that can be found by search. Do not invent ledger fields or tags. Do not use a `todo` or `question` note for it: an open one flags the capture as questionable evidence. If the reason limit (400 characters from an agent in the harness prompts, 500 in the README) cannot hold it, shorten the wording first; only then register the rest as an `observation` note on the capture with `sc add-note`, starting with the same lead-in.

1. **`To raise this:`** for every score below the top of the scale. Name concrete screen changes (what to move, resize, relabel, add or remove), never "improve contrast". Order them by score gain, largest first, put the estimated gain in points, and name the part (clarity, speed, safety, or the rubric's own parts) each change lifts. End with what a perfect score needs, if that is more than the list.
2. **`To be sure of this:`** only when the score is uncertain because of what the frame cannot show (store art, mid-transition, no playing state, tier C or D, no device capture). Name the capture, state and device that would settle it, and say whether the score could move up, down or both. Never hide a low-confidence score behind a confident number.
3. A top score gets one line: why nothing would improve it.

Estimate gains from the rubric's anchors and caps, not from a new scale; do not restate the anchors.

Worked example, design change (placeholder names):
`<app> / <case>, score 6.` Reason: "Tiles readable; Stop is a small icon beside Delete. To raise this: widen Stop to a full-width bar (+2, safety); move Delete behind a long-press (+1, safety); wrap tile names to two lines (+1, clarity). To reach 10: also show the playing tile's name in the Stop bar (+1, speed)."

Worked example, evidence gap (placeholder names):
`<app> / <case>, score 6, tier D store art.` Reason: "Board layout is clear but no sound is playing in the still. To raise this: label the two unnamed icons (+1, clarity); show Stop under the playing tile (+1, safety). To be sure of this: capture the live board on a device with a sound playing (tier A); the score could fall if Stop is small, or rise if it is large and labelled."

Top score example: "10: task control, state and exit are plain and a wrong tap is prevented; nothing to change."

## v2 route (structured ratings through the harness)

The rating harness never writes the ledger; it writes a run folder, and `sc register` loads it. The route that keeps an agentic tool in the loop:

1. `python3 <tool.harness> run --endpoint <endpoint file> --project <ledger.project> --set <set> --out <RUN_DIR> --seed <n> --emit-requests <RUN_DIR>` writes one request file per capture and calls no model. Take the harness command and endpoint file from the profile; the endpoint file names an environment variable for a key, never the key.
2. Answer each request: write the reply text exactly as you would return it, into the `response_file` the request names. A request names neither the capture nor its app.
3. `python3 <tool.harness> run --ingest-responses <RUN_DIR>` applies the harness gates, writes `<RUN_DIR>/manifest.json` and `<RUN_DIR>/rejects.jsonl`, and prints what is pending. A reply refused by a retry gate gets a second request (`<id>.a2.json`) with the gate and its detail appended; answer that one.
4. `sc register --manifest <RUN_DIR>/manifest.json --dry-run`, fix, then register only under `apply=yes` (after `sc snapshot`).
5. One response alone: `sc rate --v2 response.json --run <RUN_ID> --capture <ID>`.

Read the README "Rating v2" and "Pilot harness" sections for the response fields, gates and the escalation states. Rater admission is the owner's decision: you may write a draft with the harness's admit command when the invoker asks, never an admitted record for yourself.

## Done when

All batches ingested as dry runs or applied; `sc validate` and `sc check --all` counts recorded; spot-check done; status file written ([handback.md](handback.md)) with the lowest and highest scores you gave, and the screens they went to.
