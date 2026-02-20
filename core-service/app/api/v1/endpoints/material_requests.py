"""Material Requests API endpoints"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentUser, require_permission
from app.schemas.common import PaginationMeta
from app.schemas.material_request import (
    MaterialRequestCreate,
    MaterialRequestListItem,
    MaterialRequestListResponse,
    MaterialRequestResponse,
    MaterialRequestUpdate,
    WorkflowStatusResponse,
)
from app.services.material_request_service import MaterialRequestService

router = APIRouter()

# Permission constants (to be defined in authorization module)
MATERIAL_REQUEST_CREATE = "material_request.create"
MATERIAL_REQUEST_READ = "material_request.read"
MATERIAL_REQUEST_UPDATE = "material_request.update"


@router.post(
    "", response_model=MaterialRequestResponse, status_code=status.HTTP_201_CREATED
)
async def create_material_request(
    body: MaterialRequestCreate,
    current_user: CurrentUser = Depends(require_permission(MATERIAL_REQUEST_CREATE)),
    db: Session = Depends(get_db),
):
    """Create Material Request. Requires material_request.create."""
    svc = MaterialRequestService(db)
    data = svc.create(body.model_dump(), current_user.organization_id, current_user.id)
    return MaterialRequestResponse.model_validate(data)


@router.get("", response_model=MaterialRequestListResponse)
async def list_material_requests(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = Query(
        None,
        pattern="^(DRAFT|SUBMITTED|PARTIALLY_QUOTED|FULLY_QUOTED|CANCELLED|draft|submitted|partially_quoted|fully_quoted|cancelled)$",
    ),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    search: str | None = Query(None, description="Search in title or description"),
    current_user: CurrentUser = Depends(require_permission(MATERIAL_REQUEST_READ)),
    db: Session = Depends(get_db),
):
    """List Material Requests. Requires material_request.read."""
    svc = MaterialRequestService(db)
    items, pagination = svc.get_list(
        organization_id=current_user.organization_id,
        page=page,
        page_size=page_size,
        status=status.upper() if status else None,
        sort_by=sort_by,
        sort_order=sort_order,
        search=search,
    )
    return MaterialRequestListResponse(
        material_requests=[MaterialRequestListItem.model_validate(x) for x in items],
        pagination=PaginationMeta(**pagination),
    )


@router.get("/{material_request_id}", response_model=MaterialRequestResponse)
async def get_material_request(
    material_request_id: UUID,
    current_user: CurrentUser = Depends(require_permission(MATERIAL_REQUEST_READ)),
    db: Session = Depends(get_db),
):
    """Get Material Request by ID. Requires material_request.read."""
    svc = MaterialRequestService(db)
    data = svc.get_by_id(material_request_id, current_user.organization_id)
    return MaterialRequestResponse.model_validate(data)


@router.get("/{material_request_id}/workflow", response_model=WorkflowStatusResponse)
async def get_workflow_status(
    material_request_id: UUID,
    current_user: CurrentUser = Depends(require_permission(MATERIAL_REQUEST_READ)),
    db: Session = Depends(get_db),
):
    """
    Get complete workflow status for a Material Request.
    
    Traces the full sourcing flow: MR → RFQs → Purchase Orders → Receipts → Invoices → Payments.
    Requires material_request.read permission.
    """
    svc = MaterialRequestService(db)
    data = svc.get_workflow_status(material_request_id, current_user.organization_id)
    return WorkflowStatusResponse.model_validate(data)


@router.put("/{material_request_id}", response_model=MaterialRequestResponse)
async def update_material_request(
    material_request_id: UUID,
    body: MaterialRequestUpdate,
    current_user: CurrentUser = Depends(require_permission(MATERIAL_REQUEST_UPDATE)),
    db: Session = Depends(get_db),
):
    """Update Material Request (DRAFT only). Requires material_request.update."""
    svc = MaterialRequestService(db)
    data = svc.update(
        material_request_id,
        body.model_dump(exclude_unset=True),
        current_user.organization_id,
        current_user.id,
    )
    return MaterialRequestResponse.model_validate(data)


@router.delete("/{material_request_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_material_request(
    material_request_id: UUID,
    current_user: CurrentUser = Depends(require_permission(MATERIAL_REQUEST_UPDATE)),
    db: Session = Depends(get_db),
):
    """Delete Material Request (DRAFT only). Requires material_request.update."""
    svc = MaterialRequestService(db)
    svc.delete(material_request_id, current_user.organization_id)
    return None


@router.post(
    "/{material_request_id}/submit",
    response_model=MaterialRequestResponse,
)
async def submit_material_request(
    material_request_id: UUID,
    current_user: CurrentUser = Depends(require_permission(MATERIAL_REQUEST_UPDATE)),
    db: Session = Depends(get_db),
):
    """Submit Material Request. Requires material_request.update."""
    svc = MaterialRequestService(db)
    data = svc.submit(
        material_request_id,
        current_user.organization_id,
        current_user.id,
    )
    return MaterialRequestResponse.model_validate(data)


@router.post(
    "/{material_request_id}/cancel",
    response_model=MaterialRequestResponse,
)
async def cancel_material_request(
    material_request_id: UUID,
    current_user: CurrentUser = Depends(require_permission(MATERIAL_REQUEST_UPDATE)),
    db: Session = Depends(get_db),
):
    """Cancel Material Request. Requires material_request.update."""
    svc = MaterialRequestService(db)
    data = svc.cancel(
        material_request_id,
        current_user.organization_id,
        current_user.id,
    )
    return MaterialRequestResponse.model_validate(data)
