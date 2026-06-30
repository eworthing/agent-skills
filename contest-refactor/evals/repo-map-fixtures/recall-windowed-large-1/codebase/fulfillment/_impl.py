"""fulfillment internal implementation (cross-package wiring lives here, not in __init__)."""
from inventory._impl import InventoryApi  # fulfillment -> inventory

class FulfillmentApi:
    def __init__(self):
        self._inventory = InventoryApi
