from dataclasses import dataclass
from datetime import date
from decimal import Decimal

@dataclass(frozen=True)
class Account:
    account_id: str
    tier: str
    is_active: bool
    balance: Decimal

@dataclass(frozen=True)
class Transaction:
    transaction_id: str
    account_id: str
    amount: Decimal
    timestamp: date
    category: str
