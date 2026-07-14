"""Bank Transaction schemas for API requests and responses"""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class ImportResultResponse(BaseModel):
    """Response schema for transaction import operations"""

    imported_count: int = Field(
        ..., description="Number of transactions successfully imported"
    )
    skipped_count: int = Field(
        ..., description="Number of duplicate transactions skipped"
    )
    failed_count: int = Field(
        ..., description="Number of transactions that failed validation"
    )
    errors: list[str] = Field(
        default_factory=list, description="List of error messages"
    )
    warnings: list[str] = Field(
        default_factory=list, description="List of warning messages"
    )
    batch_id: UUID = Field(..., description="Unique identifier for this import batch")

    model_config = {"from_attributes": True}


class BankTransactionResponse(BaseModel):
    """Response schema for bank transaction details"""

    id: UUID
    organization_id: UUID
    bank_account_id: UUID
    statement_date: date
    transaction_amount: Decimal
    transaction_description: str | None = None
    bank_reference: str | None = None
    transaction_status: str  # pending, cleared, reconciled, void
    transaction_type: str  # debit, credit
    imported_at: datetime
    import_source: str | None = None
    import_batch_id: UUID | None = None
    reconciled_at: datetime | None = None
    is_duplicate: bool = False

    model_config = {"from_attributes": True}


class BankTransactionListResponse(BaseModel):
    """Response schema for paginated list of bank transactions"""

    items: list[BankTransactionResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

    model_config = {"from_attributes": True}


class TransactionFilterParams(BaseModel):
    """Query parameters for filtering transactions"""

    status: str | None = Field(None, description="Filter by transaction status")
    transaction_type: str | None = Field(
        None, description="Filter by transaction type (debit/credit)"
    )
    date_from: date | None = Field(
        None, description="Filter transactions from this date"
    )
    date_to: date | None = Field(None, description="Filter transactions to this date")
    min_amount: Decimal | None = Field(None, description="Minimum transaction amount")
    max_amount: Decimal | None = Field(None, description="Maximum transaction amount")
    search: str | None = Field(None, description="Search in description or reference")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        if v and v not in ("pending", "cleared", "reconciled", "void"):
            raise ValueError(
                "Status must be one of: pending, cleared, reconciled, void"
            )
        return v

    @field_validator("transaction_type")
    @classmethod
    def validate_transaction_type(cls, v):
        if v and v not in ("debit", "credit"):
            raise ValueError("Transaction type must be either 'debit' or 'credit'")
        return v
