"""Tax Template related Pydantic schemas"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.common import PaginationMeta


class TaxRuleBase(BaseModel):
    """Base tax rule schema with common fields"""

    rule_name: str = Field(..., min_length=1, max_length=255)
    tax_type: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)
    tax_rate: Decimal | float = Field(..., ge=0, le=100)
    account_head_id: UUID
    is_compound: bool = False
    sequence: int = Field(..., ge=1)
    applicability_conditions: dict | None = None


class TaxRuleCreate(TaxRuleBase):
    """Schema for creating a new tax rule"""

    pass


class TaxRuleUpdate(BaseModel):
    """Schema for updating a tax rule (all fields optional)"""

    rule_name: str | None = Field(None, min_length=1, max_length=255)
    tax_type: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)
    tax_rate: Decimal | float | None = Field(None, ge=0, le=100)
    account_head_id: UUID | None = None
    is_compound: bool | None = None
    sequence: int | None = Field(None, ge=1)
    applicability_conditions: dict | None = None


class TaxRuleResponse(TaxRuleBase):
    """Schema for tax rule response"""

    id: UUID
    tax_template_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TaxTemplateBase(BaseModel):
    """Base tax template schema with common fields"""

    template_code: str = Field(..., min_length=1, max_length=50)
    template_name: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(None, max_length=500)
    tax_category: str = Field(..., pattern="^(Input|Output)$")
    is_default: bool = False
    is_active: bool = True
    applicability_rules: dict | None = None
    extra_data: dict | None = None

    @field_validator("tax_category")
    @classmethod
    def validate_tax_category(cls, v: str) -> str:
        """Validate tax category is either Input or Output"""
        if v not in ["Input", "Output"]:
            raise ValueError("tax_category must be either 'Input' or 'Output'")
        return v


class TaxTemplateCreate(TaxTemplateBase):
    """Schema for creating a new tax template"""

    tax_rules: list[TaxRuleCreate] = Field(default_factory=list)

    @field_validator("tax_rules")
    @classmethod
    def validate_tax_rules(cls, v: list[TaxRuleCreate]) -> list[TaxRuleCreate]:
        """Validate that tax rules have unique sequences"""
        if v:
            sequences = [rule.sequence for rule in v]
            if len(sequences) != len(set(sequences)):
                raise ValueError("Tax rules must have unique sequence numbers")
        return v


class TaxTemplateUpdate(BaseModel):
    """Schema for updating a tax template (all fields optional)"""

    template_name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, max_length=500)
    tax_category: str | None = Field(None, pattern="^(Input|Output)$")
    is_default: bool | None = None
    is_active: bool | None = None
    applicability_rules: dict | None = None
    extra_data: dict | None = None
    tax_rules: list[TaxRuleCreate] | None = None

    @field_validator("tax_category")
    @classmethod
    def validate_tax_category(cls, v: str | None) -> str | None:
        """Validate tax category is either Input or Output"""
        if v is not None and v not in ["Input", "Output"]:
            raise ValueError("tax_category must be either 'Input' or 'Output'")
        return v

    @field_validator("tax_rules")
    @classmethod
    def validate_tax_rules(
        cls, v: list[TaxRuleCreate] | None
    ) -> list[TaxRuleCreate] | None:
        """Validate that tax rules have unique sequences"""
        if v:
            sequences = [rule.sequence for rule in v]
            if len(sequences) != len(set(sequences)):
                raise ValueError("Tax rules must have unique sequence numbers")
        return v


class TaxTemplateResponse(TaxTemplateBase):
    """Schema for tax template response"""

    id: UUID
    organization_id: UUID
    created_by: UUID | None = None
    updated_by: UUID | None = None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None
    tax_rules: list[TaxRuleResponse] = []

    model_config = ConfigDict(from_attributes=True)


class TaxTemplateListItem(BaseModel):
    """Schema for tax template in list response (lighter version)"""

    id: UUID
    organization_id: UUID
    template_code: str
    template_name: str
    tax_category: str
    is_default: bool
    is_active: bool
    tax_rules_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TaxTemplateListResponse(BaseModel):
    """Schema for paginated tax template list response"""

    templates: list[TaxTemplateListItem]
    pagination: PaginationMeta
