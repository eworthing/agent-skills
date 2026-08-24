from decimal import Decimal
from src.domain.pricing import PriceQuote

class PricingService:
    def create_quote(self, amount: Decimal, is_vip: bool) -> PriceQuote:
        discount = Decimal("0.10") if is_vip else Decimal("0.00")
        tax = Decimal("0.08")
        return PriceQuote(base_price=amount, tax_rate=tax, discount_rate=discount)
