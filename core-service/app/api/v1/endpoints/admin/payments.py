"""Admin payment tracking endpoints.

GET /admin/payments — cross-org paginated list with org_id, status filters
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentUser, require_admin
from app.schemas.admin_invoice import AdminPaymentListResponse
from app.services.admin_payment_service import AdminPaymentService

router = APIRouter()


@router.get("", response_model=AdminPaymentListResponse)
async def list_payments(
    organization_id: UUID | None = Query(None, description="Filter by organization"),
    status: str | None = Query(None, description="Filter by payment status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    _current_user: CurrentUser = Depends(require_admin),
) -> AdminPaymentListResponse:
    """Return a paginated list of payments across all organizations."""
    service = AdminPaymentService(db)
    return service.list_payments(
        organization_id=organization_id,
        status_filter=status,
        page=page,
        page_size=page_size,
    )
