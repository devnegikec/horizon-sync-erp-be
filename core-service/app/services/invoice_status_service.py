"""Invoice status service for automatic status updates based on payment allocations"""

from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import ValidationError
from app.repositories.invoice_repository import InvoiceRepository
from app.repositories.payment_reference_repository import PaymentReferenceRepository


class InvoiceStatusService:
    """Service for managing invoice payment status updates"""

    def __init__(self, db: Session):
        """
        Initialize invoice status service.

        Args:
            db: Database session
        """
        self.db = db
        self.invoice_repo = InvoiceRepository(db)
        self.reference_repo = PaymentReferenceRepository(db)

    def _calculate_total_allocated(
        self,
        invoice_id: UUID,
        organization_id: UUID,
    ) -> Decimal:
        """
        Calculate total allocated payments for an invoice.

        Uses the payment_reference_repository's get_total_allocated_for_invoice
        method to sum all allocated amounts for the invoice.

        Args:
            invoice_id: Invoice UUID
            organization_id: Organization UUID for multi-tenancy isolation

        Returns:
            Total allocated amount, or Decimal('0.00') if no allocations

        Requirements: 4.1, 4.7
        """
        return self.reference_repo.get_total_allocated_for_invoice(
            invoice_id, organization_id
        )

    def _determine_invoice_status(
        self,
        invoice_amount: Decimal,
        total_allocated: Decimal,
    ) -> str:
        """
        Determine invoice payment status based on allocated amounts.

        Status logic:
        - draft: total_allocated == 0 (Unpaid)
        - partial: 0 < total_allocated < invoice_amount (Partially Paid)
        - paid: total_allocated >= invoice_amount (Paid or Overpaid)

        Args:
            invoice_amount: Total invoice amount (grand_total)
            total_allocated: Total amount allocated from payments

        Returns:
            Invoice status string: "draft", "partial", or "paid"

        Requirements: 4.2, 4.3, 4.4, 4.5
        """
        if total_allocated == 0:
            return "draft"  # Unpaid
        elif total_allocated < invoice_amount:
            return "partial"  # Partially Paid
        else:  # total_allocated >= invoice_amount (includes both Paid and Overpaid)
            return "paid"

    def update_invoice_status(
        self,
        invoice_id: UUID,
        organization_id: UUID,
    ) -> "Invoice":
        """
        Recalculate and update invoice payment status.

        This method:
        1. Calculates total allocated payments for the invoice
        2. Calculates outstanding balance (invoice amount - total allocated)
        3. Determines new status based on allocation
        4. Updates invoice status and outstanding_balance fields

        Args:
            invoice_id: Invoice UUID
            organization_id: Organization UUID for multi-tenancy isolation

        Returns:
            Updated Invoice object

        Raises:
            ValidationError: If invoice not found

        Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7
        """
        # Get invoice (without items to avoid querying invoice_items columns that may not exist)
        invoice = self.invoice_repo.get_by_id(invoice_id, organization_id, load_items=False)
        if not invoice:
            raise ValidationError(
                f"Invoice with ID {invoice_id} not found or does not belong to organization"
            )

        # Calculate total allocated payments
        total_allocated = self._calculate_total_allocated(invoice_id, organization_id)

        # Calculate outstanding balance (guard against None from DB)
        invoice_amount = getattr(invoice, "grand_total", None) or getattr(invoice, "total_amount", None)
        if invoice_amount is None:
            invoice_amount = Decimal("0")
        invoice_amount = Decimal(str(invoice_amount))
        outstanding_balance = invoice_amount - total_allocated

        # Determine new status
        new_status = self._determine_invoice_status(invoice_amount, total_allocated)

        # Update invoice status and outstanding_balance
        invoice.status = new_status
        invoice.balance_due = outstanding_balance
        invoice.total_paid = total_allocated

        # Commit changes
        self.db.commit()
        self.db.refresh(invoice)

        return invoice

    def calculate_outstanding_balance(
        self,
        invoice_id: UUID,
        organization_id: UUID,
    ) -> Decimal:
        """
        Calculate outstanding balance for an invoice.

        Outstanding balance = invoice amount - total allocated payments

        Args:
            invoice_id: Invoice UUID
            organization_id: Organization UUID for multi-tenancy isolation

        Returns:
            Outstanding balance amount

        Raises:
            ValidationError: If invoice not found

        Requirements: 4.7, 13.3
        """
        # Get invoice (without items to avoid querying invoice_items columns that may not exist)
        invoice = self.invoice_repo.get_by_id(invoice_id, organization_id, load_items=False)
        if not invoice:
            raise ValidationError(
                f"Invoice with ID {invoice_id} not found or does not belong to organization"
            )

        # Get total allocated amount
        total_allocated = self._calculate_total_allocated(invoice_id, organization_id)

        # Calculate outstanding balance
        outstanding_balance = invoice.grand_total - total_allocated

        return outstanding_balance
