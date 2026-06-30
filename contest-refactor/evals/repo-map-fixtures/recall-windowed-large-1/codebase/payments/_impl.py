"""payments internal implementation (cross-package wiring lives here, not in __init__)."""
from ledger._impl import LedgerApi  # payments -> ledger

class PaymentsApi:
    def __init__(self):
        self._ledger = LedgerApi
