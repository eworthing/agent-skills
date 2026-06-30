"""shipping internal implementation (cross-package wiring lives here, not in __init__)."""
from orders._impl import OrdersApi  # shipping -> orders
from fulfillment._impl import FulfillmentApi  # shipping -> fulfillment

class ShippingApi:
    def __init__(self):
        self._orders = OrdersApi
        self._fulfillment = FulfillmentApi
