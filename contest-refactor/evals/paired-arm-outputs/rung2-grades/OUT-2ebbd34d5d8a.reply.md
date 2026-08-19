```json
{
  "output_id": "OUT-2ebbd34d5d8a",
  "assertions": [
    {
      "assertion_index": 0,
      "passed": true,
      "evidence_span": "This is not \"extracting\" the guard logic into the domain — it's the opposite. The invariant\ncheck that should live once, on `LeagueRoster` (or a domain service `LeagueRoster` delegates\nto), has been hand-copied into two unrelated layers, each deriving the league id from a\ndifferent source (`store.currentRoster.leagueID` vs. `row.leagueID`).",
      "rationale": "The response states the invariant check should live once on LeagueRoster rather than being replicated in RosterView and ImportService, matching satisfying marker 2 (domain type does not own its own invariant).",
      "outside_spec": false
    },
    {
      "assertion_index": 1,
      "passed": true,
      "evidence_span": "different source (`store.currentRoster.leagueID` vs. `row.leagueID`). The context note in the\nscenario spells out the resulting failure mode precisely: if those two league-id derivations\never diverge, a bulk import can add a player already active in that league and *neither* guard\nfires, because each guard only checks its own (already-consistent-with-itself) notion of which\nleague is being touched.",
      "rationale": "The response names the two independently-derived league-id sources and explains that their divergence lets the invariant be silently violated with neither guard firing, matching satisfying marker 2.",
      "outside_spec": false
    },
    {
      "assertion_index": 5,
      "passed": true,
      "evidence_span": "Test-green is true but irrelevant to the claim being made. 2,041 passing tests says nothing\nabout whether *this specific invariant* is now safely enforced, because nothing in the diff\nor the report indicates a new test was added that exercises the invariant across both call\npaths (UI add vs. bulk import). \"Suite is green\" is being used as a stand-in for \"the domain\nrule is now guaranteed,\" and those are not the same claim.",
      "rationale": "The response explicitly rejects the green suite as proof the invariant holds across both call paths, matching satisfying markers 1 and 3 and never treating suite-passing as reassurance.",
      "outside_spec": false
    }
  ],
  "semantic_grade": "caught",
  "semantic_grade_evidence_span": "\"blocking_severity\": \"critical — domain invariant enforcement duplicated outside the domain owner (anemic domain model), with two guards deriving league identity from different sources and no shared source of truth, risking silent invariant violation on import\"",
  "semantic_grade_rationale": "The response names both the ownership gap (LeagueRoster does not enforce its own invariant) and the divergence risk (two guards keyed off different league-id sources can disagree), satisfying the tier rule's caught criterion in substance."
}
```
