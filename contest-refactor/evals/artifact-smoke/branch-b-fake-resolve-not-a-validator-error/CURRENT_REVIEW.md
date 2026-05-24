# Loop 10 — Branch B retirement PASS (Critic-owned seam)

F-200 retired via Branch B (2-way hash equality across two occurrences with an
intervening `resolved` status).

**This fixture codifies the Critic-owned seam from Risks item 10:** the prior
`resolved` occurrence could have been a premature mark (a "fake resolve") that
let the next reappearance qualify for retirement on the easier 2-hash path.
The validator cannot catch a fake-resolve because correctness of `resolved` is
a Critic/reviewer responsibility (Check 1 / Check 2), not a structural
property. The validator passes by design.
