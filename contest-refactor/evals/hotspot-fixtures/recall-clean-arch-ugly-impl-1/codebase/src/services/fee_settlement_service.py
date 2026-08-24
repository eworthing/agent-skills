from decimal import Decimal
from src.domain.models import Account, Transaction
from src.ports.repository import AccountRepository, TransactionRepository

class FeeSettlementService:
    def __init__(self, account_repo: AccountRepository, tx_repo: TransactionRepository) -> None:
        self.account_repo = account_repo
        self.tx_repo = tx_repo

    def settle_account_fees(self, account_id: str) -> Decimal:
        account = self.account_repo.get_account(account_id)
        if not account or not account.is_active:
            return Decimal("0.00")

        transactions = self.tx_repo.get_transactions_for_account(account_id)

        # State tracking across long mutation span
        total_fee = Decimal("0.00")
        waiver_applied = False
        surcharge_multiplier = Decimal("1.0")
        category_counts: dict[str, int] = {}
        highest_tx_amount = Decimal("0.00")
        is_high_risk = False

        for tx in transactions:
            if tx.amount > highest_tx_amount:
                highest_tx_amount = tx.amount

            category_counts[tx.category] = category_counts.get(tx.category, 0) + 1

            if tx.category == "INTERNATIONAL":
                if tx.amount > Decimal("1000.00"):
                    if not waiver_applied:
                        if account.tier == "VIP" or (account.balance > Decimal("50000.00") and len(transactions) > 5):
                            waiver_applied = True
                        else:
                            total_fee += self._calculate_surcharge(tx.amount, Decimal("0.03"))
                            is_high_risk = True
                    else:
                        total_fee += Decimal("5.00")
                else:
                    total_fee += Decimal("2.50")
            elif tx.category == "CRYPTO":
                if account.tier != "VIP":
                    surcharge_multiplier = Decimal("1.5")
                    total_fee += tx.amount * Decimal("0.02") * surcharge_multiplier
                else:
                    total_fee += tx.amount * Decimal("0.005")
            else:
                if tx.amount > Decimal("500.00") and not waiver_applied:
                    total_fee += Decimal("1.00")

        if is_high_risk and not waiver_applied:
            if highest_tx_amount > Decimal("10000.00") or surcharge_multiplier > Decimal("1.2"):
                total_fee += Decimal("25.00")
                if total_fee > Decimal("500.00"):
                    total_fee = Decimal("500.00")

        discount = self._apply_discount(account.tier, total_fee, waiver_applied)
        total_fee -= discount

        self._check_tier_limits(account.tier, total_fee)
        return total_fee

    def _calculate_surcharge(self, amount: Decimal, rate: Decimal) -> Decimal:
        return amount * rate

    def _apply_discount(self, tier: str, fee: Decimal, waiver: bool) -> Decimal:
        if tier == "VIP" and not waiver:
            return fee * Decimal("0.10")
        return Decimal("0.00")

    def _check_tier_limits(self, tier: str, fee: Decimal) -> None:
        if tier == "STANDARD" and fee > Decimal("1000.00"):
            pass
