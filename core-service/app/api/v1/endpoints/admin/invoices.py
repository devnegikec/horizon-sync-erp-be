"""Admin invoice management endpoints.

GET    /admin/invoices          — cross-org paginated list with org_id, status, date range filters
GET    /admin/invoices/{id}     — detail with line items + payment history
POST   /admin/invoices          — create invoice in specified org
POST   /admin/invoices/{id}/send — send invoice via email
"""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentUser, require_admin
from app.schemas.admin_invoice import AdminInvoiceListResponse, AdminInvoiceStatsResponse, SendReminderRequest
from app.schemas.invoice import InvoiceCreate, InvoiceResponse
from app.services.admin_invoice_service import AdminInvoiceService

router = APIRouter()


@router.get("", response_model=AdminInvoiceListResponse)
async def list_invoices(
    organization_id: UUID | None = Query(None, description="Filter by organization"),
    status: str | None = Query(None, description="Filter by invoice status"),
    date_from: datetime | None = Query(None, description="Filter invoices from this date"),
    date_to: datetime | None = Query(None, description="Filter invoices up to this date"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    _current_user: CurrentUser = Depends(require_admin),
) -> AdminInvoiceListResponse:
    """Return a paginated list of invoices across all organizations."""
    service = AdminInvoiceService(db)
    return service.list_invoices(
        organization_id=organization_id,
        status_filter=status,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
    )


@router.get("/stats", response_model=AdminInvoiceStatsResponse)
async def get_invoice_stats(
    organization_id: UUID | None = Query(None, description="Scope stats to a single organization"),
    db: Session = Depends(get_db),
    _current_user: CurrentUser = Depends(require_admin),
) -> AdminInvoiceStatsResponse:
    """Return aggregated invoice statistics across all organizations."""
    service = AdminInvoiceService(db)
    return service.get_stats(organization_id=organization_id)


@router.get("/{invoice_id}")
async def get_invoice(
    invoice_id: UUID,
    db: Session = Depends(get_db),
    _current_user: CurrentUser = Depends(require_admin),
) -> dict:
    """Return full invoice detail with line items and payment history."""
    service = AdminInvoiceService(db)
    return service.get_invoice(invoice_id)


@router.post("", response_model=InvoiceResponse, status_code=201)
async def create_invoice(
    body: InvoiceCreate,
    organization_id: UUID = Query(..., description="Organization to create the invoice in"),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_admin),
) -> InvoiceResponse:
    """Create an invoice in the specified organization."""
    service = AdminInvoiceService(db)
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
) -> dict:
    """Send an invoice to the party's email and update status to pending."""
    service = AdminInvoiceService(db)
    return await service.send_invoice(invoice_id, current_user.id)


@router.post("/{invoice_id}/send-reminder")
async def send_reminder(
    invoice_id: UUID,
    body: SendReminderRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_admin),
) -> dict:
    """Send an overdue payment reminder email for an invoice."""
    service = AdminInvoiceService(db)
    return await service.send_reminder(invoice_id, body, current_user.id)
