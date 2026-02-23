"""Payment entry repository for database operations"""

from uuid import UUID
from datetime import datetime
from decimal import Decimal

from sqlalchemy import String, cast, func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload, joinedload

from app.models.base import PaymentEntryStatus, PaymentMode, PaymentEntryType
from app.models.payment_entry import PaymentEntry
from app.core.cache import (
    get_cached_payment_list,
    cache_payment_list,
)


class PaymentEntryRepository:
    """Repository for payment entry database operations"""

    def __init__(self, db: Session):
        self.db = db

    def create(self, data: dict) -> PaymentEntry:
        """
        Create a new payment entry.

        Args:
            data: Dictionary containing payment entry data (must include organization_id)

        Returns:
            Created PaymentEntry object

        Raises:
            IntegrityError: If validation constraints are violated
        """
        payment_entry = PaymentEntry(**data)
        self.db.add(payment_entry)
        try:
            self.db.commit()
            self.db.refresh(payment_entry)
            return payment_entry
        except IntegrityError as e:
            self.db.rollback()
            raise e

    def get_by_id(self, payment_id: UUID, organization_id: UUID) -> PaymentEntry | None:
        """
        Get payment entry by ID with organization_id filtering.
        
        Uses eager loading with selectinload to prevent N+1 queries when accessing
        payment_references relationship.

        Args:
            payment_id: Payment entry UUID
            organization_id: Organization UUID

        Returns:
            PaymentEntry object or None if not found
        """
        return (
            self.db.query(PaymentEntry)
            .options(
                selectinload(PaymentEntry.payment_references).joinedload(
                    PaymentEntry.payment_references.property.mapper.class_.invoice
                )
            )
            .filter(
                PaymentEntry.id == payment_id,
                PaymentEntry.organization_id == organization_id
            )
            .first()
        )

    def get_by_receipt_number(
        self, receipt_number: str, organization_id: UUID
    ) -> PaymentEntry | None:
        """
        Get payment entry by receipt number.
        
        Uses eager loading with selectinload to prevent N+1 queries when accessing
        payment_references relationship.

        Args:
            receipt_number: Receipt number
            organization_id: Organization UUID

        Returns:
            PaymentEntry object or None if not found
        """
        return (
            self.db.query(PaymentEntry)
            .options(
                selectinload(PaymentEntry.payment_references).joinedload(
                    PaymentEntry.payment_references.property.mapper.class_.invoice
                )
            )
            .filter(
                PaymentEntry.receipt_number == receipt_number,
                PaymentEntry.organization_id == organization_id
            )
            .first()
        )

    def update(self, payment_entry: PaymentEntry, update_data: dict) -> PaymentEntry:
        """
        Update payment entry fields (only for draft payments).

        Args:
            payment_entry: PaymentEntry object to update
            update_data: Dictionary of fields to update

        Returns:
            Updated PaymentEntry object

        Raises:
            ValueError: If payment is not in Draft status
            IntegrityError: If validation constraints are violated
        """
        if payment_entry.status != PaymentEntryStatus.DRAFT:
            raise ValueError("Only draft payments can be updated")

        for key, value in update_data.items():
            if hasattr(payment_entry, key):
                setattr(payment_entry, key, value)

        try:
            self.db.commit()
            self.db.refresh(payment_entry)
            return payment_entry
        except IntegrityError as e:
            self.db.rollback()
            raise e

    def delete(self, payment_entry: PaymentEntry) -> None:
        """
        Delete a payment entry (only for draft payments).

        Args:
            payment_entry: PaymentEntry object to delete

        Raises:
            ValueError: If payment is not in Draft status
            IntegrityError: If foreign key constraints are violated
        """
        if payment_entry.status != PaymentEntryStatus.DRAFT:
            raise ValueError("Only draft payments can be deleted")

        try:
            self.db.delete(payment_entry)
            self.db.commit()
        except IntegrityError as e:
            self.db.rollback()
            raise e

    def list_with_filters(
        self,
        organization_id: UUID,
        status: PaymentEntryStatus | None = None,
        payment_mode: PaymentMode | None = None,
        payment_type: PaymentEntryType | None = None,
        party_id: UUID | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        search: str | None = None,
        has_unallocated: bool | None = None,
        sort_by: str = "payment_date",
        sort_order: str = "desc",
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[PaymentEntry]:
        """
        List payment entries with optional filtering and pagination.
        
        Uses eager loading with selectinload to prevent N+1 queries when accessing
        payment_references relationship. This is critical for performance when
        loading lists of payments.

        Args:
            organization_id: Organization UUID
            status: Filter by payment status
            payment_mode: Filter by payment mode
            payment_type: Filter by payment type (Customer_Payment or Supplier_Payment)
            party_id: Filter by party (customer or supplier) ID
            date_from: Filter by payment date from (inclusive)
            date_to: Filter by payment date to (inclusive)
            search: Search term for reference_no or receipt_number (case-insensitive)
            has_unallocated: Filter by unallocated_amount > 0
            sort_by: Field to sort by
            sort_order: Sort order (asc or desc)
            limit: Maximum number of records to return
            offset: Number of records to skip

        Returns:
            List of payment entries matching the filters
        """
        query = (
            self.db.query(PaymentEntry)
            .options(
                selectinload(PaymentEntry.payment_references).joinedload(
                    PaymentEntry.payment_references.property.mapper.class_.invoice
                )
            )
            .filter(PaymentEntry.organization_id == organization_id)
        )

        # Apply filters
        if status is not None:
            query = query.filter(
                func.lower(cast(PaymentEntry.status, String))
                == str(status.value).lower()
            )

        if payment_mode is not None:
            query = query.filter(
                func.lower(cast(PaymentEntry.payment_mode, String))
                == str(payment_mode.value).lower()
            )

        if payment_type is not None:
            query = query.filter(
                func.lower(cast(PaymentEntry.payment_type, String))
                == str(payment_type.value).lower()
            )

        if party_id is not None:
            query = query.filter(PaymentEntry.party_id == party_id)

        if date_from is not None:
            query = query.filter(PaymentEntry.payment_date >= date_from)

        if date_to is not None:
            query = query.filter(PaymentEntry.payment_date <= date_to)

        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    PaymentEntry.reference_no.ilike(search_term),
                    PaymentEntry.receipt_number.ilike(search_term),
                )
            )

        # Note: has_unallocated filter requires loading payment_references
        # This is handled at the service layer after loading the data
        # to avoid complex subqueries that may impact performance

        # Apply sorting
        allowed_sort_fields = {
            "id",
            "payment_date",
            "amount",
            "status",
            "payment_mode",
            "created_at",
            "updated_at",
        }
        requested_sort_field = sort_by if sort_by in allowed_sort_fields else "payment_date"
        sort_column = getattr(PaymentEntry, requested_sort_field, PaymentEntry.payment_date)
        
        normalized_order = "desc" if str(sort_order).lower() == "desc" else "asc"
        if normalized_order == "desc":
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())

        # Apply pagination if limit/offset provided
        if offset is not None:
            query = query.offset(offset)
        if limit is not None:
            query = query.limit(limit)

        results = query.all()

        # Apply has_unallocated filter if specified
        if has_unallocated is not None:
            if has_unallocated:
                results = [p for p in results if p.unallocated_amount > 0]
            else:
                results = [p for p in results if p.unallocated_amount == 0]

        return results

    def count_all(
        self,
        organization_id: UUID,
        status: PaymentEntryStatus | None = None,
        payment_mode: PaymentMode | None = None,
        payment_type: PaymentEntryType | None = None,
        party_id: UUID | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        search: str | None = None,
    ) -> int:
        """
        Count all payment entries matching filters.

        Args:
            organization_id: Organization UUID
            status: Filter by payment status
            payment_mode: Filter by payment mode
            payment_type: Filter by payment type
            party_id: Filter by party ID
            date_from: Filter by payment date from (inclusive)
            date_to: Filter by payment date to (inclusive)
            search: Search term for reference_no or receipt_number

        Returns:
            Total count of payment entries matching the filters
        """
        query = self.db.query(PaymentEntry).filter(
            PaymentEntry.organization_id == organization_id
        )

        # Apply filters (same as list_with_filters)
        if status is not None:
            query = query.filter(
                func.lower(cast(PaymentEntry.status, String))
                == str(status.value).lower()
            )

        if payment_mode is not None:
            query = query.filter(
                func.lower(cast(PaymentEntry.payment_mode, String))
                == str(payment_mode.value).lower()
            )

        if payment_type is not None:
            query = query.filter(
                func.lower(cast(PaymentEntry.payment_type, String))
                == str(payment_type.value).lower()
            )

        if party_id is not None:
            query = query.filter(PaymentEntry.party_id == party_id)

        if date_from is not None:
            query = query.filter(PaymentEntry.payment_date >= date_from)

        if date_to is not None:
            query = query.filter(PaymentEntry.payment_date <= date_to)

        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    PaymentEntry.reference_no.ilike(search_term),
                    PaymentEntry.receipt_number.ilike(search_term),
                )
            )

        return query.count()

    def receipt_number_exists(
        self, receipt_number: str, organization_id: UUID
    ) -> bool:
        """
        Check if receipt number already exists.

        Args:
            receipt_number: Receipt number to check
            organization_id: Organization UUID

        Returns:
            True if receipt number exists, False otherwise
        """
        return (
            self.db.query(PaymentEntry)
            .filter(
                PaymentEntry.receipt_number == receipt_number,
                PaymentEntry.organization_id == organization_id
            )
            .count()
            > 0
        )
