"""Invoice model — pure billing domain, no cross-module dependencies."""


class LineItem:
    def __init__(self, description: str, amount: float) -> None:
        self.description = description
        self.amount = amount


class Invoice:
    def __init__(self, customer_id: str) -> None:
        self.customer_id = customer_id
        self.line_items: list[LineItem] = []

    def add_line(self, description: str, amount: float) -> None:
        self.line_items.append(LineItem(description, amount))

    def total(self) -> float:
        return sum(item.amount for item in self.line_items)
