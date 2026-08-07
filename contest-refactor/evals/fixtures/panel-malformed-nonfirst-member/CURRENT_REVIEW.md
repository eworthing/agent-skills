# Loop 1 — HALT_SUCCESS (v5 panel fixture; fail)

Member 2 (not member 1) is missing 'reason' and carries empty 'attempts'. Per-member shape validation must run at every panel index, not just the first. Negative case: G32 fails on member[1] shape.
