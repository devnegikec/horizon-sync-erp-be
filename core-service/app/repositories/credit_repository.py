"""Repository for QR Credit balance and ledger database operations"""

from uuid import UUID

from sqlalchemy.orm import Session

from app.models.qr_credit import QRCreditBalance, QRCreditLedger


class CreditRepository:
    """Repository for QR credit balance and ledger operations"""

    def __init__(self, db: Session):
        self.db = db

    def get_balance(self, organization_id: UUID) -> QRCreditBalance | None:
        """Get credit balance for an organization.

        Args:
            organization_id: Organization UUID.

        Returns:
            QRCreditBalance object or None if no balance record exists.
        """
        return (
            self.db.query(QRCreditBalance)
            .filter(QRCreditBalance.organization_id == organization_id)
            .first()
        )

    def deduct(self, organization_id: UUID, amount: int) -> None:
        """Atomically deduct credits from an organization's balance.

        Uses SELECT FOR UPDATE to prevent concurrent modification.
        Increments used_credits and decrements balance_credits.

        Args:
            organization_id: Organization UUID.
            amount: Number of credits to deduct.

        Raises:
            ValueError: If no balance record exists or insufficient credits.
        """
        balance = (
            self.db.query(QRCreditBalance)
            .filter(QRCreditBalance.organization_id == organization_id)
            .with_for_update()
            .first()
        )
        if balance is None:
            raise ValueError("No credit balance configured for this organization")
        if balance.balance_credits < amount:
            raise ValueError(
                f"Insufficient credits: available={balance.balance_credits}, required={amount}"
            )
        balance.used_credits += amount
        balance.balance_credits -= amount
        self.db.flush()

    def create_ledger_entry(self, data: dict) -> QRCreditLedger:
        """Create a credit ledger audit entry.

        Args:
            data: Dictionary containing organization_id, block_id,
                  quantity_deducted, and balance_after.

        Returns:
            Created QRCreditLedger object.
        """
        entry = QRCreditLedger(**data)
        self.db.add(entry)
        self.db.flush()
        return entry
