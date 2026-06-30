"""Order service — orchestrates domain logic via the infrastructure repository."""

from domain.models import Order
from infrastructure import OrderRepository


class OrderService:
    def __init__(self) -> None:
        self._repo = OrderRepository()

    def get_order(self, order_id: str) -> Order:
        return self._repo.find(order_id)

    def place_order(self, order_id: str) -> Order:
        order = Order(order_id, status="placed")
        self._repo.save(order)
        return order
