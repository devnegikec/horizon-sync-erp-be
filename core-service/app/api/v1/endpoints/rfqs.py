"""RFQ (Request for Quotation) API endpoints"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentUser, require_permission
from app.schemas.common import PaginationMeta
from app.schemas.rfq import (
    RecordQuoteRequest,
    RFQCreate,
    RFQListItem,
    RFQListResponse,
    RFQResponse,
    RFQUpdate,
)
from app.services.rfq_service import RFQService

router = APIRouter()

# Permission constants (to be defined in authorization module)
RFQ_CREATE = "rfq.create"
RFQ_READ = "rfq.read"
RFQ_UPDATE = "rfq.update"


@router.post("", response_model=RFQResponse, status_code=status.HTTP_201_CREATED)
async def create_rfq(
    body: RFQCreate,
    current_user: CurrentUser = Depends(require_permission(RFQ_CREATE)),
    db: Session = Depends(get_db),
):
    """
    Create new RFQ.

    Can be created from a Material Request or standalone.
    Requires rfq.create permission.
    """
    svc = RFQService(db)

    # If material_request_id is provided, create from Material Request
    if body.material_request_id:
        data = svc.create_from_material_request(
            material_request_id=body.material_request_id,
            closing_date=body.closing_date,
            supplier_ids=body.supplier_ids,
            organization_id=current_user.organization_id,
            user_id=current_user.id,
        )
    else:
        # Create standalone RFQ (not implemented in service yet, but schema supports it)
        raise NotImplementedError("Standalone RFQ creation not yet implemented")

    return RFQResponse.model_validate(data)


@router.get("", response_model=RFQListResponse)
async def list_rfqs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = Query(
        None,
        pattern="^(DRAFT|SENT|PARTIALLY_RESPONDED|FULLY_RESPONDED|CLOSED|draft|sent|partially_responded|fully_responded|closed)$",
    ),
    material_request_id: UUID | None = Query(
        None, description="Filter by Material Request ID"
    ),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    search: str | None = Query(None, description="Search in RFQ details"),
    current_user: CurrentUser = Depends(require_permission(RFQ_READ)),
    db: Session = Depends(get_db),
):
    """
    List RFQs with pagination.

    Supports filtering by status, material_request_id, sorting, and search.
    Requires rfq.read permission.
    """
    svc = RFQService(db)
    items, pagination = svc.get_list(
        organization_id=current_user.organization_id,
        page=page,
        page_size=page_size,
        status=status.upper() if status else None,
        material_request_id=material_request_id,
        sort_by=sort_by,
        sort_order=sort_order,
        search=search,
    )
    return RFQListResponse(
        rfqs=[RFQListItem.model_validate(x) for x in items],
        pagination=PaginationMeta(**pagination),
    )


@router.get("/{rfq_id}", response_model=RFQResponse)
async def get_rfq(
    rfq_id: UUID,
    current_user: CurrentUser = Depends(require_permission(RFQ_READ)),
    db: Session = Depends(get_db),
):
    """
    Retrieve RFQ by ID.

    Returns complete RFQ details including line items, suppliers, and quotes.
    Requires rfq.read permission.
    """
    svc = RFQService(db)
    data = svc.get_by_id(rfq_id, current_user.organization_id)
    return RFQResponse.model_validate(data)


@router.put("/{rfq_id}", response_model=RFQResponse)
async def update_rfq(
    rfq_id: UUID,
    body: RFQUpdate,
    current_user: CurrentUser = Depends(require_permission(RFQ_UPDATE)),
    db: Session = Depends(get_db),
):
    """
    Update RFQ (DRAFT only).

    Only RFQs in DRAFT status can be modified.
    Requires rfq.update permission.
    """
    svc = RFQService(db)
    data = svc.update(
        rfq_id,
        body.model_dump(exclude_unset=True),
        current_user.organization_id,
        current_user.id,
    )
    return RFQResponse.model_validate(data)


@router.delete("/{rfq_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rfq(
    rfq_id: UUID,
    current_user: CurrentUser = Depends(require_permission(RFQ_UPDATE)),
    db: Session = Depends(get_db),
):
    """
    Delete RFQ (DRAFT only).

    Only RFQs in DRAFT status can be deleted.
    Requires rfq.update permission.
    """
    svc = RFQService(db)
    svc.delete(rfq_id, current_user.organization_id)
    return None


@router.post("/{rfq_id}/send", response_model=RFQResponse)
async def send_rfq(
    rfq_id: UUID,
    current_user: CurrentUser = Depends(require_permission(RFQ_UPDATE)),
    db: Session = Depends(get_db),
):
    """
    Send RFQ to suppliers.

    Changes status from DRAFT to SENT.
    Requires rfq.update permission.
    """
    svc = RFQService(db)
    data = svc.send(rfq_id, current_user.organization_id, current_user.id)
    return RFQResponse.model_validate(data)


@router.post("/{rfq_id}/quotes", response_model=RFQResponse)
async def record_quote(
    rfq_id: UUID,
    body: RecordQuoteRequest,
    current_user: CurrentUser = Depends(require_permission(RFQ_UPDATE)),
    db: Session = Depends(get_db),
):
    """
    Record supplier quote for an RFQ line item.

    Validates RFQ line and supplier association.
    Automatically updates RFQ status based on quote completeness.
    Requires rfq.update permission.
    """
    svc = RFQService(db)
    data = svc.record_quote(
        rfq_id=rfq_id,
        rfq_line_id=body.rfq_line_id,
        supplier_id=body.supplier_id,
        quoted_price=body.quoted_price,
        quoted_delivery_date=body.quoted_delivery_date,
        supplier_notes=body.supplier_notes,
        organization_id=current_user.organization_id,
    )
    return RFQResponse.model_validate(data)


@router.post("/{rfq_id}/close", response_model=RFQResponse)
async def close_rfq(
    rfq_id: UUID,
    current_user: CurrentUser = Depends(require_permission(RFQ_UPDATE)),
    db: Session = Depends(get_db),
):
    """
    Close RFQ.

    Changes status to CLOSED.
    Requires rfq.update permission.
    """
    svc = RFQService(db)
    data = svc.close(rfq_id, current_user.organization_id, current_user.id)
    return RFQResponse.model_validate(data)
