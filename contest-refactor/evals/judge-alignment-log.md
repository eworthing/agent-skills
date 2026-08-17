# Judge-alignment log

Landing artifact for [`README.md` § Judge-finding routing](README.md#judge-finding-routing-layers-23-semantic-grading).
It records verdicts from the Layer 2 / Layer 3 semantic graders that concede a response is
correct in substance but fail it on wording, placement, or naming — **judge findings**, not
agent findings. Do not "fix" these by editing the criterion, the grader prompt, or skill
prose; log them here and leave them for the item-10 alignment measurement.

Each row:

- **Date** — when the verdict was observed.
- **Eval / case ID** — the `evals.json` id or `reviewer-cases/<id>` that produced it.
- **Grader verdict quote** — the reasoning, verbatim, that shows the substance/wording split.
- **Why substance-correct / wording-fail** — one line: what the response actually got right,
  and what surface property the grader failed it on.
- **Disposition** — `pending item-10 measurement` until the alignment pass runs.

| Date | Eval / case ID | Grader verdict quote | Why substance-correct / wording-fail | Disposition |
|---|---|---|---|---|
| — | — | — | — | — |

No entries yet.
