"""reporting internal implementation (cross-package wiring lives here, not in __init__)."""
from billing.policy import BillingApi  # reporting -> billing
from audit._impl import AuditApi  # reporting -> audit

class ReportingApi:
    def __init__(self):
        self._billing = BillingApi
        self._audit = AuditApi
