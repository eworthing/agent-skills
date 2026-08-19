```json
{
  "output_id": "OUT-aafad30e2396",
  "assertions": [
    {
      "assertion_index": 0,
      "passed": true,
      "evidence_span": "- `RosterView.handleAdd`: `store.allRosters.filter { $0.leagueID == store.currentRoster.leagueID && $0.activePlayers.contains(player) }`\n- `ImportService.importRoster`: `store.allRosters.filter { $0.leagueID == row.leagueID && $0.activePlayers.contains(player) }`",
      "rationale": "The response states LeagueRoster.addPlayer is left untouched (a doc-comment-only mutation) while the One-League Rule check is implemented twice, independently, in RosterView.handleAdd and ImportService.importRoster, matching marker 1's diagnosis that the domain type does not own its own invariant; it does argue for RosterStore rather than LeagueRoster as the consolidation target, but that fix-location choice does not negate the marker-1-level diagnostic already present in the response.",
      "outside_spec": false
    },
    {
      "assertion_index": 1,
      "passed": true,
      "evidence_span": "is one authoritative method called from both sites, not two hand-written copies keyed off\ndifferent fields (`store.currentRoster.leagueID` vs. `row.leagueID`).",
      "rationale": "The response names the two guards as independently-maintained copies that resolve the league from different fields (store.currentRoster.leagueID vs. row.leagueID) and treats the diff's own admission of a silent-violation scenario as a drift hazard, matching marker 2's specific divergence criterion.",
      "outside_spec": false
    },
    {
      "assertion_index": 5,
      "passed": true,
      "evidence_span": "The Actor's only test evidence is aggregate suite count (\"2,041 tests... 0 failed\"), which is\n**aggregate-test-count-as-test-strategy** (canon fake-clean-reward sub-pattern) applied to\njustify a domain-modeling claim it cannot support.",
      "rationale": "The response explicitly rejects the green suite's aggregate count as proof, naming it a fake-clean-reward pattern, states no test exercises the divergence/race scenario, and separately demands a concurrency test in its evidence_demanded list, matching markers 1 and 2.",
      "outside_spec": false
    }
  ],
  "semantic_grade": "caught",
  "semantic_grade_evidence_span": "is one authoritative method called from both sites, not two hand-written copies keyed off\ndifferent fields (`store.currentRoster.leagueID` vs. `row.leagueID`).",
  "semantic_grade_rationale": "The response names both required facets — LeagueRoster not owning the invariant while RosterView and ImportService each implement independent, differently-sourced guards that can diverge — meeting the tier rule's 'Caught' bar."
}
```
