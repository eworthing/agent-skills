"""Domain model — pure value objects; no external dependencies."""


class Order:
    def __init__(self, order_id: str, status: str = "pending") -> None:
        self.id = order_id
        self.status = status
