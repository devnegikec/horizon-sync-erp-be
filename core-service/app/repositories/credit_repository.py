"""Repository for QR Credit balance and ledger database operations"""

from uuid import UUID

from sqlalchemy.orm import Session

from app.models.qr_credit import (
    QRCreditBalance,
    QRCreditLedger,
    QRCreditReservation,
)


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

    def get_balance_for_update(
        self, organization_id: UUID
    ) -> QRCreditBalance | None:
        return (
            self.db.query(QRCreditBalance)
            .filter(QRCreditBalance.organization_id == organization_id)
            .with_for_update()
            .first()
        )

    def create_balance(self, organization_id: UUID) -> QRCreditBalance:
        balance = QRCreditBalance(
            organization_id=organization_id,
            total_credits=0,
            used_credits=0,
            reserved_credits=0,
            balance_credits=0,
        )
        self.db.add(balance)
        self.db.flush()
        return balance

    def get_reservation_by_block(
        self,
        block_id: UUID,
        organization_id: UUID,
        *,
        for_update: bool = False,
    ) -> QRCreditReservation | None:
        query = self.db.query(QRCreditReservation).filter(
            QRCreditReservation.block_id == block_id,
            QRCreditReservation.organization_id == organization_id,
        )
        if for_update:
            query = query.with_for_update()
        return query.first()

    def create_reservation(
        self,
        organization_id: UUID,
        block_id: UUID,
        quantity: int,
    ) -> QRCreditReservation:
        reservation = QRCreditReservation(
            organization_id=organization_id,
            block_id=block_id,
            quantity=quantity,
            status="reserved",
        )
        self.db.add(reservation)
        self.db.flush()
        return reservation

    def add(self, organization_id: UUID, amount: int) -> QRCreditBalance:
        """Atomically add credits, creating the Organization balance if needed."""
        balance = self.get_balance_for_update(organization_id)
        if balance is None:
            balance = self.create_balance(organization_id)
        balance.total_credits += amount
        balance.balance_credits += amount
        self.db.flush()
        return balance

    def deduct(self, organization_id: UUID, amount: int) -> QRCreditBalance:
        """Atomically deduct credits from an organization's balance.

        Uses SELECT FOR UPDATE to prevent concurrent modification.
        Increments used_credits and decrements balance_credits.

        Args:
            organization_id: Organization UUID.
            amount: Number of credits to deduct.

        Raises:
            ValueError: If no balance record exists or insufficient credits.
        """
        balance = self.get_balance_for_update(organization_id)
        if balance is None:
            raise ValueError("No credit balance configured for this organization")
        if balance.balance_credits < amount:
            raise ValueError(
                f"Insufficient credits: available={balance.balance_credits}, required={amount}"
            )
        balance.used_credits += amount
        balance.balance_credits -= amount
        self.db.flush()
        return balance

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

    def get_ledger_by_reference(
        self, organization_id: UUID, reference_id: UUID
    ) -> QRCreditLedger | None:
        return (
            self.db.query(QRCreditLedger)
            .filter(
                QRCreditLedger.organization_id == organization_id,
                QRCreditLedger.reference_id == reference_id,
            )
            .first()
        )

    def get_consumption_by_block(self, block_id: UUID) -> QRCreditLedger | None:
        return (
            self.db.query(QRCreditLedger)
            .filter(
                QRCreditLedger.block_id == block_id,
                QRCreditLedger.transaction_type == "block_consumption",
            )
            .first()
        )

    def list_ledger(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[QRCreditLedger], int]:
        query = self.db.query(QRCreditLedger).filter(
            QRCreditLedger.organization_id == organization_id
        )
        total = query.count()
        transactions = (
            query.order_by(QRCreditLedger.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return transactions, total
