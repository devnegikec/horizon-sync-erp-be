"""IngestionJob model for ASN document ingestion pipeline."""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Column, DateTime, Enum, Float, String, Text
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class IngestionStatus(str, enum.Enum):
    """Pipeline status for an ingestion job."""
    PENDING = "pending"
    PARSING = "parsing"
    EXTRACTING = "extracting"
    VALIDATING = "validating"
    DRAFT_CREATED = "draft_created"
    MANUAL_REVIEW = "manual_review"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    FAILED = "failed"


class AsnSourceType(str, enum.Enum):
    """How the ASN data arrived."""
    DOCUMENT_UPLOAD = "document_upload"      # PDF / Excel / image / email
    MANUAL_ENTRY = "manual_entry"            # Warehouse operator typed it in
    SUPPLIER_API = "supplier_api"            # EDI / webhook / API push from supplier
    INTERNAL_TRANSFER = "internal_transfer"  # DC-to-DC transfer
    CUSTOMER_RETURN = "customer_return"      # Customer return inbound


class IngestionJob(Base):
    """Tracks a single ASN document through the ingestion pipeline."""

    __tablename__ = "ingestion_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # File metadata
    original_filename = Column(String(255), nullable=False)
    stored_path = Column(String(500), nullable=True)  # local path or S3/MinIO key
    file_type = Column(String(50), nullable=True)  # pdf, xlsx, png, jpg, email

    # Pipeline status
    status = Column(Enum(IngestionStatus), default=IngestionStatus.PENDING, nullable=False)
    status_message = Column(Text, nullable=True)

    # Parsed raw text from document
    raw_text = Column(Text, nullable=True)

    # LLM extracted structured JSON
    extracted_json = Column(JSON, nullable=True)
    confidence_score = Column(Float, nullable=True)
    low_confidence_fields = Column(JSON, default=list)

    # Validation results
    validation_errors = Column(JSON, default=list)
    matched_supplier_id = Column(UUID(as_uuid=True), nullable=True)

    # Draft ASN created in core-service
    draft_asn_order_id = Column(UUID(as_uuid=True), nullable=True)
    draft_asn_order_number = Column(String(100), nullable=True)

    # Document classification (asn | quotation | pro_forma_invoice | commercial_invoice | packing_list | unknown)
    document_type = Column(String(50), nullable=True)
    rejection_reason = Column(Text, nullable=True)

    # How the ASN arrived (document_upload | manual_entry | supplier_api | internal_transfer | customer_return)
    source_type = Column(Enum(AsnSourceType), default=AsnSourceType.DOCUMENT_UPLOAD, nullable=False)

    # Human-in-the-loop review
    reviewer_user_id = Column(UUID(as_uuid=True), nullable=True)
    review_notes = Column(Text, nullable=True)

    # Who created this job (operator for manual entry, system for webhooks)
    created_by_user_id = Column(UUID(as_uuid=True), nullable=True)

    # Organization / warehouse context
    organization_id = Column(UUID(as_uuid=True), nullable=True)
    warehouse_id = Column(UUID(as_uuid=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime(timezone=True), nullable=True)
