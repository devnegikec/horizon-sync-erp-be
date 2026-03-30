"""Credit service — pre-flight credit checks and post-generation deduction with ledger audit trail.

Requirements: 6.1, 6.2, 6.3, 6.4, 6.5
"""

from uuid import UUID

from fastapi import HTTPException
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

    def deduct_credits(
        self, organization_id: UUID, block_id: UUID, quantity: int
    ) -> None:
        """Atomically deduct credits and write a ledger audit entry.

        Calls the repository to perform an atomic deduction (SELECT FOR UPDATE),
        then creates a ledger entry recording the deduction and resulting balance.

        Args:
            organization_id: Organization UUID.
            block_id: Block UUID that consumed the credits.
            quantity: Number of credits to deduct.
        """
        self.repo.deduct(organization_id, quantity)

        # Read the updated balance for the ledger entry
        balance = self.repo.get_balance(organization_id)
        balance_after = balance.balance_credits if balance else 0

        self.repo.create_ledger_entry(
            {
                "organization_id": organization_id,
                "block_id": block_id,
                "quantity_deducted": quantity,
                "balance_after": balance_after,
            }
        )

        self.db.commit()
