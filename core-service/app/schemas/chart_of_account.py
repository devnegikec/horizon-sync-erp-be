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

    @field_validator('account_code', 'account_name')
    @classmethod
    def validate_not_whitespace(cls, v: str) -> str:
        """Validate that string fields are not empty or whitespace-only"""
        if not v or not v.strip():
            raise ValueError('Field cannot be empty or whitespace-only')
        return v
    
    @field_validator('account_type')
    @classmethod
    def validate_account_type(cls, v: str) -> str:
        """Validate and normalize account type to lowercase"""
        if not v or not v.strip():
            raise ValueError('Account type cannot be empty or whitespace-only')
        # Convert to lowercase to match database enum
        return v.strip().lower()

    # Hierarchy
    parent_account_id: UUID | None = None
    
    # Currency
    currency: str = Field(default="USD", max_length=3)
    
    # Status
    status: str = Field(default="active")
    
    @field_validator('status')
    @classmethod
    def validate_status(cls, v: str) -> str:
        """Validate and normalize status to lowercase"""
        if v:
            return v.strip().lower()
        return "active"
    
    # Posting Configuration
    is_posting_account: bool = True
    
    # Description
    description: str | None = None


class ChartOfAccountCreate(ChartOfAccountBase):
    """Schema for creating a new chart of account"""

    pass


class ChartOfAccountUpdate(BaseModel):
    """Schema for updating a chart of account (all fields optional)"""

    account_name: str | None = Field(None, min_length=1)
    
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
    parent: ChartOfAccountParentInfo | None = Field(default=None, validation_alias="parent_account")
    
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


class ChartOfAccountHierarchyResponse(BaseModel):
    """Schema for account hierarchy response"""

    account: ChartOfAccountResponse
    ancestors: list[ChartOfAccountParentInfo]
    children: list[ChartOfAccountParentInfo]
    descendants_count: int

    model_config = ConfigDict(from_attributes=True)


class ChartOfAccountMoveParentRequest(BaseModel):
    """Schema for moving account to new parent"""

    new_parent_id: UUID = Field(..., description="New parent account UUID")


# Update forward reference for recursive type
ChartOfAccountTreeNode.model_rebuild()


# Balance schemas

class AccountBalanceResponse(BaseModel):
    """Schema for account balance response"""
    
    account_id: str
    currency: str
    debit_total: float
    credit_total: float
    balance: float
    base_currency_balance: float
    as_of_date: str
    account_type: str
    account_code: str
    account_name: str
    is_consolidated: bool = False
    child_count: int = 0
    
    model_config = ConfigDict(from_attributes=True)


class AccountBalancesRequest(BaseModel):
    """Schema for requesting multiple account balances"""
    
    account_ids: list[UUID] = Field(..., description="List of account UUIDs")
    as_of_date: str | None = Field(None, description="Date to calculate balances as of (YYYY-MM-DD)")


class AccountBalancesResponse(BaseModel):
    """Schema for multiple account balances response"""
    
    balances: list[AccountBalanceResponse]


class AccountBalanceHistoryResponse(BaseModel):
    """Schema for account balance history response"""
    
    account_id: str
    start_date: str
    end_date: str
    history: list[AccountBalanceResponse]
