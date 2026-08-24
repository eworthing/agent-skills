from decimal import Decimal
from src.domain.models import Account, Transaction
from src.ports.repository import AccountRepository, TransactionRepository

class InMemoryAccountRepository(AccountRepository):
    def __init__(self) -> None:
        self._accounts: dict[str, Account] = {}

    def get_account(self, account_id: str) -> Account | None:
        return self._accounts.get(account_id)

    def save_account(self, account: Account) -> None:
        self._accounts[account.account_id] = account

class InMemoryTransactionRepository(TransactionRepository):
    def __init__(self) -> None:
        self._txs: dict[str, list[Transaction]] = {}

    def get_transactions_for_account(self, account_id: str) -> list[Transaction]:
        return self._txs.get(account_id, [])
