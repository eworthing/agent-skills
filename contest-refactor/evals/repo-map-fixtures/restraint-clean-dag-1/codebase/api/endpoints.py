"""HTTP endpoint — depends on domain only; does not reach into infrastructure."""

from domain import OrderService


def handle_request(order_id: str) -> dict:
    svc = OrderService()
    order = svc.get_order(order_id)
    return {"order_id": order.id, "status": order.status}
