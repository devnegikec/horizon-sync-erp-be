"""QR Product Setting model — org-level lookup values for product creation"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text

from app.database import Base
from app.models.types import JSONB, UUID


class QRProductSetting(Base):
    """
    Organization-scoped lookup values used during QR product / block creation.

    setting_type discriminator:
      - serial_prefix   → allowed serial prefixes  (value="PH", label="Pharma")
      - channel         → distribution channels     (value="retail", label="Retail")
      - destination     → destination markets       (value="IN", label="India")
      - shelf_life      → shelf-life options        (value="12", label="12 Months")
    """

    __tablename__ = "qr_product_settings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    setting_type = Column(String(30), nullable=False, index=True)
    value = Column(String(100), nullable=False)
    label = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    sort_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    extra_data = Column(JSONB, nullable=True)

    created_by = Column(UUID(as_uuid=True), nullable=True)
    updated_by = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return (
            f"<QRProductSetting(type='{self.setting_type}', "
            f"value='{self.value}', label='{self.label}')>"
        )
