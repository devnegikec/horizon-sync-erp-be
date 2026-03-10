"""Payment Entry related Pydantic schemas"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.common import PaginationMeta


class BankAccountBasic(BaseModel):
    """Minimal bank account info for nested response"""

    id: UUID
    bank_name: str
    masked_account_number: str
    gl_account_id: UUID

    model_config = ConfigDict(from_attributes=True)


class PaymentEntryBase(BaseModel):
    """Base payment entry schema with common fields"""

    payment_type: str = Field(
        ...,
        description="Customer_Payment or Supplier_Payment",
    )
    party_id: UUID = Field(..., description="Customer or Supplier UUID")
    amount: Decimal = Field(..., gt=0, description="Payment amount (must be > 0)")
    currency_code: str = Field(default="USD", max_length=3)
    payment_date: datetime = Field(..., description="Date of payment")
    payment_mode: str = Field(
        ...,
        description="Cash, Check, or Bank_Transfer",
    )
    reference_no: str | None = Field(
        None, max_length=100, description="Check number or bank UTR"
    )

    @field_validator("currency_code")
    @classmethod
    def validate_currency_code(cls, v: str) -> str:
        """Validate currency code is valid ISO 4217 (3-letter uppercase)"""
        if not v or not v.strip():
            raise ValueError("Currency code cannot be empty")

        v = v.strip().upper()

        if len(v) != 3:
            raise ValueError("Currency code must be exactly 3 characters (ISO 4217)")

        if not v.isalpha():
            raise ValueError("Currency code must contain only letters")

        return v

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: Decimal) -> Decimal:
        """Validate amount is positive and has max 2 decimal places"""
        if v <= 0:
            raise ValueError("Amount must be greater than zero")

        # Check decimal places
        decimal_str = str(v)
        if "." in decimal_str:
            decimal_places = len(decimal_str.split(".")[1])
            if decimal_places > 2:
                raise ValueError("Amount must have at most 2 decimal places")

        return v

    @field_validator("payment_date")
    @classmethod
    def validate_payment_date(cls, v: datetime) -> datetime:
        """Validate payment date is not more than 30 days in the future"""
        from datetime import UTC, timedelta

        now = datetime.now(UTC)
        max_future_date = now + timedelta(days=30)

        # Make v timezone-aware if it isn't
        if v.tzinfo is None:

            v = v.replace(tzinfo=UTC)

        if v > max_future_date:
            raise ValueError("Payment date cannot be more than 30 days in the future")

        return v


class PaymentEntryCreate(PaymentEntryBase):
    """Schema for creating a new payment entry"""

    bank_account_id: UUID | None = Field(
        None,
        description="ID of the bank account used for Bank_Transfer payments"
    )


class PaymentEntryUpdate(BaseModel):
    """Schema for updating a payment entry (all fields optional)"""

    amount: Decimal | None = Field(None, gt=0)
    payment_date: datetime | None = None
    payment_mode: str | None = None
    reference_no: str | None = Field(None, max_length=100)
    bank_account_id: UUID | None = None

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: Decimal | None) -> Decimal | None:
        """Validate amount is positive and has max 2 decimal places"""
        if v is None:
            return v

        if v <= 0:
            raise ValueError("Amount must be greater than zero")

        # Check decimal places
        decimal_str = str(v)
        if "." in decimal_str:
            decimal_places = len(decimal_str.split(".")[1])
            if decimal_places > 2:
                raise ValueError("Amount must have at most 2 decimal places")

        return v

    @field_validator("payment_date")
    @classmethod
    def validate_payment_date(cls, v: datetime | None) -> datetime | None:
        """Validate payment date is not more than 30 days in the future"""
        if v is None:
            return v

        from datetime import UTC, timedelta

        now = datetime.now(UTC)
        max_future_date = now + timedelta(days=30)

        # Make v timezone-aware if it isn't
        if v.tzinfo is None:
            v = v.replace(tzinfo=UTC)

        if v > max_future_date:
            raise ValueError("Payment date cannot be more than 30 days in the future")

        return v


class PaymentReferenceInfo(BaseModel):
    """Minimal payment reference info for nested response"""

    id: UUID
    invoice_id: UUID
    allocated_amount: Decimal
    exchange_rate: Decimal
    allocated_amount_invoice_currency: Decimal

    model_config = ConfigDict(from_attributes=True)


class PaymentEntryResponse(BaseModel):
    """Schema for payment entry response"""

    id: UUID
    organization_id: UUID
    payment_type: str
    party_id: UUID
    amount: Decimal
    currency_code: str
    payment_date: datetime
    payment_mode: str
    reference_no: str | None = None
    bank_account_id: UUID | None = None

    # Status and Source
    status: str
    source: str
    gateway_transaction_id: str | None = None
    receipt_number: str | None = None

    # Computed field
    unallocated_amount: Decimal

    # Cancellation Information
    cancellation_reason: str | None = None
    cancelled_by: UUID | None = None
    cancelled_at: datetime | None = None

    # Audit fields
    created_by: UUID
    updated_by: UUID
    created_at: datetime
    updated_at: datetime

    # Relationships
    payment_references: list[PaymentReferenceInfo] = []
    bank_account: BankAccountBasic | None = None

    # Party display (customer/supplier name and contact; populated for detail/list)
    party_name: str | None = None
    party_code: str | None = None
    party_email: str | None = None
    party_phone: str | None = None

    model_config = ConfigDict(from_attributes=True)


class PaymentEntryListItem(BaseModel):
    """Schema for payment entry in list response (lighter version)"""

    id: UUID
    organization_id: UUID
    payment_type: str
    party_id: UUID
    amount: Decimal
    currency_code: str
    payment_date: datetime
    payment_mode: str
    reference_no: str | None = None
    status: str
    source: str
    receipt_number: str | None = None
    unallocated_amount: Decimal
    created_at: datetime

    # Party display (customer or supplier name and contact)
    party_name: str | None = None
    party_code: str | None = None
    party_email: str | None = None
    party_phone: str | None = None

    model_config = ConfigDict(from_attributes=True)


class PaymentEntryListResponse(BaseModel):
    """Schema for paginated payment entry list response"""

    payment_entries: list[PaymentEntryListItem]
    pagination: PaginationMeta


class CancelPaymentRequest(BaseModel):
    """Schema for cancelling a payment entry"""

    cancellation_reason: str = Field(
        ...,
        min_length=10,
        description="Reason for cancelling the payment (minimum 10 characters)",
    )


class BatchPaymentCreate(BaseModel):
    """Schema for batch payment creation"""

    payments: list[PaymentEntryCreate] = Field(
        ..., description="List of payment entries to create"
    )


class BatchProcessResult(BaseModel):
    """Schema for batch payment processing result"""

    total_count: int = Field(..., description="Total number of payments in batch")
    success_count: int = Field(
        ..., description="Number of successfully created payments"
    )
    error_count: int = Field(..., description="Number of failed payments")
    errors: list[dict] = Field(
        default_factory=list, description="List of errors with index and error message"
    )


class PaymentFilters(BaseModel):
    """Schema for payment entry filtering and search"""

    status: str | None = Field(
        None, description="Filter by status: Draft, Confirmed, or Cancelled"
    )
    payment_mode: str | None = Field(
        None, description="Filter by payment mode: Cash, Check, or Bank_Transfer"
    )
    party_id: UUID | None = Field(None, description="Filter by customer or supplier ID")
    date_from: datetime | None = Field(
        None, description="Filter payments from this date (inclusive)"
    )
    date_to: datetime | None = Field(
        None, description="Filter payments to this date (inclusive)"
    )
    search: str | None = Field(
        None, description="Search by reference_no or receipt_number"
    )
    has_unallocated: bool | None = Field(
        None, description="Filter payments with unallocated_amount > 0"
    )
