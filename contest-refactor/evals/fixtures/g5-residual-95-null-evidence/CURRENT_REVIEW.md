# Loop 1 — HALT_SUCCESS_candidate (invalid; G5 forward-half regression fixture)

Derived from `halt-candidate-no-challenge`: all 9 dimensions score 9.5 with
`residual_disposition: "accepted"`, but `architecture_quality` has both
`residual_blocking_10` and `residual_rationale_or_backlog_ref` nulled out —
an accepted residual with no named evidence for it. `candidate_fingerprint`
is recomputed for the mutated scorecard. The validator's G5 forward-half
check (`check_g5_forward_residual_fields`) rejects this.
