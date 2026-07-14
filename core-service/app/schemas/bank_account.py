"""Bank Account schemas for request/response validation"""

import re
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_serializer, field_validator


class BankAccountBase(BaseModel):
    """Base schema for bank account data"""

    model_config = {"extra": "forbid"}

    # Banking details
    bank_name: str = Field(..., min_length=1, max_length=100, description="Bank name")
    account_holder_name: str = Field(
        ..., min_length=1, max_length=200, description="Account holder name"
    )
    account_number: str = Field(
        ..., min_length=1, max_length=50, description="Bank account number"
    )
    country_code: str = Field(
        ..., min_length=2, max_length=2, description="ISO 3166-1 alpha-2 country code"
    )
    currency: str = Field(
        ..., min_length=3, max_length=3, description="ISO 4217 currency code"
    )
    iban: str | None = Field(None, max_length=34, description="IBAN number")
    swift_code: str | None = Field(None, max_length=11, description="SWIFT/BIC code")
    routing_number: str | None = Field(
        None, max_length=20, description="Routing number (US)"
    )
    branch_name: str | None = Field(
        None, max_length=100, description="Bank branch name"
    )
    branch_code: str | None = Field(None, max_length=20, description="Bank branch code")
    sort_code: str | None = Field(None, max_length=10, description="Sort code (UK)")
    bsb_number: str | None = Field(
        None, max_length=10, description="BSB number (Australia)"
    )
    ifsc_code: str | None = Field(None, max_length=11, description="IFSC code (India)")

    # Account metadata
    account_type: str | None = Field(
        None, max_length=50, description="Account type (checking, savings, etc.)"
    )
    account_purpose: str | None = Field(
        None, max_length=50, description="Account purpose (operating, payroll, etc.)"
    )
    is_primary: bool = Field(
        default=False, description="Is this the primary bank account"
    )
    is_active: bool = Field(default=True, description="Is this bank account active")

    # Banking features
    online_banking_enabled: bool = Field(
        default=False, description="Online banking enabled"
    )
    mobile_banking_enabled: bool = Field(
        default=False, description="Mobile banking enabled"
    )
    wire_transfer_enabled: bool = Field(
        default=False, description="Wire transfer enabled"
    )
    ach_enabled: bool = Field(default=False, description="ACH transfers enabled")

    # Limits and controls
    daily_transfer_limit: float | None = Field(
        None, gt=0, description="Daily transfer limit"
    )
    monthly_transfer_limit: float | None = Field(
        None, gt=0, description="Monthly transfer limit"
    )
    requires_dual_approval: bool = Field(
        default=False, description="Requires dual approval for transactions"
    )

    # Integration settings
    bank_api_enabled: bool = Field(
        default=False, description="Bank API integration enabled"
    )
    sync_frequency: str = Field(
        default="manual", max_length=20, description="Sync frequency"
    )

    @field_validator("iban")
    @classmethod
    def validate_iban(cls, v: str | None) -> str | None:
        """Validate IBAN format"""
        if v:
            # Remove spaces and convert to uppercase
            v = v.replace(" ", "").upper()
            # Basic IBAN format validation (country code + check digits + account identifier)
            if not re.match(r"^[A-Z]{2}[0-9]{2}[A-Z0-9]+$", v):
                raise ValueError(
                    "Invalid IBAN format. Expected format: CC##AAAA... (CC=country, ##=check digits, A=account identifier)"
                )
            # IBAN length validation (varies by country)
            if len(v) < 15 or len(v) > 34:
                raise ValueError("IBAN length must be between 15 and 34 characters")
        return v

    @field_validator("swift_code")
    @classmethod
    def validate_swift(cls, v: str | None) -> str | None:
        """Validate SWIFT/BIC code format"""
        if v:
            v = v.upper().replace(" ", "")
            # SWIFT code format: 4 chars bank code + 2 chars country + 2 chars location + optional 3 chars branch
            if not re.match(r"^[A-Z]{4}[A-Z]{2}[A-Z0-9]{2}([A-Z0-9]{3})?$", v):
                raise ValueError(
                    "Invalid SWIFT code format. Expected format: AAAACCLLBBB (A=bank, C=country, L=location, B=branch)"
                )
        return v

    @field_validator("routing_number")
    @classmethod
    def validate_routing_number(cls, v: str | None) -> str | None:
        """Validate US routing number format"""
        if v:
            v = v.replace(" ", "").replace("-", "")
            if not re.match(r"^[0-9]{9}$", v):
                raise ValueError("Invalid routing number format. Must be 9 digits")
        return v

    @field_validator("sort_code")
    @classmethod
    def validate_sort_code(cls, v: str | None) -> str | None:
        """Validate UK sort code format"""
        if v:
            v = v.replace(" ", "").replace("-", "")
            if not re.match(r"^[0-9]{6}$", v):
                raise ValueError("Invalid sort code format. Must be 6 digits")
        return v

    @field_validator("bsb_number")
    @classmethod
    def validate_bsb_number(cls, v: str | None) -> str | None:
        """Validate Australian BSB number format"""
        if v:
            v = v.replace(" ", "").replace("-", "")
            if not re.match(r"^[0-9]{6}$", v):
                raise ValueError("Invalid BSB number format. Must be 6 digits")
        return v

    @field_validator("ifsc_code")
    @classmethod
    def validate_ifsc_code(cls, v: str | None) -> str | None:
        """Validate Indian IFSC code format"""
        if v:
            v = v.upper().replace(" ", "")
            if not re.match(r"^[A-Z]{4}0[A-Z0-9]{6}$", v):
                raise ValueError(
                    "Invalid IFSC code format. Expected format: AAAA0BBBBBB (A=bank, 0=zero, B=branch)"
                )
        return v

    @field_validator("account_type")
    @classmethod
    def validate_account_type(cls, v: str | None) -> str | None:
        """Validate account type"""
        if v:
            allowed_types = [
                "checking",
                "savings",
                "business",
                "money_market",
                "certificate_deposit",
                "other",
            ]
            if v.lower() not in allowed_types:
                raise ValueError(
                    f"Invalid account type. Allowed values: {', '.join(allowed_types)}"
                )
        return v.lower() if v else v

    @field_validator("account_purpose")
    @classmethod
    def validate_account_purpose(cls, v: str | None) -> str | None:
        """Validate account purpose"""
        if v:
            allowed_purposes = [
                "operating",
                "payroll",
                "tax",
                "petty_cash",
                "investment",
                "escrow",
                "other",
            ]
            if v.lower() not in allowed_purposes:
                raise ValueError(
                    f"Invalid account purpose. Allowed values: {', '.join(allowed_purposes)}"
                )
        return v.lower() if v else v

    @field_validator("sync_frequency")
    @classmethod
    def validate_sync_frequency(cls, v: str) -> str:
        """Validate sync frequency"""
        allowed_frequencies = ["manual", "daily", "weekly", "monthly"]
        if v.lower() not in allowed_frequencies:
            raise ValueError(
                f"Invalid sync frequency. Allowed values: {', '.join(allowed_frequencies)}"
            )
        return v.lower()


class BankAccountCreate(BankAccountBase):
    """Schema for creating a new bank account"""

    pass


class BankAccountUpdate(BaseModel):
    """Schema for updating an existing bank account"""

    # All fields are optional for updates
    bank_name: str | None = Field(None, min_length=1, max_length=100)
    account_holder_name: str | None = Field(None, min_length=1, max_length=200)
    account_number: str | None = Field(None, min_length=1, max_length=50)
    iban: str | None = Field(None, max_length=34)
    swift_code: str | None = Field(None, max_length=11)
    routing_number: str | None = Field(None, max_length=20)
    branch_name: str | None = Field(None, max_length=100)
    branch_code: str | None = Field(None, max_length=20)
    sort_code: str | None = Field(None, max_length=10)
    bsb_number: str | None = Field(None, max_length=10)
    ifsc_code: str | None = Field(None, max_length=11)

    account_type: str | None = Field(None, max_length=50)
    account_purpose: str | None = Field(None, max_length=50)
    is_primary: bool | None = None
    is_active: bool | None = None

    online_banking_enabled: bool | None = None
    mobile_banking_enabled: bool | None = None
    wire_transfer_enabled: bool | None = None
    ach_enabled: bool | None = None

    daily_transfer_limit: float | None = Field(None, gt=0)
    monthly_transfer_limit: float | None = Field(None, gt=0)
    requires_dual_approval: bool | None = None

    bank_api_enabled: bool | None = None
    sync_frequency: str | None = Field(None, max_length=20)


class BankAccountResponse(BankAccountBase):
    """Schema for bank account response (with security masking)"""

    id: UUID
    gl_account_id: UUID
    organization_id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: str
    updated_by: str

    # Override sensitive fields with masking
    @field_serializer("account_number")
    def serialize_account_number(self, value: str) -> str:
        """Mask account number for security"""
        if not value:
            return ""
        if len(value) <= 4:
            return "*" * len(value)
        return "*" * (len(value) - 4) + value[-4:]

    @field_serializer("iban")
    def serialize_iban(self, value: str | None) -> str | None:
        """Mask IBAN for security"""
        if not value:
            return None
        if len(value) <= 8:
            return "*" * len(value)
        return value[:4] + "*" * (len(value) - 8) + value[-4:]

    class Config:
        from_attributes = True


class BankAccountHistoryResponse(BaseModel):
    """Schema for bank account history response"""

    id: UUID
    bank_account_id: UUID
    action_type: str
    old_values: dict | None = None
    new_values: dict | None = None
    changed_by: str
    changed_at: datetime
    reason: str | None = None

    class Config:
        from_attributes = True


class BankingOverviewResponse(BaseModel):
    """Schema for banking overview response"""

    total_bank_accounts: int
    active_bank_accounts: int
    primary_bank_accounts: int
    bank_accounts_by_purpose: dict
    bank_accounts_by_type: dict

    class Config:
        from_attributes = True


class BankAccountListResponse(BaseModel):
    """Schema for paginated bank account list response"""

    items: list[BankAccountResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_previous: bool


class BankAccountInternalResponse(BankAccountBase):
    """Schema for internal bank account response (unmasked for organization's own use)

    This schema is used when displaying the organization's own bank account details
    on documents like invoices, where full account information needs to be shown
    to customers/suppliers for payment purposes.
    """

    id: UUID
    gl_account_id: UUID
    organization_id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: str
    updated_by: str

    # No masking - return full account details
    class Config:
        from_attributes = True


class BankAccountInternalListResponse(BaseModel):
    """Schema for paginated internal bank account list response (unmasked)"""

    items: list[BankAccountInternalResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_previous: bool
