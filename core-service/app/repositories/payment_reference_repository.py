"""Payment reference repository for database operations"""

from uuid import UUID
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.payment_reference import PaymentReference


class PaymentReferenceRepository:
    """Repository for payment reference database operations"""

    def __init__(self, db: Session):
        self.db = db

    def create(self, data: dict) -> PaymentReference:
        """
        Create a new payment reference.

        Args:
            data: Dictionary containing payment reference data (must include organization_id)

        Returns:
            Created PaymentReference object

        Raises:
            IntegrityError: If unique constraint (payment_id, invoice_id) is violated
        """
        payment_reference = PaymentReference(**data)
        self.db.add(payment_reference)
        try:
            self.db.commit()
            self.db.refresh(payment_reference)
            return payment_reference
        except IntegrityError as e:
            self.db.rollback()
            raise e

    def get_by_payment_id(
        self, payment_id: UUID, organization_id: UUID
    ) -> list[PaymentReference]:
        """
        Get all payment references for a payment.

        Args:
            payment_id: Payment entry UUID
            organization_id: Organization UUID for multi-tenancy isolation

        Returns:
            List of PaymentReference objects for the payment
        """
        return (
            self.db.query(PaymentReference)
            .filter(
                PaymentReference.payment_id == payment_id,
                PaymentReference.organization_id == organization_id,
            )
            .all()
        )

    def get_by_payment_id_with_invoice_details(
        self, payment_id: UUID, organization_id: UUID
    ) -> list[PaymentReference]:
        """
        Get all payment references for a payment with eager loaded invoice details.
        
        Uses joinedload to avoid N+1 queries by loading invoice data in a single query.

        Args:
            payment_id: Payment entry UUID
            organization_id: Organization UUID for multi-tenancy isolation

        Returns:
            List of PaymentReference objects with invoice relationship loaded
        """
        from sqlalchemy.orm import joinedload
        from app.models.invoice import Invoice
        
        return (
            self.db.query(PaymentReference)
            .options(joinedload(PaymentReference.invoice))
            .filter(
                PaymentReference.payment_id == payment_id,
                PaymentReference.organization_id == organization_id,
            )
            .all()
        )

    def get_by_invoice_id(
        self, invoice_id: UUID, organization_id: UUID
    ) -> list[PaymentReference]:
        """
        Get all payment references for an invoice.

        Args:
            invoice_id: Invoice UUID
            organization_id: Organization UUID for multi-tenancy isolation

        Returns:
            List of PaymentReference objects for the invoice
        """
        return (
            self.db.query(PaymentReference)
            .filter(
                PaymentReference.invoice_id == invoice_id,
                PaymentReference.organization_id == organization_id,
            )
            .all()
        )

    def get_by_invoice_id_with_payment_details(
        self, invoice_id: UUID, organization_id: UUID
    ) -> list[PaymentReference]:
        """
        Get all payment references for an invoice with eager loaded payment details.
        
        Uses joinedload to avoid N+1 queries by loading payment entry data in a single query.

        Args:
            invoice_id: Invoice UUID
            organization_id: Organization UUID for multi-tenancy isolation

        Returns:
            List of PaymentReference objects with payment_entry relationship loaded
        """
        from sqlalchemy.orm import joinedload
        from app.models.payment_entry import PaymentEntry
        
        return (
            self.db.query(PaymentReference)
            .options(joinedload(PaymentReference.payment_entry))
            .filter(
                PaymentReference.invoice_id == invoice_id,
                PaymentReference.organization_id == organization_id,
            )
            .all()
        )

    def delete(self, payment_reference: PaymentReference) -> None:
        """
        Delete a payment reference.

        Args:
            payment_reference: PaymentReference object to delete

        Raises:
            IntegrityError: If foreign key constraints are violated
        """
        try:
            self.db.delete(payment_reference)
            self.db.commit()
        except IntegrityError as e:
            self.db.rollback()
            raise e

    def get_total_allocated_for_invoice(
        self, invoice_id: UUID, organization_id: UUID
    ) -> Decimal:
        """
        Calculate total allocated amount for an invoice.

        Args:
            invoice_id: Invoice UUID
            organization_id: Organization UUID for multi-tenancy isolation

        Returns:
            Sum of allocated_amount for the invoice, or Decimal('0.00') if no allocations
        """
        result = (
            self.db.query(func.sum(PaymentReference.allocated_amount))
            .filter(
                PaymentReference.invoice_id == invoice_id,
                PaymentReference.organization_id == organization_id,
            )
            .scalar()
        )
        return result if result is not None else Decimal("0.00")

    def get_total_allocated_for_payment(
        self, payment_id: UUID, organization_id: UUID
    ) -> Decimal:
        """
        Calculate total allocated amount for a payment.

        Args:
            payment_id: Payment entry UUID
            organization_id: Organization UUID for multi-tenancy isolation

        Returns:
            Sum of allocated_amount for the payment, or Decimal('0.00') if no allocations
        """
        result = (
            self.db.query(func.sum(PaymentReference.allocated_amount))
            .filter(
                PaymentReference.payment_id == payment_id,
                PaymentReference.organization_id == organization_id,
            )
            .scalar()
        )
        return result if result is not None else Decimal("0.00")
