"""Chart of Account related Pydantic schemas"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import PaginationMeta


class ChartOfAccountBase(BaseModel):
    """Base chart of account schema with common fields"""

    account_code: str = Field(..., min_length=1, max_length=50)
    account_name: str = Field(..., min_length=1, max_length=255)
    account_type: str = Field(
        ...,
        description="asset, liability, equity, income, expense",
    )

    # Hierarchy
    parent_account_id: UUID | None = None
    level: int = Field(default=1, ge=1)
    is_group: bool = False

    # Balances
    opening_balance: Decimal | float = 0
    current_balance: Decimal | float = 0

    # Status
    is_active: bool = True

    # Extra
    tags: list | dict | None = None
    extra_data: dict | None = None


class ChartOfAccountCreate(ChartOfAccountBase):
    """Schema for creating a new chart of account"""

    pass


class ChartOfAccountUpdate(BaseModel):
    """Schema for updating a chart of account (all fields optional)"""

    account_name: str | None = Field(None, min_length=1, max_length=255)
    account_type: str | None = None

    # Hierarchy
    parent_account_id: UUID | None = None
    level: int | None = Field(None, ge=1)
    is_group: bool | None = None

    # Balances
    opening_balance: Decimal | float | None = None
    current_balance: Decimal | float | None = None

    # Status
    is_active: bool | None = None

    # Extra
    tags: list | dict | None = None
    extra_data: dict | None = None


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
    level: int
    is_group: bool

    # Balances
    opening_balance: Decimal
    current_balance: Decimal

    # Status
    is_active: bool

    # Extra
    tags: list | dict | None = None
    extra_data: dict | None = None

    # Audit
    created_by: UUID | None = None
    updated_by: UUID | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChartOfAccountListItem(BaseModel):
    """Schema for chart of account in list response (lighter version)"""

    id: UUID
    account_code: str
    account_name: str
    account_type: str
    parent_account_id: UUID | None = None
    level: int
    is_group: bool
    is_active: bool
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
    level: int
    is_group: bool
    is_active: bool
    children: list["ChartOfAccountTreeNode"] = []

    model_config = ConfigDict(from_attributes=True)


# Update forward reference for recursive type
ChartOfAccountTreeNode.model_rebuild()
