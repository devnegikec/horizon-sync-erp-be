"""Cascade / Hierarchical QR endpoints"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.schemas.cascade_qr import (
    CascadeHistoryResponse,
    CascadeScanRequest,
    CascadeScanResponse,
    ChildQRCreate,
    ChildQRListResponse,
    LabelDownloadResponse,
    MapQRRequest,
    MapQRResponse,
    ParentQRCreate,
    ParentQRListResponse,
    ParentQRResponse,
)
from app.services.cascade_qr_service import CascadeQRService

router = APIRouter()


def get_service(db: Session = Depends(get_db)) -> CascadeQRService:
    return CascadeQRService(db)


# ── Parent QR ─────────────────────────────────────────────────────────────────

@router.post(
    "/parents",
    response_model=ParentQRResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a parent QR node (e.g. pallet, carton)",
)
def create_parent(
    data: ParentQRCreate,
    service: CascadeQRService = Depends(get_service),
    current_user: dict = Depends(get_current_user),
):
    org_id = UUID(current_user["organization_id"])
    return service.create_parent(data, org_id)


@router.get(
    "/parents",
    response_model=ParentQRListResponse,
    summary="List parent QR nodes",
)
def list_parents(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    qr_type: str | None = Query(None, description="Filter by type: pallet, carton, box, etc."),
    service: CascadeQRService = Depends(get_service),
    current_user: dict = Depends(get_current_user),
):
    org_id = UUID(current_user["organization_id"])
    return service.list_parents(org_id, page, page_size, qr_type)


@router.get(
    "/parents/{node_id}",
    response_model=ParentQRResponse,
    summary="Get a parent QR node",
)
def get_parent(
    node_id: UUID,
    service: CascadeQRService = Depends(get_service),
    current_user: dict = Depends(get_current_user),
):
    org_id = UUID(current_user["organization_id"])
    return service.get_parent(node_id, org_id)


# ── Child QR ──────────────────────────────────────────────────────────────────

@router.post(
    "/parents/{parent_id}/children",
    response_model=ParentQRResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create child QR nodes under a parent",
)
def create_child(
    parent_id: UUID,
    data: ChildQRCreate,
    service: CascadeQRService = Depends(get_service),
    current_user: dict = Depends(get_current_user),
):
    org_id = UUID(current_user["organization_id"])
    return service.create_child(parent_id, data, org_id)


@router.get(
    "/parents/{parent_id}/children",
    response_model=ChildQRListResponse,
    summary="List child QR nodes under a parent",
)
def list_children(
    parent_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    service: CascadeQRService = Depends(get_service),
    current_user: dict = Depends(get_current_user),
):
    org_id = UUID(current_user["organization_id"])
    return service.list_children(parent_id, org_id, page, page_size)


# ── Map QRs ───────────────────────────────────────────────────────────────────

@router.post(
    "/parents/{parent_id}/map",
    response_model=MapQRResponse,
    summary="Map existing child QR nodes to a parent",
)
def map_children(
    parent_id: UUID,
    req: MapQRRequest,
    service: CascadeQRService = Depends(get_service),
    current_user: dict = Depends(get_current_user),
):
    org_id = UUID(current_user["organization_id"])
    return service.map_children(parent_id, req, org_id)


# ── Cascade Scan ──────────────────────────────────────────────────────────────

@router.post(
    "/scan",
    response_model=CascadeScanResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record a cascade QR scan (public — called by QR landing page)",
)
def record_cascade_scan(
    req: CascadeScanRequest,
    organization_id: UUID = Query(...),
    service: CascadeQRService = Depends(get_service),
):
    """No auth required — called from the consumer-facing QR landing page."""
    return service.record_cascade_scan(req, organization_id)


# ── Cascade History ───────────────────────────────────────────────────────────

@router.get(
    "/history",
    response_model=CascadeHistoryResponse,
    summary="Get cascade scan history",
)
def get_scan_history(
    serial_number: str | None = Query(None, description="Filter to a specific node serial"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    service: CascadeQRService = Depends(get_service),
    current_user: dict = Depends(get_current_user),
):
    org_id = UUID(current_user["organization_id"])
    return service.get_scan_history(org_id, serial_number, page, page_size)


# ── Label Download ────────────────────────────────────────────────────────────

@router.get(
    "/parents/{parent_id}/labels",
    response_model=LabelDownloadResponse,
    summary="Download label data for all children of a parent node",
)
def get_labels(
    parent_id: UUID,
    service: CascadeQRService = Depends(get_service),
    current_user: dict = Depends(get_current_user),
):
    org_id = UUID(current_user["organization_id"])
    return service.get_labels(parent_id, org_id)
