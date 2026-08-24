from dataclasses import dataclass
from decimal import Decimal

@dataclass(frozen=True)
class PriceQuote:
    base_price: Decimal
    tax_rate: Decimal
    discount_rate: Decimal

    def total(self) -> Decimal:
        discounted = self.base_price * (Decimal("1.0") - self.discount_rate)
        return discounted * (Decimal("1.0") + self.tax_rate)
