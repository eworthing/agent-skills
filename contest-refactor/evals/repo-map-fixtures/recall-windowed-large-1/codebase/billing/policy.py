"""billing internal implementation (cross-package wiring lives here, not in __init__)."""
from payments._impl import PaymentsApi  # billing -> payments
from tax._impl import TaxApi  # billing -> tax
from reporting.audit_log import ReportingApi  # billing -> reporting

class BillingApi:
    def __init__(self):
        self._payments = PaymentsApi
        self._tax = TaxApi
        self._reporting = ReportingApi
