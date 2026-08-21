# Post-hoc gate sweep — /Users/Shared/git/BenchHype

> Interpretation: strict failures on artifacts written before a gate shipped are
> epoch observations, not violations by the run. This is phase-to-gate matrix data
> for the Tier-3 validator design.

| commit | date | loop | state | run_id | issues (rules) | diagnostics |
|---|---|---|---|---|---|---|
| e08679bb0 | 2026-05-09 | 1 | CONTINUE | null | G5×7 | — |
| a216dd52f | 2026-05-09 | 2 | CONTINUE | null | G5×6 | — |
| 9a3c6d5fc | 2026-05-09 | 3 | CONTINUE | null | G5×6 | — |
| b4dcc12db | 2026-05-09 | 4 | CONTINUE | null | G5×4 | — |
| 9a1eb357d | 2026-05-09 | 5 | CONTINUE | null | G5×5 | — |
| 6ef25d588 | 2026-05-09 | 6 | HALT_STAGNATION | null | clean | — |
| 254dfb6a0 | 2026-05-09 | 7 | HALT_STAGNATION | null | clean | — |
| 631652a99 | 2026-05-09 | — | purged | — | — | — |
| acbcd48db | 2026-05-09 | 1 | CONTINUE | null | G19×2 | g17-check-blind, reviewer-independence-unverified |
| 4e896fbc9 | 2026-05-09 | 2 | CONTINUE | null | G18, G19×2 | reviewer-independence-unverified |
| 9aadf2c0e | 2026-05-09 | 3 | HALT_SUCCESS | null | G18, G19×2, G21-scorecard×9, G5×2, schema-enum | reviewer-independence-unverified, transition-violation |
| ee0e598de | 2026-05-10 | — | purged | — | — | — |
| f821951eb | 2026-05-10 | 1 | CONTINUE | null | G18, G19×2 | reviewer-independence-unverified |
| 2251a1cfe | 2026-05-10 | 2 | CONTINUE | null | G18, G19×2 | reviewer-independence-unverified |
| 0e44334d7 | 2026-05-10 | 3 | CONTINUE | null | G18, G19×2 | reviewer-independence-unverified |
| b4f809b8f | 2026-05-10 | 4 | CONTINUE | null | G18, G19×2 | reviewer-independence-unverified |
| 942920223 | 2026-05-10 | 5 | HALT_STAGNATION | null | G18, G19×2 | — |
| df43cdc8e | 2026-05-10 | — | purged | — | — | — |
| de00f4ef2 | 2026-05-10 | 1 | HALT_STAGNATION | null | G18×2, G19 | — |
| 07a596feb | 2026-05-10 | — | purged | — | — | — |
| 91ebcbff2 | 2026-05-10 | 1 | HALT_SUCCESS | null | G18, G19×2, G22 | — |
| 3113b7e66 | 2026-05-14 | — | purged | — | — | — |
| 725bf6383 | 2026-05-16 | 1 | CONTINUE | null | clean | — |
| cb4465476 | 2026-05-16 | 2 | CONTINUE | null | G18, G19×2, G22 | reviewer-independence-unverified |
| 742208b92 | 2026-05-16 | 3 | HALT_SUCCESS | null | G18, G19×2, G22 | transition-violation |
| 38592d1aa | 2026-05-19 | 3 | HALT_SUCCESS | null | G18, G19×2, G22 | transition-violation |
| af09e610b | 2026-05-19 | 1 | HALT_SUCCESS | null | G18×2, G22 | transition-violation |
| 72d5b3134 | 2026-05-20 | — | purged | — | — | — |
| 2caa30e4b | 2026-05-25 | 1 | CONTINUE | null | G19, G28 | G17, reviewer-independence-unverified |
| 040322433 | 2026-05-25 | 2 | CONTINUE | null | G19 | reviewer-independence-unverified |
| 0309e561f | 2026-05-25 | 3 | HALT_SUCCESS | null | G19 | reviewer-independence-unverified, transition-violation |
| b7f3f3e21 | 2026-05-25 | 1 | HALT_SUCCESS | null | G18, G19 | transition-violation |
| 5877b0f6e | 2026-05-28 | 1 | CONTINUE | null | G18 | reviewer-independence-unverified, transition-violation |
| 4f49b7c60 | 2026-05-28 | 2 | CONTINUE | null | G18 | reviewer-independence-unverified, transition-violation |
| 8ba44cdc4 | 2026-05-28 | 3 | HALT_SUCCESS | null | G18 | transition-violation |
| f2e8fcff9 | 2026-05-28 | — | purged | — | — | — |
| e6673d9f9 | 2026-05-28 | 1 | CONTINUE | null | clean | reviewer-independence-unverified |
| c84ccfd9f | 2026-05-28 | 2 | HALT_STAGNATION | null | clean | — |
| bd4d1a4c1 | 2026-05-28 | 3 | CONTINUE | null | clean | reviewer-independence-unverified, transition-violation |
| 0066a5d2d | 2026-05-28 | 4 | HALT_SUCCESS | null | clean | transition-violation |
| 6f0b109d8 | 2026-05-31 | 5 | HALT_SUCCESS | null | G19×2 | transition-violation |
| f80339539 | 2026-05-31 | 1 | HALT_SUCCESS | null | G19×2, G35 | — |
| 1548d59a1 | 2026-06-11 | 1 | HALT_SUCCESS | null | G18 | reviewer-independence-unverified, transition-check-blind |
| a36a42bc6 | 2026-06-21 | 1 | HALT_SUCCESS | null | clean | — |
| 9976c153b | 2026-06-21 | — | purged | — | — | — |
| 408129927 | 2026-06-23 | 1 | HALT_STAGNATION | null | G37×2, G39, G42 | — |
| 90429d572 | 2026-06-23 | 2 | CONTINUE | null | G39, G40, G42 | reviewer-independence-unverified, transition-violation |
| 3a1b76d53 | 2026-06-23 | 3 | HALT_SUCCESS_candidate | run-2026-06-23-benchhype-contest | G32, G40 | challenge-independence-unverified, transition-violation |
| dee624481 | 2026-06-23 | 3 | HALT_SUCCESS | run-2026-06-23-benchhype-contest | G32×2, G40 | challenge-independence-unverified, transition-violation |
| b63e93835 | 2026-06-26 | 1 | CONTINUE | null | G39×4, G42×3 | reviewer-independence-unverified |
| 0f8604fc5 | 2026-06-26 | 2 | CONTINUE | null | G39×4, G42×2 | reviewer-independence-unverified |
| c7dfcf60f | 2026-06-26 | 3 | CONTINUE | null | G39, G42 | reviewer-independence-unverified |
| a03b12abf | 2026-06-26 | 4 | HALT_SUCCESS_candidate | run-c7dfcf60-l4 | G32 | challenge-independence-unverified |
| a5b049947 | 2026-06-26 | 4 | HALT_SUCCESS | run-c7dfcf60-l4 | G32×2, G34 | challenge-independence-unverified, transition-violation |
| 520aa8461 | 2026-07-01 | — | purged | — | — | — |
| 8aefda32d | 2026-07-02 | 1 | HALT_LOOP_CAP | null | G19, G39×2, G42×2 | reviewer-independence-unverified |
| baea15925 | 2026-07-08 | — | purged | — | — | — |
| 13949f53d | 2026-07-08 | 1 | HALT_SUCCESS_candidate | run-2026-07-08-benchhype-loop1 | G32 | challenge-independence-unverified |
| 04e38d29a | 2026-07-08 | 1 | HALT_SUCCESS | run-2026-07-08-benchhype-loop1 | G18, G32×2 | challenge-independence-unverified |
| 6c3b7ba50 | 2026-07-08 | 1 | HALT_STAGNATION | null | G37×9, G39, G42 | — |
| 75f984018 | 2026-07-08 | 1 | HALT_STAGNATION | null | G5×9 | reviewer-independence-unverified |
| 3b8856fb1 | 2026-07-24 | — | purged | — | — | — |
| c51331320 | 2026-08-09 | 1 | CONTINUE | null | G46×3, reviewer-independence | reviewer-independence-unverified |
| 2e23cd271 | 2026-08-09 | 2 | CONTINUE | null | G46×3, reviewer-independence | reviewer-independence-unverified |
| 46a96dde8 | 2026-08-09 | 3 | HALT_STAGNATION | null | clean | — |
| bc4e6333f | 2026-08-10 | 4 | CONTINUE | null | G46×3, reviewer-independence, transition-legality | reviewer-independence-unverified, transition-violation |
| e024a19b7 | 2026-08-10 | 5 | CONTINUE | null | G46×3, reviewer-independence, transition-legality | reviewer-independence-unverified, transition-violation |
| 02bcdb359 | 2026-08-10 | 6 | CONTINUE | null | G46×3, reviewer-independence, transition-legality | reviewer-independence-unverified, transition-violation |
| 052e46baa | 2026-08-11 | 7 | CONTINUE | null | G46×3, reviewer-independence, transition-legality | reviewer-independence-unverified, transition-violation |
| fc44da868 | 2026-08-11 | 8 | HALT_STAGNATION | null | G46×3, transition-legality | transition-violation |
| be54b1e64 | 2026-08-11 | 9 | HALT_STAGNATION | null | G46×3, transition-legality×2 | transition-violation |
| a46a72596 | 2026-08-11 | 10 | CONTINUE | null | G46×3, reviewer-independence, rounds-membership, transition-legality×3 | reviewer-independence-unverified, transition-violation |
| 462c8678f | 2026-08-11 | 11 | HALT_STAGNATION | null | G46×3, transition-legality×3 | transition-violation |
| d19cfd214 | 2026-08-16 | 12 | HALT_LOOP_CAP | null | G18, G33, G37, G39×2, G43×3, G46×3, G5×4, reviewer-independence, transition-legality×4 | G17, reviewer-independence-unverified, transition-violation |
| f03b9fcc9 | 2026-08-16 | 12 | HALT_LOOP_CAP | null | G46×3, G5×5, reviewer-independence, transition-legality×4 | G17, reviewer-independence-unverified, transition-violation |
| 0f2935143 | 2026-08-19 | 1 | HALT_SUCCESS_candidate | run-2026-08-20-001 | challenge-independence | challenge-independence |
| 2bf170dda | 2026-08-19 | 1 | HALT_SUCCESS | run-2026-08-20-001 | challenge-independence | challenge-independence |
| b871e8803 | 2026-08-19 | 1 | CONTINUE | null | CONTINUE, G18, G27×2, G46×3, G5×9, evidence-chain×12, reviewer-independence, rounds-membership, schema-enum×4 | reviewer-independence-unverified |
| 95c530a56 | 2026-08-19 | 1 | HALT_SUCCESS_candidate | run-2026-08-20-002 | G18, G21-scorecard×9, G27×2, G32, G34, G46×3, G5×9, challenge-independence, evidence-chain×12, reviewer-independence, rounds-membership, schema-enum×4 | challenge-independence-unverified, reviewer-independence-unverified |
| 302837137 | 2026-08-19 | 1 | CONTINUE | null | CONTINUE, G18, G27×2, G46×3, G5×9, reviewer-independence, rounds-membership, schema-enum×2 | reviewer-independence-unverified |
| be0f1c661 | 2026-08-19 | 2 | HALT_SUCCESS_candidate | loop-2-302837137 | G5×8, challenge-independence, reviewer-independence, rounds-membership | G17, challenge-independence-unverified, reviewer-independence-unverified, transition-check-blind |
| b731a849d | 2026-08-19 | 2 | HALT_SUCCESS | loop-2-302837137 | G18, G5×8, challenge-independence, reviewer-independence, rounds-membership | G17, challenge-independence-unverified, reviewer-independence-unverified, transition-check-blind |

## Aggregate: issues by rule

- G5: 91
- G46: 45
- G19: 34
- G18: 26
- evidence-chain: 24
- transition-legality: 21
- G21-scorecard: 18
- G39: 16
- reviewer-independence: 14
- G37: 12
- schema-enum: 11
- G42: 11
- G32: 10
- rounds-membership: 6
- G27: 6
- G22: 5
- challenge-independence: 5
- G40: 3
- G43: 3
- G34: 2
- CONTINUE: 2
- G28: 1
- G35: 1
- G33: 1

## Aggregate: bracketed diagnostics

- transition-violation: 42
- reviewer-independence-unverified: 36
- challenge-independence-unverified: 9
- G17: 5
- transition-check-blind: 3
- challenge-independence: 2
- g17-check-blind: 1
