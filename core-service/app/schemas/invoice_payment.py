"""Invoice payment schemas for admin endpoints."""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class InvoicePaymentRequest(BaseModel):
    """Schema for creating a payment from an invoice."""
    payment_amount: Decimal = Field(..., gt=0, description="Payment amount must be greater than 0")
    payment_method: str = Field(..., min_length=1, max_length=50, description="Payment method")
    payment_date: Optional[str] = Field(None, description="Optional payment date in ISO format")
    notes: Optional[str] = Field(None, max_length=500, description="Optional payment notes")


class MarkInvoicePaidRequest(BaseModel):
    """Schema for marking an invoice as paid."""
    payment_date: Optional[str] = Field(None, description="Optional payment date in ISO format")
    payment_method: Optional[str] = Field(None, max_length=50, description="Payment method")
    transaction_id: Optional[str] = Field(None, max_length=100, description="Transaction reference ID")
    notes: Optional[str] = Field(None, max_length=500, description="Optional payment notes")