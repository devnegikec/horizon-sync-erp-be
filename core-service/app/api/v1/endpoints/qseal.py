"""QSeal endpoints — hierarchical parent-child QSeal management"""

from io import BytesIO
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentUser, get_current_user, require_permission
from app.schemas.qseal import (
    QSealAggregationResponse,
    QSealAutoLinkRequest,
    QSealAutoLinkResponse,
    QSealChildCreate,
    QSealChildListResponse,
    QSealHistoryResponse,
    QSealLabelDownloadResponse,
    QSealMapRequest,
    QSealMapResponse,
    QSealParentCreate,
    QSealParentDetailResponse,
    QSealParentListResponse,
    QSealParentResponse,
    QSealScanRequest,
    QSealScanResponse,
)
from app.services.qseal_service import QSealService

router = APIRouter()


def get_service(db: Session = Depends(get_db)) -> QSealService:
    return QSealService(db)


# ── Parent QSeal ──────────────────────────────────────────────────────────────


@router.post(
    "/parents",
    response_model=QSealParentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a parent QSeal node (e.g. pallet, container)",
)
def create_parent(
    data: QSealParentCreate,
    service: QSealService = Depends(get_service),
    current_user: dict = Depends(get_current_user),
):
    org_id = current_user.organization_id
    return service.create_parent(data, org_id)


@router.get(
    "/parents",
    response_model=QSealParentListResponse,
    summary="List parent QSeal nodes",
)
def list_parents(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    qseal_type: str | None = Query(
        None, description="Filter by type: shipper, pallet, container"
    ),
    service: QSealService = Depends(get_service),
    current_user: dict = Depends(get_current_user),
):
    org_id = current_user.organization_id
    return service.list_parents(org_id, page, page_size, qseal_type)


@router.get(
    "/parents/{node_id}",
    response_model=QSealParentResponse,
    summary="Get a parent QSeal node",
)
def get_parent(
    node_id: UUID,
    service: QSealService = Depends(get_service),
    current_user: dict = Depends(get_current_user),
):
    org_id = current_user.organization_id
    return service.get_parent(node_id, org_id)


# ── Child QSeal ───────────────────────────────────────────────────────────────


@router.post(
    "/parents/{parent_id}/children",
    response_model=QSealParentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create child QSeal nodes under a parent",
)
def create_child(
    parent_id: UUID,
    data: QSealChildCreate,
    service: QSealService = Depends(get_service),
    current_user: dict = Depends(get_current_user),
):
    org_id = current_user.organization_id
    return service.create_child(parent_id, data, org_id)


@router.get(
    "/parents/{parent_id}/children",
    response_model=QSealChildListResponse,
    summary="List child QSeal nodes under a parent",
)
def list_children(
    parent_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    service: QSealService = Depends(get_service),
    current_user: dict = Depends(get_current_user),
):
    org_id = current_user.organization_id
    return service.list_children(parent_id, org_id, page, page_size)


# ── Map QSeals ────────────────────────────────────────────────────────────────


@router.post(
    "/parents/{parent_id}/map",
    response_model=QSealMapResponse,
    summary="Map existing child QSeal nodes to a parent",
)
def map_children(
    parent_id: UUID,
    req: QSealMapRequest,
    service: QSealService = Depends(get_service),
    current_user: dict = Depends(get_current_user),
):
    org_id = current_user.organization_id
    return service.map_children(parent_id, req, org_id)


# ── QSeal Scan ────────────────────────────────────────────────────────────────


@router.post(
    "/scan",
    response_model=QSealScanResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record a QSeal scan (public — called by QSeal landing page)",
)
def record_scan(
    req: QSealScanRequest,
    organization_id: UUID = Query(...),
    service: QSealService = Depends(get_service),
):
    """No auth required — called from the consumer-facing QSeal landing page."""
    return service.record_scan(req, organization_id)


# ── QSeal History ─────────────────────────────────────────────────────────────


@router.get(
    "/history",
    response_model=QSealHistoryResponse,
    summary="Get QSeal scan history",
)
def get_scan_history(
    serial_number: str | None = Query(
        None, description="Filter to a specific node serial"
    ),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    service: QSealService = Depends(get_service),
    current_user: dict = Depends(get_current_user),
):
    org_id = current_user.organization_id
    return service.get_scan_history(org_id, serial_number, page, page_size)


# ── Label Download ────────────────────────────────────────────────────────────


@router.get(
    "/parents/{parent_id}/labels",
    response_model=QSealLabelDownloadResponse,
    summary="Download label data for all children of a parent node",
)
def get_labels(
    parent_id: UUID,
    service: QSealService = Depends(get_service),
    current_user: dict = Depends(get_current_user),
):
    org_id = current_user.organization_id
    return service.get_labels(parent_id, org_id)


# ── Parent with Linked Units (for inbound/receiving) ─────────────────────────


@router.get(
    "/parents/{parent_id}/linked-units",
    response_model=QSealParentDetailResponse,
    summary="Get parent QSeal with all linked child units (for inbound scanning)",
)
def get_parent_linked_units(
    parent_id: UUID,
    service: QSealService = Depends(get_service),
    current_user: dict = Depends(get_current_user),
):
    """Returns parent node + all QSealParameters children linked to it.

    Mobile app flow: scan parent QR → get serial → resolve node ID →
    call this endpoint → show all linked units → create receiving slip.
    """
    org_id = current_user.organization_id
    return service.get_parent_with_linked_units(parent_id, org_id)


# ── Block-based Parent QSeal ──────────────────────────────────────────────────


@router.get(
    "/blocks/{block_id}/parents",
    summary="List QSeal parent nodes created for a QR block's master packs",
)
def get_block_parents(
    block_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    service: QSealService = Depends(get_service),
    current_user: dict = Depends(get_current_user),
):
    org_id = current_user.organization_id
    return service.get_parents_by_block(block_id, org_id, page, page_size)


@router.get(
    "/blocks/{block_id}/parents/download",
    summary="Download Excel file with parent QSeal QR codes for a block",
)
def download_block_parents(
    block_id: UUID,
    service: QSealService = Depends(get_service),
    current_user: dict = Depends(get_current_user),
):
    org_id = current_user.organization_id
    excel_bytes, filename = service.get_parents_excel(block_id, org_id)
    return StreamingResponse(
        BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── Auto-link (automatic cascade / aggregation) ─────────────────────────────


@router.post(
    "/blocks/{block_id}/auto-link",
    response_model=QSealAutoLinkResponse,
    summary="Auto-link a completed block's items into master packs (cascade)",
)
def auto_link_block(
    block_id: UUID,
    data: QSealAutoLinkRequest | None = Body(default=None),
    service: QSealService = Depends(get_service),
    current_user: CurrentUser = Depends(require_permission("qr_product.create")),
):
    """Automatically group a block's generated units into master packs.

    Useful for bulk testing where manual linking/cascading via mobile is slow.
    Re-running is idempotent: previous linkage is removed and rebuilt.
    """
    org_id = current_user.organization_id
    return service.auto_link_block(
        block_id,
        org_id,
        current_user.id,
        data.master_pack_size if data else None,
    )


# ── Aggregation log ─────────────────────────────────────────────────────────


@router.get(
    "/aggregation",
    response_model=QSealAggregationResponse,
    summary="List QSeal aggregation (cascading) log",
)
def list_aggregation(
    block_id: UUID | None = Query(
        None, description="Filter the log to a specific QR block/batch"
    ),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    service: QSealService = Depends(get_service),
    current_user: dict = Depends(get_current_user),
):
    """Return one row per generated unit with its parent link + activation.

    Lets operators spot wrong links or missing aggregations at batch level.
    """
    org_id = current_user.organization_id
    return service.list_aggregation(org_id, block_id, page, page_size)
