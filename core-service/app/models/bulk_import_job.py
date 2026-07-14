"""Bulk Import Job model definition"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, Integer, String, Text

from app.database import Base
from app.models.types import JSONB, UUID


class BulkImportJobStatus:
    """Enum for bulk import job statuses"""

    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class BulkImportJob(Base):
    """Model for tracking bulk item import jobs"""

    __tablename__ = "bulk_import_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    created_by_id = Column(UUID(as_uuid=True), nullable=False)

    # File Information
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(255), nullable=True)
    mime_type = Column(String(100), nullable=False)

    # Job Status
    status = Column(
        String(20),
        nullable=False,
        default=BulkImportJobStatus.PENDING,
        index=True,
    )

    # Statistics
    total_rows = Column(Integer, default=0)
    successful_rows = Column(Integer, default=0)
    failed_rows = Column(Integer, default=0)

    # Error Details (JSONB for storing row-wise errors)
    error_details = Column(JSONB, nullable=True)

    # Summary information
    summary = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
    completed_at = Column(DateTime(timezone=True), nullable=True)
