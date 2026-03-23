"""Warranty API endpoints"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentUser, get_current_active_user, require_permission
from app.schemas.warranty import (
    WarrantyCheckResponse,
    WarrantyListResponse,
    WarrantyPeriodCreate,
    WarrantyPeriodResponse,
    WarrantyRegisterRequest,
    WarrantyResponse,
)
from app.services.warranty_service import WarrantyService

router = APIRouter()


# ── Warranty Periods (admin) ──────────────────────────────────────────────────

@router.post(
    "/periods",
    response_model=WarrantyPeriodResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create warranty period",
)
async def create_warranty_period(
    data: WarrantyPeriodCreate,
    current_user: CurrentUser = Depends(require_permission("warranty.create")),
    db: Session = Depends(get_db),
):
    svc = WarrantyService(db)
    period = svc.create_period(data, current_user.organization_id)
    return WarrantyPeriodResponse.model_validate(period)


@router.get(
    "/periods",
    response_model=list[WarrantyPeriodResponse],
    summary="List warranty periods",
)
async def list_warranty_periods(
    current_user: CurrentUser = Depends(require_permission("warranty.read")),
    db: Session = Depends(get_db),
):
    svc = WarrantyService(db)
    periods = svc.list_periods(current_user.organization_id)
    return [WarrantyPeriodResponse.model_validate(p) for p in periods]


# ── Warranty Registration (public) ────────────────────────────────────────────

@router.post(
    "/register",
    response_model=WarrantyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register warranty",
    description=(
        "Public endpoint. Consumer registers warranty by providing serial number "
        "and contact details. Warranty duration is resolved from the product config "
        "or the org's default warranty period."
    ),
)
async def register_warranty(
    organization_id: UUID,
    req: WarrantyRegisterRequest,
    db: Session = Depends(get_db),
):
    svc = WarrantyService(db)
    warranty = svc.register(organization_id, req)
    return WarrantyResponse.model_validate(warranty)


# ── Warranty Check (public) ───────────────────────────────────────────────────

@router.get(
    "/check",
    response_model=WarrantyCheckResponse,
    summary="Check warranty by serial number",
    description="Public endpoint. Look up warranty status for a serial number.",
)
async def check_warranty(
    organization_id: UUID,
    serial_number: str = Query(..., description="Product serial number"),
    db: Session = Depends(get_db),
):
    svc = WarrantyService(db)
    result = svc.check_by_serial(serial_number, organization_id)
    return WarrantyCheckResponse(**result)


@router.get(
    "/search",
    response_model=list[WarrantyCheckResponse],
    summary="Search warranties by mobile number",
    description="Public endpoint. Find all warranties registered to a mobile number.",
)
async def search_warranty_by_mobile(
    organization_id: UUID,
    mobile: str = Query(..., description="Customer mobile number"),
    db: Session = Depends(get_db),
):
    svc = WarrantyService(db)
    results = svc.search_by_mobile(mobile, organization_id)
    return [WarrantyCheckResponse(**r) for r in results]


# ── Warranty List (authenticated) ─────────────────────────────────────────────

@router.get(
    "",
    response_model=WarrantyListResponse,
    summary="List all warranties",
)
async def list_warranties(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None, description="Search by serial, mobile, or name"),
    current_user: CurrentUser = Depends(require_permission("warranty.read")),
    db: Session = Depends(get_db),
):
    svc = WarrantyService(db)
    warranties, pagination = svc.list_warranties(
        current_user.organization_id, page, page_size, search
    )
    return WarrantyListResponse(
        warranties=[WarrantyResponse.model_validate(w) for w in warranties],
        pagination=pagination,
    )
