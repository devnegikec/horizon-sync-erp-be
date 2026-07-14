"""Quality inspection templates and inspections API endpoints (Phase 4)"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.authorization import (
    QUALITY_INSPECTION_CREATE,
    QUALITY_INSPECTION_DELETE,
    QUALITY_INSPECTION_READ,
    QUALITY_INSPECTION_UPDATE,
)
from app.database import get_db
from app.dependencies import CurrentUser, require_permission
from app.schemas.common import PaginationMeta
from app.schemas.quality_inspection import (
    QualityInspectionCreate,
    QualityInspectionListItem,
    QualityInspectionListResponse,
    QualityInspectionResponse,
    QualityInspectionTemplateCreate,
    QualityInspectionTemplateListItem,
    QualityInspectionTemplateListResponse,
    QualityInspectionTemplateResponse,
    QualityInspectionTemplateUpdate,
    QualityInspectionUpdate,
)
from app.services.quality_inspection_service import (
    QualityInspectionService,
    QualityInspectionTemplateService,
)

router = APIRouter()


# ----- Quality Inspection Templates -----
@router.post(
    "/templates",
    response_model=QualityInspectionTemplateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create quality inspection template",
)
async def create_quality_inspection_template(
    body: QualityInspectionTemplateCreate,
    current_user: CurrentUser = Depends(require_permission(QUALITY_INSPECTION_CREATE)),
    db: Session = Depends(get_db),
):
    """Create a quality inspection template. Requires quality_inspection.create."""
    svc = QualityInspectionTemplateService(db)
    data = svc.create(
        body.model_dump(),
        organization_id=current_user.organization_id,
        user_id=current_user.id,
    )
    return QualityInspectionTemplateResponse.model_validate(data)


@router.get(
    "/templates",
    response_model=QualityInspectionTemplateListResponse,
    summary="List quality inspection templates",
)
async def list_quality_inspection_templates(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    inspection_type: str | None = Query(
        None, pattern="^(incoming|outgoing|in_process)$"
    ),
    is_active: bool | None = None,
    search: str | None = None,
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    current_user: CurrentUser = Depends(require_permission(QUALITY_INSPECTION_READ)),
    db: Session = Depends(get_db),
):
    """List quality inspection templates. Requires quality_inspection.read."""
    svc = QualityInspectionTemplateService(db)
    items, pagination = svc.get_list(
        organization_id=current_user.organization_id,
        page=page,
        page_size=page_size,
        inspection_type=inspection_type,
        is_active=is_active,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return QualityInspectionTemplateListResponse(
        templates=[QualityInspectionTemplateListItem.model_validate(x) for x in items],
        pagination=PaginationMeta(**pagination),
    )


@router.get(
    "/templates/{template_id}",
    response_model=QualityInspectionTemplateResponse,
    summary="Get quality inspection template",
)
async def get_quality_inspection_template(
    template_id: UUID,
    current_user: CurrentUser = Depends(require_permission(QUALITY_INSPECTION_READ)),
    db: Session = Depends(get_db),
):
    """Get template by ID. Requires quality_inspection.read."""
    svc = QualityInspectionTemplateService(db)
    data = svc.get_by_id(template_id, current_user.organization_id)
    return QualityInspectionTemplateResponse.model_validate(data)


@router.put(
    "/templates/{template_id}",
    response_model=QualityInspectionTemplateResponse,
    summary="Update quality inspection template",
)
async def update_quality_inspection_template(
    template_id: UUID,
    body: QualityInspectionTemplateUpdate,
    current_user: CurrentUser = Depends(require_permission(QUALITY_INSPECTION_UPDATE)),
    db: Session = Depends(get_db),
):
    """Update template. Requires quality_inspection.update."""
    svc = QualityInspectionTemplateService(db)
    data = svc.update(
        template_id,
        body.model_dump(exclude_unset=True),
        organization_id=current_user.organization_id,
        user_id=current_user.id,
    )
    return QualityInspectionTemplateResponse.model_validate(data)


@router.delete(
    "/templates/{template_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete quality inspection template",
)
async def delete_quality_inspection_template(
    template_id: UUID,
    current_user: CurrentUser = Depends(require_permission(QUALITY_INSPECTION_DELETE)),
    db: Session = Depends(get_db),
):
    """Delete template. Requires quality_inspection.delete."""
    svc = QualityInspectionTemplateService(db)
    svc.delete(template_id, current_user.organization_id)
    return None


# ----- Quality Inspections -----
@router.post(
    "",
    response_model=QualityInspectionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create quality inspection",
)
async def create_quality_inspection(
    body: QualityInspectionCreate,
    current_user: CurrentUser = Depends(require_permission(QUALITY_INSPECTION_CREATE)),
    db: Session = Depends(get_db),
):
    """Create a quality inspection. Requires quality_inspection.create."""
    svc = QualityInspectionService(db)
    data = svc.create(
        body.model_dump(),
        organization_id=current_user.organization_id,
        user_id=current_user.id,
    )
    return QualityInspectionResponse.model_validate(data)


@router.get(
    "",
    response_model=QualityInspectionListResponse,
    summary="List quality inspections",
)
async def list_quality_inspections(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    item_id: UUID | None = None,
    status: str | None = Query(None, pattern="^(pending|accepted|rejected)$"),
    inspection_type: str | None = Query(
        None, pattern="^(incoming|outgoing|in_process)$"
    ),
    search: str | None = None,
    sort_by: str = Query("inspection_date"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    current_user: CurrentUser = Depends(require_permission(QUALITY_INSPECTION_READ)),
    db: Session = Depends(get_db),
):
    """List quality inspections. Requires quality_inspection.read."""
    svc = QualityInspectionService(db)
    items, pagination = svc.get_list(
        organization_id=current_user.organization_id,
        page=page,
        page_size=page_size,
        item_id=item_id,
        status=status,
        inspection_type=inspection_type,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return QualityInspectionListResponse(
        inspections=[QualityInspectionListItem.model_validate(x) for x in items],
        pagination=PaginationMeta(**pagination),
    )


@router.get(
    "/{inspection_id}",
    response_model=QualityInspectionResponse,
    summary="Get quality inspection",
)
async def get_quality_inspection(
    inspection_id: UUID,
    current_user: CurrentUser = Depends(require_permission(QUALITY_INSPECTION_READ)),
    db: Session = Depends(get_db),
):
    """Get inspection by ID. Requires quality_inspection.read."""
    svc = QualityInspectionService(db)
    data = svc.get_by_id(inspection_id, current_user.organization_id)
    return QualityInspectionResponse.model_validate(data)


@router.put(
    "/{inspection_id}",
    response_model=QualityInspectionResponse,
    summary="Update quality inspection",
)
async def update_quality_inspection(
    inspection_id: UUID,
    body: QualityInspectionUpdate,
    current_user: CurrentUser = Depends(require_permission(QUALITY_INSPECTION_UPDATE)),
    db: Session = Depends(get_db),
):
    """Update inspection. Requires quality_inspection.update."""
    svc = QualityInspectionService(db)
    data = svc.update(
        inspection_id,
        body.model_dump(exclude_unset=True),
        organization_id=current_user.organization_id,
        user_id=current_user.id,
    )
    return QualityInspectionResponse.model_validate(data)


@router.delete(
    "/{inspection_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete quality inspection",
)
async def delete_quality_inspection(
    inspection_id: UUID,
    current_user: CurrentUser = Depends(require_permission(QUALITY_INSPECTION_DELETE)),
    db: Session = Depends(get_db),
):
    """Delete inspection. Requires quality_inspection.delete."""
    svc = QualityInspectionService(db)
    svc.delete(inspection_id, current_user.organization_id)
    return None
