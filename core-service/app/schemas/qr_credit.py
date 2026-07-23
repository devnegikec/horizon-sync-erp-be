"""QR Credit schemas for API responses."""

from pydantic import BaseModel, ConfigDict


class QRCreditBalanceResponse(BaseModel):
    """Response schema for QR credit balance queries."""

    total_credits: int
    used_credits: int
    balance_credits: int

    model_config = ConfigDict(from_attributes=True)
