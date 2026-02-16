"""Payment Made service wrapper for Payment API"""

from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import ResourceNotFoundException, ValidationException
from app.core.transaction import transactional
from app.models.base import InvoiceStatus, PaymentType
from app.repositories.invoice_repository import InvoiceRepository
from app.repositories.payment_repository import PaymentRepository


class PaymentMadeService:
    """
    Service wrapper for creating Payment Made using existing Payment API.
    
    Integrates with:
    - Payment API (payment_type=PAY)
    - Purchase Invoice validation
    - Invoice outstanding balance updates
    
    Requirements: 7.1, 7.2, 7.3
    """

    def __init__(self, db: Session):
        self.db = db
        self.payment_repo = PaymentRepository(db)
        self.invoice_repo = InvoiceRepository(db)

    @transactional
    def create_payment(
        self,
        purchase_invoice_id: UUID,
        amount: Decimal,
        organization_id: UUID,
        user_id: UUID,
        payment_no: str,
        posting_date: str | None = None,
        payment_method: str | None = None,
        reference_no: str | None = None,
        remarks: str | None = None,
    ) -> dict:
        """
        Create Payment Made for Purchase Invoice using existing Payment API.
        
        Uses SELECT FOR UPDATE to prevent race conditions in concurrent balance updates.
        
        Args:
            purchase_invoice_id: Source Purchase Invoice ID
            amount: Payment amount
            organization_id: Organization ID
            user_id: User ID
            payment_no: Payment number
            posting_date: Payment posting date
            payment_method: Payment method (cash, bank_transfer, etc.)
            reference_no: External reference number
            remarks: Additional remarks
            
        Returns:
            dict: Created payment response
            
        Requirements:
        - 7.1: Set payment_type as PAY
        - 7.2: Set reference_type as PURCHASE_INVOICE and reference_id
        - 7.3: Validate Purchase Invoice exists and has outstanding balance > 0
        - 11.7: Use SELECT FOR UPDATE for invoice balance updates
        """
        # Requirement 7.3 & 11.7: Validate Purchase Invoice exists and lock for update
        invoice = self.invoice_repo.get_by_id(purchase_invoice_id, organization_id, for_update=True)
        if not invoice:
            raise ResourceNotFoundException(
                f"Purchase Invoice {purchase_invoice_id} not found"
            )

        # Validate invoice has outstanding balance
        outstanding_balance = Decimal(str(invoice.outstanding_amount or 0))
        if outstanding_balance <= 0:
            raise ValidationException(
                f"Cannot create payment for Purchase Invoice {purchase_invoice_id}. "
                f"Outstanding balance is {outstanding_balance}. Payment can only be made for invoices with outstanding balance > 0."
            )

        # Validate payment amount
        if amount <= 0:
            raise ValidationException("Payment amount must be greater than zero")

        if amount > outstanding_balance:
            raise ValidationException(
                f"Payment amount {amount} exceeds outstanding balance {outstanding_balance}"
            )

        # Requirement 7.1: Set payment_type as PAY
        # Note: The Payment model doesn't have reference_type/reference_id fields
        # We'll store the reference in extra_data for now
        payment_data = {
            "organization_id": organization_id,
            "payment_no": payment_no,
            "payment_type": PaymentType.PAY,
            "party_type": "SUPPLIER",
            "party_id": invoice.party_id,
            "posting_date": posting_date,
            "amount": amount,
            "status": "pending",
            "payment_method": payment_method,
            "reference_no": reference_no,
            "remarks": remarks,
            "created_by": user_id,
            "updated_by": user_id,
            "extra_data": {
                # Requirement 7.2: Store reference information
                "reference_type": "PURCHASE_INVOICE",
                "reference_id": str(purchase_invoice_id),
            },
        }

        # Create payment using existing Payment API
        payment = self.payment_repo.create(payment_data)

        # Requirement 7.4: Reduce outstanding balance by payment amount
        # Requirement 7.5: Update Purchase Invoice status to PAID when balance reaches zero
        # Note: invoice is already locked with SELECT FOR UPDATE
        self._update_invoice_balance(invoice, amount)

        return self._to_response(payment)

    def _update_invoice_balance(self, invoice, payment_amount: Decimal) -> None:
        """
        Update invoice outstanding balance and status after payment.
        
        Args:
            invoice: Invoice model instance
            payment_amount: Payment amount to reduce from outstanding balance
            
        Requirements:
        - 7.4: Reduce outstanding balance by payment amount
        - 7.5: Update Purchase Invoice status to PAID when balance reaches zero
        """
        # Calculate new outstanding balance
        new_balance = Decimal(str(invoice.outstanding_amount)) - payment_amount

        # Prepare update data
        update_data = {"outstanding_amount": new_balance}

        # Requirement 7.5: Update status to PAID when balance reaches zero
        if new_balance <= 0:
            update_data["status"] = InvoiceStatus.PAID

        # Update invoice
        self.invoice_repo.update(invoice, update_data)

    @staticmethod
    def _to_response(payment) -> dict:
        """Convert Payment model to response dict"""
        response = {
            "id": payment.id,
            "organization_id": payment.organization_id,
            "payment_no": payment.payment_no,
            "payment_type": payment.payment_type.value if payment.payment_type else None,
            "party_id": payment.party_id,
            "party_type": payment.party_type,
            "posting_date": payment.posting_date,
            "amount": payment.amount,
            "status": payment.status.value if payment.status else None,
            "payment_method": payment.payment_method.value if payment.payment_method else None,
            "reference_no": payment.reference_no,
            "remarks": payment.remarks,
            "created_by": payment.created_by,
            "updated_by": payment.updated_by,
            "created_at": payment.created_at,
            "updated_at": payment.updated_at,
        }

        # Include reference information from extra_data
        if payment.extra_data:
            response["reference_type"] = payment.extra_data.get("reference_type")
            response["reference_id"] = payment.extra_data.get("reference_id")

        return response
