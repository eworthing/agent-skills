from decimal import Decimal
from src.services.catalog import PricingService

def test_pricing():
    service = PricingService()
    quote = service.create_quote(Decimal("100.00"), is_vip=True)
    assert quote.total() == Decimal("97.2000")
