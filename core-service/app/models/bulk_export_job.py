"""Bulk Export Job model definition"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, String, Text
from app.models.types import UUID

from app.database import Base
from app.models.types import JSONB


class BulkExportJobStatus:
    """Enum for bulk export job statuses"""

    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class BulkExportJob(Base):
    """Model for tracking bulk item export jobs"""

    __tablename__ = "bulk_export_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    created_by_id = Column(UUID(as_uuid=True), nullable=False)

    # File Information
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(255), nullable=True)
    file_format = Column(String(20), nullable=False)  # csv, xlsx, json

    # Job Status
    status = Column(
        String(20),
        nullable=False,
        default=BulkExportJobStatus.PENDING,
        index=True,
    )

    # Statistics
    total_rows = Column(String(20), default="0")

    # Filter Information (store the filters used for export)
    filters = Column(JSONB, nullable=True)

    # Column Selection
    selected_columns = Column(JSONB, nullable=True)

    # Error Details
    error_message = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
    completed_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
