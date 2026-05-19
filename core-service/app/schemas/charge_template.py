"""Charge Template Pydantic schemas"""

from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ChargeTemplateCreate(BaseModel):
    """Schema for creating a charge template"""

    template_code: str = Field(..., min_length=1, max_length=100, description="Unique template code")
    template_name: str = Field(..., min_length=1, max_length=255, description="Template name")
    description: Optional[str] = Field(None, max_length=1000, description="Optional description")

    charge_type: str = Field(
        ...,
        description="Charge type: Shipping, Handling, Packaging, Insurance, Custom",
    )
    calculation_method: str = Field(
        ..., description="Calculation method: FIXED or PERCENTAGE"
    )

    fixed_amount: Decimal | None = Field(
        None, ge=0, description="Fixed amount (required when calculation_method=FIXED)"
    )
    percentage_rate: Decimal | None = Field(
        None,
        ge=0,
        description="Percentage rate (required when calculation_method=PERCENTAGE)",
    )
    base_on: str | None = Field(
        None, description="Base for percentage: Net_Total or Grand_Total"
    )

    account_head_id: UUID = Field(..., description="GL account UUID for this charge")

    is_active: bool = Field(default=True, description="Whether the template is active")
    applicability_rules: dict | None = Field(
        None, description="Optional applicability rules"
    )
    extra_data: dict | None = Field(None, description="Optional extra data")

    @model_validator(mode="after")
    def validate_calculation_fields(self) -> "ChargeTemplateCreate":
        if self.calculation_method == "FIXED":
            if self.fixed_amount is None:
                raise ValueError(
                    "fixed_amount is required when calculation_method is FIXED"
                )
        elif self.calculation_method == "PERCENTAGE":
            if self.percentage_rate is None:
                raise ValueError(
                    "percentage_rate is required when calculation_method is PERCENTAGE"
                )
            if self.base_on is None:
                raise ValueError(
                    "base_on is required when calculation_method is PERCENTAGE"
                )
            if self.base_on not in ("Net_Total", "Grand_Total"):
                raise ValueError("base_on must be Net_Total or Grand_Total")
        else:
            raise ValueError("calculation_method must be FIXED or PERCENTAGE")
        return self


class ChargeTemplateUpdate(BaseModel):
    """Schema for updating a charge template (all fields optional)"""

    template_code: Optional[str] = Field(None, min_length=1, max_length=100)
    template_name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    charge_type: Optional[str] = None
    calculation_method: Optional[str] = None
    fixed_amount: Optional[Decimal] = Field(None, ge=0)
    percentage_rate: Optional[Decimal] = Field(None, ge=0)
    base_on: Optional[str] = None
    account_head_id: Optional[UUID] = None
    is_active: Optional[bool] = None
    applicability_rules: Optional[dict] = None
    extra_data: Optional[dict] = None


class ChargeTemplateResponse(BaseModel):
    """Full charge template response"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    template_code: str
    template_name: str
    description: str | None = None
    charge_type: str
    calculation_method: str
    fixed_amount: Decimal | None = None
    percentage_rate: Decimal | None = None
    base_on: str | None = None
    account_head_id: UUID
    is_active: bool
    applicability_rules: dict | None = None
    extra_data: dict | None = None
    created_by: UUID | None = None
    updated_by: UUID | None = None
    created_at: object | None = None
    updated_at: object | None = None


class ChargeTemplateListItem(BaseModel):
    """Lightweight charge template for list responses"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    template_code: str
    template_name: str
    charge_type: str
    calculation_method: str
    is_active: bool
    created_at: object | None = None
    updated_at: object | None = None


class ChargeTemplateListResponse(BaseModel):
    """Paginated list of charge templates"""

    charge_templates: list[ChargeTemplateListItem]
    pagination: dict
