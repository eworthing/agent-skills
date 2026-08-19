```json
{
  "output_id": "OUT-91c77bfb9f99",
  "assertions": [
    {
      "assertion_index": 0,
      "passed": true,
      "evidence_span": "the object that should own the invariant (`LeagueRoster`) is a passive data bag, and every caller reimplements the business rule around it.",
      "rationale": "The response names LeagueRoster.addPlayer as unenforced (\"still a bare activePlayers.append(player) with zero enforcement\") while the check lives separately in RosterView.handleAdd and ImportService.importRoster, and explicitly states LeagueRoster is the owner that should have it instead of every caller reimplementing it, matching markers 1 and 2.",
      "outside_spec": false
    },
    {
      "assertion_index": 1,
      "passed": true,
      "evidence_span": "`RosterView` keys off `store.currentRoster.leagueID`; `ImportService` keys off `row.leagueID`. The scenario's own context section calls this out directly: if those two ever resolve a league differently (an alias, a stale cache, an ID remap), the invariant silently breaks through the import path while the UI path stays intact",
      "rationale": "The response names the two independent enforcement paths' differing data sources verbatim (store.currentRoster.leagueID vs row.leagueID) and frames the divergence as the actual defect, directly matching marker 2 rather than describing a single-module bug.",
      "outside_spec": false
    },
    {
      "assertion_index": 5,
      "passed": true,
      "evidence_span": "the green suite is not evidence the fix works, only that it didn't collide with anything else.",
      "rationale": "The response affirmatively rejects the 2,041-passing-tests figure as proof the invariant is enforced and instead demands tests exercising the direct-bypass and cross-path divergence scenarios, satisfying markers 1 and 2 and never relying on suite size/pass-rate as reassurance.",
      "outside_spec": false
    }
  ],
  "semantic_grade": "caught",
  "semantic_grade_evidence_span": "This is not a `domain_modeling` improvement; it's a relocation of the same anemic-model problem into two places instead of one, with a comment that overstates what was actually done and a newly introduced divergence bug documented in the scenario's own framing.",
  "semantic_grade_rationale": "The response names both facets required for \"caught\" — the invariant is enforced by two independently-built guards instead of by LeagueRoster, and the two guards derive the league from different sources and can disagree — so it satisfies the tier rule's naming requirement in substance."
}
```
