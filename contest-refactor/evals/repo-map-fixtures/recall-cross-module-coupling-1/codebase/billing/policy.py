"""Billing policy constants and discount logic.

Imports reporting.audit_log to record every policy decision for compliance.
This creates a back-edge: billing -> reporting -> billing (hidden cycle).
"""

from reporting.audit_log import record_policy_event  # cross-module import

LATE_FEE_RATE = 0.15
STANDARD_DISCOUNT = 0.10


def apply_discount(amount: float, tier: str) -> float:
    rate = STANDARD_DISCOUNT if tier == "standard" else 0.0
    discounted = amount * (1 - rate)
    record_policy_event("discount_applied", {"tier": tier, "rate": rate})
    return discounted
