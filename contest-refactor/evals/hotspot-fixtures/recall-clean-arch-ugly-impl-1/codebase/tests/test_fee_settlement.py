from decimal import Decimal
from datetime import date
from src.domain.models import Account, Transaction
from src.adapters.memory_repo import InMemoryAccountRepository, InMemoryTransactionRepository
from src.services.fee_settlement_service import FeeSettlementService

def test_settle_account_fees_basic():
    acc_repo = InMemoryAccountRepository()
    tx_repo = InMemoryTransactionRepository()
    account = Account(account_id="A1", tier="STANDARD", is_active=True, balance=Decimal("1000.00"))
    acc_repo.save_account(account)

    tx_repo._txs["A1"] = [
        Transaction("T1", "A1", Decimal("2000.00"), date.today(), "INTERNATIONAL")
    ]

    service = FeeSettlementService(acc_repo, tx_repo)
    fee = service.settle_account_fees("A1")
    assert fee == Decimal("60.00")
