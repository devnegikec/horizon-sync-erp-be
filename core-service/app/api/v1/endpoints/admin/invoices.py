"""Admin invoice management endpoints.

GET    /admin/invoices          — cross-org paginated list with org_id, status, date range filters
GET    /admin/invoices/{id}     — detail with line items + payment history
POST   /admin/invoices          — create invoice in specified org
POST   /admin/invoices/{id}/send — send invoice via email
"""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentUser, require_admin
from app.schemas.admin_invoice import AdminInvoiceListResponse
from app.schemas.invoice import InvoiceCreate, InvoiceResponse
from app.services.admin_invoice_service import AdminInvoiceService

router = APIRouter()
security = HTTPBearer()


@router.get("", response_model=AdminInvoiceListResponse)
async def list_invoices(
    organization_id: UUID | None = Query(None, description="Filter by organization"),
    status: str | None = Query(None, description="Filter by invoice status"),
    date_from: datetime | None = Query(None, description="Filter invoices from this date"),
    date_to: datetime | None = Query(None, description="Filter invoices up to this date"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_admin),
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> AdminInvoiceListResponse:
    """Return a paginated list of invoices from customer organizations linked to the master organization."""
    service = AdminInvoiceService(db, token=credentials.credentials)
    return await service.list_invoices(
        organization_id=organization_id,
        status_filter=status,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
        current_user_org=current_user.organization_id,
    )


@router.get("/{invoice_id}")
async def get_invoice(
    invoice_id: UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_admin),
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """Return full invoice detail with line items and payment history."""
    service = AdminInvoiceService(db, token=credentials.credentials)
    return service.get_invoice(invoice_id)


@router.post("", response_model=InvoiceResponse, status_code=201)
async def create_invoice(
    body: InvoiceCreate,
    organization_id: UUID = Query(..., description="Organization to create the invoice in"),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_admin),
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> InvoiceResponse:
    """Create an invoice in the specified organization."""
    service = AdminInvoiceService(db, token=credentials.credentials)
    data = service.create_invoice(
        data=body.model_dump(),
        organization_id=organization_id,
        user_id=current_user.id,
    )
    return InvoiceResponse.model_validate(data)


@router.post("/{invoice_id}/send")
async def send_invoice(
    invoice_id: UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_admin),
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """Send an invoice to the party's email and update status to pending."""
    service = AdminInvoiceService(db, token=credentials.credentials)
    return await service.send_invoice(invoice_id, current_user.id)
