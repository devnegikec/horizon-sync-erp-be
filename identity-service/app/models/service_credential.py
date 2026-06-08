"""Service credential model for machine-to-machine authentication.

Concept: When ai-service (or any future service) needs to call core-service,
it must prove its identity. Instead of a human login, it presents a
client_id + client_secret. This model stores the hashed secret and the
permissions that service is allowed to have.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, Column, DateTime, Index, String, Uuid, JSON

from app.database import Base


class ServiceCredential(Base):
    """Machine-to-machine service credential.

    Each row represents an authorized service client (e.g. ai-service).
    The client_secret is stored as a bcrypt hash (never plaintext).
    """

    __tablename__ = "service_credentials"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    client_id = Column(String(255), unique=True, nullable=False, index=True)
    client_secret_hash = Column(String(255), nullable=False)
    service_name = Column(String(255), nullable=False)
    permissions = Column(JSON, nullable=False, default=list)
    scopes = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
    last_used_at = Column(DateTime(timezone=True))

    __table_args__ = (
        Index("ix_service_credentials_active", "is_active", "client_id"),
    )
