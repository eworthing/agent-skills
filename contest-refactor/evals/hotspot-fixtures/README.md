# Implementation-Hotspot Eval Fixtures

Paired fixtures for the implementation-hotspot advisory candidate-evidence detector
(`scripts/audit_hotspots.py`, Method.md Step 6).

The tracked manifests serve two distinct checks:

- `_audit_hotspots_selftest.py` enforces deterministic scanner recall and restraint from the
  committed codebases and TOML expectations.
- The K≥5 paired-Critic experiment below remains a manual model-behavior measurement; CI does
  not claim to grade model judgment.

## Arms

| arm | fixture | planted defect | expected outcome |
|---|---|---|---|
| recall | `recall-clean-arch-ugly-impl-1/` | Perfect hexagonal architecture with an entangled, high-mutation, single-use-helper implementation in `FeeSettlementService.settle_account_fees` | Critic with scanner candidate evidence flags implementation complexity; bare Critic misses it due to architectural cleanliness |
| restraint | `restraint-clean-domain-1/` | Clean domain and service layer with pure functions and explicit state transformations | Scanner produces 0 candidates; Critic produces 0 simplicity findings |

## Measurement Protocol

1. **Generate Candidate Evidence:**
   ```bash
   python3 scripts/audit_hotspots.py evals/hotspot-fixtures/<fixture>/codebase/ --json
   ```

2. **Arm A (Bare Critic Control):** Run Critic on `codebase/` with standard Method steps without scanner evidence.

3. **Arm B (Candidate-Injected Critic):** Run Critic on `codebase/` with `audit_hotspots.py` output provided as Method Step 6 candidate evidence (`promotion_allowed: false`).

4. **Grade:**
   - **Recall Arm:** Arm B must triage and confirm the complexity finding on `FeeSettlementService.settle_account_fees` (citing Claim → Source → Consequence → Remedy); Arm A misses it ($\le 1/5$ catch rate).
   - **Restraint Arm:** Zero false positive simplicity findings across both arms.

5. **Repeat K≥5 times** per arm per fixture.

## Doctrine

`promotion_allowed: false` — the scanner surfaces candidate symbols and their private neighborhoods,
not findings. The Critic must evaluate the code semantically and derive any findings strictly from source.
