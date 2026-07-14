"""Charge Templates API endpoints"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentUser, get_current_active_user
from app.schemas.charge_template import (
    ChargeTemplateCreate,
    ChargeTemplateListItem,
    ChargeTemplateListResponse,
    ChargeTemplateResponse,
    ChargeTemplateUpdate,
)
from app.services.charge_template_service import ChargeTemplateService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "",
    response_model=ChargeTemplateListResponse,
    summary="List charge templates",
    description="Get paginated list of charge templates with optional filters",
)
async def list_charge_templates(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    charge_type: str | None = Query(
        None,
        description="Filter by charge type: Shipping, Handling, Packaging, Insurance, Custom",
    ),
    is_active: bool | None = Query(None, description="Filter by active status"),
    search: str | None = Query(None, description="Search in template code and name"),
    sort_by: str = Query("created_at", description="Field to sort by"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="Sort order"),
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    List charge templates with pagination and filters.

    **Query Parameters:**
    - **page**: Page number (default: 1)
    - **page_size**: Items per page (default: 20, max: 100)
    - **charge_type**: Filter by type (Shipping, Handling, Packaging, Insurance, Custom)
    - **is_active**: Filter by active status
    - **search**: Search in template code and name
    - **sort_by**: Field to sort by (default: created_at)
    - **sort_order**: asc or desc (default: desc)
    """
    service = ChargeTemplateService(db)
    templates, pagination = service.list_templates(
        organization_id=current_user.organization_id,
        filters={
            "page": page,
            "page_size": page_size,
            "charge_type": charge_type,
            "is_active": is_active,
            "search": search,
            "sort_by": sort_by,
            "sort_order": sort_order,
        },
    )
    return ChargeTemplateListResponse(
        charge_templates=[ChargeTemplateListItem(**t) for t in templates],
        pagination=pagination,
    )


@router.post(
    "",
    response_model=ChargeTemplateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create charge template",
    description="Create a new charge template",
)
async def create_charge_template(
    data: ChargeTemplateCreate,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Create a new charge template.

    **Request Body:**
    - **template_code**: Unique code (required)
    - **template_name**: Display name (required)
    - **charge_type**: Shipping | Handling | Packaging | Insurance | Custom (required)
    - **calculation_method**: FIXED | PERCENTAGE (required)
    - **fixed_amount**: Required when calculation_method=FIXED
    - **percentage_rate**: Required when calculation_method=PERCENTAGE
    - **base_on**: Net_Total | Grand_Total — required when calculation_method=PERCENTAGE
    - **account_head_id**: GL account UUID (required)
    """
    service = ChargeTemplateService(db)
    payload = data.model_dump()
    payload["organization_id"] = current_user.organization_id

    try:
        template = service.create_template(payload, user_id=current_user.id)
        return ChargeTemplateResponse(**template)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.get(
    "/{template_id}",
    response_model=ChargeTemplateResponse,
    summary="Get charge template",
    description="Get charge template details by ID",
)
async def get_charge_template(
    template_id: UUID,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get charge template by ID."""
    from app.core.exceptions import ResourceNotFoundException

    service = ChargeTemplateService(db)
    try:
        template = service.get_template(template_id, current_user.organization_id)
        return ChargeTemplateResponse(**template)
    except ResourceNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.put(
    "/{template_id}",
    response_model=ChargeTemplateResponse,
    summary="Update charge template",
    description="Update an existing charge template",
)
async def update_charge_template(
    template_id: UUID,
    data: ChargeTemplateUpdate,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Update a charge template."""
    from app.core.exceptions import ResourceNotFoundException

    service = ChargeTemplateService(db)
    payload = data.model_dump(exclude_unset=True)
    payload["organization_id"] = current_user.organization_id

    try:
        template = service.update_template(template_id, payload, user_id=current_user.id)
        return ChargeTemplateResponse(**template)
    except ResourceNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.delete(
    "/{template_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete charge template",
    description="Soft delete a charge template",
)
async def delete_charge_template(
    template_id: UUID,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Soft delete a charge template. Fails if referenced by transactions."""
    from app.core.exceptions import ResourceNotFoundException

    service = ChargeTemplateService(db)
    try:
        service.delete_template(template_id, current_user.organization_id)
    except ResourceNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    return None
