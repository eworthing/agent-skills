"""Order repository — pure infrastructure; no first-party imports."""

from __future__ import annotations


class _StubOrder:
    """Minimal stub so the repository can operate without a domain import."""

    def __init__(self, order_id: str) -> None:
        self.id = order_id
        self.status = "pending"


class OrderRepository:
    """In-memory stub. Production implementation would use a DB adapter.

    Deliberately avoids importing from `domain` to preserve the clean
    api -> domain -> infrastructure dependency direction (no back-edges).
    """

    def __init__(self) -> None:
        self._store: dict[str, object] = {}

    def find(self, order_id: str) -> object:
        return self._store.get(order_id, _StubOrder(order_id))

    def save(self, order: object) -> None:
        self._store[getattr(order, "id", str(order))] = order
