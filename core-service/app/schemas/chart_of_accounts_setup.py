"""Chart of Accounts Setup related Pydantic schemas"""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DefaultChartSetupRequest(BaseModel):
    """Schema for creating default chart of accounts for an organization"""

    organization_id: UUID = Field(..., description="UUID of the organization")
    currency: str = Field(
        default="USD",
        max_length=3,
        description="ISO currency code (3 uppercase letters)",
    )
    created_by: str = Field(
        ..., min_length=1, max_length=100, description="User identifier who created"
    )

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        """Validate currency code format (3 uppercase letters)"""
        if not v or len(v) != 3:
            raise ValueError("Currency must be a 3-letter ISO code")
        if not v.isupper():
            raise ValueError("Currency must be uppercase")
        if not v.isalpha():
            raise ValueError("Currency must contain only letters")
        return v

    @field_validator("created_by")
    @classmethod
    def validate_created_by(cls, v: str) -> str:
        """Validate created_by is not empty or whitespace-only"""
        if not v or not v.strip():
            raise ValueError("created_by cannot be empty or whitespace-only")
        return v.strip()


class DefaultChartSetupResponse(BaseModel):
    """Schema for default chart setup response"""

    success: bool = Field(..., description="Whether the operation succeeded")
    organization_id: UUID = Field(..., description="UUID of the organization")
    accounts_created: int = Field(
        ..., ge=0, description="Number of accounts created"
    )
    mappings_created: int = Field(
        ..., ge=0, description="Number of default account mappings created"
    )
    message: str = Field(..., description="Status message")
    errors: list[str] | None = Field(
        default=None, description="List of errors if operation failed"
    )

    model_config = ConfigDict(from_attributes=True)


class ManualTriggerRequest(BaseModel):
    """Schema for manually triggering default chart creation"""

    currency: str = Field(
        default="USD",
        max_length=3,
        description="ISO currency code (3 uppercase letters)",
    )
    force_recreate: bool = Field(
        default=False,
        description="If True, recreate even if accounts already exist",
    )

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        """Validate currency code format (3 uppercase letters)"""
        if not v or len(v) != 3:
            raise ValueError("Currency must be a 3-letter ISO code")
        if not v.isupper():
            raise ValueError("Currency must be uppercase")
        if not v.isalpha():
            raise ValueError("Currency must contain only letters")
        return v


class DefaultChartResult(BaseModel):
    """Internal model for service layer result"""

    accounts: list[dict] = Field(
        default_factory=list, description="List of created accounts"
    )
    mappings: list[dict] = Field(
        default_factory=list, description="List of created default account mappings"
    )
    already_existed: bool = Field(
        default=False, description="Whether the chart already existed"
    )

    model_config = ConfigDict(from_attributes=True)
