"""pricing internal implementation (cross-package wiring lives here, not in __init__)."""
from tax._impl import TaxApi  # pricing -> tax

class PricingApi:
    def __init__(self):
        self._tax = TaxApi
