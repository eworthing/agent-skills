"""api internal implementation (cross-package wiring lives here, not in __init__)."""
from orders._impl import OrdersApi  # api -> orders
from reporting.audit_log import ReportingApi  # api -> reporting
from billing.policy import BillingApi  # api -> billing

class ApiApi:
    def __init__(self):
        self._orders = OrdersApi
        self._reporting = ReportingApi
        self._billing = BillingApi
