"""Chart of Account related Pydantic schemas"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.common import PaginationMeta


class ChartOfAccountBase(BaseModel):
    """Base chart of account schema with common fields"""

    account_code: str = Field(..., min_length=1, max_length=50)
    account_name: str = Field(..., min_length=1, max_length=200)
    account_type: str = Field(
        ...,
        min_length=1,
        description="asset, liability, equity, income, expense",
    )
    organization_id: UUID

    @field_validator('account_code', 'account_name', 'account_type')
    @classmethod
    def validate_not_whitespace(cls, v: str) -> str:
        """Validate that string fields are not empty or whitespace-only"""
        if not v or not v.strip():
            raise ValueError('Field cannot be empty or whitespace-only')
        return v

    # Hierarchy
    parent_account_id: UUID | None = None
    
    # Currency
    currency: str = Field(default="USD", max_length=3)
    
    # Status
    status: str = Field(default="active")
    
    # Posting Configuration
    is_posting_account: bool = True
    
    # Description
    description: str | None = None


class ChartOfAccountCreate(ChartOfAccountBase):
    """Schema for creating a new chart of account"""

    pass


class ChartOfAccountUpdate(BaseModel):
    """Schema for updating a chart of account (all fields optional)"""

    account_name: str | None = Field(None, min_length=1, max_length=200)
    
    # Hierarchy
    parent_account_id: UUID | None = None
    
    # Currency
    currency: str | None = Field(None, max_length=3)
    
    # Status
    status: str | None = None
    
    # Posting Configuration
    is_posting_account: bool | None = None
    
    # Description
    description: str | None = None


class ChartOfAccountParentInfo(BaseModel):
    """Minimal chart of account info for nested response (parent reference)"""

    id: UUID
    account_code: str
    account_name: str

    model_config = ConfigDict(from_attributes=True)


class ChartOfAccountResponse(BaseModel):
    """Schema for chart of account response"""

    id: UUID
    organization_id: UUID
    account_code: str
    account_name: str
    account_type: str

    # Hierarchy
    parent_account_id: UUID | None = None
    parent: ChartOfAccountParentInfo | None = None
    
    # Currency
    currency: str
    
    # Status
    status: str
    
    # Posting Configuration
    is_posting_account: bool
    
    # Description
    description: str | None = None

    # Audit
    created_by: str
    updated_by: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChartOfAccountListItem(BaseModel):
    """Schema for chart of account in list response (lighter version)"""

    id: UUID
    organization_id: UUID
    account_code: str
    account_name: str
    account_type: str
    parent_account_id: UUID | None = None
    currency: str
    status: str
    is_posting_account: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChartOfAccountListResponse(BaseModel):
    """Schema for paginated chart of account list response"""

    chart_of_accounts: list[ChartOfAccountListItem]
    pagination: PaginationMeta


class ChartOfAccountTreeNode(BaseModel):
    """Schema for chart of account in tree structure"""

    id: UUID
    account_code: str
    account_name: str
    account_type: str
    status: str
    is_posting_account: bool
    children: list["ChartOfAccountTreeNode"] = []

    model_config = ConfigDict(from_attributes=True)


# Update forward reference for recursive type
ChartOfAccountTreeNode.model_rebuild()
