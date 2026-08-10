"""Discrepancy detection API endpoints for ai-service.

Real-time anomaly detection on receiving scan events + feedback loop.
"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.discrepancy_alert import (
    AlertSeverity,
    AlertStatus,
    DiscrepancyAlert,
    DiscrepancyFeedback,
)
from app.services.anomaly_engine import get_anomaly_engine

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/detect", tags=["discrepancy-detection"])


# ── Schemas ──────────────────────────────────────────────────────────────
class DetectRequest(BaseModel):
    scan_session_id: Optional[UUID] = Field(None, description="UUID of the scan session")
    asn_order_id: Optional[UUID] = Field(None, description="Linked ASN order")
    asn_order_number: Optional[str] = Field(None, description="ASN order number")
    expected_qty: float = Field(0, description="Expected quantity from ASN")
    scanned_qty: float = Field(0, description="Actual scanned quantity")
    item_category: Optional[str] = Field(None, description="Item category code")
    supplier_id: Optional[str] = Field(None, description="Supplier UUID or code")
    dock_location: Optional[str] = Field(None, description="Dock / gate location")
    vehicle_type: Optional[str] = Field(None, description="Vehicle type")
    operator_tenure_days: Optional[float] = Field(0, description="Days since operator joined")
    asn_line_count: Optional[int] = Field(1, description="Number of lines on ASN")
    avg_line_qty: Optional[float] = Field(None, description="Average line quantity")
    scan_timestamp: Optional[str] = Field(None, description="ISO timestamp of scan event")
    organization_id: Optional[UUID] = Field(None, description="Organization scope")
    warehouse_id: Optional[UUID] = Field(None, description="Warehouse scope")
    alert_type: Optional[str] = Field("pattern_anomaly", description="short | excess | damaged | pattern_anomaly")


class DetectResponse(BaseModel):
    anomaly_score: float
    is_anomaly: bool
    severity: str
    confidence: float
    alert_id: Optional[UUID]
    suggested_action: Optional[str]
    feature_vector: Optional[dict]


class FeedbackRequest(BaseModel):
    alert_id: UUID
    is_true_positive: str = Field(..., pattern="^(true_positive|false_positive|unsure)$")
    operator_notes: Optional[str] = None
    operator_user_id: Optional[UUID] = None
    actual_discrepancy_type: Optional[str] = Field(None, pattern="^(short|excess|damaged|other)$")
    actual_variance_qty: Optional[int] = None


class AlertResponse(BaseModel):
    id: UUID
    status: str
    severity: str
    alert_type: Optional[str]
    anomaly_score: float
    suggested_action: Optional[str]
    created_at: str


class AlertListResponse(BaseModel):
    items: list[AlertResponse]
    total: int


# ── Endpoints ──────────────────────────────────────────────────────────────
@router.post(
    "/discrepancy",
    response_model=DetectResponse,
    status_code=status.HTTP_200_OK,
    summary="Detect discrepancy risk from a receiving scan event",
)
async def detect_discrepancy(
    request: DetectRequest = Body(...),
    db: Session = Depends(get_db),
):
    """Submit a receiving scan event and get an anomaly assessment.

    If the event is anomalous, a DiscrepancyAlert is created and its ID is returned.
    """
    engine = get_anomaly_engine()

    # Build scan_data dict for the anomaly engine
    scan_data = request.model_dump(exclude_none=True)

    try:
        result = await engine.detect(
            scan_data=scan_data,
            db=db,
            organization_id=request.organization_id,
            warehouse_id=request.warehouse_id,
        )
    except Exception as e:
        logger.exception("Discrepancy detection failed")
        raise HTTPException(status_code=500, detail=f"Detection error: {e}")

    return DetectResponse(
        anomaly_score=result["anomaly_score"],
        is_anomaly=result["is_anomaly"],
        severity=result["severity"],
        confidence=result["confidence"],
        alert_id=result.get("alert_id"),
        suggested_action=result.get("suggested_action"),
        feature_vector=result.get("feature_vector"),
    )


@router.post("/feedback", status_code=status.HTTP_201_CREATED)
async def submit_feedback(
    request: FeedbackRequest = Body(...),
    db: Session = Depends(get_db),
):
    """Submit operator feedback on a discrepancy alert (TP / FP).

    Used for weekly model retraining.
    """
    # Verify alert exists
    alert = db.query(DiscrepancyAlert).filter(DiscrepancyAlert.id == request.alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    feedback = DiscrepancyFeedback(
        alert_id=request.alert_id,
        is_true_positive=request.is_true_positive,
        operator_notes=request.operator_notes,
        operator_user_id=request.operator_user_id,
        actual_discrepancy_type=request.actual_discrepancy_type,
        actual_variance_qty=request.actual_variance_qty,
    )
    db.add(feedback)

    # Update alert status based on feedback
    if request.is_true_positive == "true_positive":
        alert.status = AlertStatus.RESOLVED
    elif request.is_true_positive == "false_positive":
        alert.status = AlertStatus.FALSE_POSITIVE

    db.commit()
    logger.info("Feedback recorded for alert %s: %s", request.alert_id, request.is_true_positive)

    return {"message": "Feedback recorded", "feedback_id": str(feedback.id)}


@router.get("/alerts", response_model=AlertListResponse)
async def list_alerts(
    organization_id: Optional[UUID] = Query(None),
    warehouse_id: Optional[UUID] = Query(None),
    status: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """List discrepancy alerts with optional filters."""
    query = db.query(DiscrepancyAlert)

    if organization_id:
        query = query.filter(DiscrepancyAlert.organization_id == organization_id)
    if warehouse_id:
        query = query.filter(DiscrepancyAlert.warehouse_id == warehouse_id)
    if status:
        query = query.filter(DiscrepancyAlert.status == status)
    if severity:
        query = query.filter(DiscrepancyAlert.severity == severity)

    total = query.count()
    alerts = (
        query.order_by(DiscrepancyAlert.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return AlertListResponse(
        items=[
            AlertResponse(
                id=a.id,
                status=a.status.value,
                severity=a.severity.value,
                alert_type=a.alert_type,
                anomaly_score=a.anomaly_score,
                suggested_action=a.suggested_action,
                created_at=a.created_at.isoformat() if a.created_at else "",
            )
            for a in alerts
        ],
        total=total,
    )


@router.get("/alerts/{alert_id}")
async def get_alert(
    alert_id: UUID,
    db: Session = Depends(get_db),
):
    """Get a single alert with its feature vector and feedback."""
    alert = db.query(DiscrepancyAlert).filter(DiscrepancyAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    feedback = (
        db.query(DiscrepancyFeedback)
        .filter(DiscrepancyFeedback.alert_id == alert_id)
        .all()
    )

    return {
        "id": alert.id,
        "status": alert.status.value,
        "severity": alert.severity.value,
        "anomaly_score": alert.anomaly_score,
        "alert_type": alert.alert_type,
        "suggested_action": alert.suggested_action,
        "feature_vector": alert.feature_vector,
        "created_at": alert.created_at.isoformat() if alert.created_at else None,
        "feedback": [
            {
                "is_true_positive": f.is_true_positive,
                "operator_notes": f.operator_notes,
                "created_at": f.created_at.isoformat() if f.created_at else None,
            }
            for f in feedback
        ],
    }
