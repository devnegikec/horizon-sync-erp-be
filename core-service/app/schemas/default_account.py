"""Default Account related Pydantic schemas"""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DefaultAccountBase(BaseModel):
    """Base default account schema"""

    transaction_type: str = Field(..., min_length=1, max_length=100)
    scenario: str | None = Field(None, max_length=100)
    account_id: UUID = Field(..., description="UUID of the account to use as default")


class DefaultAccountCreate(DefaultAccountBase):
    """Schema for creating a default account mapping"""

    pass


class DefaultAccountUpdate(BaseModel):
    """Schema for updating a default account mapping"""

    account_id: UUID = Field(..., description="UUID of the account to use as default")


class DefaultAccountResponse(BaseModel):
    """Schema for default account response"""

    id: UUID
    organization_id: UUID
    transaction_type: str
    scenario: str | None
    account_id: UUID

    # Include account details for convenience
    account_code: str | None = None
    account_name: str | None = None
    account_type: str | None = None

    model_config = ConfigDict(from_attributes=True)


class DefaultAccountListResponse(BaseModel):
    """Schema for list of default accounts"""

    defaults: list[DefaultAccountResponse]


class DefaultAccountBulkUpdateRequest(BaseModel):
    """Schema for bulk updating default accounts"""

    defaults: list[DefaultAccountCreate] = Field(
        ..., description="List of default account mappings to create or update"
    )


class AccountCodeFormatResponse(BaseModel):
    """Schema for account code format configuration"""

    format_pattern: str = Field(
        ..., description="Regex pattern for account code format"
    )
    example: str | None = Field(None, description="Example of a valid account code")


class AccountCodeFormatUpdateRequest(BaseModel):
    """Schema for updating account code format"""

    format_pattern: str = Field(
        ..., min_length=1, description="Regex pattern for account code format"
    )
