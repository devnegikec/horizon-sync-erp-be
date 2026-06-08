"""DiscrepancyAlert and DiscrepancyFeedback models for anomaly detection.

Tracks real-time alerts when receiving patterns deviate from norms,
and operator feedback for model retraining.
"""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Enum, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.database import Base


class AlertStatus(str, enum.Enum):
    """Lifecycle of a discrepancy alert."""
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    FALSE_POSITIVE = "false_positive"
    ESCALATED = "escalated"


class AlertSeverity(str, enum.Enum):
    """Severity classification."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class DiscrepancyAlert(Base):
    """An alert generated when an anomaly is detected during receiving."""

    __tablename__ = "discrepancy_alerts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Link to scan session / ASN
    scan_session_id = Column(UUID(as_uuid=True), nullable=True)
    asn_order_id = Column(UUID(as_uuid=True), nullable=True)
    asn_order_number = Column(String(100), nullable=True)

    # Scope
    organization_id = Column(UUID(as_uuid=True), nullable=True)
    warehouse_id = Column(UUID(as_uuid=True), nullable=True)

    # Detection metadata
    anomaly_score = Column(Float, nullable=False)
    severity = Column(Enum(AlertSeverity), nullable=False, default=AlertSeverity.MEDIUM)
    alert_type = Column(String(50), nullable=True)  # short | excess | damaged | pattern_anomaly
    suggested_action = Column(Text, nullable=True)

    # Feature snapshot (for debugging / retraining)
    feature_vector = Column(JSONB, nullable=True)

    # Status
    status = Column(Enum(AlertStatus), nullable=False, default=AlertStatus.OPEN)
    acknowledged_by = Column(UUID(as_uuid=True), nullable=True)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class DiscrepancyFeedback(Base):
    """Operator feedback on whether an alert was a true or false positive."""

    __tablename__ = "discrepancy_feedback"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    alert_id = Column(UUID(as_uuid=True), nullable=False)

    # Feedback
    is_true_positive = Column(String(20), nullable=False)  # true_positive | false_positive | unsure
    operator_notes = Column(Text, nullable=True)
    operator_user_id = Column(UUID(as_uuid=True), nullable=True)

    # If TP: what was the actual discrepancy type?
    actual_discrepancy_type = Column(String(50), nullable=True)  # short | excess | damaged | other
    actual_variance_qty = Column(Integer, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
