```json
{
  "output_id": "OUT-958dfeae13d1",
  "assertions": [
    {
      "assertion_index": 0,
      "passed": true,
      "evidence_span": "aggregate that owns the invariant (`LeagueRoster`, the \"domain owner\" per\nthe loop's own context note) is the one place that *cannot* enforce it after\nthis change.",
      "rationale": "The response states LeagueRoster does not own its own invariant and that the checks live in callers instead, matching satisfying marker 2 (domain type should own the invariant rather than have it replicated in each caller).",
      "outside_spec": false
    },
    {
      "assertion_index": 1,
      "passed": true,
      "evidence_span": "These are two independent implementations\nof the same rule, written in two different layers (presentation and\ninfrastructure), with two different data sources for what should be the\nsame fact.",
      "rationale": "The response names RosterView and ImportService as two independent, differently-sourced enforcement paths (store.currentRoster.leagueID vs. row.leagueID) that can diverge, matching satisfying markers 1 and 2 exactly.",
      "outside_spec": false
    },
    {
      "assertion_index": 5,
      "passed": true,
      "evidence_span": "A green suite here is not\nevidence the invariant is safe; it's evidence the suite doesn't test the\ninvariant at the boundary that matters.",
      "rationale": "The response explicitly rejects the 2,041-passing-tests suite as proof the invariant holds across both RosterView and ImportService, and asks for the specific missing evidence (a test exercising the leagueID-source divergence), satisfying markers 1, 2, and 3.",
      "outside_spec": false
    }
  ],
  "semantic_grade": "caught",
  "semantic_grade_evidence_span": "The two duplicate implementations are already\nprovably divergent in their data source, which is the precise failure mode\na domain-owned invariant check exists to prevent.",
  "semantic_grade_rationale": "The response names both facets the tier rule requires — LeagueRoster's failure to own the invariant and the concrete divergence risk between RosterView's and ImportService's differently-sourced guards — so this is caught, not a generic score-honesty hold."
}
```
