"""Organization related database models"""

import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, String, Text, Uuid
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.base import OrganizationStatus, OrganizationType


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
