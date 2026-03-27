"""Organization related database models"""

import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, String, Text, Uuid, Integer
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.base import OrganizationStatus, OrganizationType, BillingStatus


class Organization(Base):
    """Organization model"""

    __tablename__ = "organizations"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    display_name = Column(String(255))
    description = Column(Text)

    # Contact information
    email = Column(String(255))
    phone = Column(String(20))
    website = Column(String(255))

    # Address
    address_line1 = Column(String(255))
    address_line2 = Column(String(255))
    city = Column(String(100))
    state = Column(String(100))
    postal_code = Column(String(20))
    country = Column(String(100))

    # Organization details
    organization_type = Column(
        SQLEnum(OrganizationType, values_callable=lambda x: [e.value for e in x]),
        default=OrganizationType.BUSINESS,
    )
    industry = Column(String(100))
    tax_id = Column(String(100))
    base_currency = Column(String(3), default="USD", nullable=False)  # ISO 4217 currency code

    # Branding
    logo_url = Column(String(500))
    primary_color = Column(String(7))

    # Domain and SSO
    domain = Column(String(255))
    sso_enabled = Column(Boolean, default=False)
    sso_provider = Column(String(50))
    sso_config = Column(JSON)

    # Status
    status = Column(
        SQLEnum(OrganizationStatus, values_callable=lambda x: [e.value for e in x]),
        default=OrganizationStatus.ACTIVE,
        nullable=False,
    )
    is_active = Column(Boolean, default=True, nullable=False)

    # Billing and Subscription fields (Task 1A-2) - Match actual DB schema
    billing_status = Column(
        SQLEnum(BillingStatus, values_callable=lambda x: [e.value for e in x]),
        nullable=True,  # Database allows NULL
    )
    subscription_start_date = Column(DateTime(timezone=False))  # Database uses date type
    subscription_end_date = Column(DateTime(timezone=False))    # Database uses date type
    trial_end_date = Column(DateTime(timezone=False))           # Additional field in DB
    max_users = Column(Integer, nullable=True)                  # Database column name
    max_credits = Column(Integer, nullable=True)                # Database column name
    billing_contact_email = Column(String(255))                 # Additional field in DB
    billing_cycle = Column(String(20))                          # Additional field in DB
    customer_since = Column(DateTime(timezone=True))           # Additional field in DB
    last_billed_date = Column(DateTime(timezone=False))        # Additional field in DB
    next_billing_date = Column(DateTime(timezone=False))       # Additional field in DB
    
    # Parent organization support (for hierarchical structures)
    parent_organization_id = Column(Uuid, ForeignKey("organizations.id"), nullable=True)

    # Owner
    owner_id = Column(Uuid, ForeignKey("users.id"))

    # Metadata
    settings = Column(JSON, default={})
    extra_data = Column(JSON, default={})
    deleted_at = Column(DateTime(timezone=True))
    created_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    roles = relationship(
        "Role", back_populates="organization", cascade="all, delete-orphan"
    )
    user_organization_roles = relationship(
        "UserOrganizationRole",
        back_populates="organization",
        cascade="all, delete-orphan",
    )
    invitations = relationship(
        "Invitation", back_populates="organization", cascade="all, delete-orphan"
    )
