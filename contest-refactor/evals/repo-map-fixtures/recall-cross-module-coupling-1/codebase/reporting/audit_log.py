"""Audit-log module.

Imports billing.policy to embed the current rate in every audit entry.
This is the hidden back-edge: reporting -> billing, completing the cycle
billing -> reporting -> billing.
"""

from billing.policy import LATE_FEE_RATE  # cross-module import — closes the cycle


class AuditEntry:
    def __init__(self, event: str, payload: dict) -> None:
        self.event = event
        self.payload = payload
        self.late_fee_rate_snapshot = LATE_FEE_RATE  # captured at log time


def record_policy_event(event: str, payload: dict) -> None:
    entry = AuditEntry(event, payload)
    # In production this would persist; here it's a stub.
    _ = entry
