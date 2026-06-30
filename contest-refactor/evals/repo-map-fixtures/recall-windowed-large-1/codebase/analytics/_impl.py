"""analytics internal implementation (cross-package wiring lives here, not in __init__)."""
from reporting.audit_log import ReportingApi  # analytics -> reporting
from orders._impl import OrdersApi  # analytics -> orders

class AnalyticsApi:
    def __init__(self):
        self._reporting = ReportingApi
        self._orders = OrdersApi
