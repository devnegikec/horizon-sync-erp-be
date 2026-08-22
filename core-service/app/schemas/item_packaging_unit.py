"""Pydantic schemas for ItemPackagingUnit CRUD"""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ItemPackagingUnitCreate(BaseModel):
    """Schema for creating a packaging unit for an item"""

    unit_name: str = Field(..., min_length=1, max_length=100, description="Name of the packaging unit (e.g. 'Box of 12')")
    qr_identifier: Optional[str] = Field(None, max_length=255, description="Optional unique QR identifier for this packaging unit")
    conversion_factor: Decimal = Field(..., gt=0, description="Number of base units (Eaches) in this packaging unit — must be > 0")
    items_per_master_pack: Optional[int] = Field(None, gt=0, description="Items per master pack (used for QR master pack grouping)")
    length_mm: Optional[Decimal] = Field(None, ge=0, description="Length in millimetres")
    width_mm: Optional[Decimal] = Field(None, ge=0, description="Width in millimetres")
    height_mm: Optional[Decimal] = Field(None, ge=0, description="Height in millimetres")
    weight_grams: Optional[Decimal] = Field(None, ge=0, description="Weight in grams")
    is_base_unit: bool = Field(default=False, description="Whether this is the base unit (Each)")
    is_active: bool = Field(default=True, description="Whether this packaging unit is active")

    @field_validator("conversion_factor")
    @classmethod
    def validate_conversion_factor(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("conversion_factor must be greater than 0")
        return v


class ItemPackagingUnitUpdate(BaseModel):
    """Schema for partially updating a packaging unit (all fields optional)"""

    unit_name: Optional[str] = Field(None, min_length=1, max_length=100)
    qr_identifier: Optional[str] = Field(None, max_length=255)
    conversion_factor: Optional[Decimal] = Field(None, gt=0)
    items_per_master_pack: Optional[int] = Field(None, gt=0)
    length_mm: Optional[Decimal] = Field(None, ge=0)
    width_mm: Optional[Decimal] = Field(None, ge=0)
    height_mm: Optional[Decimal] = Field(None, ge=0)
    weight_grams: Optional[Decimal] = Field(None, ge=0)
    is_base_unit: Optional[bool] = None
    is_active: Optional[bool] = None

    @field_validator("conversion_factor")
    @classmethod
    def validate_conversion_factor(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None and v <= 0:
            raise ValueError("conversion_factor must be greater than 0")
        return v


class ItemPackagingUnitResponse(BaseModel):
    """Full packaging unit response"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    item_id: UUID
    unit_name: str
    qr_identifier: Optional[str] = None
    conversion_factor: Decimal
    items_per_master_pack: Optional[int] = None
    length_mm: Optional[Decimal] = None
    width_mm: Optional[Decimal] = None
    height_mm: Optional[Decimal] = None
    weight_grams: Optional[Decimal] = None
    is_base_unit: bool
    is_active: bool
    created_at: object
    updated_at: object


class ItemPackagingUnitListResponse(BaseModel):
    """Paginated list of packaging units"""

    packaging_units: list[ItemPackagingUnitResponse]
    pagination: dict
