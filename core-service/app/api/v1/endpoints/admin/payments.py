"""Admin payment tracking endpoints.

GET /admin/payments — cross-org paginated list with org_id, status filters
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentUser, require_admin
from app.schemas.admin_invoice import AdminPaymentListResponse
from app.services.admin_payment_service import AdminPaymentService

router = APIRouter()
security = HTTPBearer()


@router.get("", response_model=AdminPaymentListResponse)
async def list_payments(
    organization_id: UUID | None = Query(None, description="Filter by organization"),
    status: str | None = Query(None, description="Filter by payment status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_admin),
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> AdminPaymentListResponse:
    """Return a paginated list of payments from the master organization."""
    service = AdminPaymentService(db, token=credentials.credentials)
    return await service.list_payments(
        organization_id=organization_id,
        status_filter=status,
        page=page,
        page_size=page_size,
        current_user_org=current_user.organization_id,
    )
