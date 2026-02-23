"""Item Group related Pydantic schemas"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import PaginationMeta


class ItemGroupBase(BaseModel):
    """Base item group schema with common fields"""

    name: str = Field(..., min_length=1, max_length=255)
    code: str = Field(..., min_length=1, max_length=50)
    description: str | None = None

    # Hierarchy
    parent_id: UUID | None = None

    # Defaults
    default_valuation_method: str | None = None
    default_uom: str | None = Field(None, max_length=50)

    # Tax Templates
    sales_tax_template_id: UUID | None = None
    purchase_tax_template_id: UUID | None = None

    # Status
    is_active: bool = True

    # Extra
    extra_data: dict | None = None


class ItemGroupCreate(ItemGroupBase):
    """Schema for creating a new item group"""

    pass


class ItemGroupUpdate(BaseModel):
    """Schema for updating an item group (all fields optional)"""

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None

    # Hierarchy
    parent_id: UUID | None = None

    # Defaults
    default_valuation_method: str | None = None
    default_uom: str | None = Field(None, max_length=50)

    # Tax Templates
    sales_tax_template_id: UUID | None = None
    purchase_tax_template_id: UUID | None = None

    # Status
    is_active: bool | None = None

    # Extra
    extra_data: dict | None = None


class ItemGroupParentInfo(BaseModel):
    """Minimal item group info for nested response (parent reference)"""

    id: UUID
    code: str
    name: str

    model_config = ConfigDict(from_attributes=True)


class TaxRuleBreakup(BaseModel):
    """Individual tax rule within a tax template"""

    rule_name: str
    tax_type: str
    rate: float
    is_compound: bool

    model_config = ConfigDict(from_attributes=True)


class TaxInfo(BaseModel):
    """Tax template info with breakup rules"""

    id: UUID
    template_name: str
    template_code: str
    is_compound: bool
    breakup: list[TaxRuleBreakup]

    model_config = ConfigDict(from_attributes=True)


class ItemGroupResponse(BaseModel):
    """Schema for item group response"""

    id: UUID
    organization_id: UUID
    name: str
    code: str
    description: str | None = None

    # Hierarchy
    parent_id: UUID | None = None
    parent: ItemGroupParentInfo | None = None

    # Defaults
    default_valuation_method: str | None = None
    default_uom: str | None = None

    # Tax Templates
    sales_tax_template_id: UUID | None = None
    purchase_tax_template_id: UUID | None = None

    # Status
    is_active: bool

    # Extra
    extra_data: dict | None = None

    # Audit
    created_by: UUID | None = None
    updated_by: UUID | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ItemGroupListItem(BaseModel):
    """Schema for item group in list response"""

    id: UUID
    name: str
    code: str
    description: str | None = None
    parent_id: UUID | None = None
    parent: ItemGroupParentInfo | None = None
    default_valuation_method: str | None = None
    default_uom: str | None = None
    sales_tax_template_id: UUID | None = None
    purchase_tax_template_id: UUID | None = None
    sales_tax_info: TaxInfo | None = None
    purchase_tax_info: TaxInfo | None = None
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ItemGroupListResponse(BaseModel):
    """Schema for paginated item group list response"""

    item_groups: list[ItemGroupListItem]
    pagination: PaginationMeta


class ItemGroupTreeNode(BaseModel):
    """Schema for item group in tree structure"""

    id: UUID
    name: str
    code: str
    default_valuation_method: str | None = None
    default_uom: str | None = None
    is_active: bool
    children: list["ItemGroupTreeNode"] = []

    model_config = ConfigDict(from_attributes=True)


# Update forward reference for recursive type
ItemGroupTreeNode.model_rebuild()
