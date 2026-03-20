"""Short URL model"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text

from app.database import Base
from app.models.types import JSONB, UUID


class ShortURL(Base):
    __tablename__ = "short_urls"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    slug = Column(String(20), nullable=False, unique=True, index=True)
    original_url = Column(Text, nullable=False)
    title = Column(String(255), nullable=True)
    product_id = Column(UUID(as_uuid=True), nullable=True)
    product_item_id = Column(UUID(as_uuid=True), nullable=True)
    click_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    extra_data = Column(JSONB, nullable=True)
    created_by = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC),
                        onupdate=lambda: datetime.now(UTC))

    def __repr__(self):
        return f"<ShortURL(slug='{self.slug}', url='{self.original_url[:40]}')>"
