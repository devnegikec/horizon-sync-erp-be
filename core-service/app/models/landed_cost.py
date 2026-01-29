"""Landed cost voucher model (header)"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, Enum, String, Text
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base
from app.models.base import DocumentStatus
from app.models.types import JSONB


class LandedCostVoucher(Base):
    __tablename__ = "landed_cost_vouchers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    voucher_no = Column(String(100), nullable=False)
    posting_date = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    status = Column(
        Enum(
            DocumentStatus,
            name="documentstatus",
            create_type=False,
            values_callable=lambda o: [e.value for e in o],
        ),
        default=DocumentStatus.DRAFT,
        nullable=False,
    )
    remarks = Column(Text, nullable=True)
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    extra_data = Column(JSONB, nullable=True)
    created_by = Column(UUID(as_uuid=True), nullable=True)
    updated_by = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
