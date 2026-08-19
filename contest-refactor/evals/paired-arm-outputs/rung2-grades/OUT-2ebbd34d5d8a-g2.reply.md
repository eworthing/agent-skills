```json
{
  "output_id": "OUT-2ebbd34d5d8a",
  "assertions": [
    {
      "assertion_index": 0,
      "passed": true,
      "evidence_span": "\"anemic domain model (LeagueRoster still cannot enforce its own invariant)\", \"duplicated invariant logic across presentation and infrastructure layers (shotgun surgery risk)\"",
      "rationale": "The response states LeagueRoster still cannot enforce its own invariant while the check was duplicated into RosterView and ImportService instead, matching satisfying marker 2 (domain type does not own its own invariant).",
      "outside_spec": false
    },
    {
      "assertion_index": 1,
      "passed": true,
      "evidence_span": "divergent duplicate guards keyed off different league-id sources (store.currentRoster.leagueID vs row.leagueID)",
      "rationale": "The response names the two guards as independently-built and diverging because they derive league identity from different sources, matching satisfying marker 2 exactly.",
      "outside_spec": false
    },
    {
      "assertion_index": 5,
      "passed": true,
      "evidence_span": "Test-green is true but irrelevant to the claim being made.",
      "rationale": "The response explicitly refuses to treat the green suite as proof the invariant holds and instead states no test exercises the invariant across both call paths, matching satisfying marker 1.",
      "outside_spec": false
    }
  ],
  "semantic_grade": "caught",
  "semantic_grade_evidence_span": "\"critical — domain invariant enforcement duplicated outside the domain owner (anemic domain model), with two guards deriving league identity from different sources and no shared source of truth, risking silent invariant violation on import\"",
  "semantic_grade_rationale": "The response names both facets required by the tier rule: LeagueRoster (the domain owner) is not enforcing the invariant, and the two independently-built guards derive league identity from different sources creating a real divergence risk."
}
```
