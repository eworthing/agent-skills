"""orders internal implementation (cross-package wiring lives here, not in __init__)."""
from catalog._impl import CatalogApi  # orders -> catalog
from inventory._impl import InventoryApi  # orders -> inventory
from pricing._impl import PricingApi  # orders -> pricing

class OrdersApi:
    def __init__(self):
        self._catalog = CatalogApi
        self._inventory = InventoryApi
        self._pricing = PricingApi
