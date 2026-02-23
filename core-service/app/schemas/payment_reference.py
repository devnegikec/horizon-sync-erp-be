"""Payment Reference related Pydantic schemas"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PaymentReferenceBase(BaseModel):
    """Base payment reference schema with common fields"""

    payment_id: UUID = Field(..., description="Payment entry UUID")
    invoice_id: UUID = Field(..., description="Invoice UUID")
    allocated_amount: Decimal = Field(..., gt=0, description="Amount allocated to invoice (must be > 0)")
    exchange_rate: Decimal | None = Field(default=1.0, description="Exchange rate if currencies differ")
    allocated_amount_invoice_currency: Decimal | None = Field(None, description="Amount in invoice currency")

    @field_validator('allocated_amount')
    @classmethod
    def validate_allocated_amount(cls, v: Decimal) -> Decimal:
        """Validate allocated amount is positive and has max 2 decimal places"""
        if v <= 0:
            raise ValueError('Allocated amount must be greater than zero')
        
        # Check decimal places
        decimal_str = str(v)
        if '.' in decimal_str:
            decimal_places = len(decimal_str.split('.')[1])
            if decimal_places > 2:
                raise ValueError('Allocated amount must have at most 2 decimal places')
        
        return v


class PaymentReferenceCreate(BaseModel):
    """Schema for creating a new payment reference (allocation request)"""

    invoice_id: UUID = Field(..., description="Invoice UUID to allocate payment to")
    allocated_amount: Decimal = Field(..., gt=0, description="Amount to allocate to this invoice")

    @field_validator('allocated_amount')
    @classmethod
    def validate_allocated_amount(cls, v: Decimal) -> Decimal:
        """Validate allocated amount is positive and has max 2 decimal places"""
        if v <= 0:
            raise ValueError('Allocated amount must be greater than zero')
        
        # Check decimal places
        decimal_str = str(v)
        if '.' in decimal_str:
            decimal_places = len(decimal_str.split('.')[1])
            if decimal_places > 2:
                raise ValueError('Allocated amount must have at most 2 decimal places')
        
        return v


class PaymentReferenceResponse(BaseModel):
    """Schema for payment reference API response"""

    id: UUID
    organization_id: UUID
    payment_id: UUID
    invoice_id: UUID
    allocated_amount: Decimal
    exchange_rate: Decimal | None = None
    allocated_amount_invoice_currency: Decimal | None = None
    created_by: UUID
    created_at: datetime
    
    # Invoice details (optional, populated when eager loaded)
    invoice_no: str | None = None
    invoice_date: datetime | None = None
    invoice_amount: Decimal | None = None
    invoice_outstanding_balance: Decimal | None = None
    
    # Payment details (optional, populated when eager loaded)
    payment_no: str | None = None
    payment_date: datetime | None = None
    payment_amount: Decimal | None = None
    payment_mode: str | None = None
    payment_status: str | None = None
    payment_currency: str | None = None

    model_config = ConfigDict(from_attributes=True)
