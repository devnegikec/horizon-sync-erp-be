"""Payment Entry service with business logic"""

from datetime import datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import ValidationError
from app.repositories.payment_entry_repository import PaymentEntryRepository
from app.core.cache import invalidate_payment_cache


class PaymentEntryService:
    """Service for payment entry operations"""

    # Maximum days in future for payment date
    MAX_FUTURE_DAYS = 30
    
    # Default cash limit (can be overridden via configuration)
    DEFAULT_CASH_LIMIT = Decimal("10000.00")

    def __init__(self, db: Session, cash_limit: Decimal | None = None):
        """
        Initialize payment entry service.

        Args:
            db: Database session
            cash_limit: Optional cash payment limit (defaults to DEFAULT_CASH_LIMIT)
        """
        self.db = db
        self.repo = PaymentEntryRepository(db)
        self.cash_limit = cash_limit or self.DEFAULT_CASH_LIMIT
        
        # Import AuditLogger for audit trail
        from app.services.audit_logger import AuditLogger
        self.audit_logger = AuditLogger(db)
        
        # Import CurrencyService for currency validation
        from app.services.currency_service import CurrencyService
        self.currency_service = CurrencyService(db)

    def _validate_party_belongs_to_organization(
        self,
        party_id: UUID,
        organization_id: UUID,
        party_type: str,
    ) -> None:
        """
        Validate that party (customer or supplier) exists and belongs to organization.

        Args:
            party_id: Customer or Supplier UUID
            organization_id: Organization UUID
            party_type: "customer" or "supplier"

        Raises:
            ValidationError: If party not found or doesn't belong to organization
        """
        if party_type == "customer":
            from app.models.customer import Customer
            party = self.db.query(Customer).filter(
                Customer.id == party_id,
                Customer.organization_id == organization_id,
            ).first()
            
            if not party:
                raise ValidationError(
                    f"Customer with ID {party_id} not found or does not belong to organization"
                )
        elif party_type == "supplier":
            from app.models.supplier import Supplier
            party = self.db.query(Supplier).filter(
                Supplier.id == party_id,
                Supplier.organization_id == organization_id,
            ).first()
            
            if not party:
                raise ValidationError(
                    f"Supplier with ID {party_id} not found or does not belong to organization"
                )
        else:
            raise ValidationError(f"Invalid party_type: {party_type}. Must be 'customer' or 'supplier'")

    def _validate_payment_date(self, payment_date: datetime) -> None:
        """
        Validate that payment date is not too far in the future.

        Args:
            payment_date: Payment date to validate

        Raises:
            ValidationError: If payment date is more than MAX_FUTURE_DAYS in the future
        """
        from datetime import UTC
        
        now = datetime.now(UTC)
        max_future_date = now + timedelta(days=self.MAX_FUTURE_DAYS)
        
        # Make payment_date timezone-aware if it isn't
        if payment_date.tzinfo is None:
            from datetime import timezone
            payment_date = payment_date.replace(tzinfo=timezone.utc)
        
        if payment_date > max_future_date:
            raise ValidationError(
                f"Payment date cannot be more than {self.MAX_FUTURE_DAYS} days in the future. "
                f"Maximum allowed date: {max_future_date.date()}"
            )

    def _validate_amount(self, amount: Decimal) -> None:
        """
        Validate that amount is greater than zero and has at most 2 decimal places.

        Args:
            amount: Amount to validate

        Raises:
            ValidationError: If amount is invalid
        """
        if amount <= 0:
            raise ValidationError(
                f"Payment amount must be greater than zero, got {amount}"
            )
        
        # Check decimal places (max 2)
        # Convert to string and check decimal places
        amount_str = str(amount)
        if '.' in amount_str:
            decimal_places = len(amount_str.split('.')[1])
            if decimal_places > 2:
                raise ValidationError(
                    f"Payment amount must have at most 2 decimal places, got {decimal_places}"
                )

    def _validate_currency_code(self, currency_code: str) -> None:
        """
        Validate currency code format (ISO 4217: 3 uppercase letters).

        Args:
            currency_code: Currency code to validate

        Raises:
            ValidationError: If currency code is invalid
        """
        if not currency_code or len(currency_code) != 3:
            raise ValidationError(
                f"Invalid currency code '{currency_code}'. Must be 3 characters (ISO 4217 format)"
            )
        
        if not currency_code.isupper():
            raise ValidationError(
                f"Invalid currency code '{currency_code}'. Must be uppercase letters (ISO 4217 format)"
            )
        
        if not currency_code.isalpha():
            raise ValidationError(
                f"Invalid currency code '{currency_code}'. Must contain only letters (ISO 4217 format)"
            )

    def _validate_cash_limit(self, amount: Decimal, payment_mode: str) -> None:
        """
        Validate that cash payments do not exceed configured limit.

        Args:
            amount: Payment amount
            payment_mode: Payment mode (Cash, Check, Bank_Transfer)

        Raises:
            ValidationError: If cash payment exceeds limit
        """
        if payment_mode == "Cash" and amount > self.cash_limit:
            raise ValidationError(
                f"Cash payment amount {amount} exceeds maximum limit of {self.cash_limit}"
            )

    def create_payment_entry(
        self,
        data: "PaymentEntryCreate",
        organization_id: UUID,
        user_id: UUID,
    ) -> "PaymentEntryResponse":
        """
        Create a new payment entry in Draft status.

        Args:
            data: Payment entry creation data
            organization_id: Organization UUID
            user_id: User UUID creating the payment

        Returns:
            PaymentEntryResponse with created payment entry

        Raises:
            ValidationError: If validation fails
        """
        from datetime import datetime, UTC
        from sqlalchemy.exc import IntegrityError
        from app.models.base import (
            PaymentEntryStatus,
            PaymentSource,
            PaymentAuditAction,
            PaymentEntryType,
        )
        from app.schemas.payment_entry import PaymentEntryResponse
        from app.repositories.payment_audit_log_repository import PaymentAuditLogRepository

        # Validate all input fields using helper methods
        self._validate_amount(data.amount)
        self._validate_currency_code(data.currency_code)
        self._validate_payment_date(data.payment_date)
        self._validate_cash_limit(data.amount, data.payment_mode)

        # Determine party type based on payment_type
        if data.payment_type == "Customer_Payment":
            party_type = "customer"
        elif data.payment_type == "Supplier_Payment":
            party_type = "supplier"
        else:
            raise ValidationError(
                f"Invalid payment_type: {data.payment_type}. "
                "Must be 'Customer_Payment' or 'Supplier_Payment'"
            )

        # Validate party belongs to organization
        self._validate_party_belongs_to_organization(
            data.party_id, organization_id, party_type
        )

        # Assign receipt number at creation (configurable Document Numbering Series)
        from app.services.document_numbering_service import DocumentNumberingService
        doc_num_svc = DocumentNumberingService(self.db)
        receipt_number = doc_num_svc.get_next_number(
            organization_id, "payment", reference_date=data.payment_date
        )
        payment_data = {
            "organization_id": organization_id,
            "payment_type": PaymentEntryType(data.payment_type),
            "party_id": data.party_id,
            "amount": data.amount,
            "currency_code": data.currency_code,
            "payment_date": data.payment_date,
            "payment_mode": data.payment_mode,
            "reference_no": data.reference_no,
            "receipt_number": receipt_number,
            # Set defaults
            "status": PaymentEntryStatus.DRAFT,
            "source": PaymentSource.MANUAL,
            # Audit fields
            "created_by": user_id,
            "updated_by": user_id,
        }

        try:
            payment_entry = self.repo.create(payment_data)
        except IntegrityError as e:
            raise ValidationError(f"Failed to create payment entry: {str(e)}")

        # Create audit log entry for CREATE action
        audit_repo = PaymentAuditLogRepository(self.db)
        audit_repo.create({
            "organization_id": organization_id,
            "payment_id": payment_entry.id,
            "action": PaymentAuditAction.CREATE,
            "user_id": user_id,
            "old_values": None,
            "new_values": {
                "payment_type": payment_entry.payment_type.value,
                "party_id": str(payment_entry.party_id),
                "amount": str(payment_entry.amount),
                "currency_code": payment_entry.currency_code,
                "payment_date": payment_entry.payment_date.isoformat(),
                "payment_mode": payment_entry.payment_mode.value,
                "reference_no": payment_entry.reference_no,
                "status": payment_entry.status.value,
                "source": payment_entry.source.value,
                "receipt_number": payment_entry.receipt_number,
            },
            "timestamp": datetime.now(UTC),
        })

        # Invalidate payment list cache for this organization
        invalidate_payment_cache(payment_entry.id, organization_id)

        # Convert to PaymentEntryResponse with party display and return
        return self._to_payment_entry_response(payment_entry, organization_id)

    def update_payment_entry(
        self,
        payment_id: UUID,
        data: "PaymentEntryUpdate",
        organization_id: UUID,
        user_id: UUID,
    ) -> "PaymentEntryResponse":
        """
        Update a draft payment entry.

        Args:
            payment_id: Payment entry UUID
            data: Payment entry update data
            organization_id: Organization UUID
            user_id: User UUID updating the payment

        Returns:
            PaymentEntryResponse with updated payment entry

        Raises:
            ValidationError: If validation fails or payment is not in Draft status
        """
        from datetime import datetime, UTC
        from sqlalchemy.exc import IntegrityError
        from app.models.base import PaymentEntryStatus, PaymentAuditAction
        from app.schemas.payment_entry import PaymentEntryResponse
        from app.repositories.payment_audit_log_repository import PaymentAuditLogRepository

        # Retrieve payment entry
        payment_entry = self.repo.get_by_id(payment_id, organization_id)
        if not payment_entry:
            raise ValidationError(
                f"Payment entry with ID {payment_id} not found or does not belong to organization"
            )

        # Validate payment is in Draft status
        if payment_entry.status != PaymentEntryStatus.DRAFT:
            raise ValidationError(
                f"Cannot update payment entry with status '{payment_entry.status.value}'. "
                "Only Draft payments can be updated."
            )

        # Capture old values before update for audit trail
        old_values = {
            "amount": str(payment_entry.amount),
            "payment_date": payment_entry.payment_date.isoformat(),
            "payment_mode": payment_entry.payment_mode.value,
            "reference_no": payment_entry.reference_no,
        }

        # Prepare update dictionary with only provided fields
        update_dict = data.model_dump(exclude_unset=True)

        # Validate updated fields using helper methods
        if "amount" in update_dict and update_dict["amount"] is not None:
            self._validate_amount(update_dict["amount"])
            # Also validate cash limit if payment mode is Cash
            payment_mode = update_dict.get("payment_mode", payment_entry.payment_mode.value)
            self._validate_cash_limit(update_dict["amount"], payment_mode)

        if "payment_date" in update_dict and update_dict["payment_date"] is not None:
            self._validate_payment_date(update_dict["payment_date"])

        # Add updated_by field
        update_dict["updated_by"] = user_id

        # Update payment entry using repository
        try:
            updated_payment = self.repo.update(payment_entry, update_dict)
        except ValueError as e:
            raise ValidationError(str(e))
        except IntegrityError as e:
            raise ValidationError(f"Failed to update payment entry: {str(e)}")

        # Capture new values after update
        new_values = {
            "amount": str(updated_payment.amount),
            "payment_date": updated_payment.payment_date.isoformat(),
            "payment_mode": updated_payment.payment_mode.value,
            "reference_no": updated_payment.reference_no,
        }

        # Create audit log entry for UPDATE action with old/new values
        audit_repo = PaymentAuditLogRepository(self.db)
        audit_repo.create({
            "organization_id": organization_id,
            "payment_id": payment_entry.id,
            "action": PaymentAuditAction.UPDATE,
            "user_id": user_id,
            "old_values": old_values,
            "new_values": new_values,
            "timestamp": datetime.now(UTC),
        })

        # Invalidate payment cache for this organization
        invalidate_payment_cache(payment_entry.id, organization_id)

        # Convert to PaymentEntryResponse with party display and return
        return self._to_payment_entry_response(updated_payment, organization_id)

    def get_payment_entry(
        self,
        payment_id: UUID,
        organization_id: UUID,
    ) -> "PaymentEntryResponse":
        """
        Retrieve payment entry by ID with organization_id filtering.
        
        Uses caching to improve performance for frequently accessed payments.

        Args:
            payment_id: Payment entry UUID
            organization_id: Organization UUID

        Returns:
            PaymentEntryResponse with payment entry details and allocations

        Raises:
            ValidationError: If payment entry not found
        """
        from app.schemas.payment_entry import PaymentEntryResponse
        from app.core.cache import get_cached_payment_entry, cache_payment_entry

        # Try to get from cache first
        cached_data = get_cached_payment_entry(payment_id)
        if cached_data:
            # Validate organization_id matches (security check)
            if cached_data.get("organization_id") == str(organization_id):
                return PaymentEntryResponse(**cached_data)

        # Retrieve payment entry with eager loaded payment_references
        payment_entry = self.repo.get_by_id(payment_id, organization_id)
        
        if not payment_entry:
            raise ValidationError(
                f"Payment entry with ID {payment_id} not found or does not belong to organization"
            )

        # Convert to PaymentEntryResponse with party display and cache
        response = self._to_payment_entry_response(payment_entry, organization_id)
        cache_payment_entry(payment_id, response.model_dump(mode="json"), ttl=300)
        return response

    def list_payment_entries(
        self,
        filters: "PaymentFilters",
        organization_id: UUID,
        page: int = 1,
        page_size: int = 50,
        sort_by: str = "payment_date",
        sort_order: str = "desc",
    ) -> "PaymentEntryListResponse":
        """
        List payment entries with filtering, sorting, and pagination.

        Args:
            filters: Payment filters (status, payment_mode, party_id, date_range, search, has_unallocated)
            organization_id: Organization UUID
            page: Page number (1-indexed, default: 1)
            page_size: Number of items per page (default: 50, max: 1000)
            sort_by: Field to sort by (default: payment_date)
            sort_order: Sort order - asc or desc (default: desc)

        Returns:
            PaymentEntryListResponse with payment entries and pagination metadata

        Raises:
            ValidationError: If validation fails
        """
        from app.models.base import PaymentEntryStatus, PaymentMode, PaymentEntryType
        from app.schemas.payment_entry import PaymentEntryListResponse, PaymentEntryListItem
        from app.schemas.common import PaginationMeta

        # Validate and constrain page_size
        page_size = min(max(1, page_size), 1000)
        page = max(1, page)

        # Convert filter strings to enums if provided
        status_enum = None
        if filters.status:
            try:
                # Handle both enum value format (e.g., "Draft") and lowercase
                status_value = filters.status.strip()
                # Try to match enum by value
                for status in PaymentEntryStatus:
                    if status.value == status_value or status.name.lower() == status_value.lower():
                        status_enum = status
                        break
                if status_enum is None:
                    raise ValidationError(
                        f"Invalid status '{filters.status}'. Must be one of: Draft, Confirmed, Cancelled"
                    )
            except (ValueError, AttributeError) as e:
                raise ValidationError(
                    f"Invalid status '{filters.status}'. Must be one of: Draft, Confirmed, Cancelled"
                )

        payment_mode_enum = None
        if filters.payment_mode:
            try:
                # Handle both enum value format (e.g., "Cash") and lowercase
                mode_value = filters.payment_mode.strip()
                # Try to match enum by value
                for mode in PaymentMode:
                    if mode.value == mode_value or mode.name.lower() == mode_value.lower():
                        payment_mode_enum = mode
                        break
                if payment_mode_enum is None:
                    raise ValidationError(
                        f"Invalid payment_mode '{filters.payment_mode}'. Must be one of: Cash, Check, Bank_Transfer"
                    )
            except (ValueError, AttributeError) as e:
                raise ValidationError(
                    f"Invalid payment_mode '{filters.payment_mode}'. Must be one of: Cash, Check, Bank_Transfer"
                )

        # Calculate offset for pagination
        offset = (page - 1) * page_size

        # Call repository.list_with_filters() with all filter parameters
        payment_entries = self.repo.list_with_filters(
            organization_id=organization_id,
            status=status_enum,
            payment_mode=payment_mode_enum,
            payment_type=None,  # Not filtering by payment_type in this task
            party_id=filters.party_id,
            date_from=filters.date_from,
            date_to=filters.date_to,
            search=filters.search,
            has_unallocated=filters.has_unallocated,
            sort_by=sort_by,
            sort_order=sort_order,
            limit=page_size,
            offset=offset,
        )

        # Call repository.count_all() for total count
        total_count = self.repo.count_all(
            organization_id=organization_id,
            status=status_enum,
            payment_mode=payment_mode_enum,
            payment_type=None,  # Not filtering by payment_type in this task
            party_id=filters.party_id,
            date_from=filters.date_from,
            date_to=filters.date_to,
            search=filters.search,
        )

        # Apply has_unallocated filter to total count if specified
        # (repository applies this filter post-query, so we need to adjust count)
        if filters.has_unallocated is not None:
            # Get all entries without pagination to count accurately
            all_entries = self.repo.list_with_filters(
                organization_id=organization_id,
                status=status_enum,
                payment_mode=payment_mode_enum,
                payment_type=None,
                party_id=filters.party_id,
                date_from=filters.date_from,
                date_to=filters.date_to,
                search=filters.search,
                has_unallocated=filters.has_unallocated,
                sort_by=sort_by,
                sort_order=sort_order,
                limit=None,
                offset=None,
            )
            total_count = len(all_entries)

        # Calculate pagination metadata
        total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 1
        has_next = page < total_pages
        has_previous = page > 1

        # Enrich with party name and contact (batch load customers/suppliers)
        party_info = self._get_party_display_maps(
            organization_id, payment_entries
        )

        # Convert to PaymentEntryListItem with party display fields
        payment_entry_items = []
        for entry in payment_entries:
            info = party_info.get(entry.party_id) or {}
            item_dict = {
                "id": entry.id,
                "organization_id": entry.organization_id,
                "payment_type": entry.payment_type.value
                    if hasattr(entry.payment_type, "value") else str(entry.payment_type),
                "party_id": entry.party_id,
                "amount": entry.amount,
                "currency_code": entry.currency_code,
                "payment_date": entry.payment_date,
                "payment_mode": entry.payment_mode.value
                    if hasattr(entry.payment_mode, "value") else str(entry.payment_mode),
                "reference_no": getattr(entry, "reference_no", None),
                "status": entry.status.value
                    if hasattr(entry.status, "value") else str(entry.status),
                "source": entry.source.value
                    if hasattr(entry.source, "value") else str(entry.source),
                "receipt_number": getattr(entry, "receipt_number", None),
                "unallocated_amount": entry.unallocated_amount,
                "created_at": entry.created_at,
                "party_name": info.get("name"),
                "party_code": info.get("code"),
                "party_email": info.get("email"),
                "party_phone": info.get("phone"),
            }
            payment_entry_items.append(PaymentEntryListItem.model_validate(item_dict))

        # Create pagination metadata
        pagination = PaginationMeta(
            page=page,
            page_size=page_size,
            total=total_count,
            total_pages=total_pages,
            has_next=has_next,
            has_prev=has_previous,
        )

        # Return PaymentEntryListResponse with payment_entries and pagination
        return PaymentEntryListResponse(
            payment_entries=payment_entry_items,
            pagination=pagination,
        )

    def delete_payment_entry(
        self,
        payment_id: UUID,
        organization_id: UUID,
    ) -> None:
        """
        Delete a draft payment entry.

        Args:
            payment_id: Payment entry UUID
            organization_id: Organization UUID

        Raises:
            ValidationError: If payment entry not found or not in Draft status
        """
        from app.models.base import PaymentEntryStatus

        # Retrieve payment entry
        payment_entry = self.repo.get_by_id(payment_id, organization_id)
        if not payment_entry:
            raise ValidationError(
                f"Payment entry with ID {payment_id} not found or does not belong to organization"
            )

        # Validate payment is in Draft status
        if payment_entry.status != PaymentEntryStatus.DRAFT:
            raise ValidationError(
                f"Cannot delete payment entry with status '{payment_entry.status.value}'. "
                "Only Draft payments can be deleted."
            )

        # Delete payment entry (cascade deletes references and audit logs)
        self.repo.delete(payment_entry)

    def _get_party_display_maps(
        self, organization_id: UUID, payment_entries: list
    ) -> dict:
        """
        Batch-load party (customer/supplier) name and contact for list display.
        Returns dict: party_id -> { "name", "code", "email", "phone" }.
        """
        from app.models.base import PaymentEntryType
        from app.models.customer import Customer
        from app.models.supplier import Supplier

        customer_ids = [
            p.party_id for p in payment_entries
            if getattr(p.payment_type, "value", str(p.payment_type)) == PaymentEntryType.CUSTOMER_PAYMENT.value
        ]
        supplier_ids = [
            p.party_id for p in payment_entries
            if getattr(p.payment_type, "value", str(p.payment_type)) == PaymentEntryType.SUPPLIER_PAYMENT.value
        ]

        result = {}
        if customer_ids:
            customers = (
                self.db.query(Customer)
                .filter(
                    Customer.id.in_(customer_ids),
                    Customer.organization_id == organization_id,
                )
                .all()
            )
            for c in customers:
                result[c.id] = {
                    "name": c.customer_name,
                    "code": getattr(c, "customer_code", None),
                    "email": getattr(c, "email", None),
                    "phone": getattr(c, "phone", None),
                }
        if supplier_ids:
            suppliers = (
                self.db.query(Supplier)
                .filter(
                    Supplier.id.in_(supplier_ids),
                    Supplier.organization_id == organization_id,
                )
                .all()
            )
            for s in suppliers:
                result[s.id] = {
                    "name": s.supplier_name,
                    "code": getattr(s, "supplier_code", None),
                    "email": getattr(s, "email", None),
                    "phone": getattr(s, "phone", None),
                }
        return result

    def _to_payment_entry_response(
        self, payment_entry, organization_id: UUID
    ) -> "PaymentEntryResponse":
        """Build PaymentEntryResponse with party name and contact populated."""
        from app.schemas.payment_entry import PaymentEntryResponse

        base = PaymentEntryResponse.model_validate(payment_entry)
        d = base.model_dump(mode="json")
        party_info = self._get_party_display_maps(
            organization_id, [payment_entry]
        ).get(payment_entry.party_id) or {}
        d["party_name"] = party_info.get("name")
        d["party_code"] = party_info.get("code")
        d["party_email"] = party_info.get("email")
        d["party_phone"] = party_info.get("phone")
        return PaymentEntryResponse.model_validate(d)

    def confirm_payment(
        self,
        payment_id: UUID,
        organization_id: UUID,
        user_id: UUID,
    ) -> "PaymentEntryResponse":
        """
        Confirm payment and post to journal.

        Args:
            payment_id: Payment entry UUID
            organization_id: Organization UUID
            user_id: User UUID confirming the payment

        Returns:
            PaymentEntryResponse with confirmed payment entry

        Raises:
            ValidationError: If validation fails
        """
        from datetime import datetime, UTC
        from sqlalchemy.exc import IntegrityError
        from app.models.base import PaymentEntryStatus, PaymentAuditAction
        from app.schemas.payment_entry import PaymentEntryResponse
        from app.repositories.payment_audit_log_repository import PaymentAuditLogRepository
        from app.repositories.payment_reference_repository import PaymentReferenceRepository
        from app.services.journal_posting_service import JournalPostingService

        # Retrieve payment entry
        payment_entry = self.repo.get_by_id(payment_id, organization_id)
        if not payment_entry:
            raise ValidationError(
                f"Payment entry with ID {payment_id} not found or does not belong to organization"
            )

        # Validate payment is in Draft status
        if payment_entry.status != PaymentEntryStatus.DRAFT:
            raise ValidationError(
                f"Cannot confirm payment entry with status '{payment_entry.status.value}'. "
                "Only Draft payments can be confirmed."
            )

        # Validate at least one allocation exists
        reference_repo = PaymentReferenceRepository(self.db)
        allocations = reference_repo.get_by_payment_id(payment_id, organization_id)
        if not allocations or len(allocations) == 0:
            raise ValidationError(
                "Cannot confirm payment without allocations. "
                "Please allocate the payment to at least one invoice before confirming."
            )

        # Validate required default accounts are configured
        journal_service = JournalPostingService(self.db)
        try:
            journal_service._validate_default_accounts_configured(
                payment_type=payment_entry.payment_type.value,
                payment_mode=payment_entry.payment_mode.value,
                organization_id=organization_id,
            )
        except ValidationError as e:
            raise ValidationError(
                f"Cannot confirm payment: {str(e)}"
            )

        # Use receipt_number already assigned at create; generate only for legacy drafts via Document Numbering
        old_receipt = getattr(payment_entry, "receipt_number", None)
        if not old_receipt:
            from app.services.document_numbering_service import DocumentNumberingService
            doc_num_svc = DocumentNumberingService(self.db)
            old_receipt = doc_num_svc.get_next_number(
                organization_id, "payment", reference_date=payment_entry.payment_date
            )
        receipt_number = old_receipt
        update_dict = {
            "status": PaymentEntryStatus.CONFIRMED,
            "receipt_number": receipt_number,
            "updated_by": user_id,
        }
        try:
            updated_payment = self.repo.update(payment_entry, update_dict)
        except ValueError as e:
            raise ValidationError(str(e))
        except IntegrityError as e:
            raise ValidationError(f"Failed to confirm payment entry: {str(e)}")

        # Call JournalPostingService.post_payment_journal_entry()
        try:
            journal_service.post_payment_journal_entry(
                payment_entry=updated_payment,
                organization_id=organization_id,
                user_id=user_id,
            )
        except Exception as e:
            # Rollback payment status if journal posting fails
            self.db.rollback()
            raise ValidationError(
                f"Failed to post journal entry: {str(e)}. Payment remains in Draft status."
            )

        # Create audit log entry for CONFIRM action
        audit_repo = PaymentAuditLogRepository(self.db)
        audit_repo.create({
            "organization_id": organization_id,
            "payment_id": payment_entry.id,
            "action": PaymentAuditAction.CONFIRM,
            "user_id": user_id,
            "old_values": {
                "status": PaymentEntryStatus.DRAFT.value,
                "receipt_number": old_receipt,
            },
            "new_values": {
                "status": PaymentEntryStatus.CONFIRMED.value,
                "receipt_number": receipt_number,
            },
            "timestamp": datetime.now(UTC),
        })

        # Commit the transaction (payment status update, journal entry, audit log)
        self.db.commit()

        # Invalidate payment cache for this organization
        invalidate_payment_cache(payment_entry.id, organization_id)

        # Convert to PaymentEntryResponse with party display and return
        return self._to_payment_entry_response(updated_payment, organization_id)

    def cancel_payment(
        self,
        payment_id: UUID,
        cancellation_reason: str,
        organization_id: UUID,
        user_id: UUID,
    ) -> "PaymentEntryResponse":
        """
        Cancel payment and reverse journal entries.

        This method:
        1. Validates payment is in Confirmed status
        2. Validates cancellation_reason is provided
        3. Updates payment status to Cancelled
        4. Sets cancellation_reason, cancelled_by, cancelled_at fields
        5. Calls JournalPostingService.reverse_payment_journal_entry()
        6. Removes all payment_references (triggers invoice status recalculation)
        7. Creates audit log entry for CANCEL action with reason
        8. Returns cancelled PaymentEntryResponse

        Args:
            payment_id: Payment entry UUID
            cancellation_reason: Reason for cancellation
            organization_id: Organization UUID
            user_id: User UUID cancelling the payment

        Returns:
            PaymentEntryResponse with cancelled payment entry

        Raises:
            ValidationError: If validation fails

        Requirements: 5.1, 5.6, 7.3, 12.1, 12.2, 12.3, 12.4, 12.5, 12.6, 12.7, 12.8
        """
        from datetime import datetime, UTC
        from sqlalchemy.exc import IntegrityError
        from app.models.base import PaymentEntryStatus, PaymentAuditAction
        from app.schemas.payment_entry import PaymentEntryResponse
        from app.repositories.payment_audit_log_repository import PaymentAuditLogRepository
        from app.repositories.payment_reference_repository import PaymentReferenceRepository
        from app.services.journal_posting_service import JournalPostingService
        from app.services.invoice_status_service import InvoiceStatusService

        # Retrieve payment entry
        payment_entry = self.repo.get_by_id(payment_id, organization_id)
        if not payment_entry:
            raise ValidationError(
                f"Payment entry with ID {payment_id} not found or does not belong to organization"
            )

        # Validate payment is in Confirmed status
        if payment_entry.status != PaymentEntryStatus.CONFIRMED:
            raise ValidationError(
                f"Cannot cancel payment entry with status '{payment_entry.status.value}'. "
                "Only Confirmed payments can be cancelled."
            )

        # Validate cancellation_reason is provided and not empty
        if not cancellation_reason or not cancellation_reason.strip():
            raise ValidationError(
                "Cancellation reason is required. Please provide a reason for cancelling the payment."
            )

        # Update payment status to Cancelled and set cancellation fields
        # Note: We directly update the fields instead of using repo.update() 
        # because repo.update() only allows updating draft payments
        try:
            payment_entry.status = PaymentEntryStatus.CANCELLED
            payment_entry.cancellation_reason = cancellation_reason.strip()
            payment_entry.cancelled_by = user_id
            payment_entry.cancelled_at = datetime.now(UTC)
            payment_entry.updated_by = user_id
            
            self.db.commit()
            self.db.refresh(payment_entry)
        except IntegrityError as e:
            self.db.rollback()
            raise ValidationError(f"Failed to cancel payment entry: {str(e)}")

        # Call JournalPostingService.reverse_payment_journal_entry() if journal entry exists
        journal_service = JournalPostingService(self.db)
        try:
            journal_service.reverse_payment_journal_entry(
                payment_entry=payment_entry,
                organization_id=organization_id,
                user_id=user_id,
            )
        except ValidationError as ve:
            # If the error is that no journal entry exists, continue with cancellation
            # This can happen if confirm failed or payment was never properly confirmed
            error_msg = str(ve).lower()
            if "journal entry not found" in error_msg or "original journal entry not found" in error_msg:
                # Log that we're cancelling without reversing journal entries
                pass  # Continue with cancellation process
            else:
                # Other validation errors should fail the cancellation
                self.db.rollback()
                raise ValidationError(
                    f"Failed to reverse journal entry: {str(ve)}. Payment cancellation failed."
                )
        except Exception as e:
            # Rollback payment status if journal reversal fails for other reasons
            self.db.rollback()
            raise ValidationError(
                f"Failed to reverse journal entry: {str(e)}. Payment cancellation failed."
            )

        # Remove all payment_references (triggers invoice status recalculation)
        reference_repo = PaymentReferenceRepository(self.db)
        invoice_status_service = InvoiceStatusService(self.db)
        
        # Get all payment references for this payment
        payment_references = reference_repo.get_by_payment_id(payment_id, organization_id)
        
        # Track invoice IDs for status recalculation
        invoice_ids = [ref.invoice_id for ref in payment_references]
        
        # Delete all payment references
        for payment_reference in payment_references:
            try:
                reference_repo.delete(payment_reference)
            except Exception as e:
                # Rollback if deletion fails
                self.db.rollback()
                raise ValidationError(
                    f"Failed to remove payment reference: {str(e)}. Payment cancellation failed."
                )
        
        # Recalculate invoice status for all affected invoices
        for invoice_id in invoice_ids:
            try:
                invoice_status_service.update_invoice_status(invoice_id, organization_id)
            except Exception as e:
                # Log error but don't fail the cancellation
                # Invoice status can be recalculated later if needed
                pass

        # Create audit log entry for CANCEL action with reason
        audit_repo = PaymentAuditLogRepository(self.db)
        audit_repo.create({
            "organization_id": organization_id,
            "payment_id": payment_entry.id,
            "action": PaymentAuditAction.CANCEL,
            "user_id": user_id,
            "old_values": {
                "status": PaymentEntryStatus.CONFIRMED.value,
                "cancellation_reason": None,
                "cancelled_by": None,
                "cancelled_at": None,
            },
            "new_values": {
                "status": PaymentEntryStatus.CANCELLED.value,
                "cancellation_reason": cancellation_reason.strip(),
                "cancelled_by": str(user_id),
                "cancelled_at": payment_entry.cancelled_at.isoformat(),
            },
            "timestamp": datetime.now(UTC),
        })

        # Invalidate payment cache for this organization
        invalidate_payment_cache(payment_entry.id, organization_id)

        # Convert to PaymentEntryResponse with party display and return
        return self._to_payment_entry_response(payment_entry, organization_id)

    def _ensure_receipt_sequence_exists(self, year: int) -> None:
        """
        Create sequence receipt_seq_{year} if it does not exist (for future years).
        Current year and next are created by migration; this handles 2027+.
        """
        from sqlalchemy import text

        seq_name = f"receipt_seq_{year}"
        self.db.execute(text(f"CREATE SEQUENCE IF NOT EXISTS {seq_name} START 1"))

    def _get_next_receipt_sequence(self, year: int) -> int:
        """
        Get next value from receipt_seq_{year}. Atomic; no race conditions.
        Ensures sequence exists (for first use of a new year), then returns nextval.
        """
        self._ensure_receipt_sequence_exists(year)
        from sqlalchemy import text

        result = self.db.execute(text(f"SELECT nextval('receipt_seq_{year}')"))
        return result.scalar()

    def _generate_receipt_number(
        self,
        organization_id: UUID,
        payment_date: datetime,
    ) -> str:
        """
        Generate unique receipt number using PostgreSQL sequence per year.
        Format: RCP-{year}-{sequence:05d}. Atomic; one sequence per year (e.g. receipt_seq_2026).
        """
        year = payment_date.year
        sequence = self._get_next_receipt_sequence(year)
        return f"RCP-{year}-{sequence:05d}"

