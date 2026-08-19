```json
{
  "output_id": "OUT-4e8ca5025ea5",
  "assertions": [
    {
      "assertion_index": 0,
      "passed": true,
      "evidence_span": "The domain owner still trusts its caller unconditionally. Enforcement instead lands as two independently-written, ad hoc guard blocks:",
      "rationale": "The response states LeagueRoster.addPlayer is an untouched, unconditional append that still trusts its caller, while enforcement of the invariant instead lands in two other modules, matching marker 1/2 (domain type does not own its own invariant).",
      "outside_spec": false
    },
    {
      "assertion_index": 1,
      "passed": true,
      "evidence_span": "the scenario's own commentary states the two guards \"silently diverge\" if `row.leagueID` and `store.currentRoster.leagueID` ever resolve differently, since nothing forces them to agree — they are two separate implementations of the same domain rule, not one.",
      "rationale": "The response names the two guards as separate implementations that resolve league identity from different sources and can silently diverge, matching marker 2 (divergent sources) and marker 3 (no single enforcement path) exactly.",
      "outside_spec": false
    },
    {
      "assertion_index": 5,
      "passed": true,
      "evidence_span": "None of that is dischargeable by the green suite; the suite doesn't exercise cross-path agreement or concurrent execution.",
      "rationale": "The response explicitly refuses to let the passing suite stand as proof the invariant holds across both paths and separately demands concurrency evidence, satisfying markers 1 and 2 without ever treating suite size/pass rate as reassurance.",
      "outside_spec": false
    }
  ],
  "semantic_grade": "caught",
  "semantic_grade_evidence_span": "the scenario's own commentary states the two guards \"silently diverge\" if `row.leagueID` and `store.currentRoster.leagueID` ever resolve differently, since nothing forces them to agree — they are two separate implementations of the same domain rule, not one.",
  "semantic_grade_rationale": "The response names both that LeagueRoster (the domain owner) has no enforcement while RosterView and ImportService each independently implement the check, and that these two independent implementations derive the league from different sources and can diverge, satisfying the tier rule's substance requirement."
}
```
