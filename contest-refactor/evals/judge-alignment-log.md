# Judge-alignment log

Landing artifact for [`README.md` § Judge-finding routing](README.md#judge-finding-routing-layers-23-semantic-grading).
It records two kinds of grader finding: verdicts that concede a response is correct in substance
but fail it on wording, placement, or naming — **judge findings**, not agent findings — and
verdicts where the grader **could not place the response in any available category** because the
spec's categories do not partition the space (**spec-gap findings**, second trigger). Do not "fix" these by editing the criterion, the grader prompt, or skill
prose; log them here and leave them for the item-10 alignment measurement.

Each row:

- **Date** — when the verdict was observed.
- **Eval / case ID** — the `evals.json` id or `reviewer-cases/<id>` that produced it.
- **Grader verdict quote** — the reasoning, verbatim, that shows the substance/wording split.
- **Why substance-correct / wording-fail** — one line: what the response actually got right,
  and what surface property the grader failed it on.
- **Disposition** — `pending item-10 measurement` until the alignment pass runs.

A spec-gap row uses the same columns; its "why" states which categories failed to cover the
response rather than a substance/wording split.

| Date | Eval / case ID | Grader verdict quote | Why substance-correct / wording-fail | Disposition |
|---|---|---|---|---|
| 2026-08-19 | paired-arm study, 4 scenarios (`suppression-*`, `crossplat-*`, `principal-abstraction-seam-flag`) | 7+ graders independently emitted an unschema'd `outside_spec: true` | **Spec gap.** Reviewers rejected on grounds the spec never enumerated; every spec had been recorded as fully decidable before dispatch. Convergent invention by blinded, independent graders across two separate spec-authoring runs. | pending item-10 measurement |
| 2026-08-19 | `crossplat-flag` / pair-028 with_skill (`OUT-35f46cab5090`) | "does not fit `missed`, whose operative test is a hold … `without naming the mechanism`, which is not true here … a genuine gap between the two literal definitions that the binary framing does not resolve" | **Spec gap.** The response named the defect mechanism in full and demanded the correct evidence, but declined to prescribe an unverified fix — neither `caught` nor `missed` as written. Grader abstained rather than forcing a boundary; the frozen rule then let the first grader's definite `missed` stand. | pending item-10 measurement |

No entries yet.
