# Findings mode

Open when: the mode is `findings` (per-frame tagged notes). Read `fairness-and-verification.md` too.

A finding is a specific, checkable thing you can see in one frame, stored as a note that shows in the viewer's notes list. This mode is not scoring.

## Batch loop

Commands come from the profile's `helpers`; flags below are the usual ones. If the profile's helper documents different flags, use those.

1. `sc check --all`; note the counts. With `apply=yes`, `sc snapshot` and note the path.
2. Build a batch: `<helpers.batch> --audit [--home | --competitors] [--own-only] --limit <batch_size> > <session>/audit-batch.json`. The helper skips frames that already carry an audit note. `--own-only` restricts to frames the same auditor family has not covered, for a same-auditor pass.
3. For each item: open the image, read the case `task` text, look at the whole image, then write 1 to 5 findings.
4. Write `<session>/audit-out.json`, a JSON array and nothing else:
   `[{"capture_id": "<id>", "findings": [{"kind": "...", "severity": "...", "tag": "...", "text": "...", "evidence": "..."}]}]`
   Copy `capture_id` exactly from the batch.
5. Dry run: `<helpers.ingest_findings> <session>/audit-out.json`. It validates and prints what it would add. Fix every reject and rerun.
6. Add `--apply` only when the invoker wrote `apply=yes` for this run. It takes a snapshot, then registers; the next batch skips the audited frames.
7. Without apply, the batch would repeat, so move on with `--offset 0,8,16,...` (a new offset per batch) and list the manifest paths in the status file.
8. Stop at the session cap (`session_caps.findings_frames`) or an empty batch.

## The finding object

| Field | Rule |
| --- | --- |
| `kind` | `defect`, `observation` or `question` (below) |
| `severity` | `high` (blocks or misleads the task), `medium` (slows the operator or risks a slip), `low` (polish) |
| `tag` | exactly one tag from the rubric's tag list; the rubric file and README section named in the profile are the only source |
| `text` | 15 to 350 characters in your own words: name the element, the problem and why it matters for the task |
| `evidence` | up to 150 characters: text copied exactly from the screen, or the element you point to (for example the header text, or "red square left of the volume control") |

Count: 1 to 5 findings per frame, at most 2 of kind `observation`.

### Kinds

- `defect`: a design problem that would cost the operator time, a wrong tap or a missed state.
- `observation`: a notable fact or a strength.
- `question`: something you cannot judge from this frame; say which other frame would settle it.

**How the ledger stores them.** A design problem in the app is not an evidence defect. The ingest helper stores it as kind `observation` with the tag `design-defect`. Kind `defect` in the ledger is reserved for problems with the capture itself (the wrong case, a mid-transition frame, a frame identical to another), and it flags the capture as questionable evidence. Write your design problems as `defect` in the batch output; do not hand-register ledger `defect` notes for design problems. For an evidence problem, add a ledger `defect` note with a tag such as `wrong-case` or `retake` as the README describes.

### Strengths

A strength is kind `observation` with the tag `strength` and no facet tag, because a facet tag on a strength is counted as a defect of that facet in later tallies. A clean screen gets one observation naming its strongest point, with `strength`. If the helper in the profile still forces a facet tag, report that in the status file and do not work around it by inventing a defect.

## Say how to fix it, and how sure you are

A defect that names no remedy is not much use. The finding has no field for it and no schema change is assumed, so the remedy goes inside `text` under fixed lead-ins that can be found by search. Do not invent tags or fields.

1. **`To raise this:`** ends every `defect`. Name the concrete screen change: what to move, resize, relabel, add or remove. Never "improve contrast". Say which facet it lifts (the tag already names the problem; add the rubric's part, such as clarity, speed or safety, when a rating pass will score the same frame). When one frame has several defects, write them largest gain first, high severity before low.
2. **`To be sure of this:`** ends every `question`, and any defect whose judgment rests on what the frame cannot show (store art, mid-transition, no playing state, tier C or D, no device capture). Name the capture, state and device that would settle it, and say whether the finding could be dropped, or get worse, once it exists.
3. A strength needs neither lead-in; it needs the `strength` tag only.

The `text` limit is 350 characters, so keep the problem to one clause and the remedy to one or two changes. If the remedy needs more, shorten the problem; do not drop the lead-in.

Worked example, design change (placeholder names):
`<app> / <case>`, kind `defect`, severity `medium`, tag from the rubric list, evidence "Stop" icon beside "Delete". Text: "Stop is a small icon next to Delete, so a rushed tap can hit the wrong one. To raise this: make Stop a full-width bar at the bottom (safety); move Delete behind a long-press (safety)."

Worked example, evidence gap (placeholder names):
`<app> / <case>`, kind `question`, severity `low`. Text: "This tier D store still shows no sound playing, so Stop cannot be judged. To be sure of this: capture the live board on a device with a sound playing; the defect, if any, would be a small Stop, and a large labelled one would close it."

## What to leave out

Every finding must be visible in this frame. No generic praise or advice ("improve contrast"): say where. The exclusions and frame-state rules are in the tool README, in the section on rulings, and apply here as they do to ratings. In short, do not report:

- device scale, empty space or grey toggles on tier C or D frames (an on-Mac run, store art);
- sample or demo data (generic track names, placeholder copy);
- a correctly disabled control, or Stop or progress on an idle frame;
- features the screen was never meant to have (unmet wishes);
- a row cut off at a pinned bar, beyond a `low` defect;
- an adjacent frame judged on anything other than what it shows of the task;
- an unrelated cover (dialog, coach mark, publisher badge): audit the surface underneath, and report the cover only when it hides a control the task needs;
- an on-Mac runtime failure message: judge how the screen words it (cause, retry), not the failure;
- stacked excluded items piled onto one real weakness.

For the home app, judge its own screen. For a simulator or fixture frame (tier B), judge layout and states, not the sample data.

## Discipline

- One finding per frame per issue. Before writing, read the frame's open notes (`sc list-notes --capture <id> --open`, or the batch item's context field) and do not restate one.
- In a same-auditor pass, do not read or copy other models' notes or scores. A batch context field showing other scores is for orientation only.
- Quote visible text exactly, with its capitalisation and punctuation.
- Every note you register carries the auditor tag from the profile and your real model ID as `author`; the ingest helper adds both when the profile's `authors.findings` is set. If it does not, stop and report.
- Not sure whether something is visible? Look again at the edges and zoom a crop before writing it. If you still cannot tell, write a `question`.

## Done when

The batch output file validated in a dry run (or applied under `apply=yes`), the counts from `sc validate` and `sc check --all` are recorded, every `defect` ends with `To raise this:` and every `question` with `To be sure of this:`, and the spot-check is done. Then write the status file ([handback.md](handback.md)).
