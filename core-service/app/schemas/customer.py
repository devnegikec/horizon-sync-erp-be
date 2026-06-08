"""Customer related Pydantic schemas"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import PaginationMeta


class CustomerStatusCounts(BaseModel):
    """Schema for customer status counts"""

    active: int = 0
    inactive: int = 0
    blocked: int = 0
    total: int = 0


class CustomerBase(BaseModel):
    """Base customer schema with common fields"""

    customer_name: str = Field(..., min_length=1, max_length=255)
    customer_code: str | None = Field(None, max_length=50)

    # Contact
    email: str | None = Field(None, max_length=255)
    phone: str | None = Field(None, max_length=50)

    # Address
    address: str | None = Field(None, max_length=1000)
    address_line1: str | None = Field(None, max_length=255)
    address_line2: str | None = Field(None, max_length=255)
    city: str | None = Field(None, max_length=100)
    state: str | None = Field(None, max_length=100)
    postal_code: str | None = Field(None, max_length=20)
    country: str | None = Field(None, max_length=100)

    # Tax
    tax_number: str | None = Field(None, max_length=50)
    is_tax_exempt: bool = False
    tax_exemption_certificate_no: str | None = Field(None, max_length=100)

    # Status
    status: str = Field(default="active")

    # Credit
    credit_limit: Decimal | float = 0
    outstanding_balance: Decimal | float = 0

    # Extra
    tags: list | dict | None = None
    custom_fields: dict | None = None
    extra_data: dict | None = None


class CustomerCreate(CustomerBase):
    """Schema for creating a new customer"""

    pass


class CustomerUpdate(BaseModel):
    """Schema for updating a customer (all fields optional)"""

    customer_name: str | None = Field(None, min_length=1, max_length=255)

    # Contact
    email: str | None = Field(None, max_length=255)
    phone: str | None = Field(None, max_length=50)

    # Address
    address: str | None = Field(None, max_length=1000)
    address_line1: str | None = Field(None, max_length=255)
    address_line2: str | None = Field(None, max_length=255)
    city: str | None = Field(None, max_length=100)
    state: str | None = Field(None, max_length=100)
    postal_code: str | None = Field(None, max_length=20)
    country: str | None = Field(None, max_length=100)

    # Tax
    tax_number: str | None = Field(None, max_length=50)
    is_tax_exempt: bool | None = None
    tax_exemption_certificate_no: str | None = Field(None, max_length=100)

    # Status
    status: str | None = None

    # Credit
    credit_limit: Decimal | float | None = None
    outstanding_balance: Decimal | float | None = None

    # Extra
    tags: list | dict | None = None
    custom_fields: dict | None = None
    extra_data: dict | None = None


class CustomerResponse(BaseModel):
    """Schema for customer response"""

    id: UUID
    organization_id: UUID
    customer_name: str
    customer_code: str

    # Contact
    email: str | None = None
    phone: str | None = None

    # Address
    address: str | None = None
    address_line1: str | None = None
    address_line2: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    country: str | None = None

    # Tax
    tax_number: str | None = None
    is_tax_exempt: bool = False
    tax_exemption_certificate_no: str | None = None

    # Status
    status: str

    # Credit
    credit_limit: Decimal
    outstanding_balance: Decimal

    # Extra
    tags: list | dict | None = None
    custom_fields: dict | None = None
    extra_data: dict | None = None

    # Audit
    created_by: UUID | None = None
    updated_by: UUID | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CustomerListItem(BaseModel):
    """Schema for customer in list response (lighter version)"""

    id: UUID
    customer_name: str
    customer_code: str
    email: str | None = None
    phone: str | None = None
    address: str | None = None
    city: str | None = None
    tax_number: str | None = None
    status: str
    tags: list | dict | None = None
    credit_limit: Decimal
    outstanding_balance: Decimal
    custom_fields: dict | None = None
    extra_data: dict | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CustomerListResponse(BaseModel):
    """Schema for paginated customer list response"""

    customers: list[CustomerListItem]
    pagination: PaginationMeta
    status_counts: CustomerStatusCounts
