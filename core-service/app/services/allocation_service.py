"""Allocation service for payment-to-invoice linking"""

from decimal import Decimal
from uuid import UUID

from sqlalchemy.exc import IntegrityError as SQLIntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ValidationError
from app.repositories.payment_entry_repository import PaymentEntryRepository
from app.repositories.payment_reference_repository import PaymentReferenceRepository
from app.repositories.invoice_repository import InvoiceRepository
from app.core.cache import (
    get_cached_unpaid_invoices,
    cache_unpaid_invoices,
    invalidate_invoice_cache,
    invalidate_payment_cache,
)


class AllocationService:
    """Service for managing payment allocation to invoices"""

    def __init__(self, db: Session):
        """
        Initialize allocation service.

        Args:
            db: Database session
        """
        self.db = db
        self.payment_repo = PaymentEntryRepository(db)
        self.reference_repo = PaymentReferenceRepository(db)
        self.invoice_repo = InvoiceRepository(db)
        
        # Import PaymentAuditLogRepository for audit trail
        from app.repositories.payment_audit_log_repository import PaymentAuditLogRepository
        self.audit_logger = PaymentAuditLogRepository(db)
        
        # Import InvoiceStatusService for automatic status updates
        from app.services.invoice_status_service import InvoiceStatusService
        self.invoice_status_service = InvoiceStatusService(db)

    def _validate_allocation_amount(
        self,
        allocated_amount: Decimal,
        payment_unallocated_amount: Decimal,
        invoice_outstanding_balance: Decimal,
    ) -> None:
        """
        Validate that allocation amount is valid.

        Args:
            allocated_amount: Amount to allocate
            payment_unallocated_amount: Remaining unallocated amount on payment
            invoice_outstanding_balance: Outstanding balance on invoice

        Raises:
            ValidationError: If allocation amount is invalid
        """
        if allocated_amount <= 0:
            raise ValidationError(
                f"Allocation amount must be greater than zero, got {allocated_amount}"
            )

        # Check decimal places (max 2)
        amount_str = str(allocated_amount)
        if '.' in amount_str:
            decimal_places = len(amount_str.split('.')[1])
            if decimal_places > 2:
                raise ValidationError(
                    f"Allocation amount must have at most 2 decimal places, got {decimal_places}"
                )

        if allocated_amount > payment_unallocated_amount:
            raise ValidationError(
                f"Allocation amount {allocated_amount} exceeds payment unallocated amount {payment_unallocated_amount}"
            )

        if allocated_amount > invoice_outstanding_balance:
            msg = (
                f"Allocation amount {allocated_amount} exceeds invoice outstanding balance {invoice_outstanding_balance}. "
            )
            if invoice_outstanding_balance == 0:
                msg += "The invoice may already be fully allocated or have no amount set. Check the invoice total and existing allocations."
            raise ValidationError(msg)

    def _validate_invoice_belongs_to_party(
        self,
        invoice_party_id: UUID,
        payment_party_id: UUID,
    ) -> None:
        """
        Validate that invoice belongs to same party as payment.

        Args:
            invoice_party_id: Party ID from invoice
            payment_party_id: Party ID from payment

        Raises:
            ValidationError: If invoice doesn't belong to same party
        """
        if invoice_party_id != payment_party_id:
            raise ValidationError(
                f"Invoice party {invoice_party_id} does not match payment party {payment_party_id}. "
                "All invoices must belong to the same party as the payment."
            )

    def _validate_invoice_belongs_to_organization(
        self,
        invoice_organization_id: UUID,
        payment_organization_id: UUID,
    ) -> None:
        """
        Validate that invoice belongs to same organization as payment.

        Args:
            invoice_organization_id: Organization ID from invoice
            payment_organization_id: Organization ID from payment

        Raises:
            ValidationError: If invoice doesn't belong to same organization
        """
        if invoice_organization_id != payment_organization_id:
            raise ValidationError(
                f"Invoice organization {invoice_organization_id} does not match payment organization {payment_organization_id}. "
                "All invoices must belong to the same organization as the payment."
            )

    def _calculate_invoice_outstanding_balance(
        self,
        invoice_id: UUID,
        organization_id: UUID,
    ) -> Decimal:
        """
        Calculate outstanding balance for an invoice.

        Args:
            invoice_id: Invoice UUID
            organization_id: Organization UUID

        Returns:
            Outstanding balance (invoice amount - total allocated)

        Raises:
            ValidationError: If invoice not found
        """
        # Get invoice (without items to avoid querying invoice_items columns that may not exist)
        invoice = self.invoice_repo.get_by_id(invoice_id, organization_id, load_items=False)
        if not invoice:
            raise ValidationError(
                f"Invoice with ID {invoice_id} not found or does not belong to organization"
            )

        # Get total allocated amount for this invoice
        total_allocated_raw = self.reference_repo.get_total_allocated_for_invoice(
            invoice_id, organization_id
        )

        # Outstanding = how much can still be allocated. Use all available sources
        # and take the maximum so we don't undercount when one source is 0/unset.
        def _to_decimal(v):
            if v is None:
                return Decimal("0")
            return Decimal(str(v))

        total_allocated = _to_decimal(total_allocated_raw)

        total_from_header = _to_decimal(
            getattr(invoice, "grand_total", None)
        )
        balance_due = _to_decimal(getattr(invoice, "outstanding_amount", None))
        try:
            total_from_items = self.invoice_repo.get_invoice_total_from_items(
                invoice_id, organization_id
            )
        except Exception:
            # invoice_items may lack amount column or table may differ; don't fail allocation.
            # Roll back so the current transaction is not left aborted for later INSERT.
            self.db.rollback()
            total_from_items = Decimal("0")

        # Take the max of: balance_due, (total - allocated), (sum items - allocated)
        # so allocation works whether amounts live in header, balance_due, or line items.
        outstanding_from_header = max(Decimal("0"), total_from_header - total_allocated)
        outstanding_from_balance_due = balance_due  # already "current due" in many setups
        outstanding_from_items = max(Decimal("0"), total_from_items - total_allocated)

        outstanding_balance = max(
            outstanding_from_header,
            outstanding_from_balance_due,
            outstanding_from_items,
        )

        return outstanding_balance


    def create_allocation(
        self,
        payment_id: UUID,
        invoice_id: UUID,
        allocated_amount: Decimal,
        organization_id: UUID,
        user_id: UUID,
    ) -> "PaymentReference":
        """
        Allocate payment amount to an invoice.

        Args:
            payment_id: Payment entry UUID
            invoice_id: Invoice UUID
            allocated_amount: Amount to allocate to this invoice
            organization_id: Organization UUID
            user_id: User performing the allocation

        Returns:
            Created PaymentReference object

        Raises:
            ValidationError: If validation fails
        """
        from app.models.base import PaymentEntryStatus, PaymentAuditAction
        from app.models.payment_reference import PaymentReference
        from app.services.currency_service import CurrencyService
        from datetime import date

        # Get payment entry
        payment = self.payment_repo.get_by_id(payment_id, organization_id)
        if not payment:
            raise ValidationError(
                f"Payment with ID {payment_id} not found or does not belong to organization"
            )

        # Validate payment is in Draft status (support both enum and string from DB)
        status_val = getattr(payment.status, "value", payment.status)
        is_draft = (
            payment.status == PaymentEntryStatus.DRAFT
            or (str(status_val or "").lower() == "draft")
        )
        if not is_draft:
            raise ValidationError(
                f"Cannot allocate payment in {status_val} status. "
                "Payment must be in Draft status to modify allocations."
            )

        # Get invoice (without items to avoid querying invoice_items columns that may not exist)
        invoice = self.invoice_repo.get_by_id(invoice_id, organization_id, load_items=False)
        if not invoice:
            raise ValidationError(
                f"Invoice with ID {invoice_id} not found or does not belong to organization"
            )

        # Validate invoice belongs to same party as payment
        self._validate_invoice_belongs_to_party(invoice.party_id, payment.party_id)

        # Validate invoice belongs to same organization
        self._validate_invoice_belongs_to_organization(
            invoice.organization_id, payment.organization_id
        )

        # Calculate invoice outstanding balance
        invoice_outstanding_balance = self._calculate_invoice_outstanding_balance(
            invoice_id, organization_id
        )

        # Validate allocated amount
        self._validate_allocation_amount(
            allocated_amount,
            payment.unallocated_amount,
            invoice_outstanding_balance,
        )

        # Calculate exchange rate if currencies differ
        exchange_rate = Decimal("1.0")
        allocated_amount_invoice_currency = allocated_amount

        payment_currency = payment.currency_code
        # Invoice model uses 'currency' field, not 'currency_code'
        invoice_currency = getattr(invoice, 'currency', 'USD')

        if payment_currency != invoice_currency:
            # Get exchange rate from currency service
            currency_service = CurrencyService(self.db)
            try:
                exchange_rate = currency_service.get_exchange_rate(
                    from_currency=payment_currency,
                    to_currency=invoice_currency,
                    effective_date=date.today(),
                )
                # Calculate allocated amount in invoice currency
                allocated_amount_invoice_currency = (
                    allocated_amount * exchange_rate
                ).quantize(Decimal("0.01"))
            except Exception as e:
                raise ValidationError(
                    f"Failed to get exchange rate from {payment_currency} to {invoice_currency}: {str(e)}"
                )

        # Create payment reference record
        payment_reference_data = {
            "organization_id": organization_id,
            "payment_id": payment_id,
            "invoice_id": invoice_id,
            "allocated_amount": allocated_amount,
            "exchange_rate": exchange_rate,
            "allocated_amount_invoice_currency": allocated_amount_invoice_currency,
            "created_by": user_id,
        }

        try:
            payment_reference = self.reference_repo.create(payment_reference_data)
        except SQLIntegrityError as e:
            if "unique" in (e.orig.args[0] if e.orig else "").lower() or "unique_payment_references" in str(e):
                raise ValidationError(
                    "An allocation for this payment and invoice already exists."
                ) from e
            raise

        # Create audit log entry for ALLOCATE action
        audit_log_data = {
            "organization_id": organization_id,
            "payment_id": payment_id,
            "action": PaymentAuditAction.ALLOCATE,
            "user_id": user_id,
            "old_values": None,
            "new_values": {
                "invoice_id": str(invoice_id),
                "allocated_amount": str(allocated_amount),
                "exchange_rate": str(exchange_rate),
                "allocated_amount_invoice_currency": str(allocated_amount_invoice_currency),
            },
        }
        self.audit_logger.create(audit_log_data)

        # Update invoice status based on new allocation (before commit)
        self.invoice_status_service.update_invoice_status(invoice_id, organization_id)

        # Commit transaction
        self.db.commit()
        self.db.refresh(payment_reference)

        # Invalidate caches after successful allocation
        # Invalidate payment cache (affects unallocated_amount)
        invalidate_payment_cache(payment_id, organization_id)
        # Invalidate invoice cache (affects unpaid invoices list)
        invalidate_invoice_cache(invoice_id, payment.party_id, organization_id)

        return payment_reference

    def create_bulk_allocations(
        self,
        payment_id: UUID,
        allocations: list[dict],
        organization_id: UUID,
        user_id: UUID,
    ) -> list["PaymentReference"]:
        """
        Allocate payment to multiple invoices at once.

        All validations are performed before creating any allocations.
        All allocations are created within a single database transaction.

        Args:
            payment_id: Payment entry UUID
            allocations: List of allocation dicts with 'invoice_id' and 'allocated_amount'
            organization_id: Organization UUID
            user_id: User performing the allocations

        Returns:
            List of created PaymentReference objects

        Raises:
            ValidationError: If any validation fails
        """
        from app.models.base import PaymentEntryStatus, PaymentAuditAction
        from app.models.payment_reference import PaymentReference
        from app.services.currency_service import CurrencyService
        from datetime import date

        if not allocations:
            raise ValidationError("At least one allocation is required")

        # Get payment entry
        payment = self.payment_repo.get_by_id(payment_id, organization_id)
        if not payment:
            raise ValidationError(
                f"Payment with ID {payment_id} not found or does not belong to organization"
            )

        # Validate payment is in Draft status (support both enum and string from DB)
        status_val = getattr(payment.status, "value", payment.status)
        is_draft = (
            payment.status == PaymentEntryStatus.DRAFT
            or (str(status_val or "").lower() == "draft")
        )
        if not is_draft:
            raise ValidationError(
                f"Cannot allocate payment in {status_val} status. "
                "Payment must be in Draft status to modify allocations."
            )

        # Calculate total allocated amount
        total_allocated = sum(
            Decimal(str(alloc.get("allocated_amount", 0))) for alloc in allocations
        )

        # Validate total allocated amount does not exceed payment amount
        if total_allocated > payment.unallocated_amount:
            raise ValidationError(
                f"Total allocated amount {total_allocated} exceeds payment unallocated amount {payment.unallocated_amount}"
            )

        # Validate each allocation and collect invoice data
        invoice_data = []
        for idx, alloc in enumerate(allocations):
            invoice_id = alloc.get("invoice_id")
            allocated_amount = Decimal(str(alloc.get("allocated_amount", 0)))

            if not invoice_id:
                raise ValidationError(f"Allocation {idx}: invoice_id is required")

            if allocated_amount <= 0:
                raise ValidationError(
                    f"Allocation {idx}: allocated_amount must be greater than zero"
                )

            # Check decimal places (max 2)
            amount_str = str(allocated_amount)
            if '.' in amount_str:
                decimal_places = len(amount_str.split('.')[1])
                if decimal_places > 2:
                    raise ValidationError(
                        f"Allocation {idx}: allocated_amount must have at most 2 decimal places"
                    )

            # Get invoice (without items to avoid querying invoice_items columns that may not exist)
            invoice = self.invoice_repo.get_by_id(invoice_id, organization_id, load_items=False)
            if not invoice:
                raise ValidationError(
                    f"Allocation {idx}: Invoice with ID {invoice_id} not found or does not belong to organization"
                )

            # Validate invoice belongs to same party as payment
            if invoice.party_id != payment.party_id:
                raise ValidationError(
                    f"Allocation {idx}: Invoice party {invoice.party_id} does not match payment party {payment.party_id}. "
                    "All invoices must belong to the same party as the payment."
                )

            # Validate invoice belongs to same organization
            if invoice.organization_id != payment.organization_id:
                raise ValidationError(
                    f"Allocation {idx}: Invoice organization {invoice.organization_id} does not match payment organization {payment.organization_id}. "
                    "All invoices must belong to the same organization as the payment."
                )

            # Calculate invoice outstanding balance
            invoice_outstanding_balance = self._calculate_invoice_outstanding_balance(
                invoice_id, organization_id
            )

            # Validate allocated amount does not exceed invoice outstanding balance
            if allocated_amount > invoice_outstanding_balance:
                raise ValidationError(
                    f"Allocation {idx}: Allocated amount {allocated_amount} exceeds invoice outstanding balance {invoice_outstanding_balance}"
                )

            # Store invoice data for later processing
            invoice_data.append({
                "invoice_id": invoice_id,
                "invoice": invoice,
                "allocated_amount": allocated_amount,
                "outstanding_balance": invoice_outstanding_balance,
            })

        # All validations passed - create all allocations within transaction
        created_references = []
        currency_service = CurrencyService(self.db)

        try:
            for data in invoice_data:
                invoice_id = data["invoice_id"]
                invoice = data["invoice"]
                allocated_amount = data["allocated_amount"]

                # Calculate exchange rate if currencies differ
                exchange_rate = Decimal("1.0")
                allocated_amount_invoice_currency = allocated_amount

                payment_currency = payment.currency_code
                invoice_currency = getattr(invoice, 'currency', 'USD')

                if payment_currency != invoice_currency:
                    try:
                        exchange_rate = currency_service.get_exchange_rate(
                            from_currency=payment_currency,
                            to_currency=invoice_currency,
                            effective_date=date.today(),
                        )
                        allocated_amount_invoice_currency = (
                            allocated_amount * exchange_rate
                        ).quantize(Decimal("0.01"))
                    except Exception as e:
                        raise ValidationError(
                            f"Failed to get exchange rate from {payment_currency} to {invoice_currency}: {str(e)}"
                        )

                # Create payment reference record
                payment_reference_data = {
                    "organization_id": organization_id,
                    "payment_id": payment_id,
                    "invoice_id": invoice_id,
                    "allocated_amount": allocated_amount,
                    "exchange_rate": exchange_rate,
                    "allocated_amount_invoice_currency": allocated_amount_invoice_currency,
                    "created_by": user_id,
                }

                payment_reference = self.reference_repo.create(payment_reference_data)
                created_references.append(payment_reference)

                # Create audit log entry for ALLOCATE action
                audit_log_data = {
                    "organization_id": organization_id,
                    "payment_id": payment_id,
                    "action": PaymentAuditAction.ALLOCATE,
                    "user_id": user_id,
                    "old_values": None,
                    "new_values": {
                        "invoice_id": str(invoice_id),
                        "allocated_amount": str(allocated_amount),
                        "exchange_rate": str(exchange_rate),
                        "allocated_amount_invoice_currency": str(allocated_amount_invoice_currency),
                    },
                }
                self.audit_logger.create(audit_log_data)

            # Update invoice status for all affected invoices (before commit)
            # Collect unique invoice IDs to avoid duplicate updates
            unique_invoice_ids = set(data["invoice_id"] for data in invoice_data)
            for invoice_id in unique_invoice_ids:
                self.invoice_status_service.update_invoice_status(invoice_id, organization_id)

            # Commit all allocations in single transaction
            self.db.commit()

            # Refresh all created references
            for ref in created_references:
                self.db.refresh(ref)

            # Invalidate caches after successful bulk allocation
            # Invalidate payment cache (affects unallocated_amount)
            invalidate_payment_cache(payment_id, organization_id)
            # Invalidate invoice cache for all affected invoices
            for invoice_id in unique_invoice_ids:
                invalidate_invoice_cache(invoice_id, payment.party_id, organization_id)

            return created_references

        except Exception as e:
            # Rollback transaction on any error
            self.db.rollback()
            raise

    def remove_allocation(
        self,
        allocation_id: UUID,
        organization_id: UUID,
        user_id: UUID,
    ) -> None:
        """
        Remove a payment allocation.

        Args:
            allocation_id: Payment reference UUID to remove
            organization_id: Organization UUID
            user_id: User performing the deallocation

        Raises:
            ValidationError: If validation fails
        """
        from app.models.base import PaymentEntryStatus, PaymentAuditAction
        from app.models.payment_reference import PaymentReference

        # Get the payment_reference record first to capture details for audit log
        payment_reference = (
            self.db.query(PaymentReference)
            .filter(
                PaymentReference.id == allocation_id,
                PaymentReference.organization_id == organization_id,
            )
            .first()
        )

        if not payment_reference:
            raise ValidationError(
                f"Payment allocation with ID {allocation_id} not found or does not belong to organization"
            )

        # Get the associated payment to validate status
        payment = self.payment_repo.get_by_id(
            payment_reference.payment_id, organization_id
        )
        if not payment:
            raise ValidationError(
                f"Payment with ID {payment_reference.payment_id} not found"
            )

        # Validate payment is in Draft status
        if payment.status != PaymentEntryStatus.DRAFT:
            raise ValidationError(
                f"Cannot remove allocation from payment in {payment.status.value} status. "
                "Payment must be in Draft status to modify allocations."
            )

        # Capture allocation details for audit log before deletion
        old_values = {
            "invoice_id": str(payment_reference.invoice_id),
            "allocated_amount": str(payment_reference.allocated_amount),
            "exchange_rate": str(payment_reference.exchange_rate),
            "allocated_amount_invoice_currency": str(
                payment_reference.allocated_amount_invoice_currency
            ),
        }

        # Delete the payment_reference record
        self.reference_repo.delete(payment_reference)

        # The payment.unallocated_amount will be automatically recalculated via the computed property

        # Create audit log entry for DEALLOCATE action
        audit_log_data = {
            "organization_id": organization_id,
            "payment_id": payment_reference.payment_id,
            "action": PaymentAuditAction.DEALLOCATE,
            "user_id": user_id,
            "old_values": old_values,
            "new_values": None,
        }
        self.audit_logger.create(audit_log_data)

        # Update invoice status after removing allocation (before commit)
        self.invoice_status_service.update_invoice_status(
            payment_reference.invoice_id, organization_id
        )

        # Commit transaction
        self.db.commit()

        # Invalidate caches after successful deallocation
        # Invalidate payment cache (affects unallocated_amount)
        invalidate_payment_cache(payment_reference.payment_id, organization_id)
        # Invalidate invoice cache (affects unpaid invoices list)
        invalidate_invoice_cache(payment_reference.invoice_id, payment.party_id, organization_id)

    def get_payment_allocations(
        self,
        payment_id: UUID,
        organization_id: UUID,
    ) -> list["PaymentReferenceResponse"]:
        """
        Get all allocations for a payment with invoice details.
        
        Retrieves all payment_references for a payment and includes invoice details
        (invoice number, date, amount, outstanding balance) using eager loading
        to avoid N+1 queries.

        Args:
            payment_id: Payment entry UUID
            organization_id: Organization UUID

        Returns:
            List of PaymentReferenceResponse with invoice details

        Raises:
            ValidationError: If payment not found
        """
        from app.schemas.payment_reference import PaymentReferenceResponse

        # Validate payment exists
        payment = self.payment_repo.get_by_id(payment_id, organization_id)
        if not payment:
            raise ValidationError(
                f"Payment with ID {payment_id} not found or does not belong to organization"
            )

        # Get all payment references with eager loaded invoice details
        payment_references = self.reference_repo.get_by_payment_id_with_invoice_details(
            payment_id, organization_id
        )

        # Convert to response schemas with invoice details
        responses = []
        for ref in payment_references:
            # Build response dict with payment reference data
            response_data = {
                "id": ref.id,
                "organization_id": ref.organization_id,
                "payment_id": ref.payment_id,
                "invoice_id": ref.invoice_id,
                "allocated_amount": ref.allocated_amount,
                "exchange_rate": ref.exchange_rate,
                "allocated_amount_invoice_currency": ref.allocated_amount_invoice_currency,
                "created_by": ref.created_by,
                "created_at": ref.created_at,
            }

            # Add invoice details if invoice is loaded
            if hasattr(ref, 'invoice') and ref.invoice:
                invoice = ref.invoice
                response_data["invoice_no"] = invoice.invoice_no
                response_data["invoice_date"] = invoice.posting_date
                response_data["invoice_amount"] = invoice.grand_total
                response_data["invoice_outstanding_balance"] = invoice.outstanding_amount

            responses.append(PaymentReferenceResponse(**response_data))

        return responses

    def get_invoice_allocations(
        self,
        invoice_id: UUID,
        organization_id: UUID,
    ) -> list["PaymentReferenceResponse"]:
        """
        Get all allocations for an invoice with payment details.
        
        Retrieves all payment_references for an invoice and includes payment details
        (payment number, date, amount, mode, status, currency) using eager loading
        to avoid N+1 queries.

        Args:
            invoice_id: Invoice UUID
            organization_id: Organization UUID

        Returns:
            List of PaymentReferenceResponse with payment details

        Raises:
            ValidationError: If invoice not found
        """
        from app.schemas.payment_reference import PaymentReferenceResponse

        # Validate invoice exists (without items to avoid querying invoice_items columns that may not exist)
        invoice = self.invoice_repo.get_by_id(invoice_id, organization_id, load_items=False)
        if not invoice:
            raise ValidationError(
                f"Invoice with ID {invoice_id} not found or does not belong to organization"
            )

        # Get all payment references with eager loaded payment details
        payment_references = self.reference_repo.get_by_invoice_id_with_payment_details(
            invoice_id, organization_id
        )

        # Convert to response schemas with payment details
        responses = []
        for ref in payment_references:
            # Build response dict with payment reference data
            response_data = {
                "id": ref.id,
                "organization_id": ref.organization_id,
                "payment_id": ref.payment_id,
                "invoice_id": ref.invoice_id,
                "allocated_amount": ref.allocated_amount,
                "exchange_rate": ref.exchange_rate,
                "allocated_amount_invoice_currency": ref.allocated_amount_invoice_currency,
                "created_by": ref.created_by,
                "created_at": ref.created_at,
            }

            # Add payment details if payment_entry is loaded
            if hasattr(ref, 'payment_entry') and ref.payment_entry:
                payment = ref.payment_entry
                response_data["payment_no"] = payment.receipt_number
                response_data["payment_date"] = payment.payment_date
                response_data["payment_amount"] = payment.amount
                response_data["payment_mode"] = payment.payment_mode.value
                response_data["payment_status"] = payment.status.value
                response_data["payment_currency"] = payment.currency_code

            responses.append(PaymentReferenceResponse(**response_data))

        return responses
