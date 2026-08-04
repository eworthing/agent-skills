<!--
Pinned dispatch template for the Tier-1P prioritization probe.

Both arms MUST receive this text byte-identically with only the {{...}} placeholders
substituted, or the measurement is comparing prompts instead of skill prose. The
placeholders are filled by scripts/priority_probe_materialize.py.

Blind dispatch: the template deliberately never names the four candidate roles, never
says how many findings to expect, and never mentions distance-to-target or stall as
criteria. It points at the skill's own files and asks for a normal Step-1 output. The
whole question is what the loaded prose makes the Critic do.

Placeholders: {{REPO}} {{SKILL_DIR}} {{HISTORY}} {{LENS}} {{TEST_COMMAND}}
-->

You are running **Step 1 (Critic) only** of a `/contest-refactor` loop. Do not run
Step 2 or Step 3: no plan, no code changes, no commit. Produce the review's findings
and Improvement Backlog and stop.

Repository under review: `{{REPO}}`
Skill protocol directory: `{{SKILL_DIR}}`

Read these from the skill directory and follow them as written:

- `references/method.md` — the 10-step Method, the Evidence Chain, the Meta-Rules,
  and the Simplify Pressure Test.
- `references/method-critic.md` — the Critic-only convergence passes.
- `references/architecture-rubric.md` — vocabulary, smells, Severity Anchors, the
  architectural tests, and the Unified Seam Policy.
- `references/architecture-rubric-scoring.md` — the Score Anchors.
- `references/output-format-markdown.md` — the Improvement Backlog section contract.
- `references/{{LENS}}` plus `references/lens-security.md` and
  `references/lens-efficiency.md`.

Prior-loop context, which is real and should be treated as this run's history:

- Scorecard trajectory and per-dimension deltas for the 15 loops before this one:
  `{{HISTORY}}`. The current scores are the last entry's.
- Standing operational constraint recorded by the user in an earlier loop and still
  in force: **do not change observable per-item request behaviour against the
  third-party confirmations endpoint without a behavioural oracle.** Nothing in this
  repository covers the network.
- Discovery: lens `{{LENS}}`, test command `{{TEST_COMMAND}}`. Assume the build and
  test suite are green; you are not being asked to run them.

Investigate the source at `{{REPO}}` and emit findings through the normal evidence
chain, then assign the Improvement Backlog exactly as the protocol directs.

Return **JSON only**, no prose before or after, in this shape:

```json
{
  "findings": [
    {
      "loop_local_id": "F1",
      "title": "...",
      "severity": "<one of the four canon Severity Anchors, verbatim>",
      "evidence": ["path/to/File.swift:12 — what is there"],
      "why_it_matters": "...",
      "residual_disposition": null
    }
  ],
  "backlog": [
    {
      "priority": 1,
      "title": "...",
      "kind": "structural",
      "rank": "needed for winning",
      "why_it_matters": "...",
      "score_impact": "<canon_dim_id> <signed delta>"
    }
  ],
  "priority_1_accounting": "One sentence: which dimension Priority 1 moves, and why no candidate on a dimension further from target was available.",
  "scorecard_note": "One line per dimension you would move, and why."
}
```

`score_impact` must name each affected dimension by its **canon machine id** from
`canon/scorecard-dimensions.toml` with a signed delta, semicolon-joined for a
multi-dimension item — for example `data_flow +0.5; simplicity +0.5`. An item whose
`score_impact` cannot name a dimension is not a backlog item.

If a finding's correct disposition under the protocol is an accepted residual rather
than a backlog item, say so in `residual_disposition` and leave it out of the backlog.
