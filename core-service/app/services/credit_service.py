"""Credit service — QR credit allocation, reservation, and consumption.

Requirements: 6.1, 6.2, 6.3, 6.4, 6.5
"""

from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.repositories.credit_repository import CreditRepository


class CreditService:
    """Service for QR credit balance checks and atomic deductions."""

    def __init__(self, db: Session):
        self.db = db
        self.repo = CreditRepository(db)

    def check_balance(self, organization_id: UUID, required: int) -> bool:
        """Check that the organization has enough credits for the requested quantity.

        Args:
            organization_id: Organization UUID.
            required: Number of credits needed.

        Returns:
            True if balance_credits >= required.

        Raises:
            HTTPException: 422 if no balance record exists or insufficient credits.
        """
        balance = self.repo.get_balance(organization_id)
        if balance is None:
            raise HTTPException(status_code=422, detail="No credit balance configured")
        if balance.balance_credits < required:
            raise HTTPException(
                status_code=422,
                detail=f"Insufficient credits: available={balance.balance_credits}, required={required}",
            )
        return True

    def get_balance(self, organization_id: UUID):
        return self.repo.get_balance(organization_id)

    def reserve_credits(
        self,
        organization_id: UUID,
        block_id: UUID,
        quantity: int,
        *,
        commit: bool = True,
    ):
        """Atomically hold available credits for one pending Block job."""
        existing = self.repo.get_reservation_by_block(
            block_id,
            organization_id,
            for_update=True,
        )
        if existing:
            if existing.quantity != quantity:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Block credit reservation has a different quantity",
                )
            if existing.status == "reserved":
                return existing
            if existing.status == "consumed":
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Credits for this Block were already consumed",
                )

        balance = self.repo.get_balance_for_update(organization_id)
        if balance is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="No credit balance configured",
            )
        if balance.balance_credits < quantity:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"Insufficient credits: available={balance.balance_credits}, "
                    f"required={quantity}"
                ),
            )

        balance.balance_credits -= quantity
        balance.reserved_credits += quantity
        if existing is None:
            reservation = self.repo.create_reservation(
                organization_id,
                block_id,
                quantity,
            )
        else:
            existing.status = "reserved"
            existing.resolved_at = None
            reservation = existing
        if commit:
            self.db.commit()
        return reservation

    def consume_reserved_credits(
        self,
        organization_id: UUID,
        block_id: UUID,
        user_id: UUID | None = None,
    ) -> None:
        """Convert one active reservation into final QR credit consumption."""
        if self.repo.get_consumption_by_block(block_id):
            return

        reservation = self.repo.get_reservation_by_block(
            block_id,
            organization_id,
            for_update=True,
        )
        if reservation is None or reservation.status != "reserved":
            raise RuntimeError("Active credit reservation not found for QR Block")

        balance = self.repo.get_balance_for_update(organization_id)
        if balance is None or balance.reserved_credits < reservation.quantity:
            raise RuntimeError("Reserved QR credit balance is inconsistent")

        balance.reserved_credits -= reservation.quantity
        balance.used_credits += reservation.quantity
        reservation.status = "consumed"
        reservation.resolved_at = datetime.now(UTC)
        self.repo.create_ledger_entry(
            {
                "organization_id": organization_id,
                "block_id": block_id,
                "transaction_type": "block_consumption",
                "amount": -reservation.quantity,
                "balance_after": balance.balance_credits,
                "reason": "QR Block generation",
                "created_by": user_id,
                "reference_id": None,
            }
        )
        self.db.commit()

    def release_reserved_credits(
        self,
        organization_id: UUID,
        block_id: UUID,
    ) -> None:
        """Return a failed job's held credits to the available balance."""
        reservation = self.repo.get_reservation_by_block(
            block_id,
            organization_id,
            for_update=True,
        )
        if reservation is None or reservation.status != "reserved":
            return

        balance = self.repo.get_balance_for_update(organization_id)
        if balance is None or balance.reserved_credits < reservation.quantity:
            raise RuntimeError("Reserved QR credit balance is inconsistent")

        balance.reserved_credits -= reservation.quantity
        balance.balance_credits += reservation.quantity
        reservation.status = "released"
        reservation.resolved_at = datetime.now(UTC)
        self.db.commit()

    def list_ledger(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list, dict]:
        transactions, total = self.repo.list_ledger(
            organization_id, page, page_size
        )
        total_pages = max(1, (total + page_size - 1) // page_size)
        return transactions, {
            "page": page,
            "page_size": page_size,
            "total_items": total,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
        }

    def add_credits(
        self,
        organization_id: UUID,
        amount: int,
        reason: str,
        reference_id: UUID,
        user_id: UUID,
    ):
        """Add Organization credits once and record the administrator action."""
        existing = self.repo.get_ledger_by_reference(
            organization_id, reference_id
        )
        if existing:
            if (
                existing.transaction_type != "credit_addition"
                or existing.amount != amount
            ):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Credit request reference was already used",
                )
            return self.repo.get_balance(organization_id)

        try:
            balance = self.repo.add(organization_id, amount)
            self.repo.create_ledger_entry(
                {
                    "organization_id": organization_id,
                    "block_id": None,
                    "transaction_type": "credit_addition",
                    "amount": amount,
                    "balance_after": balance.balance_credits,
                    "reason": reason,
                    "created_by": user_id,
                    "reference_id": reference_id,
                }
            )
            self.db.commit()
            self.db.refresh(balance)
            return balance
        except IntegrityError as exc:
            self.db.rollback()
            existing = self.repo.get_ledger_by_reference(
                organization_id, reference_id
            )
            if existing:
                return self.repo.get_balance(organization_id)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Credits were updated concurrently; retry with a new request",
            ) from exc

    def deduct_credits(
        self,
        organization_id: UUID,
        block_id: UUID,
        quantity: int,
        user_id: UUID | None = None,
    ) -> None:
        """Atomically consume credits once for a completed QR Block.

        Calls the repository to perform an atomic deduction (SELECT FOR UPDATE),
        then creates a ledger entry recording the deduction and resulting balance.

        Args:
            organization_id: Organization UUID.
            block_id: Block UUID that consumed the credits.
            quantity: Number of credits to deduct.
        """
        if self.repo.get_consumption_by_block(block_id):
            return

        try:
            balance = self.repo.deduct(organization_id, quantity)
            self.repo.create_ledger_entry(
                {
                    "organization_id": organization_id,
                    "block_id": block_id,
                    "transaction_type": "block_consumption",
                    "amount": -quantity,
                    "balance_after": balance.balance_credits,
                    "reason": "QR Block generation",
                    "created_by": user_id,
                    "reference_id": None,
                }
            )
            self.db.commit()
        except ValueError as exc:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exc),
            ) from exc
        except IntegrityError:
            self.db.rollback()
            if self.repo.get_consumption_by_block(block_id):
                return
            raise
