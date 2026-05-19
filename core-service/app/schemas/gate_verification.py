"""Pydantic schemas for gate verification endpoints.

Handles the gate verification workflow:
- Start gate verification session linked to a completed pick list
- Record gate scans validating items against the pick list
- Track session progress (scanned vs expected counts)
- Verify/complete gate sessions

Requirements: 12.1, 12.7
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field

# ===========================================
# REQUEST SCHEMAS
# ===========================================


class GateSessionRequest(BaseModel):
    """Request schema for starting a gate verification session.

    Requirements: 12.1
    """

    pick_list_id: UUID = Field(
        ..., description="UUID of the completed pick list to verify against"
    )
    vehicle_number: str | None = Field(
        None, max_length=100, description="Vehicle registration number"
    )
    driver_name: str | None = Field(None, max_length=255, description="Driver name")
    driver_contact: str | None = Field(
        None, max_length=50, description="Driver contact number"
    )


class GateScanRequest(BaseModel):
    """Request schema for recording a gate scan.

    Requirements: 12.2, 12.3
    """

    qr_data: str = Field(
        ..., min_length=1, description="Raw QR code payload string (JSON)"
    )
    device_type: str | None = Field(
        None, max_length=50, description="Device type (e.g., 'mobile', 'tablet')"
    )
    os: str | None = Field(None, max_length=50, description="Operating system info")


# ===========================================
# RESPONSE SCHEMAS
# ===========================================


class GateVerificationItemResponse(BaseModel):
    """Response schema for a single gate verification item."""

    id: str
    qr_identifier: str
    sku: str
    quantity: int
    status: str  # "verified" or "unauthorized"
    scanned_at: str | None = None


class DispatchInfo(BaseModel):
    """Inline dispatch record info returned when a gate session is verified.

    Requirements: 12.6, 13.1
    """

    id: str
    organization_id: str
    dispatch_number: str
    pick_list_id: str
    gate_session_id: str
    invoice_reference: str | None = None
    vehicle_number: str | None = None
    driver_name: str | None = None
    dispatched_at: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class GateSessionResponse(BaseModel):
    """Response schema for a gate verification session.

    Requirements: 12.1, 12.6
    """

    id: str
    organization_id: str
    pick_list_id: str
    warehouse_id: str
    worker_id: str
    vehicle_number: str | None = None
    driver_name: str | None = None
    driver_contact: str | None = None
    status: str
    verified_at: str | None = None
    items: list[GateVerificationItemResponse] = []
    dispatch: DispatchInfo | None = None
    created_at: str | None = None
    updated_at: str | None = None


class GateScanResult(BaseModel):
    """Response schema for a recorded gate scan.

    Requirements: 12.3, 12.4
    """

    gate_item_id: str
    session_id: str
    qr_identifier: str
    sku: str
    quantity: int
    batch: str | None = None
    status: str  # "verified" or "unauthorized"
    scanned_at: str | None = None


class GateSessionProgress(BaseModel):
    """Response schema for gate session progress.

    Requirements: 12.7
    """

    session_id: str
    status: str
    pick_list_id: str
    vehicle_number: str | None = None
    driver_name: str | None = None
    total_scanned: int = Field(
        ..., description="Total number of items scanned at the gate"
    )
    verified_count: int = Field(
        ..., description="Number of items verified against the pick list"
    )
    unauthorized_count: int = Field(
        ..., description="Number of unauthorized items detected"
    )
    verified_qty: int = Field(..., description="Total verified quantity")
    expected_total_qty: int = Field(
        ..., description="Total expected quantity from the pick list"
    )
    all_verified: bool = Field(
        ..., description="Whether all expected items have been verified"
    )
    items: list[GateVerificationItemResponse] = []
